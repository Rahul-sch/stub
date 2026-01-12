#!/usr/bin/env python3
"""
Ketchup Factory Sensor Data Consumer

Consumes ketchup-specific sensor data from Kafka,
performs anomaly detection, and stores in PostgreSQL.
Broadcasts real-time updates via dashboard API.

100% PARALLEL to existing consumer.py - does NOT modify original system.
"""

import os
import sys
import json
import logging
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import requests
import psycopg2
from psycopg2.extras import Json
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
import numpy as np
from sklearn.ensemble import IsolationForest

# ============================================================================
# CONFIGURATION
# ============================================================================

KAFKA_BOOTSTRAP = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = 'ketchup-sensor-data'
KAFKA_GROUP = 'ketchup-consumer-group'

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/rig_alpha')

DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://localhost:5000')
TELEMETRY_ENDPOINT = f'{DASHBOARD_URL}/api/internal/ketchup-telemetry-update'

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [KETCHUP-CONSUMER] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# KETCHUP SENSOR THRESHOLDS
# ============================================================================

KETCHUP_THRESHOLDS = {
    'fill_level': {'low': 88.0, 'high': 98.0, 'critical_low': 85.0, 'critical_high': 100.0},
    'viscosity': {'low': 2800.0, 'high': 4200.0, 'critical_low': 2500.0, 'critical_high': 4500.0},
    'sauce_temp': {'low': 145.0, 'high': 180.0, 'critical_low': 140.0, 'critical_high': 185.0},
    'cap_torque': {'low': 1.8, 'high': 3.2, 'critical_low': 1.5, 'critical_high': 3.5},
    'bottle_flow_rate': {'low': 90.0, 'high': 180.0, 'critical_low': 80.0, 'critical_high': 200.0},
    'label_alignment': {'low': -3.0, 'high': 3.0, 'critical_low': -5.0, 'critical_high': 5.0}
}

SENSOR_COLUMNS = ['fill_level', 'viscosity', 'sauce_temp', 'cap_torque', 'bottle_flow_rate', 'label_alignment']

# ============================================================================
# ANOMALY DETECTOR
# ============================================================================

class KetchupAnomalyDetector:
    """
    ML-based anomaly detection for ketchup production lines.
    Uses Isolation Forest + rule-based thresholds.
    """

    def __init__(self):
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.1,
            random_state=42,
            n_jobs=-1
        )
        self.is_fitted = False
        self.training_buffer: List[List[float]] = []
        self.min_training_samples = 500
        self.lock = threading.Lock()

    def _extract_features(self, data: Dict[str, Any]) -> List[float]:
        """Extract ML features from sensor reading."""
        return [
            data.get('fill_level', 95.0),
            data.get('viscosity', 3500.0),
            data.get('sauce_temp', 165.0),
            data.get('cap_torque', 2.5),
            data.get('bottle_flow_rate', 150.0),
            abs(data.get('label_alignment', 0.0))  # Use absolute for ML
        ]

    def _rule_based_check(self, data: Dict[str, Any]) -> tuple[float, Optional[str]]:
        """
        Rule-based anomaly detection using thresholds.
        Returns (score, anomaly_type).
        """
        max_score = 0.0
        anomaly_type = None

        for sensor, thresholds in KETCHUP_THRESHOLDS.items():
            value = data.get(sensor)
            if value is None:
                continue

            # Handle label_alignment specially (check absolute value)
            if sensor == 'label_alignment':
                value = abs(value)
                check_value = value
            else:
                check_value = value

            # Critical violation
            if sensor == 'label_alignment':
                if check_value > abs(thresholds['critical_high']):
                    score = 1.0
                    if score > max_score:
                        max_score = score
                        anomaly_type = 'label_misalign'
                elif check_value > abs(thresholds['high']):
                    score = 0.6 + (check_value - abs(thresholds['high'])) / (abs(thresholds['critical_high']) - abs(thresholds['high'])) * 0.4
                    if score > max_score:
                        max_score = score
                        anomaly_type = 'label_misalign'
            else:
                if check_value < thresholds['critical_low']:
                    score = 1.0
                    if score > max_score:
                        max_score = score
                        anomaly_type = self._get_anomaly_type(sensor, 'low')
                elif check_value > thresholds['critical_high']:
                    score = 1.0
                    if score > max_score:
                        max_score = score
                        anomaly_type = self._get_anomaly_type(sensor, 'high')
                # Warning zone
                elif check_value < thresholds['low']:
                    score = 0.5 + (thresholds['low'] - check_value) / (thresholds['low'] - thresholds['critical_low']) * 0.5
                    if score > max_score:
                        max_score = score
                        anomaly_type = self._get_anomaly_type(sensor, 'low')
                elif check_value > thresholds['high']:
                    score = 0.5 + (check_value - thresholds['high']) / (thresholds['critical_high'] - thresholds['high']) * 0.5
                    if score > max_score:
                        max_score = score
                        anomaly_type = self._get_anomaly_type(sensor, 'high')

        return max_score, anomaly_type

    def _get_anomaly_type(self, sensor: str, direction: str) -> str:
        """Map sensor + direction to anomaly type."""
        mapping = {
            ('fill_level', 'low'): 'underfill',
            ('fill_level', 'high'): 'overfill',
            ('viscosity', 'low'): 'viscosity_fault',
            ('viscosity', 'high'): 'viscosity_fault',
            ('sauce_temp', 'low'): 'thermal_fault',
            ('sauce_temp', 'high'): 'thermal_spike',
            ('cap_torque', 'low'): 'torque_failure',
            ('cap_torque', 'high'): 'torque_failure',
            ('bottle_flow_rate', 'low'): 'flow_fault',
            ('bottle_flow_rate', 'high'): 'flow_fault',
        }
        return mapping.get((sensor, direction), 'unknown')

    def detect(self, data: Dict[str, Any]) -> tuple[float, Optional[str]]:
        """
        Detect anomalies using combined ML + rule-based approach.
        Returns (anomaly_score, anomaly_type).
        """
        features = self._extract_features(data)

        # Rule-based check first
        rule_score, rule_type = self._rule_based_check(data)

        # ML-based check
        ml_score = 0.0
        with self.lock:
            # Add to training buffer
            self.training_buffer.append(features)

            # Train model when we have enough samples
            if not self.is_fitted and len(self.training_buffer) >= self.min_training_samples:
                logger.info(f"Training Isolation Forest with {len(self.training_buffer)} samples")
                X = np.array(self.training_buffer)
                self.model.fit(X)
                self.is_fitted = True
                logger.info("Isolation Forest training complete")

            # Run ML prediction if fitted
            if self.is_fitted:
                X = np.array([features])
                # decision_function returns negative for anomalies
                decision = self.model.decision_function(X)[0]
                # Convert to 0-1 score (more negative = higher anomaly)
                ml_score = max(0, min(1, 0.5 - decision))

        # Combine scores (rule-based takes priority if high)
        if rule_score > 0.7:
            return rule_score, rule_type

        # Blend ML and rule scores
        combined_score = max(rule_score, ml_score * 0.8)

        # Determine type
        if combined_score > 0.5 and rule_type:
            return combined_score, rule_type
        elif combined_score > 0.5:
            return combined_score, 'ml_detected'

        return combined_score, None


