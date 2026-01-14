"""
Configuration file for sensor data pipeline.
Contains all settings for Kafka, PostgreSQL, timing, and sensor parameters.
"""

import os
import logging
from urllib.parse import urlparse

# Load environment variables from .env file (for development)
# In production/Docker, environment variables are set via container config
try:
    from dotenv import load_dotenv
    # Load .env from the same directory as this config file
    _env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
        logging.info(f"Loaded environment variables from {_env_path}")
    else:
        # Try loading from current directory as fallback
        load_dotenv()
except ImportError:
    # python-dotenv not installed, rely on system environment variables
    pass

# ============================================================================
# TIMING CONFIGURATION
# ============================================================================

# Default configuration values so the dashboard can reset safely
# Changed to 999 hours (effectively infinite) so producer runs continuously
DEFAULT_DURATION_HOURS = 999
DEFAULT_INTERVAL_SECONDS = 1

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
# Set to 999 hours (effectively infinite) for continuous operation
# User can stop via dashboard STOP button
DURATION_HOURS = DEFAULT_DURATION_HOURS

# Interval between sensor readings (seconds)
INTERVAL_SECONDS = DEFAULT_INTERVAL_SECONDS

# ============================================================================
# KAFKA CONFIGURATION (Cloud-Aware)
# ============================================================================

# Kafka broker connection - check environment variable first (for Upstash/Render)
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BROKER_URL', 'localhost:9092')
KAFKA_TOPIC = 'sensor-data'

# Kafka SASL authentication (for cloud providers like Upstash)
KAFKA_SASL_USERNAME = os.environ.get('KAFKA_SASL_USERNAME', '')
KAFKA_SASL_PASSWORD = os.environ.get('KAFKA_SASL_PASSWORD', '')
KAFKA_USE_SASL = bool(KAFKA_SASL_USERNAME and KAFKA_SASL_PASSWORD)

# Producer configuration (with SASL support for cloud)
KAFKA_PRODUCER_CONFIG = {
    'bootstrap_servers': KAFKA_BOOTSTRAP_SERVERS,
    'acks': 'all',  # Wait for all replicas to acknowledge (strongest durability)
    'retries': 5,  # Retry failed sends
    'retry_backoff_ms': 300,  # Wait 300ms between retries
    'request_timeout_ms': 30000,  # 30 second timeout
    'max_in_flight_requests_per_connection': 1,  # Preserve message ordering
    'api_version_auto_timeout_ms': 10000,  # Time to negotiate API version with broker
    'value_serializer': lambda v: v.encode('utf-8')  # Encode JSON strings to bytes
}

# Add SASL configuration if credentials are provided
if KAFKA_USE_SASL:
    KAFKA_PRODUCER_CONFIG.update({
        'security_protocol': 'SASL_SSL',
        'sasl_mechanism': 'SCRAM-SHA-256',
        'sasl_plain_username': KAFKA_SASL_USERNAME,
        'sasl_plain_password': KAFKA_SASL_PASSWORD
    })

# Consumer configuration (with SASL support for cloud)
KAFKA_CONSUMER_CONFIG = {
    'bootstrap_servers': KAFKA_BOOTSTRAP_SERVERS,
    'group_id': 'sensor-consumer-group',
    'auto_offset_reset': 'earliest',  # Start from beginning if no offset exists
    'enable_auto_commit': False,  # Manual commit after DB write (exactly-once semantics)
    'max_poll_records': 100,
    'session_timeout_ms': 30000,  # 30 seconds
    'heartbeat_interval_ms': 10000,  # 10 seconds
    'api_version_auto_timeout_ms': 10000,  # Time to negotiate API version with broker
    'value_deserializer': lambda v: v.decode('utf-8')  # Decode bytes to strings
}

# Add SASL configuration if credentials are provided
if KAFKA_USE_SASL:
    KAFKA_CONSUMER_CONFIG.update({
        'security_protocol': 'SASL_SSL',
        'sasl_mechanism': 'SCRAM-SHA-256',
        'sasl_plain_username': KAFKA_SASL_USERNAME,
        'sasl_plain_password': KAFKA_SASL_PASSWORD
    })

# ============================================================================
# DATABASE CONFIGURATION (Cloud-Aware)
# ============================================================================

# Check for DATABASE_URL environment variable (for Neon/Render)
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# Debug: Print first 20 characters of DATABASE_URL (masked for security)
if DATABASE_URL:
    masked_url = DATABASE_URL[:20] + '...' if len(DATABASE_URL) > 20 else DATABASE_URL
    print(f"Connecting to: {masked_url}")
    logging.info(f"Connecting to: {masked_url}")

