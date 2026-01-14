# BACKEND CODE WALKTHROUGH
## Line-by-Line Explanation of Every Backend Component

**Document 04 of 09**  
**Reading Time:** 120-180 minutes  
**Level:** Advanced  
**Prerequisites:** Documents 01-03  
**Best for:** Developers wanting to modify or extend the system

---

## 📋 TABLE OF CONTENTS

1. [Configuration (config.py)](#1-configuration-configpy)
2. [Producer (producer.py)](#2-producer-producerpy)
3. [Consumer (consumer.py)](#3-consumer-consumerpy)
4. [ML Detection (ml_detector.py)](#4-ml-detection-ml_detectorpy)
5. [LSTM Detector (lstm_detector.py)](#5-lstm-detector-lstm_detectorpy)
6. [Combined Pipeline (combined_pipeline.py)](#6-combined-pipeline-combined_pipelinepy)
7. [Analysis Engine (analysis_engine.py)](#7-analysis-engine-analysis_enginepy)
8. [Report Generator (report_generator.py)](#8-report-generator-report_generatorpy)
9. [Prediction Engine (prediction_engine.py)](#9-prediction-engine-prediction_enginepy)

---

## 1. CONFIGURATION (config.py)

### 1.1 File Purpose

`config.py` is the **central configuration file** for the entire Rig Alpha system. Every module imports this file to access settings.

**Why centralized config?**
- Single source of truth
- Easy to modify settings
- Environment-aware (dev/production)
- No hardcoded values in code

### 1.2 Imports and Environment Loading

**Lines 1-24:**
```python
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
```

**Explanation line-by-line:**

**Line 1-4:** Module docstring
- Documents purpose of the file
- Shows up in `help(config)` and IDE tooltips

**Line 6-8:** Standard library imports
- `os`: Access environment variables and file paths
- `logging`: For configuration logging
- `urlparse`: Parse DATABASE_URL for cloud deployments

**Line 12-13:** Try to import `dotenv`
- `python-dotenv` loads `.env` file into `os.environ`
- Not required in production (uses container environment)

**Line 15:** Find `.env` file path
- `__file__` = Path to config.py
- `os.path.dirname(__file__)` = Directory containing config.py
- `os.path.join(...)` = Full path to .env file

**Line 16-17:** Load if exists
- Check file exists first (safe)
- Load variables into environment
- Log success for debugging

**Line 19-20:** Fallback
- Try current directory if not found
- Allows flexible .env placement

**Line 21-24:** Exception handling
- If `python-dotenv` not installed, continue
- System will use OS environment variables
- No crash, graceful degradation

### 1.3 Timing Configuration

**Lines 26-54:**
```python
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
```

**Explanation:**

**Line 32-33:** Default values
- `DURATION_HOURS = 999`: Run "forever" (41 days)
- `INTERVAL_SECONDS = 1`: Generate 1 reading per second

**Why 999 hours?**
- Practical "infinite" - longer than any realistic session
- Avoids actual infinity (could cause bugs)
- User stops manually via dashboard button

**Lines 36-46:** Validation limits
- Dictionary structure for easy lookup
- Dashboard uses this to validate user input
- Prevents absurd values (e.g., -1 hours, 1 million seconds)

**Why max 168 hours (1 week)?**
- Longest realistic continuous run
- Beyond 1 week, restart for system health
- Database cleanup typically weekly

**Why max 3600 seconds (1 hour)?**
- Slower than 1 reading/hour = not "real-time"
- If need slower, rethink architecture

**Lines 50-54:** Actual config values
- Start with defaults
- Can be overridden by dashboard
- Producer reads these values

### 1.4 Kafka Configuration

**Lines 56-109:**
```python
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
```

**Explanation line-by-line:**

**Line 60:** Bootstrap servers
```python
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BROKER_URL', 'localhost:9092')
```
- `os.environ.get(key, default)`: Get environment variable or default
- Local dev: `localhost:9092`
- Cloud (Upstash): `xxx.upstash.io:9092`

**Line 61:** Topic name
```python
KAFKA_TOPIC = 'sensor-data'
```
- All sensor readings published to this topic
- Consumers subscribe to same topic
- Could have multiple topics (e.g., 'anomalies', 'alerts')

**Lines 64-67:** SASL authentication
```python
KAFKA_SASL_USERNAME = os.environ.get('KAFKA_SASL_USERNAME', '')
KAFKA_SASL_PASSWORD = os.environ.get('KAFKA_SASL_PASSWORD', '')
KAFKA_USE_SASL = bool(KAFKA_SASL_USERNAME and KAFKA_SASL_PASSWORD)
```
- SASL = Simple Authentication and Security Layer
- Only used for cloud Kafka (Upstash)
- Local Docker doesn't need authentication
- `KAFKA_USE_SASL`: True only if BOTH username AND password set

**Lines 70-78:** Producer config dictionary
```python
KAFKA_PRODUCER_CONFIG = {
    'bootstrap_servers': KAFKA_BOOTSTRAP_SERVERS,
    'acks': 'all',  # ← CRITICAL!
    ...
}
```

**Parameter explanations:**

**`'acks': 'all'`** - Most important setting!
- `0`: Fire and forget (fast, can lose data)
- `1`: Wait for leader (medium reliability)
- `'all'` or `-1`: Wait for ALL replicas (maximum safety)
- **Why 'all':** Sensor data critical, cannot lose

**`'retries': 5`** - Automatic retry
- If send fails, retry up to 5 times
- Handles temporary network issues
- With exponential backoff (below)

**`'retry_backoff_ms': 300`** - Wait between retries
- First retry: 300ms
- Second: 600ms (doubles)
- Third: 1200ms
- Exponential backoff built-in

**`'request_timeout_ms': 30000`** - Give up after 30 seconds
- Per request timeout
- Prevents hanging forever
- 30s reasonable for network hiccups

**`'max_in_flight_requests_per_connection': 1`** - Preserve order!
- Only send 1 message at a time
- Ensures ordering even with retries
- Slower but guaranteed order
- **Critical for time-series data**

**Example why ordering matters:**
```
Without this:
  Send: msg1(t=1), msg2(t=2), msg3(t=3)
  msg2 fails → retry
  Received: msg1(t=1), msg3(t=3), msg2(t=2)  ← Out of order!
  LSTM sees: t=1, t=3, t=2  ← Breaks temporal analysis!

With max_in_flight=1:
  Send: msg1(t=1) → wait → msg2(t=2) → wait → msg3(t=3)
  Always in order!
```

**`'api_version_auto_timeout_ms': 10000`** - Protocol negotiation
- Kafka client discovers broker API version
- 10 seconds to complete handshake
- Usually takes < 1 second

**`'value_serializer': lambda v: v.encode('utf-8')`** - Encode messages
- Kafka stores bytes, not strings
- Lambda function: Anonymous inline function
- `v.encode('utf-8')`: Convert string → bytes using UTF-8 encoding
- Called automatically for each message

**Lines 81-87:** Add SASL if cloud
```python
if KAFKA_USE_SASL:
    KAFKA_PRODUCER_CONFIG.update({
        'security_protocol': 'SASL_SSL',
        'sasl_mechanism': 'SCRAM-SHA-256',
        ...
    })
```
- `.update()`: Merge new keys into existing dict
- Only runs if using cloud Kafka
- Local development skips this block

**SASL parameters:**

**`'security_protocol': 'SASL_SSL'`**
- SASL = Authentication
- SSL = Encryption
- Combined: Authenticated + Encrypted connection

**`'sasl_mechanism': 'SCRAM-SHA-256'`**
- SCRAM = Salted Challenge Response Authentication Mechanism
- SHA-256 = Cryptographic hash function
- Secure password authentication without sending password plaintext

### 1.5 Database Configuration (Cloud-Aware)

**Lines 111-165:**
```python
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
```

**Explanation:**

**Line 116:** Get DATABASE_URL
```python
DATABASE_URL = os.environ.get('DATABASE_URL', '')
```
- Cloud platforms (Render, Heroku, Neon) provide DATABASE_URL
- Format: `postgresql://user:pass@host:port/dbname?sslmode=require`
- Empty string if not set (use local defaults)

**Lines 119-122:** Masked logging
```python
if DATABASE_URL:
    masked_url = DATABASE_URL[:20] + '...'
    print(f"Connecting to: {masked_url}")
```
- **Security**: Never log full URL (contains password!)
- Show first 20 chars only: `postgresql://user:pas...`
- Enough to verify which DB, not enough to expose credentials

**Lines 124-129:** postgres:// → postgresql://
```python
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
```
- Some platforms use `postgres://` (deprecated)
- psycopg2 requires `postgresql://` (current standard)
- `.replace(..., 1)`: Replace only first occurrence

**Lines 132-137:** Parse URL
```python
parsed = urlparse(DATABASE_URL)

DB_HOST = parsed.hostname or 'localhost'
DB_PORT = parsed.port or 5432
DB_NAME = parsed.path.lstrip('/') if parsed.path else 'sensordb'
DB_USER = parsed.username or 'sensoruser'
DB_PASSWORD = parsed.password or 'sensorpass'
```

**urlparse example:**
```python
URL: "postgresql://user123:pass456@ep-cool-123.aws.neon.tech:5432/neondb?sslmode=require"

parsed.hostname = "ep-cool-123.aws.neon.tech"
parsed.port = 5432
parsed.path = "/neondb"
parsed.username = "user123"
parsed.password = "pass456"
```

**`or` fallbacks:**
- If any component missing, use sensible default
- `.lstrip('/')`: Remove leading slash from path ("/neondb" → "neondb")

**Lines 140-148:** Local fallback
```python
else:
    # Fallback to local defaults
    DB_HOST = 'localhost'
    DB_PORT = 5432
    ...
```
- If no DATABASE_URL, assume local Docker
- Standard PostgreSQL port: 5432
- Matches docker-compose.yml settings

**Lines 151:** Connection string
```python
DB_CONNECTION_STRING = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"
```
- Format psycopg2 expects
- Used by older code (before connection pooling)

**Lines 154-160:** DB_CONFIG dictionary
```python
DB_CONFIG = {
    'host': DB_HOST,
    'port': DB_PORT,
    'database': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD
}
```
- Dictionary format psycopg2 also accepts
- Cleaner than connection string
- Used by connection pool

**Lines 163-165:** Add SSL for cloud
```python
if DATABASE_URL and ('neon' in DATABASE_URL.lower() or 'sslmode' in DATABASE_URL.lower()):
    DB_CONFIG['sslmode'] = 'require'
```
- Cloud databases require SSL
- Check if "neon" or "sslmode" in URL
- Add 'sslmode': 'require' to config
- psycopg2 will use encrypted connection

### 1.6 Sensor Ranges and Thresholds

**Lines 183-256 (Environmental Sensors Example):**
```python
SENSOR_RANGES = {
    # ENVIRONMENTAL SENSORS (10)
    'temperature': {'min': 60.0, 'max': 100.0, 'unit': '°F', 'category': 'environmental'},
    'pressure': {'min': 0.0, 'max': 15.0, 'unit': 'PSI', 'category': 'environmental'},
    'humidity': {'min': 20.0, 'max': 80.0, 'unit': '%', 'category': 'environmental'},
    ...
}

SENSOR_THRESHOLDS = {
    # Temperature: Indoor comfort 65-78°F, industrial up to 85°F safe
    'temperature': {'low': 65.0, 'high': 85.0, 'unit': '°F'},
    # Pressure: Atmospheric ~14.7 PSI, slight overpressure acceptable
    'pressure': {'low': 2.0, 'high': 12.0, 'unit': 'PSI'},
    ...
}
```

**Explanation:**

**SENSOR_RANGES** - Physical limits
- **min/max**: Absolute physical range sensor can measure
- **unit**: Measurement unit for display
- **category**: Group for UI organization
- Producer clamps values to this range

**SENSOR_THRESHOLDS** - Safe operating limits
- **low/high**: Warning thresholds for alerts
- Inside range: Normal (green)
- Outside range: Anomaly (red)
- Used by rule-based detection

**Example:**
```python
'temperature': {
    'min': 60.0,   # Sensor can measure down to 60°F
    'max': 100.0,  # Sensor can measure up to 100°F
    'unit': '°F',
    'category': 'environmental'
}

Thresholds:
'temperature': {
    'low': 65.0,   # Below 65°F = too cold
    'high': 85.0,  # Above 85°F = too hot
}

Values:
  62°F: In range (60-100), below threshold → ALERT (too cold)
  75°F: In range, in threshold → Normal
  90°F: In range, above threshold → ALERT (too hot)
  105°F: Out of range → Clipped to 100°F
```

### 1.7 ML Configuration

**Lines 389-474:**
```python
# ML DETECTION CONFIGURATION
ML_DETECTION_ENABLED = True

# Isolation Forest parameters
ISOLATION_FOREST_CONTAMINATION = 0.05  # Expected anomaly rate (5%)
ISOLATION_FOREST_N_ESTIMATORS = 100  # Number of trees
MIN_TRAINING_SAMPLES = 100  # Minimum readings before training model

# LSTM AUTOENCODER CONFIGURATION
LSTM_ENABLED = os.environ.get('LSTM_ENABLED', 'true').lower() == 'true'
LSTM_SEQUENCE_LENGTH = int(os.environ.get('LSTM_SEQUENCE_LENGTH', '20'))
LSTM_ENCODING_DIM = int(os.environ.get('LSTM_ENCODING_DIM', '32'))
LSTM_THRESHOLD_PERCENTILE = float(os.environ.get('LSTM_THRESHOLD_PERCENTILE', '95'))
LSTM_MIN_READINGS = int(os.environ.get('LSTM_MIN_READINGS', '100'))

# HYBRID DETECTION CONFIGURATION
HYBRID_DETECTION_STRATEGY = os.environ.get('HYBRID_DETECTION_STRATEGY', 'hybrid_smart')

# AI REPORT GENERATION CONFIGURATION (Groq)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_BASE_URL = 'https://api.groq.com/openai/v1'
AI_MODEL = 'llama-3.3-70b-versatile'
```

**Explanation:**

**Line 393:** Enable ML
```python
ML_DETECTION_ENABLED = True
```
- Master switch for ML detection
- Set to False to disable all ML (rule-based only)

**Line 396:** Contamination
```python
ISOLATION_FOREST_CONTAMINATION = 0.05  # 5%
```
- Tells Isolation Forest: "Expect about 5% of data to be outliers"
- Industry standard: 1-10% anomaly rate
- 5% = good balance

**Line 397:** N_estimators
```python
ISOLATION_FOREST_N_ESTIMATORS = 100
```
- Number of decision trees in forest
- More trees = More accurate but slower
- 100 = Good balance for real-time

**Line 398:** Min training samples
```python
MIN_TRAINING_SAMPLES = 100
```
- Won't train model with < 100 readings
- Need sufficient data for patterns
- Collects normal data first

**Lines 410-413:** LSTM config
```python
LSTM_ENABLED = os.environ.get('LSTM_ENABLED', 'true').lower() == 'true'
```
- Can disable via environment variable
- `.lower() == 'true'`: Case-insensitive boolean
- Allows: `LSTM_ENABLED=TRUE`, `lstm_enabled=True`, etc.

**Line 411:** Sequence length
```python
LSTM_SEQUENCE_LENGTH = int(os.environ.get('LSTM_SEQUENCE_LENGTH', '20'))
```
- LSTM analyzes last 20 readings
- 20 readings × 1 sec = 20 seconds history
- Longer = Better for gradual trends, Slower
- Shorter = Faster response, Misses long patterns

**Line 412:** Encoding dimension
```python
LSTM_ENCODING_DIM = int(os.environ.get('LSTM_ENCODING_DIM', '32'))
```
- Bottleneck size in autoencoder
- Compresses 50 features → 32 → 50
- Smaller = More compression, might lose information
- 32 = Good balance

**Line 413:** Threshold percentile
```python
LSTM_THRESHOLD_PERCENTILE = float(os.environ.get('LSTM_THRESHOLD_PERCENTILE', '95'))
```
- Flag top 5% of reconstruction errors as anomalies
- 95 = Flag if in worst 5%
- 90 = More sensitive (flag top 10%)
- 99 = Less sensitive (flag top 1%)

**Line 421:** Hybrid strategy
```python
HYBRID_DETECTION_STRATEGY = os.environ.get('HYBRID_DETECTION_STRATEGY', 'hybrid_smart')
```
- Combines Isolation Forest + LSTM
- Options:
  - `'isolation_forest'`: IF only
  - `'lstm'`: LSTM only
  - `'hybrid_or'`: Either flags → anomaly
  - `'hybrid_and'`: Both must flag
  - `'hybrid_smart'`: IF primary, LSTM backup (recommended)

**Lines 436-439:** Groq API
```python
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_BASE_URL = 'https://api.groq.com/openai/v1'
AI_MODEL = 'llama-3.3-70b-versatile'
```
- Groq provides fast LLM inference
- API key from environment (security best practice)
- Base URL: OpenAI-compatible endpoint
- Model: 70 billion parameter LLaMA 3.3

---

## 2. PRODUCER (producer.py)

### 2.1 Overview and Purpose

`producer.py` generates simulated sensor data and publishes to Kafka.

**Real-world equivalent:**
- Edge gateway collecting sensor readings
- PLC (Programmable Logic Controller) outputs
- SCADA system data

**Why simulation?**
- Testing without physical sensors
- Reproducible data for development
- Demonstrates complete system

### 2.2 Class Initialization

**Lines 45-76:**
```python
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
        
        # Anomaly injection state
        self.last_injection_check = None
        self.next_injection_time = None
        self.custom_thresholds = {}
        
        # Custom sensors state
        self.custom_sensors = {}
        self.last_config_reload = None
        self.config_reload_interval = 60
```

**Explanation:**

**Line 46:** Class definition
```python
class SensorDataProducer:
```
- Encapsulates all producer logic
- Object-oriented design
- Reusable, testable

**Line 49:** `__init__` constructor
```python
def __init__(self):
```
- Called when creating instance: `producer = SensorDataProducer()`
- Initializes state
- Sets up resources

**Line 51:** Setup logging
```python
self.setup_logging()
```
- Calls method to configure logging
- Must be first (need logger for everything else)

**Line 52-54:** Instance variables
```python
self.producer = None  # Kafka producer (created later)
self.message_count = 0  # Track messages sent
self.total_messages = int((config.DURATION_HOURS * 3600) / config.INTERVAL_SECONDS)
```

**Total messages calculation:**
```python
Duration: 999 hours
Interval: 1 second

Hours → Seconds: 999 × 3600 = 3,596,400 seconds
Messages: 3,596,400 / 1 = 3,596,400 messages

(If run for full duration)
```

**Line 55:** Shutdown flag
```python
self.should_shutdown = False
```
- Set to True when SIGINT (Ctrl+C) received
- Main loop checks this flag
- Allows graceful shutdown

**Lines 58-62:** Signal handlers
```python
signal.signal(signal.SIGINT, self.signal_handler)
signal.signal(signal.SIGTERM, self.signal_handler)
```
- **SIGINT**: Ctrl+C in terminal
- **SIGTERM**: Sent by `kill` command or system shutdown
- **SIGBREAK** (Windows): Ctrl+Break
- All call `self.signal_handler` method

**Why signal handlers?**
```python
Without:
  User presses Ctrl+C
  Process killed immediately
  Kafka producer buffer not flushed
  Last few messages lost!

With:
  User presses Ctrl+C
  signal_handler sets should_shutdown = True
  Main loop exits cleanly
  Producer flushes buffer
  All messages safely sent
  Clean shutdown ✓
```

**Lines 68-70:** Custom sensors
```python
self.custom_sensors = {}  # Loaded from database
self.last_config_reload = None  # Last reload time
self.config_reload_interval = 60  # Reload every 60 seconds
```
- Custom sensors defined by users
- Periodically reload from database
- Allows adding sensors without restart

### 2.3 Sensor Reading Generation with Correlations

**Lines 266-604:** (Simplified key sections)

```python
def generate_sensor_reading(self):
    """Generate a correlated sensor reading with all 50 parameters."""
    
    # Start with RPM as the base - machinery speed drives other values
    rpm = round(random.uniform(
        config.SENSOR_RANGES['rpm']['min'],
        config.SENSOR_RANGES['rpm']['max']
    ), 2)

    # Normalize RPM to 0-1 range for correlations
    rpm_normalized = (rpm - config.SENSOR_RANGES['rpm']['min']) / (
        config.SENSOR_RANGES['rpm']['max'] - config.SENSOR_RANGES['rpm']['min']
    )

    # === ENVIRONMENTAL SENSORS ===
    # Higher RPM = Higher temperature (machinery heats up with speed)
    temp_min = config.SENSOR_RANGES['temperature']['min']
    temp_max = config.SENSOR_RANGES['temperature']['max']
    temperature = round(temp_min + (rpm_normalized * (temp_max - temp_min)) + random.uniform(-5, 5), 2)
    temperature = max(temp_min, min(temp_max, temperature))
```

**Explanation line-by-line:**

**Lines 275-279:** Generate base RPM
```python
rpm = round(random.uniform(
    config.SENSOR_RANGES['rpm']['min'],  # 1000
    config.SENSOR_RANGES['rpm']['max']   # 5000
), 2)
```
- `random.uniform(a, b)`: Random float between a and b
- Uniform distribution (all values equally likely)
- `.round(..., 2)`: Round to 2 decimal places
- Result: 1000.00 to 5000.00

**Lines 282-284:** Normalize to 0-1
```python
rpm_normalized = (rpm - 1000) / (5000 - 1000)
```
- Scales RPM to 0.0-1.0 range
- 1000 RPM → 0.0
- 3000 RPM → 0.5
- 5000 RPM → 1.0

**Why normalize?**
- Easy to calculate correlations
- `temperature = base + (normalized × range)` formula
- Works for any sensor range

**Lines 289-291:** Temperature correlation
```python
temperature = temp_min + (rpm_normalized * (temp_max - temp_min)) + random.uniform(-5, 5)
```

**Breaking down the formula:**
```python
Base temperature: temp_min = 60°F

If RPM normalized = 0.5 (mid-range):
  Correlation component: 0.5 × (100 - 60) = 0.5 × 40 = 20°F
  Base + correlation: 60 + 20 = 80°F
  
Add noise: random.uniform(-5, 5)
  Could be: -3.2°F
  Final: 80 - 3.2 = 76.8°F
  
Result: Mid RPM → Mid temperature with realistic variation
```

**Why add noise `random.uniform(-5, 5)`?**
- Real sensors have measurement noise
- Not perfectly correlated (other factors exist)
- Makes data realistic
- ML models learn to handle noise

**Line 292:** Clamp to range
```python
temperature = max(temp_min, min(temp_max, temperature))
```
- Ensures value within physical limits
- `min(value, max)`: Cap at maximum
- `max(min_value, ...)`: Raise to minimum
- Prevents impossible values

**Example:**
```python
temp_min = 60, temp_max = 100

If temperature = 105 (too high):
  min(105, 100) = 100
  max(60, 100) = 100  ← Clamped to max

If temperature = 55 (too low):
  min(55, 100) = 55
  max(60, 55) = 60  ← Clamped to min

If temperature = 75 (valid):
  min(75, 100) = 75
  max(60, 75) = 75  ← Unchanged
```

**Similar pattern for all 50 sensors:**
- Some correlate positively with RPM (temperature, vibration)
- Some correlate negatively with temperature (humidity)
- Some correlate with each other (bearing_temp ↔ lubrication_pressure)
- All have realistic noise and clamping

### 2.4 Kafka Message Sending

**Lines 606-661:**
```python
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

        # Log message sent with key parameters
        self.logger.info(f"Message {self.message_count}/{self.total_messages} sent: "
                       f"timestamp={data['timestamp']}, "
                       f"rpm={data['rpm']}, "
                       f"temp={data['temperature']}°F, "
                       f"vibration={data['vibration']}mm/s")

        # Log progress every N messages
        if self.message_count % config.LOG_PROGRESS_INTERVAL == 0:
            progress = (self.message_count / self.total_messages) * 100
            self.logger.info(f"Progress: {self.message_count}/{self.total_messages} "
                           f"({progress:.1f}%) messages sent")

        return True

    except Exception as e:
        self.logger.error(f"Failed to send message: {e}")
        return False
```

**Explanation:**

**Line 610:** Serialize to JSON
```python
message = json.dumps(data)
```
- `data`: Python dictionary
- `json.dumps()`: Convert dict → JSON string
- Kafka stores bytes, needs serialization

**Example:**
```python
data = {
    'timestamp': '2026-01-12T15:30:00',
    'temperature': 75.5,
    'rpm': 3500
}

message = '{"timestamp": "2026-01-12T15:30:00", "temperature": 75.5, "rpm": 3500}'
```

**Line 613:** Send to Kafka
```python
future = self.producer.send(config.KAFKA_TOPIC, value=message)
```
- `.send()`: Asynchronous operation
- Returns `Future` object (promise of result)
- Doesn't block immediately
- Message queued for sending

**Line 616:** Wait for acknowledgment
```python
record_metadata = future.get(timeout=10)
```
- `.get()`: Block until complete (makes it synchronous)
- `timeout=10`: Wait max 10 seconds
- Returns metadata if successful
- Raises exception if failed

**Why `.get()`?**
```python
Without .get() (fire and forget):
  Send message
  Return immediately
  Don't know if succeeded
  Might lose data!

With .get() (synchronous):
  Send message
  Wait for Kafka acknowledgment
  Know it's safely stored
  Guaranteed delivery
```

**Line 618:** Increment counter
```python
self.message_count += 1
```
- Track total messages sent
- Used for progress logging
- Used for statistics

**Lines 621-625:** Logging
```python
self.logger.info(f"Message {self.message_count}/{self.total_messages} sent: ...")
```
- Log every message (useful for debugging)
- Shows key parameters (timestamp, rpm, temp, vibration)
- Human-readable format

**Lines 628-632:** Progress logging
```python
if self.message_count % config.LOG_PROGRESS_INTERVAL == 0:
    progress = (self.message_count / self.total_messages) * 100
    self.logger.info(f"Progress: {self.message_count}/{self.total_messages} ({progress:.1f}%)")
```
- `%` modulo operator: Remainder after division
- `10 % 10 = 0`: Every 10th message
- Only log every Nth message (reduce spam)
- Shows progress percentage

**Example:**
```
LOG_PROGRESS_INTERVAL = 10

Message 9: No log
Message 10: "Progress: 10/1000 (1.0%)" ← Logged!
Message 11: No log
...
Message 20: "Progress: 20/1000 (2.0%)" ← Logged!
```

---

*[Due to space constraints, continuing with essential sections of remaining files]*

---

## 3. CONSUMER (consumer.py)

### 3.1 Key Sections Overview

The consumer:
1. **Connects** to Kafka and PostgreSQL
2. **Polls** for messages
3. **Validates** messages
4. **Inserts** to database
5. **Runs ML detection**
6. **Updates telemetry** for 3D twin
7. **Commits offset** (exactly-once semantics)

### 3.2 Message Processing Pipeline

**Lines 453-517 (Simplified):**
```python
def process_message(self, message):
    """Process a single message from Kafka."""
    try:
        # 1. Decode and parse JSON
        data = json.loads(message.value)

        # 2. Validate message
        if not self.validate_message(data):
            self.logger.warning(f"Invalid message skipped")
            self.consumer.commit()  # Still commit (don't reprocess)
            return False

        # 3. Check for rule-based anomalies
        anomalies = self.detect_anomalies(data)
        if anomalies:
            for anomaly in anomalies:
                self.logger.warning(f"Rule-based anomaly: {anomaly}")
                self.record_alert('SENSOR_ANOMALY', anomaly, severity='CRITICAL')
            self.consumer.commit()  # Commit even if anomaly
            return False

        # 4. Insert into database
        reading_id = self.insert_reading(data)
        if reading_id:
            # 5. ONLY commit offset after successful DB insert
            self.consumer.commit()
            
            self.message_count += 1
            self.logger.info(f"Message {self.message_count} processed: DB_ID={reading_id}")

            # 6. Run ML detection (non-blocking)
            ml_result = self.run_ml_detection(data, reading_id)

            # 7. Update 3D telemetry (non-blocking)
            self.update_3d_telemetry(data, ml_result)

            return True
        else:
            # Insert failed - DON'T commit
            # Message will be reprocessed on next poll
            self.logger.error("Insert failed - will retry")
            return False

    except Exception as e:
        self.logger.error(f"Error processing message: {e}", exc_info=True)
        return False
```

**Key Point - Exactly-Once Semantics:**

```python
# This order is CRITICAL:
1. Insert to database
2. IF successful → commit offset
3. IF failed → DON'T commit

Result:
  Success: Message processed once, offset committed
  Failure: Message NOT committed, will be redelivered
  
Idempotent operations:
  If message reprocessed, insert might succeed second time
  OR duplicate key error (reading already exists)
  Either way, data not lost!
```

---

## 4. ML DETECTION (ml_detector.py)

### 4.1 Isolation Forest Implementation

**Lines 40-68:**
```python
class AnomalyDetector:
    """Isolation Forest-based anomaly detector."""
    
    SENSOR_COLUMNS = [
        'temperature', 'pressure', 'humidity', ...,  # All 50 sensors
    ]

    def __init__(self, contamination=None, n_estimators=None):
        """Initialize the anomaly detector."""
        self.contamination = contamination or config.ISOLATION_FOREST_CONTAMINATION
        self.n_estimators = n_estimators or config.ISOLATION_FOREST_N_ESTIMATORS
        
        self.model = IsolationForest(
            contamination=self.contamination,  # 0.05 (5%)
            n_estimators=self.n_estimators,    # 100 trees
            random_state=42,                   # Reproducible results
            n_jobs=-1                          # Use all CPU cores
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_means = None
        self.feature_stds = None
        
        self.logger = logging.getLogger(__name__)
        
        # Ensure models directory exists
        os.makedirs(config.MODELS_DIR, exist_ok=True)
        
        # Try to load existing model
        self._load_model()
```

**Explanation:**

**Line 48-50:** Model initialization
```python
self.model = IsolationForest(
    contamination=0.05,  # Expect 5% outliers
    n_estimators=100,    # 100 decision trees
    random_state=42,     # Seed for reproducibility
    n_jobs=-1           # Parallelize across all CPUs
)
```

**Key parameters:**

**`contamination=0.05`**
- Tells algorithm: "About 5% of data will be anomalous"
- Affects threshold calculation
- Industry standard: 1-10%

**`n_estimators=100`**
- Build 100 isolation trees
- Each tree votes on whether point is anomaly
- More trees = More accurate, slower
- 100 = Sweet spot

**`random_state=42`**
- Seed for random number generator
- Makes results reproducible
- Same seed → same tree splits every time
- Useful for debugging

**`n_jobs=-1`**
- Number of parallel jobs
- -1 = Use all available CPU cores
- Speeds up training and prediction

**Line 57:** StandardScaler
```python
self.scaler = StandardScaler()
```
- Normalizes features to mean=0, std=1
- **Critical for ML:** Different sensors have different scales
- Example:
  ```
  RPM: 1000-5000 (large numbers)
  vibration: 0-10 (small numbers)
  
  Without scaling:
    Model dominated by large-scale features
    
  With scaling:
    All features contribute equally
  ```

**Line 58-60:** State tracking
```python
self.is_trained = False      # Model trained yet?
self.feature_means = None    # For z-score calculation
self.feature_stds = None     # For z-score calculation
```

### 4.2 Model Training

**Lines 146-201 (Simplified):**
```python
def train(self, data=None):
    """Train the Isolation Forest model."""
    if data is None:
        data = self._fetch_training_data()
        
    if data is None or len(data) < config.MIN_TRAINING_SAMPLES:
        self.logger.warning(f"Not enough data. Need {config.MIN_TRAINING_SAMPLES}, got {len(data)}")
        return False

    try:
        # Extract sensor columns only
        feature_data = data[self.SENSOR_COLUMNS].copy()
        
        # Handle missing values
        feature_data = feature_data.fillna(feature_data.mean())
        
        # Store statistics for z-score analysis
        self.feature_means = feature_data.mean().to_dict()
        self.feature_stds = feature_data.std().to_dict()
        
        # Scale the data
        scaled_data = self.scaler.fit_transform(feature_data)
        
        # Train the model
        self.model.fit(scaled_data)
        self.is_trained = True
        
        # Save to disk
        self._save_model()
        
        self.logger.info(f"Trained Isolation Forest on {len(data)} samples")
        return True
        
    except Exception as e:
        self.logger.error(f"Training failed: {e}")
        return False
```

**Explanation:**

**Line 152-155:** Check minimum data
```python
if len(data) < config.MIN_TRAINING_SAMPLES:  # 100
    return False
```
- Need at least 100 readings
- Can't learn patterns from too little data
- Waits until enough data collected

**Line 159:** Extract features
```python
feature_data = data[self.SENSOR_COLUMNS].copy()
```
- Select only the 50 sensor columns
- Ignore timestamp, id, etc.
- `.copy()`: Don't modify original data

**Line 162:** Handle missing values
```python
feature_data = feature_data.fillna(feature_data.mean())
```
- Some sensors might be None/NULL
- `.fillna(mean)`: Replace with column average
- Simple but effective imputation

**Lines 165-166:** Store statistics
```python
self.feature_means = feature_data.mean().to_dict()
self.feature_stds = feature_data.std().to_dict()
```
- Calculate mean and std dev for each sensor
- Used later for z-score analysis
- Identifies which sensors contributed to anomaly

**Line 169:** Scale features
```python
scaled_data = self.scaler.fit_transform(feature_data)
```
- `.fit()`: Learn scaling parameters (mean, std)
- `.transform()`: Apply scaling
- Combined: `.fit_transform()`

**Example:**
```python
Original:
  temperature: [70, 75, 80, 85, 90]
  vibration: [1, 2, 3, 4, 5]

After StandardScaler:
  temperature: [-1.41, -0.71, 0, 0.71, 1.41]
  vibration: [-1.41, -0.71, 0, 0.71, 1.41]
  
Both now have mean=0, std=1
```

**Line 172:** Train model
```python
self.model.fit(scaled_data)
```
- Learn normal patterns from scaled data
- Builds 100 isolation trees
- Stores trees in model
- Ready for prediction

---

*[Continuing with remaining files in summary format due to length]*

---

## 5. LSTM DETECTOR (lstm_detector.py)

### Key Implementation Points:

**Model Architecture:**
```python
# Encoder
inputs = Input(shape=(sequence_length, n_features))  # (20, 50)
encoded = LSTM(128, activation='relu')(inputs)        # Compress
encoded = LSTM(64, activation='relu')(encoded)        # Compress more
encoded = Dense(32)(encoded)                          # Bottleneck

# Decoder  
decoded = RepeatVector(sequence_length)(encoded)      # Expand
decoded = LSTM(64, activation='relu')(decoded)        # Reconstruct
decoded = LSTM(128, activation='relu')(decoded)       # Reconstruct
outputs = TimeDistributed(Dense(n_features))(decoded) # Output: (20, 50)
```

**Detection Process:**
1. Get last 20 readings
2. Scale features
3. Reconstruct with autoencoder
4. Calculate MSE (Mean Squared Error)
5. If MSE > threshold → Anomaly!

---

## 6. COMBINED PIPELINE (combined_pipeline.py)

**Hybrid Smart Strategy:**
```python
def _detect_hybrid(self, reading, reading_id):
    # Step 1: Run Isolation Forest (fast)
    if_anomaly, if_score, if_sensors = self.if_detector.detect(reading)
    
    if if_anomaly:
        return True, if_score, if_sensors, 'isolation_forest'  # Return immediately
    
    # Step 2: IF said normal, check LSTM
    lstm_anomaly, lstm_error, lstm_sensors = self.lstm_detector.detect(sequence)
    
    if lstm_anomaly:
        return True, lstm_error, lstm_sensors, 'lstm_autoencoder'  # LSTM caught gradual issue
    
    # Step 3: Both say normal
    return False, if_score, if_sensors, 'isolation_forest'
```

---

## 7. ANALYSIS ENGINE (analysis_engine.py)

**Context Window Extraction:**
```python
def get_context_window(reading_id):
    # Get 10 readings before anomaly
    before = fetch_readings_before(reading_id, limit=10)
    
    # Get the anomalous reading
    anomaly = fetch_reading(reading_id)
    
    # Get 10 readings after
    after = fetch_readings_after(reading_id, limit=10)
    
    return {'before': before, 'anomaly': anomaly, 'after': after}
```

**Correlation Computation:**
```python
def compute_correlations(data):
    # Compute correlation matrix
    corr_matrix = data.corr()
    
    # Find significant correlations
    for sensor1, sensor2 in all_pairs:
        correlation = corr_matrix[sensor1, sensor2]
        if abs(correlation) > 0.5 and p_value < 0.05:
            significant_correlations.append({
                'sensor1': sensor1,
                'sensor2': sensor2,
                'correlation': correlation
            })
```

---

## 8. REPORT GENERATOR (report_generator.py)

**AI Prompt Construction:**
```python
def _build_prompt(anomaly_data, analysis_summary):
    prompt = f"""
    You are an industrial sensor analyst expert.
    
    ANOMALY DETECTED:
    - Score: {anomaly_score}
    - Method: {detection_method}
    - Sensors: {detected_sensors}
    
    TOP DEVIATIONS:
    {format_deviations(top_deviations)}
    
    CORRELATIONS:
    {format_correlations(significant_correlations)}
    
    Provide:
    1. Root Cause Analysis
    2. Affected Systems
    3. Severity Assessment
    4. Prevention Recommendations
    5. Immediate Actions
    """
    return prompt
```

---

## 9. PREDICTION ENGINE (prediction_engine.py)

**RUL Calculation:**
```python
def predict_rul(sensor_sequence):
    for sensor in ['vibration', 'temperature', 'bearing_temp']:
        values = sensor_sequence[sensor]
        
        # Linear regression: value = slope * time + intercept
        slope, intercept = np.polyfit(time_indices, values, 1)
        
        # Extrapolate to failure threshold
        threshold = failure_thresholds[sensor]
        hours_to_failure = (threshold - current_value) / slope_per_hour
        
        rul_predictions.append(hours_to_failure)
    
    # Return minimum (most critical sensor)
    return min(rul_predictions)
```

---

## 🎓 SUMMARY

You now understand the complete backend codebase:

✅ **Configuration**: All settings centralized in config.py  
✅ **Producer**: Generates correlated sensor data  
✅ **Consumer**: Processes messages with exactly-once semantics  
✅ **Isolation Forest**: Point-based anomaly detection  
✅ **LSTM**: Temporal pattern detection  
✅ **Combined Pipeline**: Hybrid detection strategy  
✅ **Analysis Engine**: Context and correlation analysis  
✅ **Report Generator**: AI-powered reports via Groq  
✅ **Prediction Engine**: RUL estimation  

**Next Document:** [05-CODE-DASHBOARD.md](05-CODE-DASHBOARD.md)
- Flask application walkthrough
- Authentication and authorization
- API endpoints
- WebSocket telemetry

---

*Continue to Document 05: Dashboard Code Walkthrough →*
