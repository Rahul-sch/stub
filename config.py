"""
Configuration file for sensor data pipeline.
Contains all settings for Kafka, PostgreSQL, timing, and sensor parameters.
"""

# ============================================================================
# TIMING CONFIGURATION
# ============================================================================

# Default configuration values so the dashboard can reset safely
DEFAULT_DURATION_HOURS = 3.0
DEFAULT_INTERVAL_SECONDS = 10

# Limits for dashboard config validation
CONFIG_LIMITS = {
    'duration_hours': {
        'min': 0,
        'max': 168  # one week
    },
    'interval_seconds': {
        'min': 1,
        'max': 3600  # once an hour
    }
}

# Duration for data generation (hours)
# Set to 0.01 for quick test (36 seconds, ~1-2 messages)
# Set to 24 for production run (24 hours, 2,880 messages)
DURATION_HOURS = DEFAULT_DURATION_HOURS

# Interval between sensor readings (seconds)
INTERVAL_SECONDS = DEFAULT_INTERVAL_SECONDS

# ============================================================================
# KAFKA CONFIGURATION
# ============================================================================

# Kafka broker connection
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPIC = 'sensor-data'

# Producer configuration
KAFKA_PRODUCER_CONFIG = {
    'bootstrap_servers': KAFKA_BOOTSTRAP_SERVERS,
    'acks': 'all',  # Wait for all replicas to acknowledge (strongest durability)
    'retries': 5,  # Retry failed sends
    'retry_backoff_ms': 300,  # Wait 300ms between retries
    'request_timeout_ms': 30000,  # 30 second timeout
    'max_in_flight_requests_per_connection': 1,  # Preserve message ordering
    'value_serializer': lambda v: v.encode('utf-8')  # Encode JSON strings to bytes
}

# Consumer configuration
KAFKA_CONSUMER_CONFIG = {
    'bootstrap_servers': KAFKA_BOOTSTRAP_SERVERS,
    'group_id': 'sensor-consumer-group',
    'auto_offset_reset': 'earliest',  # Start from beginning if no offset exists
    'enable_auto_commit': False,  # Manual commit after DB write (exactly-once semantics)
    'max_poll_records': 100,
    'session_timeout_ms': 30000,  # 30 seconds
    'heartbeat_interval_ms': 10000,  # 10 seconds
    'value_deserializer': lambda v: v.decode('utf-8')  # Decode bytes to strings
}

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DB_HOST = 'localhost'
DB_PORT = 5432
DB_NAME = 'sensordb'
DB_USER = 'sensoruser'
DB_PASSWORD = 'sensorpass'

# Connection string for psycopg2
DB_CONNECTION_STRING = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"

# Database connection settings
DB_CONFIG = {
    'host': DB_HOST,
    'port': DB_PORT,
    'database': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD
}

# ============================================================================
# RETRY CONFIGURATION
# ============================================================================

# Maximum retry attempts for connections
MAX_RETRIES = 10

# Initial retry delay (seconds)
INITIAL_RETRY_DELAY = 1

# Maximum retry delay (seconds)
MAX_RETRY_DELAY = 60

# Backoff multiplier for exponential backoff
BACKOFF_MULTIPLIER = 2

# ============================================================================
# SENSOR PARAMETER RANGES
# ============================================================================

SENSOR_RANGES = {
    'temperature': {
        'min': 60.0,
        'max': 100.0,
        'unit': '°F',
        'description': 'Temperature sensor reading'
    },
    'pressure': {
        'min': 0.0,
        'max': 15.0,
        'unit': 'PSI',
        'description': 'Pressure sensor reading'
    },
    'vibration': {
        'min': 0.0,
        'max': 10.0,
        'unit': 'mm/s',
        'description': 'Vibration sensor reading'
    },
    'humidity': {
        'min': 20.0,
        'max': 80.0,
        'unit': '%',
        'description': 'Humidity sensor reading'
    },
    'rpm': {
        'min': 1000.0,
        'max': 5000.0,
        'unit': 'RPM',
        'description': 'RPM sensor reading'
    }
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Log progress every N messages
LOG_PROGRESS_INTERVAL = 10
