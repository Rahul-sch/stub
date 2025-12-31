"""
Sensor Data Producer
Generates stub sensor data and sends to Kafka topic every 30 seconds.
"""

import json
import logging
import random
import signal
import sys
import time
from datetime import datetime, timedelta
from kafka import KafkaProducer
from kafka.errors import KafkaError

import config


class SensorDataProducer:
    """Generates stub sensor data and publishes to Kafka."""

    def __init__(self):
        """Initialize the producer with configuration."""
        self.setup_logging()
        self.producer = None
        self.message_count = 0
        self.total_messages = int((config.DURATION_HOURS * 3600) / config.INTERVAL_SECONDS)
        self.should_shutdown = False

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        # Windows-specific signal for process termination
        if sys.platform == 'win32':
            signal.signal(signal.SIGBREAK, self.signal_handler)

        self.logger.info(f"Producer initialized - Duration: {config.DURATION_HOURS} hours, "
                        f"Interval: {config.INTERVAL_SECONDS}s, "
                        f"Total messages: {self.total_messages}")

    def setup_logging(self):
        """Configure logging."""
        logging.basicConfig(
            level=config.LOG_LEVEL,
            format=config.LOG_FORMAT,
            datefmt=config.LOG_DATE_FORMAT
        )
        self.logger = logging.getLogger(__name__)

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
                producer = KafkaProducer(**config.KAFKA_PRODUCER_CONFIG)
                self.logger.info(f"Successfully connected to Kafka at {config.KAFKA_BOOTSTRAP_SERVERS}")
                return producer

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

    def generate_sensor_reading(self):
        """Generate a correlated sensor reading with timestamp."""
        # Start with RPM as the base - machinery speed drives other values
        rpm = round(random.uniform(
            config.SENSOR_RANGES['rpm']['min'],
            config.SENSOR_RANGES['rpm']['max']
        ), 2)

        # Higher RPM = Higher temperature (machinery heats up with speed)
        # Normalize RPM to 0-1 range, then map to temperature range
        rpm_normalized = (rpm - config.SENSOR_RANGES['rpm']['min']) / (
            config.SENSOR_RANGES['rpm']['max'] - config.SENSOR_RANGES['rpm']['min']
        )
        temp_min = config.SENSOR_RANGES['temperature']['min']
        temp_max = config.SENSOR_RANGES['temperature']['max']
        temperature = round(temp_min + (rpm_normalized * (temp_max - temp_min)) + random.uniform(-5, 5), 2)
        temperature = max(temp_min, min(temp_max, temperature))  # Clamp to range

        # Higher RPM = Higher vibration (faster rotation = more vibration)
        vib_min = config.SENSOR_RANGES['vibration']['min']
        vib_max = config.SENSOR_RANGES['vibration']['max']
        vibration = round(vib_min + (rpm_normalized * (vib_max - vib_min)) + random.uniform(-1, 1), 2)
        vibration = max(vib_min, min(vib_max, vibration))

        # Higher temperature = Lower humidity (heat dries air)
        temp_normalized = (temperature - temp_min) / (temp_max - temp_min)
        hum_min = config.SENSOR_RANGES['humidity']['min']
        hum_max = config.SENSOR_RANGES['humidity']['max']
        humidity = round(hum_max - (temp_normalized * (hum_max - hum_min)) + random.uniform(-5, 5), 2)
        humidity = max(hum_min, min(hum_max, humidity))

        # Pressure correlates with temperature (thermal expansion)
        press_min = config.SENSOR_RANGES['pressure']['min']
        press_max = config.SENSOR_RANGES['pressure']['max']
        pressure = round(press_min + (temp_normalized * 0.6 * (press_max - press_min)) + random.uniform(0, 3), 2)
        pressure = max(press_min, min(press_max, pressure))

        reading = {
            'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'),
            'temperature': temperature,
            'pressure': pressure,
            'vibration': vibration,
            'humidity': humidity,
            'rpm': rpm
        }
        return reading

    def send_message(self, data):
        """Send message to Kafka topic."""
        try:
            # Serialize to JSON
            message = json.dumps(data)

            # Send to Kafka
            future = self.producer.send(config.KAFKA_TOPIC, value=message)

            # Wait for acknowledgment
            record_metadata = future.get(timeout=10)

            self.message_count += 1

            # Log message sent
            self.logger.info(f"Message {self.message_count}/{self.total_messages} sent: "
                           f"timestamp={data['timestamp']}, "
                           f"temp={data['temperature']}°F, "
                           f"pressure={data['pressure']}PSI")

            # Log progress every N messages
            if self.message_count % config.LOG_PROGRESS_INTERVAL == 0:
                progress = (self.message_count / self.total_messages) * 100
                self.logger.info(f"Progress: {self.message_count}/{self.total_messages} "
                               f"({progress:.1f}%) messages sent")

            return True

        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False

    def run(self):
        """Main producer loop."""
        try:
            # Connect to Kafka
            self.producer = self.connect_to_kafka()
            if not self.producer:
                self.logger.error("Could not establish Kafka connection. Exiting.")
                return

            # Calculate end time
            end_time = datetime.utcnow() + timedelta(hours=config.DURATION_HOURS)
            self.logger.info(f"Starting data generation. Will run until {end_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

            # Main loop
            while datetime.utcnow() < end_time and not self.should_shutdown:
                # Generate sensor reading
                reading = self.generate_sensor_reading()

                # Send to Kafka
                self.send_message(reading)

                # Sleep until next interval
                time.sleep(config.INTERVAL_SECONDS)

            # Log completion
            if not self.should_shutdown:
                self.logger.info(f"Data generation complete! Total messages sent: {self.message_count}")
            else:
                self.logger.info(f"Shutdown requested. Messages sent: {self.message_count}/{self.total_messages}")

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received. Shutting down...")
        except Exception as e:
            self.logger.error(f"Unexpected error in producer: {e}", exc_info=True)
        finally:
            self.shutdown()

    def shutdown(self):
        """Cleanup and shutdown."""
        if self.producer:
            self.logger.info("Flushing producer buffer...")
            self.producer.flush(timeout=30)
            self.logger.info("Closing Kafka producer...")
            self.producer.close()
        self.logger.info("Producer shutdown complete.")


def main():
    """Main entry point."""
    producer = SensorDataProducer()
    producer.run()


if __name__ == '__main__':
    main()