# ============================================================================
# DATABASE HANDLER
# ============================================================================

class KetchupDatabaseHandler:
    """Handles PostgreSQL operations for ketchup sensor data."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None
        self.connect()

    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.conn.autocommit = False
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def ensure_connection(self):
        """Reconnect if connection is lost."""
        if self.conn is None or self.conn.closed:
            self.connect()

    def insert_reading(self, data: Dict[str, Any], anomaly_score: float, anomaly_type: Optional[str]) -> bool:
        """Insert a sensor reading into the database."""
        self.ensure_connection()

        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sensor_readings_ketchup (
                        timestamp, line_id,
                        fill_level, viscosity, sauce_temp, cap_torque,
                        bottle_flow_rate, label_alignment,
                        bottle_count, reject_count, efficiency,
                        ambient_temp, humidity,
                        anomaly_score, anomaly_type,
                        custom_sensors
                    ) VALUES (
                        %s, %s,
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s
                    )
                """, (
                    data.get('timestamp'),
                    data.get('line_id', 'L01'),
                    data.get('fill_level'),
                    data.get('viscosity'),
                    data.get('sauce_temp'),
                    data.get('cap_torque'),
                    data.get('bottle_flow_rate'),
                    data.get('label_alignment'),
                    data.get('bottle_count', 0),
                    data.get('reject_count', 0),
                    data.get('efficiency'),
                    data.get('ambient_temp'),
                    data.get('humidity'),
                    anomaly_score,
                    anomaly_type,
                    Json(data.get('custom_sensors', {}))
                ))

                # Log anomaly if significant
                if anomaly_score > 0.5 and anomaly_type:
                    cur.execute("""
                        INSERT INTO ketchup_anomaly_log (
                            line_id, anomaly_type, anomaly_score, sensor_snapshot
                        ) VALUES (%s, %s, %s, %s)
                    """, (
                        data.get('line_id'),
                        anomaly_type,
                        anomaly_score,
                        Json(data)
                    ))

                self.conn.commit()
                return True

        except Exception as e:
            logger.error(f"Database insert failed: {e}")
            self.conn.rollback()
            return False

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# ============================================================================
# DASHBOARD BROADCASTER
# ============================================================================

