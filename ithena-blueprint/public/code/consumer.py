"""
Sensor Data Consumer
Consumes messages from Kafka and persists to PostgreSQL database.
"""

import json
import logging
import signal
import sys
import time
import os
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import psycopg2
from psycopg2 import sql, OperationalError
from psycopg2.extras import Json

# HTTP requests for 3D Twin telemetry updates
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

import config

# ML Detection imports - Combined Pipeline (Isolation Forest + LSTM)
if config.ML_DETECTION_ENABLED:
    try:
        from combined_pipeline import get_combined_detector, LSTM_AVAILABLE
        ML_AVAILABLE = True
    except ImportError as e:
        ML_AVAILABLE = False
        logging.warning(f"ML detection not available: {e}")
else:
    ML_AVAILABLE = False
    LSTM_AVAILABLE = False


class SensorDataConsumer:
    """Consumes sensor data from Kafka and writes to PostgreSQL."""

    def __init__(self):
        """Initialize the consumer with configuration."""
        self.setup_logging()
        self.consumer = None
        self.db_conn = None
        self.db_cursor = None
        self.message_count = 0
        self.should_shutdown = False

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        # Windows-specific signal for process termination
        if sys.platform == 'win32':
            signal.signal(signal.SIGBREAK, self.signal_handler)

            self.logger.info("Consumer initialized")
            self.logger.info("Consumer initialized - ready to connect")

    def setup_logging(self):
        """Configure structured logging."""
        logging.basicConfig(
            level=config.LOG_LEVEL,
            format='[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("=" * 60)
        self.logger.info("CONSUMER STARTING")
        self.logger.info("=" * 60)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.should_shutdown = True

    def connect_to_kafka(self):
        """Connect to Kafka with retry logic and exponential backoff."""
        retry_delay = config.INITIAL_RETRY_DELAY

        for attempt in range(1, config.MAX_RETRIES + 1):
            if self.should_shutdown:
                return None

            try:
                self.logger.info(f"Attempting to connect to Kafka (attempt {attempt}/{config.MAX_RETRIES})...")
                consumer = KafkaConsumer(
                    config.KAFKA_TOPIC,
                    **config.KAFKA_CONSUMER_CONFIG
                )
                self.logger.info(f"Successfully connected to Kafka and subscribed to topic: {config.KAFKA_TOPIC}")
                self.logger.info(f"[SUCCESS] Connected to Kafka topic: {config.KAFKA_TOPIC}")
                return consumer

            except KafkaError as e:
                self.logger.warning(f"Failed to connect to Kafka: {e}")

                if attempt < config.MAX_RETRIES:
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * config.BACKOFF_MULTIPLIER, config.MAX_RETRY_DELAY)
                else:
                    self.logger.error("Max retries reached. Could not connect to Kafka.")
                    raise

        return None

    def connect_to_database(self):
        """Connect to PostgreSQL with retry logic and exponential backoff."""
        retry_delay = config.INITIAL_RETRY_DELAY

        for attempt in range(1, config.MAX_RETRIES + 1):
            if self.should_shutdown:
                return None, None

            try:
                self.logger.info(f"Attempting to connect to PostgreSQL (attempt {attempt}/{config.MAX_RETRIES})...")
                conn = psycopg2.connect(**config.DB_CONFIG)
                conn.autocommit = False  # Explicit transaction control
                cursor = conn.cursor()

                # Test connection
                cursor.execute("SELECT 1")
                cursor.fetchone()

                self.logger.info(f"Successfully connected to PostgreSQL database: {config.DB_NAME}")
                self.logger.info(f"[SUCCESS] Connected to database: {config.DB_NAME}")
                return conn, cursor

            except OperationalError as e:
                self.logger.warning(f"Failed to connect to PostgreSQL: {e}")

                if attempt < config.MAX_RETRIES:
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * config.BACKOFF_MULTIPLIER, config.MAX_RETRY_DELAY)
                else:
                    self.logger.error("Max retries reached. Could not connect to PostgreSQL.")
                    raise

        return None, None

    def validate_message(self, data):
        """Validate that message contains required fields."""
        # Only timestamp and the 3 NOT NULL sensor fields are strictly required
        required_fields = ['timestamp', 'temperature', 'pressure', 'humidity', 'vibration', 'rpm']

        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Message missing required field: {field}")
                return False

        return True

    def detect_anomalies(self, reading):
        """Return list of anomaly descriptions for out-of-range sensor values."""
        anomalies = []

        for sensor_name, bounds in config.SENSOR_RANGES.items():
            value = reading.get(sensor_name)
            if value is None:
                continue

            if value < bounds['min'] or value > bounds['max']:
                unit = bounds.get('unit', '')
                anomalies.append(
                    f"{sensor_name.title()} out of range ({value}{unit} not in "
                    f"{bounds['min']} - {bounds['max']}) at {reading.get('timestamp')}"
                )

        return anomalies

    def record_alert(self, alert_type, message, severity='HIGH', source='consumer'):
        """Persist an alert so the dashboard can display it."""
        try:
            conn = psycopg2.connect(**config.DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO alerts (alert_type, source, severity, message)
                VALUES (%s, %s, %s, %s)
                """,
                (alert_type, source, severity, message)
            )
            conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to record alert: {e}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def validate_custom_sensors(self, custom_sensors):
        """Validate custom sensors against registry.
        
        Args:
            custom_sensors: Dict of {sensor_name: value}
            
        Returns:
            tuple: (validated_dict, invalid_sensors_list)
        """
        if not custom_sensors:
            return {}, []
        
        validated = {}
        invalid = []
        
        try:
            # Get list of active custom sensors from database
            self.db_cursor.execute("""
                SELECT sensor_name, min_range, max_range
                FROM custom_sensors
                WHERE is_active = TRUE
            """)
            
            registered_sensors = {row[0]: {'min': row[1], 'max': row[2]} 
                                 for row in self.db_cursor.fetchall()}
            
            # Validate each custom sensor
            for sensor_name, value in custom_sensors.items():
                if sensor_name not in registered_sensors:
                    invalid.append(sensor_name)
                    self.logger.warning(f"Unknown custom sensor '{sensor_name}' in reading. Skipping.")
                    continue
                
                # Validate value is within range
                sensor_config = registered_sensors[sensor_name]
                min_val = sensor_config['min']
                max_val = sensor_config['max']
                
                try:
                    float_value = float(value)
                    if min_val <= float_value <= max_val:
                        validated[sensor_name] = float_value
                    else:
                        invalid.append(sensor_name)
                        self.logger.warning(
                            f"Custom sensor '{sensor_name}' value {float_value} "
                            f"outside range [{min_val}, {max_val}]. Skipping."
                        )
                except (ValueError, TypeError):
                    invalid.append(sensor_name)
                    self.logger.warning(f"Invalid value for custom sensor '{sensor_name}': {value}. Skipping.")
            
        except Exception as e:
            # If validation fails, log but don't crash - return empty dict
            self.logger.warning(f"Failed to validate custom sensors: {e}. Skipping custom sensors.")
            return {}, list(custom_sensors.keys())
        
        return validated, invalid

    def insert_reading(self, reading):
        """Insert sensor reading with all 50 parameters into database.
        
        Returns:
            int or None: The inserted reading ID, or None on failure
        """
        # Extract and validate custom sensors
        custom_sensors_raw = reading.get('custom_sensors', {})
        custom_sensors_validated, invalid_sensors = self.validate_custom_sensors(custom_sensors_raw)
        
        # Convert validated custom sensors to JSONB (use psycopg2 Json for proper handling)
        custom_sensors_jsonb = Json(custom_sensors_validated) if custom_sensors_validated else Json({})
        
        insert_query = """
            INSERT INTO sensor_readings (
                timestamp, machine_id,
                temperature, pressure, humidity, ambient_temp, dew_point,
                air_quality_index, co2_level, particle_count, noise_level, light_intensity,
                vibration, rpm, torque, shaft_alignment, bearing_temp,
                motor_current, belt_tension, gear_wear, coupling_temp, lubrication_pressure,
                coolant_temp, exhaust_temp, oil_temp, radiator_temp, thermal_efficiency,
                heat_dissipation, inlet_temp, outlet_temp, core_temp, surface_temp,
                voltage, current, power_factor, frequency, resistance,
                capacitance, inductance, phase_angle, harmonic_distortion, ground_fault,
                flow_rate, fluid_pressure, viscosity, density, reynolds_number,
                pipe_pressure_drop, pump_efficiency, cavitation_index, turbulence, valve_position,
                custom_sensors
            )
            VALUES (
                %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s
            )
            RETURNING id
        """

        try:
            self.db_cursor.execute(insert_query, (
                reading['timestamp'],
                reading.get('machine_id', 'A'),  # Default to 'A' if not present
                # Environmental
                reading['temperature'], reading['pressure'], reading['humidity'],
                reading.get('ambient_temp'), reading.get('dew_point'),
                reading.get('air_quality_index'), reading.get('co2_level'),
                reading.get('particle_count'), reading.get('noise_level'), reading.get('light_intensity'),
                # Mechanical
                reading['vibration'], reading['rpm'],
                reading.get('torque'), reading.get('shaft_alignment'), reading.get('bearing_temp'),
                reading.get('motor_current'), reading.get('belt_tension'), reading.get('gear_wear'),
                reading.get('coupling_temp'), reading.get('lubrication_pressure'),
                # Thermal
                reading.get('coolant_temp'), reading.get('exhaust_temp'), reading.get('oil_temp'),
                reading.get('radiator_temp'), reading.get('thermal_efficiency'),
                reading.get('heat_dissipation'), reading.get('inlet_temp'), reading.get('outlet_temp'),
                reading.get('core_temp'), reading.get('surface_temp'),
                # Electrical
                reading.get('voltage'), reading.get('current'), reading.get('power_factor'),
                reading.get('frequency'), reading.get('resistance'),
                reading.get('capacitance'), reading.get('inductance'), reading.get('phase_angle'),
                reading.get('harmonic_distortion'), reading.get('ground_fault'),
                # Fluid Dynamics
                reading.get('flow_rate'), reading.get('fluid_pressure'), reading.get('viscosity'),
                reading.get('density'), reading.get('reynolds_number'),
                reading.get('pipe_pressure_drop'), reading.get('pump_efficiency'),
                reading.get('cavitation_index'), reading.get('turbulence'), reading.get('valve_position'),
                # Custom sensors JSONB (psycopg2 Json handles conversion)
                custom_sensors_jsonb
            ))
            reading_id = self.db_cursor.fetchone()[0]
            self.db_conn.commit()
            
            return reading_id

        except Exception as e:
            error_msg = f"Failed to insert reading into database: {e}"
            self.logger.error(error_msg)
            self.logger.error(f"[ERROR] {error_msg}", exc_info=True)
            self.record_alert('DB_WRITE_FAILURE', str(e), severity='ERROR')
            if self.db_conn:
                self.db_conn.rollback()
            return None

    def run_ml_detection(self, reading, reading_id):
        """Run ML-based anomaly detection using combined pipeline.

        Uses Isolation Forest and/or LSTM Autoencoder based on config.
        Strategy is set via config.HYBRID_DETECTION_STRATEGY.

        Args:
            reading: Dict with sensor values
            reading_id: ID of the inserted reading

        Returns:
            dict: ML detection result with score and method, or None if unavailable
        """
        if not ML_AVAILABLE:
            return None

        try:
            # Get combined detector (handles IF + LSTM)
            detector = get_combined_detector()

            # Run detection with configured strategy
            is_anomaly, score, contributing_sensors, method = detector.detect(reading, reading_id)

            # Record the detection result
            detection_id = detector.record_detection(
                reading_id=reading_id,
                is_anomaly=is_anomaly,
                score=score,
                sensors=contributing_sensors,
                method=method
            )

            if is_anomaly:
                sensors_str = ', '.join(contributing_sensors[:5]) if contributing_sensors else 'multiple parameters'
                method_display = method.upper().replace('_', ' ')
                self.logger.warning(
                    f"{method_display} anomaly detected (score: {score:.4f}): {sensors_str}"
                )
                self.record_alert(
                    'SENSOR_ANOMALY_ML',
                    f"{method_display} detected anomaly (score: {score:.4f}) - "
                    f"Contributing sensors: {sensors_str}",
                    severity='HIGH'
                )

            # Return result for 3D Twin telemetry
            return {
                'is_anomaly': is_anomaly,
                'score': score,
                'contributing_sensors': contributing_sensors,
                'method': method
            }

        except Exception as e:
            self.logger.error(f"ML detection failed: {e}")
            return None

    def update_3d_telemetry(self, reading, ml_result):
        """Push telemetry data to 3D Digital Twin dashboard via internal API.

        This updates the WebSocket broadcast cache so real-time visualizations
        can animate based on current sensor values.

        Args:
            reading: Dict with sensor values
            ml_result: Optional dict with ML detection result
        """
        if not REQUESTS_AVAILABLE:
            return

        try:
            # Extract anomaly score from ML result
            anomaly_score = 0
            detection_method = 'none'
            detected_sensors = []

            if ml_result:
                anomaly_score = ml_result.get('score', 0)
                detection_method = ml_result.get('method', 'hybrid')
                detected_sensors = ml_result.get('contributing_sensors', [])

            # POST to internal telemetry endpoint (non-blocking with short timeout)
            requests.post(
                'http://localhost:5000/api/internal/telemetry-update',
                json={
                    'machine_id': reading.get('machine_id', 'A'),
                    'rpm': reading.get('rpm', 0),
                    'temperature': reading.get('temperature', 70),
                    'vibration': reading.get('vibration', 0),
                    'pressure': reading.get('pressure', 100),
                    'bearing_temp': reading.get('bearing_temp', 120),
                    'anomaly_score': anomaly_score,
                    'detection_method': detection_method,
                    'detected_sensors': detected_sensors
                },
                timeout=0.5  # Quick timeout to not block consumer
            )
        except requests.exceptions.RequestException:
            # Silently ignore - 3D Twin might not be running
            pass
        except Exception as e:
            # Log but don't fail - this is non-critical
            self.logger.debug(f"3D telemetry update skipped: {e}")

    def process_message(self, message):
        """Process a single message from Kafka."""
        try:
            # Decode and parse JSON
            data = json.loads(message.value)

            # Validate message
            if not self.validate_message(data):
                self.logger.warning(f"Invalid message skipped: {message.value}")
                self.consumer.commit()
                return False

            # Check for rule-based anomalies before inserting
            anomalies = self.detect_anomalies(data)
            if anomalies:
                for anomaly in anomalies:
                    self.logger.warning(f"Rule-based anomaly detected: {anomaly}")
                    self.record_alert('SENSOR_ANOMALY', anomaly, severity='CRITICAL')

                # Skip inserting bad data but do not reprocess it
                self.consumer.commit()
                return False

            # Insert into database
            reading_id = self.insert_reading(data)
            if reading_id:
                # Commit Kafka offset only after successful DB insert (exactly-once semantics)
                self.consumer.commit()

                self.message_count += 1

                # Log message processed with key parameters
                log_msg = (f"Message {self.message_count} processed: "
                          f"timestamp={data['timestamp']}, "
                          f"rpm={data['rpm']}, "
                          f"temp={data['temperature']}°F, "
                          f"vibration={data['vibration']}mm/s, "
                          f"DB_ID={reading_id}")
                self.logger.info(log_msg)
                self.logger.info(f"[OK] {log_msg}")

                # Run ML-based anomaly detection (non-blocking)
                ml_result = self.run_ml_detection(data, reading_id)

                # Update 3D Digital Twin telemetry cache (non-blocking)
                self.update_3d_telemetry(data, ml_result)

                # Log progress every N messages
                if self.message_count % config.LOG_PROGRESS_INTERVAL == 0:
                    self.logger.info(f"Progress: {self.message_count} messages processed and inserted")

                return True
            else:
                error_msg = f"Failed to insert reading - insert_reading returned None"
                self.logger.error(error_msg)
                self.logger.error(f"[ERROR] {error_msg}")
                return False

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON message: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error processing message: {e}", exc_info=True)
            return False

    def run(self):
        """Main consumer loop."""
        try:
            # Connect to Kafka
            self.consumer = self.connect_to_kafka()
            if not self.consumer:
                self.logger.error("Could not establish Kafka connection. Exiting.")
                return

            # Connect to database
            self.db_conn, self.db_cursor = self.connect_to_database()
            if not self.db_conn or not self.db_cursor:
                self.logger.error("Could not establish database connection. Exiting.")
                return

            self.logger.info("Consumer ready. Waiting for messages...")
            self.logger.info("[READY] Consumer is running and waiting for messages from Kafka...")
            self.logger.info("        (Messages will appear here as they are processed)")

            # Main loop - continuously poll for messages
            while not self.should_shutdown:
                try:
                    # Poll for messages (timeout in milliseconds)
                    messages = self.consumer.poll(timeout_ms=1000)

                    if messages:
                        for topic_partition, records in messages.items():
                            for message in records:
                                if self.should_shutdown:
                                    break
                                self.process_message(message)

                except Exception as e:
                    self.logger.error(f"Error during message poll: {e}", exc_info=True)
                    time.sleep(1)  # Brief pause before continuing

            self.logger.info(f"Consumer shutting down. Total messages processed: {self.message_count}")

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received. Shutting down...")
        except Exception as e:
            self.logger.error(f"Unexpected error in consumer: {e}", exc_info=True)
        finally:
            self.shutdown()

    def shutdown(self):
        """Cleanup and shutdown."""
        # Close Kafka consumer
        if self.consumer:
            self.logger.info("Closing Kafka consumer...")
            self.consumer.close()

        # Close database connection
        if self.db_cursor:
            self.logger.info("Closing database cursor...")
            self.db_cursor.close()

        if self.db_conn:
            self.logger.info("Closing database connection...")
            self.db_conn.close()

        self.logger.info("Consumer shutdown complete.")


def main():
    """Main entry point."""
    consumer = SensorDataConsumer()
    consumer.run()


if __name__ == '__main__':
    main()