if DATABASE_URL:
    # Parse DATABASE_URL (format: postgresql://user:password@host:port/dbname)
    # Render/Neon compatibility: replace postgres:// with postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        logging.info("Converted postgres:// to postgresql:// for compatibility")
    
    # Parse the URL
    parsed = urlparse(DATABASE_URL)
    
    DB_HOST = parsed.hostname or 'localhost'
    DB_PORT = parsed.port or 5432
    DB_NAME = parsed.path.lstrip('/') if parsed.path else 'sensordb'
    DB_USER = parsed.username or 'sensoruser'
    DB_PASSWORD = parsed.password or 'sensorpass'
    
    logging.info(f"Using cloud database: {DB_NAME} on {DB_HOST}:{DB_PORT}")
else:
    # Fallback to local defaults
    DB_HOST = 'localhost'
    DB_PORT = 5432
    DB_NAME = 'sensordb'
    DB_USER = 'sensoruser'
    DB_PASSWORD = 'sensorpass'
    logging.info("Using local database configuration")

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

# Add SSL for Neon/cloud databases
if DATABASE_URL and ('neon' in DATABASE_URL.lower() or 'sslmode' in DATABASE_URL.lower()):
    DB_CONFIG['sslmode'] = 'require'

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
# SENSOR THRESHOLDS - Normal/Safe Operating Limits for Anomaly Detection
# Based on industry standards (ISO, OSHA, IEEE, ASHRAE) and best practices
# These represent the UPPER limit before a reading is considered anomalous
# For parameters where LOW values are dangerous, use 'low_threshold' as well
# ============================================================================