class DashboardBroadcaster:
    """Sends real-time updates to the dashboard via HTTP POST."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def broadcast(self, data: Dict[str, Any], anomaly_score: float, anomaly_type: Optional[str]) -> bool:
        """Send telemetry update to dashboard."""
        try:
            payload = {
                'line_id': data.get('line_id', 'L01'),
                'fill_level': data.get('fill_level', 95.0),
                'viscosity': data.get('viscosity', 3500.0),
                'sauce_temp': data.get('sauce_temp', 165.0),
                'cap_torque': data.get('cap_torque', 2.5),
                'bottle_flow_rate': data.get('bottle_flow_rate', 150.0),
                'label_alignment': data.get('label_alignment', 0.0),
                'bottle_count': data.get('bottle_count', 0),
                'anomaly_score': anomaly_score,
                'anomaly_type': anomaly_type,
                'timestamp': data.get('timestamp', datetime.now(timezone.utc).isoformat())
            }

            response = self.session.post(self.endpoint, json=payload, timeout=1.0)
            return response.status_code == 200

        except requests.RequestException as e:
            # Silently fail - dashboard might not be running
            return False


# ============================================================================
# MAIN CONSUMER
# ============================================================================

class KetchupConsumer:
    """
    Main Kafka consumer for ketchup factory sensor data.
    """

    def __init__(self):
        self.consumer = None
        self.db_handler = None
        self.anomaly_detector = KetchupAnomalyDetector()
        self.broadcaster = DashboardBroadcaster(TELEMETRY_ENDPOINT)
        self.running = False
        self.stats = {
            'messages_processed': 0,
            'anomalies_detected': 0,
            'db_inserts': 0,
            'db_errors': 0
        }

    def connect_kafka(self, max_retries: int = 5) -> bool:
        """Connect to Kafka with retries."""
        for attempt in range(max_retries):
            try:
                self.consumer = KafkaConsumer(
                    KAFKA_TOPIC,
                    bootstrap_servers=KAFKA_BOOTSTRAP,
                    group_id=KAFKA_GROUP,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    max_poll_interval_ms=300000,
                    session_timeout_ms=30000
                )
                logger.info(f"Connected to Kafka topic: {KAFKA_TOPIC}")
                return True
            except NoBrokersAvailable:
                logger.warning(f"Kafka connection attempt {attempt + 1}/{max_retries} failed")
                time.sleep(2 ** attempt)  # Exponential backoff

        logger.error("Failed to connect to Kafka after all retries")
        return False

    def connect_database(self) -> bool:
        """Connect to PostgreSQL."""
        try:
            self.db_handler = KetchupDatabaseHandler(DATABASE_URL)
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def process_message(self, data: Dict[str, Any]):
        """Process a single sensor reading."""
        try:
            # Detect anomalies
            anomaly_score, anomaly_type = self.anomaly_detector.detect(data)

            # Store in database
            if self.db_handler:
                success = self.db_handler.insert_reading(data, anomaly_score, anomaly_type)
                if success:
                    self.stats['db_inserts'] += 1
                else:
                    self.stats['db_errors'] += 1

            # Broadcast to dashboard
            self.broadcaster.broadcast(data, anomaly_score, anomaly_type)

            # Update stats
            self.stats['messages_processed'] += 1
            if anomaly_score > 0.5:
                self.stats['anomalies_detected'] += 1
                logger.warning(
                    f"ANOMALY [{data.get('line_id')}]: {anomaly_type} "
                    f"(score={anomaly_score:.2f})"
                )

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def run(self):
        """Main consumer loop."""
        logger.info("=" * 60)
        logger.info("KETCHUP FACTORY SENSOR CONSUMER")
        logger.info("=" * 60)

        # Connect to services
        if not self.connect_kafka():
            logger.error("Cannot start without Kafka connection")
            return

        if not self.connect_database():
            logger.warning("Running without database - data will not be persisted")

        self.running = True
        logger.info("Consumer started. Listening for ketchup sensor data...")

        try:
            while self.running:
                # Poll for messages
                messages = self.consumer.poll(timeout_ms=100)

                for topic_partition, records in messages.items():
                    for record in records:
                        self.process_message(record.value)

                # Periodic stats logging
                if self.stats['messages_processed'] > 0 and self.stats['messages_processed'] % 1000 == 0:
                    logger.info(
                        f"Stats: processed={self.stats['messages_processed']}, "
                        f"anomalies={self.stats['anomalies_detected']}, "
                        f"db_inserts={self.stats['db_inserts']}, "
                        f"db_errors={self.stats['db_errors']}"
                    )

        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown."""
        self.running = False

        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")

        if self.db_handler:
            self.db_handler.close()
            logger.info("Database connection closed")

        logger.info(f"Final stats: {self.stats}")
        logger.info("Ketchup consumer shutdown complete")


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Entry point for ketchup consumer."""
    consumer = KetchupConsumer()
    consumer.run()


if __name__ == '__main__':
    main()
