"""
Sensor Data Consumer
Consumes messages from Kafka and persists to PostgreSQL database.
"""

import json
import logging
import signal
import sys
import time
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import psycopg2
from psycopg2 import sql, OperationalError

import config


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

        self.logger.info("Consumer initialized")

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
                consumer = KafkaConsumer(
                    config.KAFKA_TOPIC,
                    **config.KAFKA_CONSUMER_CONFIG
                )
                self.logger.info(f"Successfully connected to Kafka and subscribed to topic: {config.KAFKA_TOPIC}")
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
        required_fields = ['timestamp', 'temperature', 'pressure', 'vibration', 'humidity', 'rpm']

        for field in required_fields:
            if field not in data:
                self.logger.warning(f"Message missing required field: {field}")
                return False

        return True

    def insert_reading(self, reading):
        """Insert sensor reading into database."""
        insert_query = """
            INSERT INTO sensor_readings (timestamp, temperature, pressure, vibration, humidity, rpm)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        try:
            self.db_cursor.execute(insert_query, (
                reading['timestamp'],
                reading['temperature'],
                reading['pressure'],
                reading['vibration'],
                reading['humidity'],
                reading['rpm']
            ))
            self.db_conn.commit()
            return True

        except Exception as e:
            self.logger.error(f"Failed to insert reading into database: {e}")
            self.db_conn.rollback()
            return False

    def process_message(self, message):
        """Process a single message from Kafka."""
        try:
            # Decode and parse JSON
            data = json.loads(message.value)

            # Validate message
            if not self.validate_message(data):
                self.logger.warning(f"Invalid message skipped: {message.value}")
                return False

            # Insert into database
            if self.insert_reading(data):
                # Commit Kafka offset only after successful DB insert (exactly-once semantics)
                self.consumer.commit()

                self.message_count += 1

                # Log message processed
                self.logger.info(f"Message {self.message_count} processed: "
                               f"timestamp={data['timestamp']}, "
                               f"temp={data['temperature']}°F, "
                               f"pressure={data['pressure']}PSI")

                # Log progress every N messages
                if self.message_count % config.LOG_PROGRESS_INTERVAL == 0:
                    self.logger.info(f"Progress: {self.message_count} messages processed and inserted")

                return True
            else:
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