SENSOR_THRESHOLDS = {
    # ENVIRONMENTAL SENSORS
    # Temperature: Indoor comfort 65-78°F, industrial up to 85°F safe
    'temperature': {'low': 65.0, 'high': 85.0, 'unit': '°F'},
    # Pressure: Atmospheric ~14.7 PSI, slight overpressure acceptable
    'pressure': {'low': 2.0, 'high': 12.0, 'unit': 'PSI'},
    # Humidity: ASHRAE recommends 30-60% RH for comfort and health
    'humidity': {'low': 30.0, 'high': 65.0, 'unit': '%'},
    # Ambient temp: Similar to temperature, industrial environment
    'ambient_temp': {'low': 55.0, 'high': 82.0, 'unit': '°F'},
    # Dew point: Condensation risk above 60°F, too dry below 35°F
    'dew_point': {'low': 35.0, 'high': 60.0, 'unit': '°F'},
    # Air Quality Index: EPA scale - 0-50 Good, 51-100 Moderate, >100 Unhealthy for sensitive
    'air_quality_index': {'low': 0, 'high': 100, 'unit': 'AQI'},
    # CO2: OSHA limit 5000ppm, ASHRAE recommends <1000ppm for good air quality
    'co2_level': {'low': 350, 'high': 1000, 'unit': 'ppm'},
    # Particle count: Class 100,000 cleanroom standard ~3,520,000 particles/m³
    'particle_count': {'low': 0, 'high': 50000, 'unit': 'particles/m³'},
    # Noise: OSHA 85dB requires hearing protection, 70dB safe for prolonged exposure
    'noise_level': {'low': 30, 'high': 85, 'unit': 'dB'},
    # Light: 300-500 lux for office work, 500-1000 for detailed tasks
    'light_intensity': {'low': 200, 'high': 5000, 'unit': 'lux'},

    # MECHANICAL SENSORS
    # Vibration: ISO 10816 - <2.8 mm/s Good, 2.8-7.1 Satisfactory, >7.1 Unsatisfactory
    'vibration': {'low': 0.0, 'high': 4.5, 'unit': 'mm/s'},
    # RPM: Typical industrial motor 1800-3600 RPM, excessive speed causes wear
    'rpm': {'low': 1200.0, 'high': 4200.0, 'unit': 'RPM'},
    # Torque: Should not exceed motor/gearbox rated torque
    'torque': {'low': 50, 'high': 400, 'unit': 'Nm'},
    # Shaft alignment: ISO 10816 - should be within ±0.05mm for precision, ±0.25mm acceptable
    'shaft_alignment': {'low': -0.25, 'high': 0.25, 'unit': 'mm'},
    # Bearing temp: Normal 100-150°F, alarm at 180°F, critical at 200°F
    'bearing_temp': {'low': 80, 'high': 160, 'unit': '°F'},
    # Motor current: Should not exceed 80% of nameplate rating continuously
    'motor_current': {'low': 5, 'high': 80, 'unit': 'A'},
    # Belt tension: Manufacturer specific, typical 40-80 lbf
    'belt_tension': {'low': 30, 'high': 85, 'unit': 'lbf'},
    # Gear wear: <20% good, 20-50% monitor, >50% replace soon
    'gear_wear': {'low': 0, 'high': 40, 'unit': '%'},
    # Coupling temp: Similar to bearing, slightly lower
    'coupling_temp': {'low': 65, 'high': 130, 'unit': '°F'},
    # Lubrication pressure: Minimum required for film, max before seal damage
    'lubrication_pressure': {'low': 20, 'high': 50, 'unit': 'PSI'},

    # THERMAL SENSORS
    # Coolant temp: Normal 180-200°F, overheating begins >210°F
    'coolant_temp': {'low': 160, 'high': 205, 'unit': '°F'},
    # Exhaust temp: Varies by engine type, 400-700°F typical, >800°F dangerous
    'exhaust_temp': {'low': 350, 'high': 750, 'unit': '°F'},
    # Oil temp: Normal 180-220°F, degradation accelerates >230°F
    'oil_temp': {'low': 160, 'high': 220, 'unit': '°F'},
    # Radiator temp: Should track coolant, slightly higher
    'radiator_temp': {'low': 160, 'high': 210, 'unit': '°F'},
    # Thermal efficiency: Modern systems 80-95%, <70% indicates problems
    'thermal_efficiency': {'low': 70, 'high': 95, 'unit': '%'},
    # Heat dissipation: System-specific, excessive indicates overload
    'heat_dissipation': {'low': 100, 'high': 4000, 'unit': 'W'},
    # Inlet temp: Cooling system intake, should be ambient
    'inlet_temp': {'low': 55, 'high': 100, 'unit': '°F'},
    # Outlet temp: Higher than inlet by design delta-T
    'outlet_temp': {'low': 90, 'high': 170, 'unit': '°F'},
    # Core temp: Internal component temperature
    'core_temp': {'low': 150, 'high': 210, 'unit': '°F'},
    # Surface temp: External touch temperature, <140°F safe for brief contact
    'surface_temp': {'low': 75, 'high': 150, 'unit': '°F'},

    # ELECTRICAL SENSORS
    # Voltage: US standard 120V ±5% (114-126V normal), ±10% acceptable
    'voltage': {'low': 114, 'high': 126, 'unit': 'V'},
    # Current: Load-dependent, should not exceed circuit rating
    'current': {'low': 0.5, 'high': 40, 'unit': 'A'},
    # Power factor: IEEE recommends >0.9, utilities penalize <0.85
    'power_factor': {'low': 0.85, 'high': 1.0, 'unit': 'PF'},
    # Frequency: US 60Hz ±0.5Hz for grid stability
    'frequency': {'low': 59.5, 'high': 60.5, 'unit': 'Hz'},
    # Resistance: Application-specific, high resistance indicates degradation
    'resistance': {'low': 0.5, 'high': 75, 'unit': 'Ω'},
    # Capacitance: Should match design value ±20%
    'capacitance': {'low': 50, 'high': 800, 'unit': 'μF'},
    # Inductance: Should match design value
    'inductance': {'low': 0.5, 'high': 8, 'unit': 'mH'},
    # Phase angle: Unity power factor = 0°, typical inductive loads 30-45°
    'phase_angle': {'low': -45, 'high': 45, 'unit': '°'},
    # Harmonic distortion: IEEE 519 - <5% excellent, 5-8% good, >10% problem
    'harmonic_distortion': {'low': 0, 'high': 8, 'unit': '%'},
    # Ground fault: >6mA personnel hazard (GFCI trips at 5mA), >30mA equipment protection
    'ground_fault': {'low': 0, 'high': 25, 'unit': 'mA'},

    # FLUID DYNAMICS SENSORS
    # Flow rate: System-specific, too low = blockage, too high = pump issue
    'flow_rate': {'low': 50, 'high': 400, 'unit': 'L/min'},
    # Fluid pressure: System operating pressure limits
    'fluid_pressure': {'low': 10, 'high': 80, 'unit': 'PSI'},
    # Viscosity: Temperature-dependent, should match spec for lubricant/coolant
    'viscosity': {'low': 10, 'high': 75, 'unit': 'cP'},
    # Density: Fluid-specific, contamination changes density
    'density': {'low': 0.8, 'high': 1.2, 'unit': 'g/cm³'},
    # Reynolds number: <2300 laminar, 2300-4000 transition, >4000 turbulent
    'reynolds_number': {'low': 2500, 'high': 8000, 'unit': ''},
    # Pipe pressure drop: Excessive indicates blockage or pump problems
    'pipe_pressure_drop': {'low': 1, 'high': 35, 'unit': 'PSI'},
    # Pump efficiency: Modern pumps 70-90%, <65% indicates wear/cavitation
    'pump_efficiency': {'low': 70, 'high': 95, 'unit': '%'},
    # Cavitation index: <2 low risk, 2-5 moderate, >5 high risk of damage
    'cavitation_index': {'low': 0, 'high': 5, 'unit': ''},
    # Turbulence: Application-specific, excessive can cause vibration
    'turbulence': {'low': 0, 'high': 60, 'unit': '%'},
    # Valve position: 0-100%, near limits may indicate control issues
    'valve_position': {'low': 5, 'high': 95, 'unit': '%'}
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Log progress every N messages
LOG_PROGRESS_INTERVAL = 10

# ============================================================================
# ML DETECTION CONFIGURATION
# ============================================================================

# Enable/disable ML-based anomaly detection
ML_DETECTION_ENABLED = True

# Isolation Forest parameters
ISOLATION_FOREST_CONTAMINATION = 0.05  # Expected anomaly rate (5%)
ISOLATION_FOREST_N_ESTIMATORS = 100  # Number of trees
MIN_TRAINING_SAMPLES = 100  # Minimum readings before training model

# Context analysis settings
CONTEXT_WINDOW_SIZE = 10  # Readings before/after anomaly to analyze

# Model storage path
MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')

# ============================================================================
# LSTM AUTOENCODER CONFIGURATION
# ============================================================================

# Enable/disable LSTM Autoencoder (requires TensorFlow)
LSTM_ENABLED = os.environ.get('LSTM_ENABLED', 'true').lower() == 'true'

# LSTM Model Parameters
LSTM_SEQUENCE_LENGTH = int(os.environ.get('LSTM_SEQUENCE_LENGTH', '20'))
LSTM_ENCODING_DIM = int(os.environ.get('LSTM_ENCODING_DIM', '32'))
LSTM_THRESHOLD_PERCENTILE = float(os.environ.get('LSTM_THRESHOLD_PERCENTILE', '95'))

# Minimum readings required before using LSTM
LSTM_MIN_READINGS = int(os.environ.get('LSTM_MIN_READINGS', '100'))

# ============================================================================
# HYBRID DETECTION CONFIGURATION
# ============================================================================

# Hybrid Detection Strategy
# Options:
#   'isolation_forest' - Only use Isolation Forest (default, fast)
#   'lstm' - Only use LSTM (requires TensorFlow and trained model)
#   'hybrid_or' - Flag anomaly if EITHER method detects it
#   'hybrid_and' - Flag anomaly only if BOTH methods agree
#   'hybrid_smart' - IF primary, LSTM catches what IF misses (recommended)
HYBRID_DETECTION_STRATEGY = os.environ.get('HYBRID_DETECTION_STRATEGY', 'hybrid_smart')

# ============================================================================
# AI REPORT GENERATION CONFIGURATION (Groq)
# ============================================================================

# Groq API key - loaded from .env file or environment variable
# Get your free API key at: https://console.groq.com/keys
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

# Log API key status (without revealing the key)
if GROQ_API_KEY and GROQ_API_KEY.startswith('gsk_'):
    logging.info("Groq API key loaded successfully (starts with 'gsk_')")
elif GROQ_API_KEY:
    logging.warning("GROQ_API_KEY is set but doesn't start with 'gsk_' - may be invalid")
else:
    logging.warning("GROQ_API_KEY not set - AI reports will use fallback mode. Set it in .env file or environment.")

# Groq API endpoint (OpenAI-compatible)
GROQ_BASE_URL = 'https://api.groq.com/openai/v1'

# Model to use for report generation (Groq models)
# Options: 'llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768'
AI_MODEL = 'llama-3.3-70b-versatile'

# Legacy OpenAI config (kept for backwards compatibility)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
CHATGPT_MODEL = 'gpt-4'

# ============================================================================
# ANOMALY INJECTION CONFIGURATION
# ============================================================================

# Default injection settings (can be overridden via UI)
ANOMALY_INJECTION_ENABLED = False  # Disabled by default
ANOMALY_INJECTION_INTERVAL_MINUTES = 30  # Default: inject every 30 minutes

# Number of sensors to affect when injecting an anomaly
INJECTION_MIN_SENSORS = 3
INJECTION_MAX_SENSORS = 7

# How far outside thresholds to push anomalous values (as % of range)
INJECTION_DEVIATION_MIN = 0.1  # 10% outside threshold
INJECTION_DEVIATION_MAX = 0.5  # 50% outside threshold