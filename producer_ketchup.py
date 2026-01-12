#!/usr/bin/env python3
"""
============================================================================
KETCHUP FACTORY SENSOR PRODUCER
============================================================================
Simulates 25 ketchup bottling production lines with correlated sensor data.
Publishes to Kafka topic: 'ketchup-sensor-data'

100% parallel to existing producer.py - does NOT modify original system.

Sensors per line:
- fill_level (85-100%) - Base driver
- viscosity (2500-4500 cP) - Temp-dependent
- sauce_temp (140-185°F) - Affects viscosity
- cap_torque (1.5-3.5 Nm) - Capping quality
- bottle_flow_rate (80-200 b/min) - Throughput
- label_alignment (-5 to +5°) - Drift over time

Anomaly Types:
- overfill: fill_level > 98%
- underfill: fill_level < 88%
- viscosity_fault: outside 2800-4200 cP
- torque_failure: outside 1.8-3.2 Nm
- label_misalign: |alignment| > 3°
- thermal_spike: sauce_temp > 180°F

Usage:
    python producer_ketchup.py [--lines 25] [--interval 1.0] [--anomaly-rate 0.05]
============================================================================
"""

import json
import random
import time
import math
import logging
import argparse
import signal
import sys
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError, NoBrokersAvailable
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("WARNING: kafka-python not installed. Running in simulation mode.")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Import config if available, else use defaults
try:
    import config
    KAFKA_BOOTSTRAP_SERVERS = getattr(config, 'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
except ImportError:
    KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'

# =============================================================================
# CONFIGURATION
# =============================================================================

KAFKA_TOPIC = 'ketchup-sensor-data'
DEFAULT_INTERVAL = 1.0  # seconds between readings per line
DEFAULT_NUM_LINES = 25
DEFAULT_ANOMALY_RATE = 0.05  # 5% chance of anomaly injection

# Sensor ranges for ketchup bottling
KETCHUP_SENSOR_RANGES = {
    'fill_level': {'min': 85.0, 'max': 100.0, 'unit': '%', 'normal_min': 92.0, 'normal_max': 98.0},
    'viscosity': {'min': 2500.0, 'max': 4500.0, 'unit': 'cP', 'normal_min': 2800.0, 'normal_max': 4200.0},
    'sauce_temp': {'min': 140.0, 'max': 185.0, 'unit': '°F', 'normal_min': 155.0, 'normal_max': 175.0},
    'cap_torque': {'min': 1.5, 'max': 3.5, 'unit': 'Nm', 'normal_min': 1.8, 'normal_max': 3.2},
    'bottle_flow_rate': {'min': 80.0, 'max': 200.0, 'unit': 'bottles/min', 'normal_min': 100.0, 'normal_max': 170.0},
    'label_alignment': {'min': -5.0, 'max': 5.0, 'unit': '°', 'normal_min': -2.0, 'normal_max': 2.0},
}

# Anomaly types and their effects
ANOMALY_TYPES = {
    'overfill': {'sensor': 'fill_level', 'direction': 'high', 'severity': 0.7},
    'underfill': {'sensor': 'fill_level', 'direction': 'low', 'severity': 0.6},
    'viscosity_fault': {'sensor': 'viscosity', 'direction': 'both', 'severity': 0.5},
    'torque_failure': {'sensor': 'cap_torque', 'direction': 'both', 'severity': 0.8},
    'label_misalign': {'sensor': 'label_alignment', 'direction': 'both', 'severity': 0.4},
    'thermal_spike': {'sensor': 'sauce_temp', 'direction': 'high', 'severity': 0.9},
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# LINE STATE CLASS
# =============================================================================

class LineState:
    """Maintains state for a single production line with realistic drift and correlation."""

    def __init__(self, line_id: str):
        self.line_id = line_id
        self.bottle_count = 0
        self.reject_count = 0

        # Initialize with slight variation per line
        line_num = int(line_id[1:])
        random.seed(line_num * 42)  # Deterministic initial state per line

        # Base values with line-specific offset
        self.base_fill = random.uniform(94.0, 96.0)
        self.base_temp = random.uniform(160.0, 170.0)
        self.base_viscosity = 3500.0 - (self.base_temp - 165.0) * 10

        # Drift accumulators (simulate gradual changes)
        self.label_drift = random.uniform(-0.5, 0.5)
        self.temp_drift = 0.0
        self.efficiency = random.uniform(92.0, 98.0)

        # Tank level (decreases over time, refilled periodically)
        self.tank_level = random.uniform(70.0, 100.0)

        # Time-based phase offset for sinusoidal variations
        self.phase_offset = random.uniform(0, 2 * math.pi)

        random.seed()  # Reset to random seed

    def update_drift(self, delta_time: float):
        """Update drift values over time."""
        # Label alignment drifts slowly
        self.label_drift += random.gauss(0, 0.02) * delta_time
        self.label_drift = max(-3.0, min(3.0, self.label_drift))

        # Temperature drift (thermal mass inertia)
        self.temp_drift += random.gauss(0, 0.1) * delta_time
        self.temp_drift = max(-5.0, min(5.0, self.temp_drift))

        # Tank depletes, refills when low
        self.tank_level -= random.uniform(0.05, 0.15) * delta_time
        if self.tank_level < 20.0:
            self.tank_level = random.uniform(85.0, 100.0)  # Refill
            logger.debug(f"[{self.line_id}] Tank refilled to {self.tank_level:.1f}%")


# =============================================================================
# KETCHUP PRODUCER CLASS
# =============================================================================

class KetchupProducer:
    """
    Simulates sensor data for 25 ketchup bottling lines.
    Generates correlated, realistic sensor readings with anomaly injection.
    """

    def __init__(
        self,
        num_lines: int = DEFAULT_NUM_LINES,
        interval: float = DEFAULT_INTERVAL,
        anomaly_rate: float = DEFAULT_ANOMALY_RATE
    ):
        self.num_lines = min(num_lines, 25)  # Max 25 lines (L01-L25)
        self.interval = interval
        self.anomaly_rate = anomaly_rate
        self.should_shutdown = False
        self.producer: Optional[KafkaProducer] = None
        self.message_count = 0
        self.start_time = datetime.now(timezone.utc)

        # Initialize line states
        self.line_ids = [f"L{str(i+1).zfill(2)}" for i in range(self.num_lines)]
        self.lines: Dict[str, LineState] = {
            line_id: LineState(line_id) for line_id in self.line_ids
        }

        # Anomaly injection settings (can be updated via API)
        self.injection_enabled = True
        self.injection_settings: Dict[str, Any] = {
            'rate': self.anomaly_rate,
            'types': list(ANOMALY_TYPES.keys()),
            'target_lines': self.line_ids  # All lines by default
        }

        # Statistics
        self.stats = {
            'total_messages': 0,
            'anomalies_injected': 0,
            'errors': 0,
            'by_line': {lid: {'messages': 0, 'anomalies': 0} for lid in self.line_ids}
        }

        logger.info(f"Initialized KetchupProducer with {self.num_lines} lines")

    def connect_to_kafka(self) -> bool:
        """Establish connection to Kafka broker."""
        if not KAFKA_AVAILABLE:
            logger.warning("Kafka not available - running in simulation mode")
            return False

        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3,
                retry_backoff_ms=500,
                request_timeout_ms=30000,
                max_block_ms=60000
            )
            logger.info(f"Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return True
        except NoBrokersAvailable:
            logger.error(f"No Kafka brokers available at {KAFKA_BOOTSTRAP_SERVERS}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False

    def generate_line_reading(self, line_id: str, current_time: float) -> Dict[str, Any]:
        """
        Generate a single sensor reading for a production line.
        Uses correlated sensor simulation with realistic physics.
        """
        state = self.lines[line_id]
        state.update_drift(self.interval)

        # Time-based sinusoidal variation (simulates production cycles)
        cycle = math.sin(current_time * 0.1 + state.phase_offset)
        fast_cycle = math.sin(current_time * 0.5 + state.phase_offset)

        # =================================================================
        # SENSOR GENERATION WITH CORRELATIONS
        # =================================================================

        # 1. SAUCE TEMPERATURE (base driver for viscosity)
        # Fluctuates around base with drift and cycle
        sauce_temp = (
            state.base_temp
            + state.temp_drift
            + cycle * 3.0  # ±3°F cycle
            + random.gauss(0, 0.5)  # Noise
        )
        sauce_temp = max(145.0, min(180.0, sauce_temp))

        # 2. VISCOSITY (inversely correlated with temperature)
        # Higher temp = lower viscosity (sauce flows easier)
        temp_factor = (sauce_temp - 165.0) / 10.0  # Normalized around 165°F
        viscosity = (
            3500.0
            - temp_factor * 150.0  # -150 cP per 10°F above baseline
            + random.gauss(0, 50.0)  # Noise
        )
        viscosity = max(2600.0, min(4300.0, viscosity))

        # 3. FILL LEVEL (affected by viscosity and pump efficiency)
        # Higher viscosity = slightly lower fill (harder to pump)
        viscosity_factor = (viscosity - 3500.0) / 1000.0
        fill_level = (
            state.base_fill
            - viscosity_factor * 1.0  # Viscosity effect
            + fast_cycle * 0.5  # Small cycle variation
            + random.gauss(0, 0.3)  # Noise
        )
        fill_level = max(88.0, min(99.0, fill_level))

        # 4. BOTTLE FLOW RATE (depends on fill level and viscosity)
        # Target ~150 bottles/min, affected by conditions
        base_flow = 150.0
        fill_efficiency = 1.0 - abs(fill_level - 95.0) / 20.0  # Optimal at 95%
        viscosity_efficiency = 1.0 - abs(viscosity - 3500.0) / 2000.0
        bottle_flow_rate = (
            base_flow
            * fill_efficiency
            * viscosity_efficiency
            + random.gauss(0, 5.0)
        )
        bottle_flow_rate = max(90.0, min(180.0, bottle_flow_rate))

        # 5. CAP TORQUE (relatively independent, slight correlation with flow rate)
        # Faster line = slightly more torque variation
        flow_factor = (bottle_flow_rate - 150.0) / 100.0
        cap_torque = (
            2.5  # Target torque
            + flow_factor * 0.1  # Flow effect
            + random.gauss(0, 0.15)  # Noise
        )
        cap_torque = max(1.7, min(3.3, cap_torque))

        # 6. LABEL ALIGNMENT (drifts over time, occasional corrections)
        label_alignment = (
            state.label_drift
            + random.gauss(0, 0.2)  # Noise
        )
        label_alignment = max(-4.0, min(4.0, label_alignment))

        # =================================================================
        # UPDATE LINE STATE
        # =================================================================

        # Increment bottle count based on flow rate
        bottles_this_interval = int(bottle_flow_rate * self.interval / 60.0)
        state.bottle_count += bottles_this_interval

        # Calculate efficiency
        max_possible = int(180.0 * self.interval / 60.0)
        state.efficiency = (bottles_this_interval / max_possible * 100.0) if max_possible > 0 else 0

        # =================================================================
        # BUILD READING
        # =================================================================

        reading = {
            'line_id': line_id,
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'),

            # Core ketchup sensors
            'fill_level': round(fill_level, 2),
            'viscosity': round(viscosity, 1),
            'sauce_temp': round(sauce_temp, 1),
            'cap_torque': round(cap_torque, 3),
            'bottle_flow_rate': round(bottle_flow_rate, 1),
            'label_alignment': round(label_alignment, 2),

            # Production metrics
            'bottle_count': state.bottle_count,
            'reject_count': state.reject_count,
            'efficiency': round(state.efficiency, 1),

            # Environmental
            'ambient_temp': round(72.0 + random.gauss(0, 1.5), 1),
            'humidity': round(45.0 + random.gauss(0, 3.0), 1),

            # Equipment status
            'tank_level': round(state.tank_level, 1),
            'conveyor_speed': round(bottle_flow_rate / 60.0, 3),  # m/s approximation
            'pump_pressure': round(45.0 + viscosity / 200.0 + random.gauss(0, 2.0), 1),

            # Anomaly (to be filled by injection)
            'anomaly_score': 0.0,
            'anomaly_type': None,
        }

        return reading

    def inject_anomaly(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject an anomaly into the reading based on injection settings.
        Returns the modified reading with anomaly flag set.
        """
        if not self.injection_enabled:
            return reading

        if random.random() > self.injection_settings['rate']:
            return reading

        line_id = reading['line_id']
        if line_id not in self.injection_settings.get('target_lines', self.line_ids):
            return reading

        # Select anomaly type
        anomaly_types = self.injection_settings.get('types', list(ANOMALY_TYPES.keys()))
        if not anomaly_types:
            return reading

        anomaly_type = random.choice(anomaly_types)
        anomaly_config = ANOMALY_TYPES[anomaly_type]
        sensor = anomaly_config['sensor']
        direction = anomaly_config['direction']
        severity = anomaly_config['severity']

        # Get sensor range
        sensor_range = KETCHUP_SENSOR_RANGES[sensor]

        # Calculate anomalous value
        current_value = reading[sensor]
        normal_range = sensor_range['normal_max'] - sensor_range['normal_min']

        if direction == 'high':
            deviation = normal_range * random.uniform(0.3, 0.8)
            new_value = sensor_range['normal_max'] + deviation
        elif direction == 'low':
            deviation = normal_range * random.uniform(0.3, 0.8)
            new_value = sensor_range['normal_min'] - deviation
        else:  # 'both'
            deviation = normal_range * random.uniform(0.3, 0.8)
            new_value = current_value + deviation * random.choice([-1, 1])

        # Clamp to absolute sensor limits
        new_value = max(sensor_range['min'], min(sensor_range['max'], new_value))

        # Update reading
        reading[sensor] = round(new_value, 2)
        reading['anomaly_score'] = severity + random.uniform(-0.1, 0.1)
        reading['anomaly_score'] = max(0.3, min(1.0, reading['anomaly_score']))
        reading['anomaly_type'] = anomaly_type

        # Update statistics
        self.stats['anomalies_injected'] += 1
        self.stats['by_line'][line_id]['anomalies'] += 1

        # Also update reject count for quality anomalies
        if anomaly_type in ['overfill', 'underfill', 'label_misalign']:
            state = self.lines[line_id]
            state.reject_count += random.randint(1, 5)
            reading['reject_count'] = state.reject_count

        logger.warning(
            f"ANOMALY [{line_id}] {anomaly_type}: {sensor}={new_value:.2f} "
            f"(score: {reading['anomaly_score']:.2f})"
        )

        return reading

    def send_reading(self, reading: Dict[str, Any]) -> bool:
        """Send a reading to Kafka topic."""
        if self.producer is None:
            # Simulation mode - just log
            logger.debug(f"[SIM] {reading['line_id']}: {json.dumps(reading)[:100]}...")
            return True

        try:
            future = self.producer.send(KAFKA_TOPIC, value=reading)
            record_metadata = future.get(timeout=10)
            self.message_count += 1
            self.stats['total_messages'] += 1
            self.stats['by_line'][reading['line_id']]['messages'] += 1

            if self.message_count % 100 == 0:
                logger.info(
                    f"Sent {self.message_count} messages | "
                    f"Anomalies: {self.stats['anomalies_injected']} | "
                    f"Partition: {record_metadata.partition}"
                )
            return True

        except KafkaError as e:
            logger.error(f"Kafka error sending reading: {e}")
            self.stats['errors'] += 1
            return False
        except Exception as e:
            logger.error(f"Error sending reading: {e}")
            self.stats['errors'] += 1
            return False

    def run(self):
        """Main production loop - generates readings for all lines."""
        logger.info(f"Starting Ketchup Producer for {self.num_lines} lines")
        logger.info(f"Interval: {self.interval}s | Anomaly Rate: {self.anomaly_rate*100:.1f}%")
        logger.info(f"Kafka Topic: {KAFKA_TOPIC}")

        # Connect to Kafka
        kafka_connected = self.connect_to_kafka()
        if not kafka_connected:
            logger.warning("Running in simulation mode (no Kafka)")

        start_time = time.time()
        iteration = 0

        try:
            while not self.should_shutdown:
                iteration += 1
                current_time = time.time() - start_time
                cycle_start = time.time()

                # Generate readings for all lines
                for line_id in self.line_ids:
                    if self.should_shutdown:
                        break

                    # Generate base reading
                    reading = self.generate_line_reading(line_id, current_time)

                    # Inject anomaly based on rate
                    reading = self.inject_anomaly(reading)

                    # Send to Kafka
                    self.send_reading(reading)

                # Calculate sleep time to maintain interval
                elapsed = time.time() - cycle_start
                sleep_time = max(0, self.interval - elapsed)

                if iteration % 60 == 0:  # Log stats every ~60 seconds
                    self.log_stats()

                time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Shutdown requested (Ctrl+C)")
        finally:
            self.shutdown()

    def log_stats(self):
        """Log current production statistics."""
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        rate = self.stats['total_messages'] / elapsed if elapsed > 0 else 0

        logger.info(
            f"STATS | Messages: {self.stats['total_messages']} | "
            f"Rate: {rate:.1f}/s | "
            f"Anomalies: {self.stats['anomalies_injected']} | "
            f"Errors: {self.stats['errors']}"
        )

    def shutdown(self):
        """Clean shutdown of producer."""
        logger.info("Shutting down Ketchup Producer...")
        self.should_shutdown = True

        if self.producer:
            try:
                self.producer.flush(timeout=5)
                self.producer.close(timeout=5)
                logger.info("Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing producer: {e}")

        self.log_stats()
        logger.info("Ketchup Producer shutdown complete")

    def update_injection_settings(self, settings: Dict[str, Any]):
        """Update anomaly injection settings (can be called from API)."""
        if 'enabled' in settings:
            self.injection_enabled = settings['enabled']
        if 'rate' in settings:
            self.injection_settings['rate'] = max(0, min(1, settings['rate']))
        if 'types' in settings:
            valid_types = [t for t in settings['types'] if t in ANOMALY_TYPES]
            self.injection_settings['types'] = valid_types or list(ANOMALY_TYPES.keys())
        if 'target_lines' in settings:
            valid_lines = [l for l in settings['target_lines'] if l in self.line_ids]
            self.injection_settings['target_lines'] = valid_lines or self.line_ids

        logger.info(f"Updated injection settings: {self.injection_settings}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Ketchup Factory Sensor Producer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--lines', '-l',
        type=int,
        default=DEFAULT_NUM_LINES,
        help=f'Number of production lines (1-25, default: {DEFAULT_NUM_LINES})'
    )
    parser.add_argument(
        '--interval', '-i',
        type=float,
        default=DEFAULT_INTERVAL,
        help=f'Seconds between readings (default: {DEFAULT_INTERVAL})'
    )
    parser.add_argument(
        '--anomaly-rate', '-a',
        type=float,
        default=DEFAULT_ANOMALY_RATE,
        help=f'Anomaly injection rate 0-1 (default: {DEFAULT_ANOMALY_RATE})'
    )
    parser.add_argument(
        '--kafka-server', '-k',
        type=str,
        default=KAFKA_BOOTSTRAP_SERVERS,
        help=f'Kafka bootstrap server (default: {KAFKA_BOOTSTRAP_SERVERS})'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create and run producer
    producer = KetchupProducer(
        num_lines=args.lines,
        interval=args.interval,
        anomaly_rate=args.anomaly_rate
    )

    # Handle shutdown signals
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        producer.should_shutdown = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run producer
    producer.run()


if __name__ == '__main__':
    main()
