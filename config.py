"""
Configuration file for sensor data pipeline.
Contains all settings for Kafka, PostgreSQL, timing, and sensor parameters.
"""

# ============================================================================
# TIMING CONFIGURATION
# ============================================================================

# Default configuration values so the dashboard can reset safely
DEFAULT_DURATION_HOURS = 3.0
DEFAULT_INTERVAL_SECONDS = 5

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
# SENSOR PARAMETER RANGES (50 Parameters across 5 Categories)
# ============================================================================

# Sensor categories for UI organization
SENSOR_CATEGORIES = {
    'environmental': 'Environmental',
    'mechanical': 'Mechanical',
    'thermal': 'Thermal',
    'electrical': 'Electrical',
    'fluid': 'Fluid Dynamics'
}

SENSOR_RANGES = {
    # ENVIRONMENTAL SENSORS (10)
    'temperature': {'min': 60.0, 'max': 100.0, 'unit': '°F', 'category': 'environmental'},
    'pressure': {'min': 0.0, 'max': 15.0, 'unit': 'PSI', 'category': 'environmental'},
    'humidity': {'min': 20.0, 'max': 80.0, 'unit': '%', 'category': 'environmental'},
    'ambient_temp': {'min': 50.0, 'max': 90.0, 'unit': '°F', 'category': 'environmental'},
    'dew_point': {'min': 30.0, 'max': 70.0, 'unit': '°F', 'category': 'environmental'},
    'air_quality_index': {'min': 0, 'max': 500, 'unit': 'AQI', 'category': 'environmental'},
    'co2_level': {'min': 400, 'max': 2000, 'unit': 'ppm', 'category': 'environmental'},
    'particle_count': {'min': 0, 'max': 100000, 'unit': 'particles/m³', 'category': 'environmental'},
    'noise_level': {'min': 40, 'max': 110, 'unit': 'dB', 'category': 'environmental'},
    'light_intensity': {'min': 0, 'max': 10000, 'unit': 'lux', 'category': 'environmental'},

    # MECHANICAL SENSORS (10)
    'vibration': {'min': 0.0, 'max': 10.0, 'unit': 'mm/s', 'category': 'mechanical'},
    'rpm': {'min': 1000.0, 'max': 5000.0, 'unit': 'RPM', 'category': 'mechanical'},
    'torque': {'min': 0, 'max': 500, 'unit': 'Nm', 'category': 'mechanical'},
    'shaft_alignment': {'min': -0.5, 'max': 0.5, 'unit': 'mm', 'category': 'mechanical'},
    'bearing_temp': {'min': 70, 'max': 180, 'unit': '°F', 'category': 'mechanical'},
    'motor_current': {'min': 0, 'max': 100, 'unit': 'A', 'category': 'mechanical'},
    'belt_tension': {'min': 20, 'max': 100, 'unit': 'lbf', 'category': 'mechanical'},
    'gear_wear': {'min': 0, 'max': 100, 'unit': '%', 'category': 'mechanical'},
    'coupling_temp': {'min': 60, 'max': 150, 'unit': '°F', 'category': 'mechanical'},
    'lubrication_pressure': {'min': 10, 'max': 60, 'unit': 'PSI', 'category': 'mechanical'},

    # THERMAL SENSORS (10)
    'coolant_temp': {'min': 140, 'max': 220, 'unit': '°F', 'category': 'thermal'},
    'exhaust_temp': {'min': 300, 'max': 900, 'unit': '°F', 'category': 'thermal'},
    'oil_temp': {'min': 150, 'max': 250, 'unit': '°F', 'category': 'thermal'},
    'radiator_temp': {'min': 150, 'max': 230, 'unit': '°F', 'category': 'thermal'},
    'thermal_efficiency': {'min': 60, 'max': 95, 'unit': '%', 'category': 'thermal'},
    'heat_dissipation': {'min': 0, 'max': 5000, 'unit': 'W', 'category': 'thermal'},
    'inlet_temp': {'min': 50, 'max': 120, 'unit': '°F', 'category': 'thermal'},
    'outlet_temp': {'min': 80, 'max': 200, 'unit': '°F', 'category': 'thermal'},
    'core_temp': {'min': 140, 'max': 240, 'unit': '°F', 'category': 'thermal'},
    'surface_temp': {'min': 70, 'max': 180, 'unit': '°F', 'category': 'thermal'},

    # ELECTRICAL SENSORS (10)
    'voltage': {'min': 110, 'max': 130, 'unit': 'V', 'category': 'electrical'},
    'current': {'min': 0, 'max': 50, 'unit': 'A', 'category': 'electrical'},
    'power_factor': {'min': 0.7, 'max': 1.0, 'unit': 'PF', 'category': 'electrical'},
    'frequency': {'min': 59.0, 'max': 61.0, 'unit': 'Hz', 'category': 'electrical'},
    'resistance': {'min': 0.1, 'max': 100, 'unit': 'Ω', 'category': 'electrical'},
    'capacitance': {'min': 1, 'max': 1000, 'unit': 'μF', 'category': 'electrical'},
    'inductance': {'min': 0.1, 'max': 10, 'unit': 'mH', 'category': 'electrical'},
    'phase_angle': {'min': -180, 'max': 180, 'unit': '°', 'category': 'electrical'},
    'harmonic_distortion': {'min': 0, 'max': 20, 'unit': '%', 'category': 'electrical'},
    'ground_fault': {'min': 0, 'max': 100, 'unit': 'mA', 'category': 'electrical'},

    # FLUID DYNAMICS SENSORS (10)
    'flow_rate': {'min': 0, 'max': 500, 'unit': 'L/min', 'category': 'fluid'},
    'fluid_pressure': {'min': 0, 'max': 100, 'unit': 'PSI', 'category': 'fluid'},
    'viscosity': {'min': 1, 'max': 100, 'unit': 'cP', 'category': 'fluid'},
    'density': {'min': 0.5, 'max': 1.5, 'unit': 'g/cm³', 'category': 'fluid'},
    'reynolds_number': {'min': 2000, 'max': 10000, 'unit': '', 'category': 'fluid'},
    'pipe_pressure_drop': {'min': 0, 'max': 50, 'unit': 'PSI', 'category': 'fluid'},
    'pump_efficiency': {'min': 60, 'max': 95, 'unit': '%', 'category': 'fluid'},
    'cavitation_index': {'min': 0, 'max': 10, 'unit': '', 'category': 'fluid'},
    'turbulence': {'min': 0, 'max': 100, 'unit': '%', 'category': 'fluid'},
    'valve_position': {'min': 0, 'max': 100, 'unit': '%', 'category': 'fluid'}
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Log progress every N messages
LOG_PROGRESS_INTERVAL = 10
