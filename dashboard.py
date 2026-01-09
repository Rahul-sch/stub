"""
Simple Web Dashboard for Sensor Data Pipeline
Provides controls and monitoring for the Kafka pipeline
"""

from flask import Flask, render_template, jsonify, request, make_response, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import subprocess
import os
import sys
import signal
import json
import threading
import time
import csv
import io
import logging
import psutil
from datetime import datetime, timezone
from functools import wraps
from psycopg2 import pool

# Flask-Talisman for CSP headers
try:
    from flask_talisman import Talisman
    TALISMAN_AVAILABLE = True
except ImportError:
    TALISMAN_AVAILABLE = False
    # Logger not yet initialized, use print for now
    print("Warning: Flask-Talisman not available. CSP headers will not be set.")

# Import PDF and AI libraries
try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
    print("[OK] PyPDF2 loaded successfully")
except ImportError as e:
    PDF_AVAILABLE = False
    print(f"Warning: PyPDF2 not available. PDF parsing will not work. Error: {e}")

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("Warning: groq library not available. AI parsing will use fallback.")
try:
    from kafka.admin import KafkaAdminClient
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
except ImportError:
    from kafka import KafkaAdminClient, KafkaProducer
    from kafka.errors import KafkaError

# Import ML components
try:
    from report_generator import ReportGenerator, get_report, get_report_by_anomaly
    from analysis_engine import ContextAnalyzer, get_anomaly_details
    from lstm_predictor import get_predictor, predict_next_anomaly
    from lstm_detector import get_lstm_detector, is_lstm_available
    ML_REPORTS_AVAILABLE = True
    LSTM_AVAILABLE = is_lstm_available()
except ImportError as e:
    ML_REPORTS_AVAILABLE = False
    LSTM_AVAILABLE = False
    print(f"ML report generation not available: {e}")

app = Flask(__name__)

# ============================================================================
# STRUCTURED LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE CONNECTION POOL
# ============================================================================
db_pool = None

def init_db_pool():
    """Initialize database connection pool."""
    global db_pool
    try:
        import config
        # Debug: Print connection info
        db_url_preview = os.environ.get('DATABASE_URL', '')[:20] + '...' if os.environ.get('DATABASE_URL', '') else 'local config'
        logger.info(f"Initializing database pool. DATABASE_URL preview: {db_url_preview}")
        logger.info(f"DB_CONFIG: host={config.DB_CONFIG.get('host', 'N/A')}, database={config.DB_CONFIG.get('database', 'N/A')}")
        
        db_pool = pool.ThreadedConnectionPool(
            minconn=5,
            maxconn=50,  # Increased to handle dashboard's concurrent API requests
            **config.DB_CONFIG
        )
        logger.info("Database connection pool initialized (minconn=5, maxconn=50)")
    except Exception as e:
        logger.error(f"Failed to initialize database connection pool: {e}")
        db_pool = None

# Initialize pool on module load
init_db_pool()

# ============================================================================
# CONTENT SECURITY POLICY (CSP) CONFIGURATION
# ============================================================================
if TALISMAN_AVAILABLE:
    csp = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            "'unsafe-inline'",
            "'unsafe-eval'",  # Required for Three.js and dynamic JavaScript
            'https://cdnjs.cloudflare.com',  # For Three.js library
            'https://cdn.jsdelivr.net'  # For OrbitControls
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",  # Required for inline styles
            'https://cdnjs.cloudflare.com',  # For Inter font
            'https://cdn.jsdelivr.net',  # For Gridstack CSS
            'https://fonts.googleapis.com'  # For Google Fonts if used
        ],
        'connect-src': [
            "'self'",
            'https://*.neon.tech',  # Allow Neon database connections
            'https://*.aws.neon.tech',  # Allow AWS Neon connections
            'https://cdn.jsdelivr.net',  # Allow Gridstack source maps
            'http://127.0.0.1:7243'  # Allow debug logging endpoint
        ],
        'font-src': [
            "'self'",
            'https://cdnjs.cloudflare.com',
            'https://fonts.gstatic.com'
        ],
        'img-src': "'self' data:",
        'frame-ancestors': "'none'"
    }
    
    Talisman(
        app,
        content_security_policy=csp,
        force_https=False,  # Set to True in production with HTTPS
        strict_transport_security=False  # Set to True in production
    )
    logger.info("Flask-Talisman initialized with CSP headers")

# Session configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-me-in-production-secret-key-12345')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# Store process IDs
processes = {
    'producer': None,
    'consumer': None
}

# Lock to prevent concurrent start/stop operations
import threading
component_lock = threading.Lock()

# ============================================================================
# MACHINE STATE MANAGEMENT (Phase 1 - In-Memory Only)
# ============================================================================

# Machine state: {machineId: {'running': bool, 'sensors': {sensor_name: {'enabled': bool, 'baseline': float}}}}
machine_state = {
    'A': {
        'running': False,
        'sensors': {}
    },
    'B': {
        'running': False,
        'sensors': {}
    },
    'C': {
        'running': False,
        'sensors': {}
    }
}

# Initialize all sensors as enabled with no baseline for each machine
def initialize_machine_sensors():
    """Initialize sensor state for all machines - all enabled by default, no baselines"""
    import config
    for machine_id in ['A', 'B', 'C']:
        for sensor_name in config.SENSOR_RANGES.keys():
            if sensor_name not in machine_state[machine_id]['sensors']:
                machine_state[machine_id]['sensors'][sensor_name] = {
                    'enabled': True,
                    'baseline': None
                }

# Initialize on module load
initialize_machine_sensors()

machine_state_lock = threading.Lock()

kafka_health = {
    'status': 'unknown',
    'checked_at': None,
    'latency_ms': None,
    'error': None
}
kafka_health_lock = threading.Lock()
HEARTBEAT_INTERVAL_SECONDS = 10
last_kafka_status = None
heartbeat_thread_started = False
heartbeat_lock = threading.Lock()

def get_db_connection():
    """Get PostgreSQL connection from pool."""
    global db_pool
    
    if db_pool:
        try:
            conn = db_pool.getconn()
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            return None
    else:
        # Fallback to direct connection if pool not available
        try:
            import config
            conn = psycopg2.connect(**config.DB_CONFIG)
            return conn
        except Exception as e:
            logger.error(f"Failed to create direct database connection: {e}")
            return None

def return_db_connection(conn):
    """Return connection to pool."""
    global db_pool
    if db_pool and conn:
        try:
            db_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
            try:
                conn.close()
            except:
                pass

def record_alert(alert_type, message, severity='INFO', source='dashboard'):
    """Persist alert messages for dashboard display."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to get database connection for alert recording")
            return
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
        logger.error(f"Failed to record alert: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_db_connection(conn)

def get_alerts(limit=20):
    """Fetch recent alerts."""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT alert_type, source, severity, message, created_at
            FROM alerts
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,)
        )
        records = cursor.fetchall()
        cursor.close()
        return_db_connection(conn)
        return [
            {
                'alert_type': row[0],
                'source': row[1],
                'severity': row[2],
                'message': row[3],
                'created_at': str(row[4])
            } for row in records
        ]
    except Exception:
        if conn:
            return_db_connection(conn)
        return []

def check_kafka_health():
    """Ping Kafka broker and update global status."""
    global last_kafka_status
    start_time = time.time()
    try:
        import config
        admin = KafkaAdminClient(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            client_id='dashboard-heartbeat',
            request_timeout_ms=10000,
            api_version_auto_timeout_ms=10000
        )
        admin.list_topics()
        admin.close()

        latency_ms = round((time.time() - start_time) * 1000, 2)
        with kafka_health_lock:
            kafka_health.update({
                'status': 'healthy',
                'checked_at': datetime.now(timezone.utc).isoformat(),
                'latency_ms': latency_ms,
                'error': None
            })

        if last_kafka_status != 'healthy':
            last_kafka_status = 'healthy'
    except Exception as e:
        error_message = str(e)
        with kafka_health_lock:
            kafka_health.update({
                'status': 'unhealthy',
                'checked_at': datetime.now(timezone.utc).isoformat(),
                'latency_ms': None,
                'error': error_message
            })

        if last_kafka_status != 'unhealthy':
            record_alert('KAFKA_HEARTBEAT', f"Kafka heartbeat failed: {error_message}", severity='CRITICAL')
            last_kafka_status = 'unhealthy'

def heartbeat_worker():
    """Background thread that keeps Kafka heartbeat fresh."""
    while True:
        check_kafka_health()
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)

def start_kafka_monitor():
    """Launch heartbeat worker exactly once."""
    global heartbeat_thread_started
    with heartbeat_lock:
        if heartbeat_thread_started:
            return
        thread = threading.Thread(target=heartbeat_worker, daemon=True)
        thread.start()
        heartbeat_thread_started = True

def get_stats():
    """Get current statistics from database with all 50 parameters organized by category"""
    conn = get_db_connection()
    if not conn:
        return {'error': 'Database not connected'}

    try:
        import config
        cursor = conn.cursor()

        # Total count
        cursor.execute("SELECT COUNT(*) FROM sensor_readings;")
        total_count = cursor.fetchone()[0]

        # Recent readings (last 10 with key parameters for top stats)
        cursor.execute("""
            SELECT timestamp, rpm, temperature, vibration, pressure, humidity, created_at
            FROM sensor_readings
            ORDER BY created_at DESC
            LIMIT 10;
        """)
        recent_readings = cursor.fetchall()

        # Recent readings with ALL 50 parameters for history display
        # Check if custom_sensors column exists before including it
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'sensor_readings' AND column_name = 'custom_sensors'
        """)
        has_custom_sensors_column = cursor.fetchone() is not None
        
        if has_custom_sensors_column:
            cursor.execute("""
                SELECT
                    timestamp, created_at,
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
                FROM sensor_readings
                ORDER BY created_at DESC
                LIMIT 10;
            """)
        else:
            cursor.execute("""
                SELECT
                    timestamp, created_at,
                    temperature, pressure, humidity, ambient_temp, dew_point,
                    air_quality_index, co2_level, particle_count, noise_level, light_intensity,
                    vibration, rpm, torque, shaft_alignment, bearing_temp,
                    motor_current, belt_tension, gear_wear, coupling_temp, lubrication_pressure,
                    coolant_temp, exhaust_temp, oil_temp, radiator_temp, thermal_efficiency,
                    heat_dissipation, inlet_temp, outlet_temp, core_temp, surface_temp,
                    voltage, current, power_factor, frequency, resistance,
                    capacitance, inductance, phase_angle, harmonic_distortion, ground_fault,
                    flow_rate, fluid_pressure, viscosity, density, reynolds_number,
                    pipe_pressure_drop, pump_efficiency, cavitation_index, turbulence, valve_position
                FROM sensor_readings
                ORDER BY created_at DESC
                LIMIT 10;
            """)
        full_readings = cursor.fetchall()

        # Calculate averages for all 50 parameters organized by category
        stats_by_category = {}
        for category_key, category_name in config.SENSOR_CATEGORIES.items():
            # Get sensors in this category
            sensors = [name for name, spec in config.SENSOR_RANGES.items()
                      if spec.get('category') == category_key]

            if sensors:
                # Build dynamic query for averages
                avg_fields = ', '.join([f"AVG({sensor})::NUMERIC(10,2) as avg_{sensor}" for sensor in sensors])
                query = f"SELECT {avg_fields} FROM sensor_readings;"
                cursor.execute(query)
                averages = cursor.fetchone()

                # Build category stats with metadata enrichment
                try:
                    from sensor_metadata import get_sensor_metadata
                    metadata_available = True
                except ImportError:
                    metadata_available = False
                
                category_stats = {}
                for i, sensor in enumerate(sensors):
                    value = averages[i] if averages and averages[i] is not None else None
                    sensor_data = {
                        'value': float(value) if value is not None else None,
                        'unit': config.SENSOR_RANGES[sensor].get('unit', '')
                    }
                    
                    # Enrich with metadata if available
                    if metadata_available:
                        try:
                            metadata = get_sensor_metadata(sensor)
                            sensor_data['metadata'] = {
                                'location': metadata.get('location', ''),
                                'equipment_section': metadata.get('equipment_section', ''),
                                'criticality': metadata.get('criticality', 'medium'),
                                'unit': metadata.get('unit', '') or sensor_data['unit']
                            }
                        except Exception as e:
                            # Safe fallback if metadata lookup fails
                            logging.warning(f"Metadata lookup failed for {sensor}: {e}")
                            sensor_data['metadata'] = {
                                'location': '',
                                'equipment_section': '',
                                'criticality': 'medium',
                                'unit': sensor_data['unit']
                            }
                    else:
                        # No metadata available - use defaults
                        sensor_data['metadata'] = {
                            'location': '',
                            'equipment_section': '',
                            'criticality': 'medium',
                            'unit': sensor_data['unit']
                        }
                    
                    category_stats[sensor] = sensor_data

                stats_by_category[category_key] = {
                    'name': category_name,
                    'sensors': category_stats
                }

        # Add custom sensors category (only if custom_sensors table exists)
        try:
            cursor.execute("""
                SELECT sensor_name, category, unit, min_range, max_range
                FROM custom_sensors
                WHERE is_active = TRUE
                ORDER BY sensor_name
            """)
            custom_sensors_list = cursor.fetchall()
        except Exception:
            # Table doesn't exist yet - skip custom sensors
            custom_sensors_list = []
        
        if custom_sensors_list:
            custom_stats = {}
            for sensor_name, category, unit, min_range, max_range in custom_sensors_list:
                # Calculate average from JSONB using PostgreSQL JSON functions
                cursor.execute("""
                    SELECT AVG((custom_sensors->>%s)::float)::NUMERIC(10,2)
                    FROM sensor_readings
                    WHERE custom_sensors ? %s
                """, (sensor_name, sensor_name))
                avg_result = cursor.fetchone()
                avg_value = float(avg_result[0]) if avg_result and avg_result[0] is not None else None
                
                custom_stats[sensor_name] = {
                    'value': avg_value,
                    'unit': unit or '',
                    'metadata': {
                        'location': '',
                        'equipment_section': '',
                        'criticality': 'medium',
                        'unit': unit or ''
                    }
                }
            
            if custom_stats:
                stats_by_category['custom'] = {
                    'name': 'Custom Parameters',
                    'sensors': custom_stats
                }

        cursor.close()
        return_db_connection(conn)

        # Build full readings with all 50 parameters + custom sensors
        full_readings_list = []
        if full_readings:
            for reading in full_readings:
                reading_dict = {
                    'timestamp': str(reading[0]),
                    'created_at': str(reading[1]),
                    'temperature': reading[2], 'pressure': reading[3], 'humidity': reading[4],
                    'ambient_temp': reading[5], 'dew_point': reading[6],
                    'air_quality_index': reading[7], 'co2_level': reading[8],
                    'particle_count': reading[9], 'noise_level': reading[10], 'light_intensity': reading[11],
                    'vibration': reading[12], 'rpm': reading[13], 'torque': reading[14],
                    'shaft_alignment': reading[15], 'bearing_temp': reading[16],
                    'motor_current': reading[17], 'belt_tension': reading[18], 'gear_wear': reading[19],
                    'coupling_temp': reading[20], 'lubrication_pressure': reading[21],
                    'coolant_temp': reading[22], 'exhaust_temp': reading[23], 'oil_temp': reading[24],
                    'radiator_temp': reading[25], 'thermal_efficiency': reading[26],
                    'heat_dissipation': reading[27], 'inlet_temp': reading[28], 'outlet_temp': reading[29],
                    'core_temp': reading[30], 'surface_temp': reading[31],
                    'voltage': reading[32], 'current': reading[33], 'power_factor': reading[34],
                    'frequency': reading[35], 'resistance': reading[36],
                    'capacitance': reading[37], 'inductance': reading[38], 'phase_angle': reading[39],
                    'harmonic_distortion': reading[40], 'ground_fault': reading[41],
                    'flow_rate': reading[42], 'fluid_pressure': reading[43], 'viscosity': reading[44],
                    'density': reading[45], 'reynolds_number': reading[46],
                    'pipe_pressure_drop': reading[47], 'pump_efficiency': reading[48],
                    'cavitation_index': reading[49], 'turbulence': reading[50], 'valve_position': reading[51]
                }
                
                # Add custom sensors from JSONB if column exists (reading[52])
                if has_custom_sensors_column and len(reading) > 52:
                    if reading[52] and isinstance(reading[52], dict):
                        reading_dict['custom_sensors'] = reading[52]
                    elif reading[52]:
                        # If it's a string, parse it
                        try:
                            reading_dict['custom_sensors'] = json.loads(reading[52]) if isinstance(reading[52], str) else reading[52]
                        except:
                            reading_dict['custom_sensors'] = {}
                    else:
                        reading_dict['custom_sensors'] = {}
                else:
                    reading_dict['custom_sensors'] = {}
                
                full_readings_list.append(reading_dict)

        return {
            'total_count': total_count,
            'recent_readings': [
                {
                    'timestamp': str(reading[0]),
                    'rpm': reading[1],
                    'temperature': reading[2],
                    'vibration': reading[3],
                    'pressure': reading[4],
                    'humidity': reading[5],
                    'created_at': str(reading[6])
                } for reading in recent_readings
            ] if recent_readings else [],
            'recent_readings_full': full_readings_list,
            'stats_by_category': stats_by_category
        }
    except Exception as e:
        if conn:
            return_db_connection(conn)
        logger.error(f"Error in get_stats: {e}")
        return {'error': str(e)}

def get_config():
    """Get current configuration"""
    try:
        import config
        total_hours = config.DURATION_HOURS
        hours = int(total_hours)
        minutes = int((total_hours - hours) * 60)
        return {
            'duration_hours': hours,
            'duration_minutes': minutes,
            'interval_seconds': config.INTERVAL_SECONDS,
            'limits': config.CONFIG_LIMITS,
            'defaults': get_default_config_values()
        }
    except Exception as e:
        return {'error': str(e)}

def get_default_config_values():
    """Expose defaults from config module."""
    try:
        import config
        total_hours = config.DEFAULT_DURATION_HOURS
        hours = int(total_hours)
        minutes = int(round((total_hours - hours) * 60))
        return {
            'duration_hours': hours,
            'duration_minutes': minutes,
            'interval_seconds': config.DEFAULT_INTERVAL_SECONDS
        }
    except Exception:
        return {
            'duration_hours': 0,
            'duration_minutes': 1,
            'interval_seconds': 5
        }

def validate_config_values(duration_hours, duration_minutes, interval_seconds):
    """Validate duration and interval input from dashboard."""
    try:
        import config
        if duration_hours < 0 or duration_minutes < 0:
            return False, "Duration cannot be negative."

        total_hours = duration_hours + (duration_minutes / 60.0)
        limits = config.CONFIG_LIMITS['duration_hours']
        if total_hours < limits['min'] or total_hours > limits['max']:
            return False, f"Duration must be between {limits['min']} and {limits['max']} hours."

        interval_limits = config.CONFIG_LIMITS['interval_seconds']
        if interval_seconds < interval_limits['min'] or interval_seconds > interval_limits['max']:
            return False, f"Interval must be between {interval_limits['min']} and {interval_limits['max']} seconds."

        return True, ""
    except Exception as e:
        return False, str(e)

def update_config(duration_hours, duration_minutes, interval_seconds):
    """Update config.py file"""
    try:
        is_valid, message = validate_config_values(duration_hours, duration_minutes, interval_seconds)
        if not is_valid:
            return False, message

        # Convert hours + minutes to decimal hours
        total_hours = duration_hours + (duration_minutes / 60.0)

        config_path = os.path.join(os.path.dirname(__file__), 'config.py')
        with open(config_path, 'r') as f:
            content = f.read()

        # Update values
        import re
        content = re.sub(
            r'DURATION_HOURS\s*=\s*[\d.]+',
            f'DURATION_HOURS = {total_hours}',
            content
        )
        content = re.sub(
            r'INTERVAL_SECONDS\s*=\s*\d+',
            f'INTERVAL_SECONDS = {interval_seconds}',
            content
        )

        with open(config_path, 'w') as f:
            f.write(content)

        return True, "Configuration updated."
    except Exception as e:
        return False, str(e)

def bootstrap_admin_user():
    """Create initial admin user if it doesn't exist."""
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin')
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    
    conn = get_db_connection()
    if not conn:
        logging.error("Cannot bootstrap admin user: database not connected")
        return
    
    try:
        cursor = conn.cursor()
        
        # Check if admin user exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (admin_username,))
        if cursor.fetchone():
            cursor.close()
            return_db_connection(conn)
            logger.info(f"Admin user '{admin_username}' already exists")
            return
        
        # Create admin user
        password_hash = generate_password_hash(admin_password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, role)
            VALUES (%s, %s, 'admin')
        """, (admin_username, password_hash))
        
        conn.commit()
        cursor.close()
        return_db_connection(conn)
        
        logger.info(f"Created initial admin user '{admin_username}'")
    except Exception as e:
        logging.error(f"Failed to bootstrap admin user: {e}")
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()


@app.route('/login')
def login_page():
    """Login page"""
    return render_template('login.html')

@app.route('/health')
def health():
    """Health check endpoint - returns 200 OK if service is running."""
    return jsonify({"status": "healthy"}), 200

@app.route('/ready')
def ready():
    """Readiness check endpoint - verifies database connection is live."""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"status": "not ready", "error": "Database connection failed"}), 503
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        return_db_connection(conn)
        
        return jsonify({"status": "ready"}), 200
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        if conn:
            return_db_connection(conn)
        return jsonify({"status": "not ready", "error": str(e)}), 503

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Authenticate user and create session."""
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Get user
        cursor.execute("""
            SELECT id, username, password_hash, role
            FROM users
            WHERE username = %s
        """, (username,))
        row = cursor.fetchone()
        
        if not row:
            cursor.close()
            return_db_connection(conn)
            return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
        
        user_id, db_username, password_hash, role = row
        
        # Verify password
        if not check_password_hash(password_hash, password):
            cursor.close()
            return_db_connection(conn)
            return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
        
        # Get user's accessible machines
        cursor.execute("""
            SELECT machine_id FROM user_machine_access
            WHERE user_id = %s
            ORDER BY machine_id
        """, (user_id,))
        machine_rows = cursor.fetchall()
        accessible_machines = [row[0] for row in machine_rows]
        
        # If admin, give access to all machines
        if role == 'admin':
            accessible_machines = ['A', 'B', 'C']
        
        # Update last_login
        cursor.execute("""
            UPDATE users SET last_login = NOW() WHERE id = %s
        """, (user_id,))
        conn.commit()
        
        # Create session BEFORE closing connection
        session.permanent = True
        session['user_id'] = user_id
        session['username'] = db_username
        session['role'] = role
        session['accessible_machines'] = accessible_machines
        
        cursor.close()
        return_db_connection(conn)
        
        return jsonify({
            'success': True,
            'user': {
                'id': user_id,
                'username': db_username,
                'role': role,
                'accessible_machines': accessible_machines
            }
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
            if cursor:
                cursor.close()
            return_db_connection(conn)
        logging.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Destroy session."""
    # #region agent log
    import json as json_lib
    log_data = {
        'location': 'dashboard.py:711',
        'message': 'api_logout: Logging out user',
        'data': {
            'had_session': 'user_id' in session,
            'user_id': session.get('user_id'),
            'username': session.get('username')
        },
        'timestamp': int(time.time() * 1000),
        'sessionId': 'debug-session',
        'runId': 'run1',
        'hypothesisId': 'C'
    }
    try:
        with open(r'c:\Users\rahul\Desktop\stubby\.cursor\debug.log', 'a', encoding='utf-8') as log_file:
            log_file.write(json_lib.dumps(log_data) + '\n')
    except: pass
    # #endregion
    
    session.clear()
    return jsonify({'success': True})


@app.route('/api/auth/me', methods=['GET'])
def api_auth_me():
    """Get current user info."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    return jsonify({
        'success': True,
        'user': {
            'id': session['user_id'],
            'username': session['username'],
            'role': session['role'],
            'accessible_machines': session.get('accessible_machines', [])
        }
    })


@app.route('/api/auth/signup', methods=['POST'])
# No @require_admin - signup is open to everyone
def api_signup():
    """Create a new user (open to everyone)."""
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'operator')
    machine_ids = data.get('machine_ids', [])  # List of machine IDs user can access
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
    
    if role not in ['admin', 'operator']:
        return jsonify({'success': False, 'error': 'Invalid role'}), 400
    
    if role == 'operator' and not machine_ids:
        return jsonify({'success': False, 'error': 'Operator users must have at least one machine assigned'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            cursor.close()
            return_db_connection(conn)
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        
        # Create user
        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, role)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (username, password_hash, role))
        
        user_id = cursor.fetchone()[0]
        
        # If operator, assign machines
        if role == 'operator' and machine_ids:
            for machine_id in machine_ids:
                if machine_id in ['A', 'B', 'C']:
                    cursor.execute("""
                        INSERT INTO user_machine_access (user_id, machine_id)
                        VALUES (%s, %s)
                    """, (user_id, machine_id))
        
        conn.commit()
        cursor.close()
        return_db_connection(conn)
        
        return jsonify({
            'success': True,
            'message': f'User {username} created successfully',
            'user_id': user_id
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
            if cursor:
                cursor.close()
            return_db_connection(conn)
        logging.error(f"Signup error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# AUTHORIZATION DECORATORS
# ============================================================================

def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def log_action(action_type, resource_type=None, resource_id=None, capture_state=False):
    """
    Decorator to log actions to audit_logs_v2.
    
    Args:
        action_type: 'CREATE', 'READ', 'UPDATE', 'DELETE', 'INGEST', 'PARSE', etc.
        resource_type: Type of resource (e.g., 'sensor', 'user', 'sensor_file', 'ingest')
        resource_id: ID of the resource (optional)
        capture_state: If True, capture before/after state for UPDATE operations
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get user info from session (if available)
            user_id = session.get('user_id')
            username = session.get('username')
            role = session.get('role')
            
            # If no session (e.g., API key auth for /api/v1/ingest), default to admin_rahul
            if not user_id:
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        # Get admin_rahul user (ID: 1) as default operator
                        cursor.execute("SELECT id, username, role FROM users WHERE username = 'admin_rahul' OR id = 1 LIMIT 1")
                        admin_row = cursor.fetchone()
                        if admin_row:
                            user_id = admin_row[0]
                            username = admin_row[1] or 'admin_rahul'
                            role = admin_row[2] or 'admin'
                        else:
                            # Fallback if admin_rahul doesn't exist
                            user_id = None
                            username = 'system'
                            role = 'system'
                        cursor.close()
                    except Exception as e:
                        logging.warning(f"Failed to get default admin user for audit log: {e}")
                        user_id = None
                        username = 'system'
                        role = 'system'
                    finally:
                        if conn:
                            conn.close()
                else:
                    # No DB connection, use system defaults
                    user_id = None
                    username = 'system'
                    role = 'system'
            
            # Get request metadata
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            
            # Get request data for state capture
            previous_state = None
            new_state = None
            if capture_state and request.method in ['POST', 'PUT', 'PATCH']:
                new_state = request.get_json(silent=True)
            
            # Extract resource_id from kwargs if not provided (e.g., sensor_id from URL)
            final_resource_id = resource_id
            if not final_resource_id:
                # Try to get from kwargs (common pattern: sensor_id, user_id, machine_id, etc.)
                for key in ['sensor_id', 'user_id', 'machine_id', 'id']:
                    if key in kwargs:
                        final_resource_id = str(kwargs[key])
                        break
            
            # Execute the function
            try:
                result = f(*args, **kwargs)
                
                # Extract resource_id from result if still not set
                if not final_resource_id and isinstance(result, tuple):
                    # Try to extract from response
                    response_data = result[0] if len(result) > 0 else None
                    if hasattr(response_data, 'get_json'):
                        try:
                            json_data = response_data.get_json()
                            if json_data and 'id' in json_data:
                                final_resource_id = str(json_data['id'])
                        except:
                            pass
                
                # Log to audit_logs_v2
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO audit_logs_v2 
                            (user_id, username, role, ip_address, user_agent,
                             action_type, resource_type, resource_id,
                             previous_state, new_state)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            user_id,
                            username,
                            role,
                            ip_address,
                            user_agent,
                            action_type,
                            resource_type,
                            final_resource_id,
                            json.dumps(previous_state) if previous_state else None,
                            json.dumps(new_state) if new_state else None
                        ))
                        conn.commit()
                        cursor.close()
                    except Exception as e:
                        logging.warning(f"Failed to log audit action: {e}")
                        if conn:
                            conn.rollback()
                    finally:
                        if conn:
                            conn.close()
                
                return result
            except Exception as e:
                # Log failed action
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO audit_logs_v2 
                            (user_id, username, role, ip_address, user_agent,
                             action_type, resource_type, resource_id, new_state)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            user_id,
                            username,
                            role,
                            ip_address,
                            user_agent,
                            f"{action_type}_FAILED",
                            resource_type,
                            resource_id,
                            json.dumps({'error': str(e)})
                        ))
                        conn.commit()
                        cursor.close()
                    except:
                        pass
                    finally:
                        if conn:
                            conn.close()
                raise
            
        return decorated_function
    return decorator

def require_admin(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # #region agent log
        import json as json_lib
        log_data = {
            'location': 'dashboard.py:824',
            'message': 'require_admin: Checking session',
            'data': {
                'has_user_id': 'user_id' in session,
                'user_id': session.get('user_id'),
                'role': session.get('role'),
                'username': session.get('username'),
                'session_keys': list(session.keys())
            },
            'timestamp': int(time.time() * 1000),
            'sessionId': 'debug-session',
            'runId': 'run1',
            'hypothesisId': 'B'
        }
        try:
            with open(r'c:\Users\rahul\Desktop\stubby\.cursor\debug.log', 'a', encoding='utf-8') as log_file:
                log_file.write(json_lib.dumps(log_data) + '\n')
        except: pass
        # #endregion
        
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        if session.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def require_machine_access(machine_id_param='machine_id'):
    """Decorator factory to require access to a specific machine.
    
    Args:
        machine_id_param: Name of the parameter containing machine_id (default: 'machine_id')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            # Get machine_id from kwargs or route parameter
            machine_id = kwargs.get(machine_id_param)
            if not machine_id:
                return jsonify({'success': False, 'error': 'Machine ID required'}), 400
            
            # Admins have access to all machines
            if session.get('role') == 'admin':
                return f(*args, **kwargs)
            
            # Check if user has access to this machine
            accessible_machines = session.get('accessible_machines', [])
            if machine_id not in accessible_machines:
                return jsonify({'success': False, 'error': 'Access denied to this machine'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def init_background_threads():
    """Ensure background monitors are running."""
    start_kafka_monitor()
init_background_threads()

@app.route('/api/stats')
@require_auth
def api_stats():
    """Get current stats"""
    return jsonify(get_stats())

@app.route('/api/alerts')
@require_auth
def api_alerts():
    """Get recent alerts"""
    limit = request.args.get('limit', default=20, type=int)
    return jsonify({'alerts': get_alerts(limit)})

@app.route('/api/config', methods=['GET', 'POST'])
@require_auth
def api_config():
    """Get or update configuration"""
    if request.method == 'POST':
        data = request.json or {}
        duration_hours = int(data.get('duration_hours', 0))
        duration_minutes = int(data.get('duration_minutes', 0))
        interval = int(data.get('interval_seconds', 30))

        success, message = update_config(duration_hours, duration_minutes, interval)
        if success:
            return jsonify({'success': True, 'config': get_config()})
        else:
            return jsonify({'success': False, 'error': message})
    else:
        return jsonify(get_config())

@app.route('/api/config/reset', methods=['POST'])
@require_auth
def reset_config():
    """Reset config.py to default values."""
    defaults = get_default_config_values()
    success, message = update_config(
        defaults['duration_hours'],
        defaults['duration_minutes'],
        defaults['interval_seconds']
    )
    if success:
        return jsonify({'success': True, 'config': get_config()})
    else:
        return jsonify({'success': False, 'error': message})

@app.route('/api/start/<component>', methods=['POST'])
@require_auth
def start_component(component):
    """Start producer or consumer"""
    if component not in ['producer', 'consumer']:
        return jsonify({'success': False, 'error': 'Invalid component'})

    # Use lock to prevent concurrent starts (rapid clicking)
    if not component_lock.acquire(blocking=False):
        logger.warning(f"{component.capitalize()} start already in progress, ignoring duplicate request")
        return jsonify({'success': False, 'error': f'{component.capitalize()} start already in progress'}), 409
    
    try:
        # Check if already running AFTER acquiring lock
        if is_component_running(component):
            logger.warning(f"{component.capitalize()} is already running")
            component_lock.release()
            return jsonify({'success': False, 'error': f'{component.capitalize()} is already running'}), 409

        # ALWAYS kill existing processes first to prevent duplicates
        logger.info(f"Killing any existing {component} processes before starting...")
        try:
            script_name = f'{component}.py'
            if os.name == 'nt':
                # Windows: Use WMIC to find and kill all processes
                result = subprocess.run(
                    ['wmic', 'process', 'where', f"CommandLine like '%{script_name}%'", 'get', 'ProcessId'],
                    capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # Skip header
                        line = line.strip()
                        if line and line.isdigit() and 'wmic' not in line.lower():
                            pid = int(line)
                            try:
                                subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)],
                                             capture_output=True, timeout=2)
                                logger.info(f"Killed existing {component} process PID {pid}")
                            except Exception as e:
                                logger.warning(f"Failed to kill PID {pid}: {e}")
        except Exception as e:
            logger.warning(f"Error killing existing {component} processes: {e}")
        
        # Also kill tracked process
        proc = processes.get(component)
        if proc:
            try:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                                 capture_output=True, timeout=2)
                else:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            except Exception:
                pass
            processes[component] = None
        
        # Wait a moment for processes to die
        import time
        time.sleep(0.5)

        # Determine Python executable path (cross-platform)
        script_path = os.path.join(os.path.dirname(__file__), f'{component}.py')
        
        # Check for venv first (Windows)
        if os.name == 'nt':
            venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'Scripts', 'python.exe')
            if os.path.exists(venv_python):
                python_exe = venv_python
            else:
                python_exe = sys.executable  # Use current Python
        else:
            # macOS/Linux
            venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'python')
            if os.path.exists(venv_python):
                python_exe = venv_python
            else:
                python_exe = sys.executable  # Use current Python

        # Prepare subprocess arguments
        popen_args = [python_exe, script_path]
        popen_kwargs = {}
        
        # Only use Windows-specific creationflags on Windows
        if os.name == 'nt':
            popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen(popen_args, **popen_kwargs)
        processes[component] = proc  # Store the process object, not just PID

        logger.info(f"{component.capitalize()} started successfully (PID: {proc.pid})")
        return jsonify({'success': True, 'pid': proc.pid})
    except Exception as e:
        logger.error(f"Failed to start {component}: {e}")
        return jsonify({'success': False, 'error': str(e)})
    finally:
        # Always release the lock
        component_lock.release()

@app.route('/api/stop/<component>', methods=['POST'])
@require_auth
def stop_component(component):
    """Stop producer or consumer"""
    if component not in ['producer', 'consumer']:
        return jsonify({'success': False, 'error': 'Invalid component'})

    try:
        proc = processes.get(component)
        killed_pids = []

        # First try to kill tracked process
        if proc:
            pid = proc.pid
            if os.name == 'nt':
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)],
                             capture_output=True, timeout=5)
            else:
                # macOS/Linux: Try graceful shutdown first (SIGTERM), then force kill (SIGKILL)
                try:
                    proc.terminate()  # Send SIGTERM
                    try:
                        proc.wait(timeout=2)  # Wait up to 2 seconds
                    except subprocess.TimeoutExpired:
                        # Process didn't respond, force kill
                        proc.kill()  # Send SIGKILL
                        proc.wait(timeout=1)
                except ProcessLookupError:
                    pass  # Process already dead

            try:
                proc.wait(timeout=1)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                pass

            killed_pids.append(pid)
            processes[component] = None

        # Also search for any running processes with the component script name
        # This catches processes started outside the dashboard
        script_name = f'{component}.py'
        
        if os.name == 'nt':
            # Windows: Use WMIC
            try:
                result = subprocess.run(
                    ['wmic', 'process', 'where', f"CommandLine like '%{script_name}%'", 'get', 'CommandLine,ProcessId'],
                    capture_output=True, text=True, timeout=2
                )

                # Parse output and filter for actual Python processes (not wmic itself)
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # Skip header
                    try:
                        # Extract PID from the end of the line
                        parts = line.strip().split()
                        if parts and parts[-1].isdigit():
                            # Check if this is an actual python process (not wmic)
                            if script_name in line and 'wmic' not in line.lower() and 'python' in line.lower():
                                pid = parts[-1]
                                subprocess.run(['taskkill', '/F', '/T', '/PID', pid],
                                             capture_output=True, timeout=2)
                                killed_pids.append(int(pid))
                    except:
                        pass
            except:
                pass
        else:
            # macOS/Linux: Use ps to find and kill processes
            # Note: 'ps aux' works on macOS and most Linux distributions
            try:
                result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if script_name in line and 'python' in line.lower() and 'grep' not in line:
                            try:
                                # Extract PID (second column in ps aux output)
                                parts = line.split()
                                if len(parts) >= 2 and parts[1].isdigit():
                                    pid = int(parts[1])
                                    # Only kill if not already killed
                                    if pid not in killed_pids:
                                        try:
                                            os.kill(pid, signal.SIGTERM)
                                            # Wait a bit, then force kill if still running
                                            time.sleep(0.5)
                                            try:
                                                os.kill(pid, 0)  # Check if process exists
                                                os.kill(pid, signal.SIGKILL)  # Force kill
                                            except ProcessLookupError:
                                                pass  # Process already dead
                                            killed_pids.append(pid)
                                        except ProcessLookupError:
                                            pass  # Process doesn't exist
                            except (ValueError, IndexError):
                                pass
            except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
                # ps command not available or failed - continue without error
                pass

        if killed_pids:
            return jsonify({'success': True, 'pids': killed_pids})
        else:
            return jsonify({'success': False, 'error': 'No running process found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def is_component_running(component):
    """Check if a component (producer or consumer) is running, even if not tracked by dashboard"""
    # First check tracked process
    proc = processes.get(component)
    if proc:
        # Check if process is still alive
        poll_result = proc.poll()
        if poll_result is None:
            # Process is still running
            return True
        else:
            # Process has terminated, clean it up
            processes[component] = None

    # Search for any running process with the component script name
    script_name = f'{component}.py'
    
    if os.name == 'nt':
        # Windows: Use WMIC
        try:
            result = subprocess.run(
                ['wmic', 'process', 'where', f"CommandLine like '%{script_name}%'", 'get', 'CommandLine,ProcessId'],
                capture_output=True, text=True, timeout=2
            )

            # Filter out lines that are from wmic itself and check for actual script execution
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Skip header
                line = line.strip()
                # Check if this is an actual python process running the script (not wmic)
                if script_name in line and 'wmic' not in line.lower() and 'python' in line.lower():
                    return True
        except Exception:
            # If WMIC fails, return False (assume not running)
            pass
    else:
        # macOS/Linux: Use ps to find processes
        # Note: 'ps aux' works on macOS and most Linux distributions
        # For systems where 'ps aux' doesn't work, we fall back gracefully
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if script_name in line and 'python' in line.lower() and 'grep' not in line:
                        return True
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            # ps command not available or failed - assume process not running
            pass

    return False

@app.route('/api/status')
@require_auth
def api_status():
    """Get status of components"""
    with kafka_health_lock:
        kafka_snapshot = kafka_health.copy()

    # Check if processes are actually running (including those not tracked by dashboard)
    producer_running = is_component_running('producer')
    consumer_running = is_component_running('consumer')

    return jsonify({
        'producer_running': producer_running,
        'consumer_running': consumer_running,
        'kafka': kafka_snapshot
    })

@app.route('/api/system-metrics')
@require_auth
def api_system_metrics():
    """Get system metrics: CPU load and DB latency"""
    # Get CPU load using psutil
    cpu_percent = psutil.cpu_percent(interval=0.1)

    # Measure DB latency by pinging the database
    db_latency_ms = None
    db_status = 'unknown'

    try:
        import config
        start_time = time.time()
        conn = psycopg2.connect(**config.DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        db_latency_ms = round((time.time() - start_time) * 1000, 2)
        db_status = 'healthy'
    except Exception as e:
        db_status = 'unhealthy'
        logging.warning(f"DB latency check failed: {e}")

    return jsonify({
        'cpu_percent': cpu_percent,
        'db_latency_ms': db_latency_ms,
        'db_status': db_status,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

@app.route('/api/log-critical-alarm', methods=['POST'])
@require_auth
def api_log_critical_alarm():
    """Log a CRITICAL_ALARM_TRIGGERED event to audit_logs_v2"""
    # Get user info from session (or default to admin_rahul)
    user_id = session.get('user_id')
    username = session.get('username')
    role = session.get('role')

    # If no session, default to admin_rahul (ID: 1)
    if not user_id:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, role FROM users WHERE username = 'admin_rahul' OR id = 1 LIMIT 1")
                admin_row = cursor.fetchone()
                if admin_row:
                    user_id = admin_row[0]
                    username = admin_row[1] or 'admin_rahul'
                    role = admin_row[2] or 'admin'
                else:
                    user_id = 1
                    username = 'admin_rahul'
                    role = 'admin'
                cursor.close()
            except Exception as e:
                logging.warning(f"Failed to get admin user for critical alarm log: {e}")
                user_id = 1
                username = 'admin_rahul'
                role = 'admin'
            finally:
                if conn:
                    conn.close()
        else:
            user_id = 1
            username = 'admin_rahul'
            role = 'admin'

    # Get request data
    data = request.get_json(silent=True) or {}
    risk_score = data.get('risk_score', 0)
    machine_id = data.get('machine_id', 'A')

    # Log to audit_logs_v2
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_logs_v2
                (user_id, username, role, ip_address, user_agent,
                 action_type, resource_type, resource_id, new_state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                username,
                role,
                request.remote_addr,
                request.headers.get('User-Agent', ''),
                'CRITICAL_ALARM_TRIGGERED',
                'system_alarm',
                f'machine_{machine_id}',
                json.dumps({
                    'risk_score': risk_score,
                    'machine_id': machine_id,
                    'triggered_at': datetime.now(timezone.utc).isoformat(),
                    'severity': 'CRITICAL'
                })
            ))
            conn.commit()
            cursor.close()

            # Also record to alerts table
            record_alert('CRITICAL_ALARM', f'Risk score {risk_score:.1f}% exceeded threshold on Machine {machine_id}', severity='CRITICAL', source='system')

            return jsonify({'success': True, 'message': 'Critical alarm logged'})
        except Exception as e:
            logging.error(f"Failed to log critical alarm: {e}")
            if conn:
                conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            if conn:
                conn.close()

    return jsonify({'success': False, 'error': 'Database not connected'}), 500

@app.route('/api/clear_data')
@require_auth
def clear_data():
    """Clear all data from database"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database not connected'})

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sensor_readings;")
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/anomalies')
@require_auth
def api_anomalies():
    """Get ML-detected anomalies."""
    limit = request.args.get('limit', default=50, type=int)
    only_anomalies = request.args.get('only_anomalies', default='true', type=str).lower() == 'true'
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Check if tables exist first
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'anomaly_detections'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            cursor.close()
            return_db_connection(conn)
            return jsonify({'anomalies': []})
        
        query = """
            SELECT 
                ad.id, ad.reading_id, ad.detection_method, ad.anomaly_score,
                ad.is_anomaly, ad.detected_sensors, ad.created_at,
                sr.timestamp, sr.temperature, sr.pressure, sr.rpm, sr.vibration,
                ar.id as report_id, ar.status as report_status
            FROM anomaly_detections ad
            JOIN sensor_readings sr ON ad.reading_id = sr.id
            LEFT JOIN analysis_reports ar ON ad.id = ar.anomaly_id
        """
        
        if only_anomalies:
            query += " WHERE ad.is_anomaly = TRUE"
        
        query += " ORDER BY ad.created_at DESC LIMIT %s"
        
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        cursor.close()
        return_db_connection(conn)
        
        anomalies = []
        for row in rows:
            anomalies.append({
                'id': row[0],
                'reading_id': row[1],
                'detection_method': row[2],
                'anomaly_score': row[3],
                'is_anomaly': row[4],
                'detected_sensors': row[5] or [],
                'created_at': str(row[6]),
                'reading_timestamp': str(row[7]),
                'temperature': row[8],
                'pressure': row[9],
                'rpm': row[10],
                'vibration': row[11],
                'report_id': row[12],
                'report_status': row[13]
            })
        
        return jsonify({'anomalies': anomalies})
        
    except Exception as e:
        logging.error(f"Error fetching anomalies: {e}")
        if conn:
            return_db_connection(conn)
        return jsonify({'anomalies': []})


@app.route('/api/anomalies/<int:anomaly_id>')
@require_auth
def api_anomaly_detail(anomaly_id):
    """Get details of a specific anomaly."""
    if not ML_REPORTS_AVAILABLE:
        return jsonify({'error': 'ML components not available'}), 500
    
    anomaly = get_anomaly_details(anomaly_id)
    if not anomaly:
        return jsonify({'error': 'Anomaly not found'}), 404
    
    return jsonify(anomaly)


@app.route('/api/generate-report/<int:anomaly_id>', methods=['POST'])
@require_auth
def api_generate_report(anomaly_id):
    """Generate an analysis report for an anomaly."""
    if not ML_REPORTS_AVAILABLE:
        return jsonify({'error': 'ML components not available'}), 500
    
    try:
        generator = ReportGenerator()
        report_id, report_data = generator.generate_and_save_report(anomaly_id)
        
        if report_id:
            return jsonify({
                'success': True,
                'report_id': report_id,
                'message': 'Report generated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to generate report'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/reports/<int:report_id>')
@require_auth
def api_get_report(report_id):
    """Get a generated report."""
    if not ML_REPORTS_AVAILABLE:
        return jsonify({'error': 'ML components not available'}), 500
    
    report = get_report(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    return jsonify(report)


@app.route('/api/reports/by-anomaly/<int:anomaly_id>')
@require_auth
def api_get_report_by_anomaly(anomaly_id):
    """Get report for a specific anomaly."""
    if not ML_REPORTS_AVAILABLE:
        return jsonify({'error': 'ML components not available'}), 500
    
    report = get_report_by_anomaly(anomaly_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    return jsonify(report)


def generate_pdf_from_markdown(markdown_text, title="Report"):
    """Generate PDF from markdown text.
    
    Args:
        markdown_text: Markdown formatted text
        title: PDF document title
        
    Returns:
        BytesIO buffer containing the PDF
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib import colors
    import io
    import re
    
    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title=title)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#059669'),
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_LEFT,
        leftIndent=0
    )
    
    # Build content
    elements = []
    
    # Add title
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Parse markdown - handle multi-line content better
    lines = markdown_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines (but add spacing)
        if not line:
            elements.append(Spacer(1, 0.1*inch))
            i += 1
            continue
        
        # Check for headers (process in order: ###, ##, #)
        if line.startswith('###'):
            header_text = line.replace('###', '').strip()
            # Remove emojis and clean up
            header_text = re.sub(r'[🔴🟠🟡🟢⚪⚠️📈📉➡️✅👀🛠️■]', '', header_text).strip()
            if header_text:
                elements.append(Paragraph(header_text, heading_style))
        elif line.startswith('##'):
            header_text = line.replace('##', '').strip()
            # Remove emojis and clean up
            header_text = re.sub(r'[🔴🟠🟡🟢⚪⚠️📈📉➡️✅👀🛠️■]', '', header_text).strip()
            if header_text:
                elements.append(Paragraph(header_text, heading_style))
        elif line.startswith('#'):
            header_text = line.replace('#', '').strip()
            # Remove duplicate title
            if 'LSTM Future Anomaly Prediction Report' in header_text:
                i += 1
                continue  # Skip duplicate title
            # Remove emojis and clean up
            header_text = re.sub(r'[🔴🟠🟡🟢⚪⚠️📈📉➡️✅👀🛠️■]', '', header_text).strip()
            if header_text:
                elements.append(Paragraph(header_text, heading_style))
        # Check for horizontal rules
        elif line.strip() in ['---', '***', '___']:
            elements.append(Spacer(1, 0.2*inch))
        # Check for list items
        elif line.startswith('- ') or line.startswith('* '):
            list_text = line[2:].strip()
            # Convert markdown bold to reportlab bold
            list_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', list_text)
            list_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', list_text)
            # Remove emojis
            list_text = re.sub(r'[🔴🟠🟡🟢⚪⚠️📈📉➡️✅👀🛠️■]', '', list_text).strip()
            if list_text:
                elements.append(Paragraph(f"• {list_text}", body_style))
        # Numbered list
        elif re.match(r'^\d+\.', line):
            list_text = re.sub(r'^\d+\.\s*', '', line)
            # Convert markdown bold to reportlab bold
            list_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', list_text)
            list_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', list_text)
            # Remove emojis
            list_text = re.sub(r'[🔴🟠🟡🟢⚪⚠️📈📉➡️✅👀🛠️■]', '', list_text).strip()
            if list_text:
                elements.append(Paragraph(list_text, body_style))
        # Regular paragraph
        else:
            # Clean up any escaped characters
            line = line.replace('\\n', ' ').replace('\\t', ' ')
            
            # Convert markdown bold to reportlab bold
            line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line)
            
            # Remove emojis (they don't render well in PDF)
            line = re.sub(r'[🔴🟠🟡🟢⚪⚠️📈📉➡️✅👀🛠️■]', '', line).strip()
            
            # Only add non-empty lines
            if line:
                elements.append(Paragraph(line, body_style))
        
        i += 1
    
    # Add footer
    elements.append(Spacer(1, 0.5*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_CENTER
    )
    elements.append(Paragraph("<i>Generated by Sensor Data Pipeline Dashboard</i>", footer_style))
    elements.append(Paragraph(f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>", footer_style))
    
    # Build PDF
    doc.build(elements)
    
    # Return buffer
    buffer.seek(0)
    return buffer


@app.route('/api/reports/<int:report_id>/pdf')
@require_auth
def api_get_report_pdf(report_id):
    """Generate and download a PDF report."""
    if not ML_REPORTS_AVAILABLE:
        return jsonify({'error': 'ML components not available'}), 500
    
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
        from reportlab.lib import colors
        import markdown
        import re
        
        # Get the report data
        report = get_report(report_id)
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        # Container for PDF elements
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Custom title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Custom heading style
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#059669'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            borderWidth=1,
            borderColor=colors.HexColor('#d1fae5'),
            borderPadding=5
        )
        
        # Body text style
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=12
        )
        
        # Metadata style
        meta_style = ParagraphStyle(
            'MetaData',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=6
        )
        
        # Add title
        elements.append(Paragraph("Anomaly Analysis Report", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Add metadata
        elements.append(Paragraph(f"<b>Report ID:</b> #{report['id']}", meta_style))
        elements.append(Paragraph(f"<b>Anomaly ID:</b> #{report['anomaly_id']}", meta_style))
        
        generated_time = report.get('completed_at') or report.get('created_at', 'N/A')
        elements.append(Paragraph(f"<b>Generated:</b> {generated_time}", meta_style))
        elements.append(Paragraph(f"<b>Status:</b> {report.get('status', 'N/A').upper()}", meta_style))
        
        elements.append(Spacer(1, 0.4*inch))
        
        # Process the analysis text
        analysis = report.get('chatgpt_analysis', 'No analysis available')
        
        # Convert markdown to plain text with formatting
        # Remove markdown code blocks
        analysis = re.sub(r'```.*?```', '', analysis, flags=re.DOTALL)
        
        # Process markdown headers
        lines = analysis.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                elements.append(Spacer(1, 0.1*inch))
                continue
            
            # Check for headers
            if line.startswith('###'):
                header_text = line.replace('###', '').strip()
                elements.append(Paragraph(header_text, heading_style))
            elif line.startswith('##'):
                header_text = line.replace('##', '').strip()
                elements.append(Paragraph(header_text, heading_style))
            elif line.startswith('#'):
                header_text = line.replace('#', '').strip()
                elements.append(Paragraph(header_text, heading_style))
            # Check for list items
            elif line.startswith('- ') or line.startswith('* '):
                list_text = line[2:].strip()
                # Convert markdown bold to reportlab bold
                list_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', list_text)
                list_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', list_text)
                elements.append(Paragraph(f"• {list_text}", body_style))
            # Numbered list
            elif re.match(r'^\d+\.', line):
                list_text = re.sub(r'^\d+\.\s*', '', line)
                # Convert markdown bold to reportlab bold
                list_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', list_text)
                list_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', list_text)
                elements.append(Paragraph(list_text, body_style))
            # Regular paragraph
            else:
                # Convert markdown bold to reportlab bold
                line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line)
                elements.append(Paragraph(line, body_style))
        
        # Add footer
        elements.append(Spacer(1, 0.5*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#64748b'),
            alignment=TA_CENTER
        )
        elements.append(Paragraph("<i>Generated by Sensor Data Pipeline Dashboard</i>", footer_style))
        elements.append(Paragraph(f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>", footer_style))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create response
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=anomaly_report_{report_id}_{datetime.now().strftime("%Y-%m-%d")}.pdf'
        
        return response
        
    except Exception as e:
        import traceback
        print(f"PDF generation error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to generate PDF: {str(e)}'}), 500


@app.route('/api/generate-full-report', methods=['POST'])
@require_auth
def api_generate_full_session_report():
    """Generate a comprehensive report for the entire monitoring session."""
    if not ML_REPORTS_AVAILABLE:
        return jsonify({'error': 'ML components not available'}), 500
    
    try:
        from report_generator import generate_full_session_report
        result = generate_full_session_report()
        return jsonify(result)
    except Exception as e:
        logging.error(f"Full session report generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ml-stats')
@require_auth
def api_ml_stats():
    """Get ML detection statistics."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Check if anomaly_detections table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'anomaly_detections'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            cursor.close()
            return_db_connection(conn)
            return jsonify({
                'total_detections': 0,
                'total_anomalies': 0,
                'avg_score': 0,
                'min_score': 0,
                'max_score': 0,
                'recent_anomaly_rate': 0,
                'total_reports': 0,
                'completed_reports': 0,
                'ml_available': ML_REPORTS_AVAILABLE
            })
        
        # Total detections and anomalies
        cursor.execute("""
            SELECT 
                COUNT(*) as total_detections,
                COUNT(*) FILTER (WHERE is_anomaly = TRUE) as total_anomalies,
                AVG(anomaly_score) as avg_score,
                MIN(anomaly_score) as min_score,
                MAX(anomaly_score) as max_score
            FROM anomaly_detections
        """)
        stats = cursor.fetchone()
        
        # Recent anomaly rate (last 100 readings)
        cursor.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE is_anomaly = TRUE)::FLOAT / 
                NULLIF(COUNT(*), 0) * 100 as recent_anomaly_rate
            FROM (
                SELECT is_anomaly FROM anomaly_detections 
                ORDER BY created_at DESC LIMIT 100
            ) recent
        """)
        recent_rate = cursor.fetchone()[0] or 0
        
        # Reports generated (check if table exists)
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_reports,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_reports
                FROM analysis_reports
            """)
            report_stats = cursor.fetchone()
        except:
            report_stats = (0, 0)
        
        cursor.close()
        return_db_connection(conn)
        
        return jsonify({
            'total_detections': stats[0] or 0,
            'total_anomalies': stats[1] or 0,
            'avg_score': round(stats[2], 4) if stats[2] else 0,
            'min_score': round(stats[3], 4) if stats[3] else 0,
            'max_score': round(stats[4], 4) if stats[4] else 0,
            'recent_anomaly_rate': round(recent_rate, 2),
            'total_reports': report_stats[0] or 0,
            'completed_reports': report_stats[1] or 0,
            'ml_available': ML_REPORTS_AVAILABLE
        })
        
    except Exception as e:
        logging.error(f"Error fetching ML stats: {e}")
        if conn:
            return_db_connection(conn)
        return jsonify({
            'total_detections': 0,
            'total_anomalies': 0,
            'avg_score': 0,
            'min_score': 0,
            'max_score': 0,
            'recent_anomaly_rate': 0,
            'total_reports': 0,
            'completed_reports': 0,
            'ml_available': False,
            'error': str(e)
        })


@app.route('/api/audit-logs')
@require_auth
def api_audit_logs():
    """Get audit logs from audit_logs_v2 table."""
    limit = request.args.get('limit', default=100, type=int)
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Try to query audit_logs_v2 table
        cursor.execute("""
            SELECT 
                id, user_id, username, role, action_type, resource_type, 
                resource_id, timestamp, ip_address
            FROM audit_logs_v2
            ORDER BY timestamp DESC
            LIMIT %s
        """, (limit,))
        
        rows = cursor.fetchall()
        cursor.close()
        return_db_connection(conn)
        
        logs = []
        for row in rows:
            logs.append({
                'id': row[0],
                'user_id': row[1],
                'operator_name': row[2] or 'system',
                'role': row[3],
                'action': f"{row[4]} {row[5] or ''}".strip(),
                'resource_id': row[6],
                'timestamp': str(row[7]),
                'ip_address': str(row[8]) if row[8] else None,
                'machine_id': None  # Not stored in audit_logs_v2
            })
        
        return jsonify({'success': True, 'logs': logs})
        
    except Exception as e:
        # If table doesn't exist or other error, return empty logs
        logging.warning(f"Failed to fetch audit logs: {e}")
        if conn:
            return_db_connection(conn)
        return jsonify({'success': True, 'logs': []})


# Alias for audit-log (singular) - frontend sometimes calls this
@app.route('/api/audit-log', methods=['GET', 'POST'])
@require_auth
def api_audit_log_alias():
    """Alias for /api/audit-logs"""
    return api_audit_logs()


# ============================================================================
# THRESHOLD AND ANOMALY INJECTION APIs
# ============================================================================

# Store custom thresholds in memory (session-based)
custom_thresholds = {}

# Anomaly injection settings
injection_settings = {
    'enabled': False,
    'interval_minutes': 30,
    'next_injection_time': None,
    'inject_now': False
}


@app.route('/api/thresholds', methods=['GET'])
@require_auth
def api_get_thresholds():
    """Get all custom thresholds and default safe operating limits."""
    import config
    
    # Build defaults from SENSOR_THRESHOLDS (safe operating limits)
    # Fall back to SENSOR_RANGES if threshold not defined
    defaults = {}
    for name, info in config.SENSOR_RANGES.items():
        threshold = config.SENSOR_THRESHOLDS.get(name, {})
        defaults[name] = {
            'low': threshold.get('low', info['min']),
            'high': threshold.get('high', info['max']),
            'unit': info.get('unit', ''),
            # Also include ranges for reference
            'range_min': info['min'],
            'range_max': info['max']
        }
    
    return jsonify({
        'thresholds': custom_thresholds,
        'defaults': defaults
    })


@app.route('/api/thresholds', methods=['POST'])
@require_auth
def api_set_threshold():
    """Set custom threshold for a sensor."""
    data = request.get_json()
    if not data or 'sensor' not in data:
        return jsonify({'error': 'Missing sensor name'}), 400
    
    sensor = data['sensor']
    
    # Validate sensor exists
    if sensor not in config.SENSOR_RANGES:
        return jsonify({'error': f'Unknown sensor: {sensor}'}), 400
    
    # Handle reset
    if data.get('reset'):
        if sensor in custom_thresholds:
            del custom_thresholds[sensor]
        return jsonify({'success': True, 'message': f'Threshold for {sensor} reset to default'})
    
    # Set custom threshold
    min_val = data.get('min')
    max_val = data.get('max')
    
    if min_val is None or max_val is None:
        return jsonify({'error': 'Missing min or max value'}), 400
    
    try:
        min_val = float(min_val)
        max_val = float(max_val)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid min or max value'}), 400
    
    if min_val >= max_val:
        return jsonify({'error': 'Min must be less than max'}), 400
    
    custom_thresholds[sensor] = {'min': min_val, 'max': max_val}
    
    return jsonify({
        'success': True,
        'sensor': sensor,
        'min': min_val,
        'max': max_val
    })


@app.route('/api/injection-settings', methods=['GET'])
@require_auth
def api_get_injection_settings():
    """Get anomaly injection settings for producer."""
    # Return inject_now flag and clear it immediately (one-time trigger)
    inject_now = injection_settings.get('inject_now', False)
    if inject_now:
        injection_settings['inject_now'] = False
    
    return jsonify({
        'enabled': injection_settings['enabled'],
        'interval_minutes': injection_settings['interval_minutes'],
        'next_injection_time': injection_settings['next_injection_time'],
        'inject_now': inject_now,
        'thresholds': custom_thresholds
    })


@app.route('/api/injection-settings', methods=['POST'])
@require_auth
def api_set_injection_settings():
    """Update anomaly injection settings."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing data'}), 400
    
    if 'enabled' in data:
        injection_settings['enabled'] = bool(data['enabled'])
    
    if 'interval_minutes' in data:
        try:
            interval = int(data['interval_minutes'])
            if interval < 1:
                return jsonify({'error': 'Interval must be at least 1 minute'}), 400
            injection_settings['interval_minutes'] = interval
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid interval'}), 400
    
    # Calculate next injection time
    if injection_settings['enabled']:
        from datetime import datetime, timedelta, timezone
        injection_settings['next_injection_time'] = (
            datetime.now(timezone.utc) + timedelta(minutes=injection_settings['interval_minutes'])
        ).isoformat()
    else:
        injection_settings['next_injection_time'] = None
    
    return jsonify({
        'success': True,
        'settings': injection_settings
    })


@app.route('/api/inject-anomaly', methods=['POST'])
@require_auth
def api_inject_anomaly_now():
    """Trigger immediate anomaly injection."""
    injection_settings['inject_now'] = True
    return jsonify({
        'success': True,
        'message': 'Anomaly injection triggered for next reading'
    })


@app.route('/api/export')
@require_auth
def export_data():
    """Export recent readings as CSV with all 50 parameters."""
    limit = request.args.get('limit', default=500, type=int)
    if limit is None:
        limit = 500
    limit = max(1, min(limit, 5000))
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not connected'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                timestamp, created_at,
                temperature, pressure, humidity, ambient_temp, dew_point,
                air_quality_index, co2_level, particle_count, noise_level, light_intensity,
                vibration, rpm, torque, shaft_alignment, bearing_temp,
                motor_current, belt_tension, gear_wear, coupling_temp, lubrication_pressure,
                coolant_temp, exhaust_temp, oil_temp, radiator_temp, thermal_efficiency,
                heat_dissipation, inlet_temp, outlet_temp, core_temp, surface_temp,
                voltage, current, power_factor, frequency, resistance,
                capacitance, inductance, phase_angle, harmonic_distortion, ground_fault,
                flow_rate, fluid_pressure, viscosity, density, reynolds_number,
                pipe_pressure_drop, pump_efficiency, cavitation_index, turbulence, valve_position
            FROM sensor_readings
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        # Write CSV header with all 50 parameters
        writer.writerow([
            'timestamp', 'created_at',
            'temperature', 'pressure', 'humidity', 'ambient_temp', 'dew_point',
            'air_quality_index', 'co2_level', 'particle_count', 'noise_level', 'light_intensity',
            'vibration', 'rpm', 'torque', 'shaft_alignment', 'bearing_temp',
            'motor_current', 'belt_tension', 'gear_wear', 'coupling_temp', 'lubrication_pressure',
            'coolant_temp', 'exhaust_temp', 'oil_temp', 'radiator_temp', 'thermal_efficiency',
            'heat_dissipation', 'inlet_temp', 'outlet_temp', 'core_temp', 'surface_temp',
            'voltage', 'current', 'power_factor', 'frequency', 'resistance',
            'capacitance', 'inductance', 'phase_angle', 'harmonic_distortion', 'ground_fault',
            'flow_rate', 'fluid_pressure', 'viscosity', 'density', 'reynolds_number',
            'pipe_pressure_drop', 'pump_efficiency', 'cavitation_index', 'turbulence', 'valve_position'
        ])
        for row in rows:
            writer.writerow(row)

        response = make_response(output.getvalue())
        filename = f"sensor_readings_50params_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Type'] = 'text/csv'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-future-report', methods=['POST'])
@require_auth
def api_generate_future_report():
    """Generate and download LSTM future anomaly prediction report as PDF."""
    if not ML_REPORTS_AVAILABLE:
        return jsonify({'error': 'ML reports not available'}), 503
    
    if not LSTM_AVAILABLE:
        return jsonify({'error': 'LSTM not available'}), 503
    
    try:
        # Get report generator
        report_gen = ReportGenerator()
        
        # Generate the future anomaly report
        report_text = report_gen.generate_future_anomaly_report()
        
        # Generate PDF
        pdf_buffer = generate_pdf_from_markdown(
            report_text,
            f"LSTM Future Anomaly Prediction Report - {datetime.now().strftime('%Y-%m-%d')}"
        )
        
        # Return PDF
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=future_anomaly_report_{datetime.now().strftime("%Y-%m-%d")}.pdf'
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/lstm-predictions')
@require_auth
def api_lstm_predictions():
    """Get LSTM future anomaly predictions with detailed sensor analysis."""
    if not LSTM_AVAILABLE:
        return jsonify({
            'available': False,
            'error': 'LSTM not available'
        })
    
    try:
        predictor = get_predictor()
        
        # Get current prediction (now includes sensor_analyses and sensor_details)
        current_prediction = predict_next_anomaly()
        
        # Get LSTM detector info
        lstm_detector = get_lstm_detector()
        
        return jsonify({
            'available': True,
            'trained': lstm_detector.is_trained if lstm_detector else False,
            'current_prediction': current_prediction,
            'model_info': {
                'threshold': float(lstm_detector.threshold) if lstm_detector and lstm_detector.is_trained else 0,
                'sequence_length': lstm_detector.sequence_length if lstm_detector else 0
            }
        })
    except Exception as e:
        return jsonify({
            'available': True,
            'error': str(e)
        }), 500


@app.route('/api/lstm-status')
@require_auth
def api_lstm_status():
    """Get LSTM model training status and quality metrics."""
    if not LSTM_AVAILABLE:
        return jsonify({
            'available': False,
            'trained': False,
            'quality_score': 0,
            'message': 'LSTM not available - TensorFlow not installed'
        })
    
    try:
        lstm_detector = get_lstm_detector()
        
        if not lstm_detector or not lstm_detector.is_trained:
            return jsonify({
                'available': True,
                'trained': False,
                'quality_score': 0,
                'message': 'LSTM model not trained yet'
            })
        
        # Get reading count
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM sensor_readings')
        reading_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        # Calculate quality score (0-100)
        quality_score = calculate_lstm_quality_score(lstm_detector, reading_count)
        
        return jsonify({
            'available': True,
            'trained': True,
            'quality_score': quality_score,
            'threshold': float(lstm_detector.threshold),
            'sequence_length': lstm_detector.sequence_length,
            'reading_count': reading_count,
            'message': get_quality_message(quality_score)
        })
    except Exception as e:
        return jsonify({
            'available': True,
            'error': str(e)
        }), 500


def calculate_lstm_quality_score(lstm_detector, reading_count):
    """Calculate LSTM training quality score (0-100)."""
    score = 0
    
    # Data amount score (0-40 points)
    if reading_count >= 1000:
        data_score = 40
    elif reading_count >= 500:
        data_score = 30 + (reading_count - 500) / 500 * 10
    elif reading_count >= 100:
        data_score = 10 + (reading_count - 100) / 400 * 20
    else:
        data_score = reading_count / 100 * 10
    score += data_score
    
    # Model performance score (0-30 points)
    # Based on threshold - lower threshold means model is more sensitive
    threshold = lstm_detector.threshold
    if threshold < 0.5:
        perf_score = 30
    elif threshold < 1.0:
        perf_score = 20 + (1.0 - threshold) / 0.5 * 10
    elif threshold < 2.0:
        perf_score = 10 + (2.0 - threshold) / 1.0 * 10
    else:
        perf_score = max(0, 10 - (threshold - 2.0) * 2)
    score += perf_score
    
    # Sequence coverage score (0-30 points)
    # More data = better coverage
    if reading_count >= 1000:
        coverage_score = 30
    elif reading_count >= 500:
        coverage_score = 20 + (reading_count - 500) / 500 * 10
    else:
        coverage_score = reading_count / 500 * 20
    score += coverage_score
    
    return min(100, max(0, score))


def get_quality_message(quality_score):
    """Get quality message based on score."""
    if quality_score >= 80:
        return 'Excellent - Model is well-trained and reliable'
    elif quality_score >= 60:
        return 'Good - Model is adequately trained'
    elif quality_score >= 40:
        return 'Fair - Model needs more training data'
    else:
        return 'Poor - Collect more data for better predictions'


# ============================================================================
# MACHINE MANAGEMENT API ENDPOINTS (Phase 1)
# ============================================================================

@app.route('/api/machines', methods=['GET'])
def api_machines():
    """Get all machine states"""
    with machine_state_lock:
        return jsonify({
            'machines': {
                machine_id: {
                    'running': state['running'],
                    'sensors': {
                        sensor_name: {
                            'enabled': sensor_config['enabled'],
                            'baseline': sensor_config['baseline']
                        }
                        for sensor_name, sensor_config in state['sensors'].items()
                    }
                }
                for machine_id, state in machine_state.items()
            }
        })

@app.route('/api/machines/<machine_id>/start', methods=['POST'])
@require_machine_access('machine_id')
def api_start_machine(machine_id):
    """Start a machine (set running state and start producer/consumer)"""
    if machine_id not in ['A', 'B', 'C']:
        return jsonify({'success': False, 'error': 'Invalid machine ID'}), 400
    
    # Check if machine is already running
    with machine_state_lock:
        if machine_state[machine_id]['running']:
            return jsonify({'success': False, 'error': f'Machine {machine_id} is already running'}), 409
    
    # Start producer if not running
    if not is_component_running('producer'):
        producer_result = start_component('producer')
        producer_data = producer_result.get_json()
        if not producer_data.get('success'):
            return jsonify({'success': False, 'error': f"Failed to start producer: {producer_data.get('error')}"}), 500
    
    # Start consumer if not running
    if not is_component_running('consumer'):
        consumer_result = start_component('consumer')
        consumer_data = consumer_result.get_json()
        if not consumer_data.get('success'):
            return jsonify({'success': False, 'error': f"Failed to start consumer: {consumer_data.get('error')}"}), 500
    
    with machine_state_lock:
        machine_state[machine_id]['running'] = True
    
    return jsonify({'success': True, 'machine_id': machine_id, 'running': True})

@app.route('/api/machines/<machine_id>/stop', methods=['POST'])
@require_machine_access('machine_id')
def api_stop_machine(machine_id):
    """Stop a machine (set running state and stop producer)"""
    if machine_id not in ['A', 'B', 'C']:
        return jsonify({'success': False, 'error': 'Invalid machine ID'}), 400
    
    # Stop producer if running
    if is_component_running('producer'):
        stop_result = stop_component('producer')
        stop_data = stop_result.get_json()
        if not stop_data.get('success'):
            logger.warning(f"Failed to stop producer: {stop_data.get('error')}")
            # Continue anyway - we'll still set the state
    
    with machine_state_lock:
        machine_state[machine_id]['running'] = False
    
    return jsonify({'success': True, 'machine_id': machine_id, 'running': False})

@app.route('/api/machines/<machine_id>/sensors/<sensor_name>/toggle', methods=['POST'])
@require_machine_access('machine_id')
def api_toggle_sensor(machine_id, sensor_name):
    """Toggle sensor enabled/disabled state (built-in sensors only)"""
    if machine_id not in ['A', 'B', 'C']:
        return jsonify({'success': False, 'error': 'Invalid machine ID'}), 400
    
    import config
    if sensor_name not in config.SENSOR_RANGES:
        return jsonify({'success': False, 'error': 'Invalid sensor name'}), 400
    
    with machine_state_lock:
        if sensor_name in machine_state[machine_id]['sensors']:
            current_state = machine_state[machine_id]['sensors'][sensor_name]['enabled']
            machine_state[machine_id]['sensors'][sensor_name]['enabled'] = not current_state
            return jsonify({
                'success': True,
                'machine_id': machine_id,
                'sensor_name': sensor_name,
                'enabled': not current_state
            })
        else:
            return jsonify({'success': False, 'error': 'Sensor not found'}), 404


@app.route('/api/machines/<machine_id>/custom-sensors/<sensor_name>/toggle', methods=['POST'])
@require_machine_access('machine_id')
def api_toggle_custom_sensor(machine_id, sensor_name):
    """Toggle custom sensor enabled/disabled state for a specific machine (uses machine_sensor_config)"""
    if machine_id not in ['A', 'B', 'C']:
        return jsonify({'success': False, 'error': 'Invalid machine ID'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Check if custom sensor exists and is active
        cursor.execute("""
            SELECT sensor_name FROM custom_sensors 
            WHERE sensor_name = %s AND is_active = TRUE
        """, (sensor_name,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Custom sensor not found or inactive'}), 404
        
        # Get current enabled state from machine_sensor_config
        cursor.execute("""
            SELECT enabled FROM machine_sensor_config
            WHERE machine_id = %s AND sensor_name = %s
        """, (machine_id, sensor_name))
        row = cursor.fetchone()
        
        if row:
            # Update existing config
            new_enabled = not row[0]
            cursor.execute("""
                UPDATE machine_sensor_config
                SET enabled = %s, updated_at = NOW()
                WHERE machine_id = %s AND sensor_name = %s
            """, (new_enabled, machine_id, sensor_name))
        else:
            # Create new config (default to enabled, but we're toggling so set to False)
            new_enabled = False
            cursor.execute("""
                INSERT INTO machine_sensor_config (machine_id, sensor_name, enabled, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (machine_id, sensor_name) 
                DO UPDATE SET enabled = %s, updated_at = NOW()
            """, (machine_id, sensor_name, new_enabled, new_enabled))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'machine_id': machine_id,
            'sensor_name': sensor_name,
            'enabled': new_enabled
        })
    except Exception as e:
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/machines/<machine_id>/custom-sensors', methods=['GET'])
@require_machine_access('machine_id')
def api_get_machine_custom_sensors(machine_id):
    """Get enabled/disabled state of custom sensors for a specific machine"""
    if machine_id not in ['A', 'B', 'C']:
        return jsonify({'success': False, 'error': 'Invalid machine ID'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Get all active custom sensors with their machine-specific enabled state
        cursor.execute("""
            SELECT 
                cs.sensor_name,
                COALESCE(msc.enabled, TRUE) as enabled
            FROM custom_sensors cs
            LEFT JOIN machine_sensor_config msc 
                ON cs.sensor_name = msc.sensor_name 
                AND msc.machine_id = %s
            WHERE cs.is_active = TRUE
            ORDER BY cs.sensor_name
        """, (machine_id,))
        
        sensors = {}
        for row in cursor.fetchall():
            sensors[row[0]] = {
                'enabled': row[1]
            }
        
        cursor.close()
        return_db_connection(conn)
        
        return jsonify({
            'success': True,
            'machine_id': machine_id,
            'sensors': sensors
        })
    except Exception as e:
        if conn:
            return_db_connection(conn)
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# RESOLUTION HELPER FUNCTIONS
# ============================================================================

def resolve_sensor_enabled(machine_id, sensor_name):
    """
    Resolve enabled state for a sensor using resolution order:
    machine_sensor_config.enabled (if exists) → 
    global_sensor_config.enabled (built-in) OR custom_sensors.is_active (custom) → 
    default True
    
    Returns: (enabled: bool, source: str)
    """
    conn = get_db_connection()
    if not conn:
        return True, 'default'  # Safe default
    
    try:
        cursor = conn.cursor()
        
        # Check machine-specific override first
        cursor.execute("""
            SELECT enabled FROM machine_sensor_config
            WHERE machine_id = %s AND sensor_name = %s
        """, (machine_id, sensor_name))
        row = cursor.fetchone()
        if row is not None:
            cursor.close()
            return_db_connection(conn)
            return row[0], 'machine'
        
        # Check if it's a built-in sensor (check global_sensor_config)
        cursor.execute("""
            SELECT enabled FROM global_sensor_config
            WHERE sensor_name = %s
        """, (sensor_name,))
        row = cursor.fetchone()
        if row is not None:
            cursor.close()
            conn.close()
            return row[0], 'global'
        
        # Check if it's a custom sensor (check custom_sensors.is_active)
        cursor.execute("""
            SELECT is_active FROM custom_sensors
            WHERE sensor_name = %s
        """, (sensor_name,))
        row = cursor.fetchone()
        if row is not None:
            cursor.close()
            conn.close()
            return row[0], 'global'
        
        # Default: enabled
        cursor.close()
        conn.close()
        return True, 'default'
        
    except Exception as e:
        logging.error(f"Error resolving sensor enabled state: {e}")
        if conn:
            cursor.close()
            conn.close()
        return True, 'default'  # Safe default


def resolve_sensor_frequency(machine_id, sensor_name):
    """
    Resolve frequency (seconds) for a sensor using resolution order:
    machine_sensor_config.frequency_seconds (if set) → 
    global_sensor_config.default_frequency_seconds (built-in) OR custom_sensors.default_frequency_seconds (custom) → 
    config.INTERVAL_SECONDS (system default)
    
    Returns: (frequency_seconds: int, source: str)
    """
    import config
    conn = get_db_connection()
    if not conn:
        return config.INTERVAL_SECONDS, 'default'  # Safe default
    
    try:
        cursor = conn.cursor()
        
        # Check machine-specific override first
        cursor.execute("""
            SELECT frequency_seconds FROM machine_sensor_config
            WHERE machine_id = %s AND sensor_name = %s AND frequency_seconds IS NOT NULL
        """, (machine_id, sensor_name))
        row = cursor.fetchone()
        if row is not None and row[0] is not None:
            cursor.close()
            conn.close()
            return row[0], 'machine'
        
        # Check if it's a built-in sensor (check global_sensor_config)
        cursor.execute("""
            SELECT default_frequency_seconds FROM global_sensor_config
            WHERE sensor_name = %s AND default_frequency_seconds IS NOT NULL
        """, (sensor_name,))
        row = cursor.fetchone()
        if row is not None and row[0] is not None:
            cursor.close()
            conn.close()
            return row[0], 'global'
        
        # Check if it's a custom sensor (check custom_sensors.default_frequency_seconds)
        cursor.execute("""
            SELECT default_frequency_seconds FROM custom_sensors
            WHERE sensor_name = %s AND default_frequency_seconds IS NOT NULL
        """, (sensor_name,))
        row = cursor.fetchone()
        if row is not None and row[0] is not None:
            cursor.close()
            conn.close()
            return row[0], 'global'
        
        # Default: system INTERVAL_SECONDS
        cursor.close()
        conn.close()
        return config.INTERVAL_SECONDS, 'default'
        
    except Exception as e:
        logging.error(f"Error resolving sensor frequency: {e}")
        if conn:
            cursor.close()
            conn.close()
        return config.INTERVAL_SECONDS, 'default'  # Safe default


@app.route('/api/machines/<machine_id>/sensors/<sensor_name>/baseline', methods=['POST'])
@require_machine_access('machine_id')
def api_set_baseline(machine_id, sensor_name):
    """Set baseline value for a sensor (in-memory only)"""
    if machine_id not in ['A', 'B', 'C']:
        return jsonify({'success': False, 'error': 'Invalid machine ID'}), 400
    
    import config
    if sensor_name not in config.SENSOR_RANGES:
        return jsonify({'success': False, 'error': 'Invalid sensor name'}), 400
    
    data = request.json or {}
    baseline = data.get('baseline')
    
    if baseline is not None:
        try:
            baseline = float(baseline)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Baseline must be a number'}), 400
    
    with machine_state_lock:
        if sensor_name in machine_state[machine_id]['sensors']:
            machine_state[machine_id]['sensors'][sensor_name]['baseline'] = baseline
            return jsonify({
                'success': True,
                'machine_id': machine_id,
                'sensor_name': sensor_name,
                'baseline': baseline
            })
        else:
            return jsonify({'success': False, 'error': 'Sensor not found'}), 404

@app.route('/api/machines/<machine_id>/sensors/<sensor_name>/frequency', methods=['GET', 'POST'])
@require_machine_access('machine_id')
def api_sensor_frequency(machine_id, sensor_name):
    """Get or set frequency for a sensor on a specific machine"""
    if machine_id not in ['A', 'B', 'C']:
        return jsonify({'success': False, 'error': 'Invalid machine ID'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        if request.method == 'GET':
            # Get resolved frequency
            frequency, source = resolve_sensor_frequency(machine_id, sensor_name)
            cursor.close()
            conn.close()
            return jsonify({
                'success': True,
                'machine_id': machine_id,
                'sensor_name': sensor_name,
                'frequency_seconds': frequency,
                'source': source
            })
        
        else:  # POST
            data = request.json or {}
            frequency = data.get('frequency_seconds')
            
            if frequency is None:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': 'frequency_seconds required'}), 400
            
            try:
                frequency = int(frequency)
                if frequency < 1 or frequency > 3600:
                    cursor.close()
                    conn.close()
                    return jsonify({'success': False, 'error': 'frequency_seconds must be between 1 and 3600'}), 400
            except (ValueError, TypeError):
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': 'frequency_seconds must be an integer'}), 400
            
            # Upsert into machine_sensor_config
            cursor.execute("""
                INSERT INTO machine_sensor_config (machine_id, sensor_name, frequency_seconds, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (machine_id, sensor_name)
                DO UPDATE SET frequency_seconds = %s, updated_at = NOW()
            """, (machine_id, sensor_name, frequency, frequency))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'machine_id': machine_id,
                'sensor_name': sensor_name,
                'frequency_seconds': frequency
            })
            
    except Exception as e:
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sensors/<sensor_name>/frequency', methods=['GET', 'POST'])
@require_admin
def api_global_sensor_frequency(sensor_name):
    """Get or set global frequency for a built-in sensor (uses global_sensor_config)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Check if it's a built-in sensor
        import config
        if sensor_name not in config.SENSOR_RANGES:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Sensor not found or not a built-in sensor'}), 404
        
        if request.method == 'GET':
            # Get global frequency
            cursor.execute("""
                SELECT default_frequency_seconds FROM global_sensor_config
                WHERE sensor_name = %s
            """, (sensor_name,))
            row = cursor.fetchone()
            
            import config
            frequency = row[0] if row and row[0] is not None else config.INTERVAL_SECONDS
            source = 'global' if row and row[0] is not None else 'default'
            
            cursor.close()
            conn.close()
            return jsonify({
                'success': True,
                'sensor_name': sensor_name,
                'frequency_seconds': frequency,
                'source': source
            })
        
        else:  # POST
            data = request.json or {}
            frequency = data.get('frequency_seconds')
            
            if frequency is None:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': 'frequency_seconds required'}), 400
            
            try:
                frequency = int(frequency)
                if frequency < 1 or frequency > 3600:
                    cursor.close()
                    conn.close()
                    return jsonify({'success': False, 'error': 'frequency_seconds must be between 1 and 3600'}), 400
            except (ValueError, TypeError):
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': 'frequency_seconds must be an integer'}), 400
            
            # Upsert into global_sensor_config
            cursor.execute("""
                INSERT INTO global_sensor_config (sensor_name, default_frequency_seconds, enabled, updated_at)
                VALUES (%s, %s, TRUE, NOW())
                ON CONFLICT (sensor_name)
                DO UPDATE SET default_frequency_seconds = %s, updated_at = NOW()
            """, (sensor_name, frequency, frequency))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'sensor_name': sensor_name,
                'frequency_seconds': frequency
            })
            
    except Exception as e:
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/machines/<machine_id>/stats', methods=['GET'])
@require_machine_access('machine_id')
def api_machine_stats(machine_id):
    """Get stats filtered by machine and enabled sensors only"""
    if machine_id not in ['A', 'B', 'C']:
        return jsonify({'error': 'Invalid machine ID'}), 400
    
    # Get enabled sensors for this machine
    with machine_state_lock:
        enabled_sensors = {
            sensor_name
            for sensor_name, sensor_config in machine_state[machine_id]['sensors'].items()
            if sensor_config['enabled']
        }
    
    # Get all stats (we'll filter in the response)
    all_stats = get_stats()
    if 'error' in all_stats:
        return jsonify(all_stats), 500
    
    # Filter stats_by_category to only include enabled sensors
    filtered_stats = all_stats.copy()
    if 'stats_by_category' in filtered_stats:
        for category_key, category_data in filtered_stats['stats_by_category'].items():
            if 'sensors' in category_data:
                category_data['sensors'] = {
                    sensor_name: sensor_data
                    for sensor_name, sensor_data in category_data['sensors'].items()
                    if sensor_name in enabled_sensors
                }
    
    # Filter recent_readings_full to only include enabled sensors
    if 'recent_readings_full' in filtered_stats:
        for reading in filtered_stats['recent_readings_full']:
            # Keep only enabled sensor fields
            reading_copy = {'timestamp': reading.get('timestamp'), 'created_at': reading.get('created_at')}
            for sensor_name in enabled_sensors:
                if sensor_name in reading:
                    reading_copy[sensor_name] = reading[sensor_name]
            # Replace original reading with filtered version
            for key in list(reading.keys()):
                if key not in reading_copy:
                    del reading[key]
            reading.update(reading_copy)
    
    filtered_stats['machine_id'] = machine_id
    filtered_stats['enabled_sensors_count'] = len(enabled_sensors)
    filtered_stats['total_sensors_count'] = len(machine_state[machine_id]['sensors'])
    
    return jsonify(filtered_stats)


# ============================================================================
# CUSTOM SENSOR MANAGEMENT API ENDPOINTS (Phase 5)
# ============================================================================

@app.route('/api/admin/custom-sensors', methods=['GET'])
@require_admin
@log_action('READ', resource_type='custom_sensor', resource_id=None)
def api_list_custom_sensors():
    """List all custom sensors (active and inactive)."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'custom_sensors'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            db_name = conn.get_dsn_parameters().get('dbname')
            db_host = conn.get_dsn_parameters().get('host')
            cursor.close()
            conn.close()
            return jsonify({
                'error': 'custom_sensors table does not exist. Migration add_custom_sensors.sql has not been applied to this database.'
            }), 500
        
        cursor.execute("""
            SELECT id, sensor_name, category, unit, min_range, max_range,
                   low_threshold, high_threshold, is_active, created_at, updated_at, created_by
            FROM custom_sensors
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        sensors = []
        for row in rows:
            sensors.append({
                'id': row[0],
                'sensor_name': row[1],
                'category': row[2] or 'custom',
                'unit': row[3] or '',
                'min_range': float(row[4]),
                'max_range': float(row[5]),
                'low_threshold': float(row[6]) if row[6] else None,
                'high_threshold': float(row[7]) if row[7] else None,
                'is_active': row[8],
                'created_at': str(row[9]) if row[9] else None,
                'updated_at': str(row[10]) if row[10] else None,
                'created_by': row[11] or 'admin'
            })
        
        return jsonify({'sensors': sensors})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/custom-sensors', methods=['POST'])
@require_admin
@log_action('CREATE', resource_type='custom_sensor', resource_id=None)
def api_create_custom_sensor():
    """Create a new custom sensor."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing request data'}), 400
    
    # Validate required fields
    sensor_name = data.get('sensor_name', '').strip()
    if not sensor_name:
        return jsonify({'error': 'sensor_name is required'}), 400
    
    # Validate sensor name format (alphanumeric + underscore)
    if not sensor_name.replace('_', '').isalnum():
        return jsonify({'error': 'sensor_name must contain only letters, numbers, and underscores'}), 400
    
    # Check for conflicts with built-in sensors
    import config
    if sensor_name in config.SENSOR_RANGES:
        return jsonify({'error': f'sensor_name "{sensor_name}" conflicts with built-in sensor'}), 400
    
    min_range = data.get('min_range')
    max_range = data.get('max_range')
    if min_range is None or max_range is None:
        return jsonify({'error': 'min_range and max_range are required'}), 400
    
    try:
        min_range = float(min_range)
        max_range = float(max_range)
    except (ValueError, TypeError):
        return jsonify({'error': 'min_range and max_range must be numbers'}), 400
    
    if min_range >= max_range:
        return jsonify({'error': 'min_range must be less than max_range'}), 400
    
    category = data.get('category', 'custom')
    unit = data.get('unit', '')
    low_threshold = data.get('low_threshold')
    high_threshold = data.get('high_threshold')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Check if sensor name already exists
        cursor.execute("SELECT id FROM custom_sensors WHERE sensor_name = %s", (sensor_name,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': f'sensor_name "{sensor_name}" already exists'}), 400
        
        # Insert new sensor
        cursor.execute("""
            INSERT INTO custom_sensors 
            (sensor_name, category, unit, min_range, max_range, low_threshold, high_threshold, is_active, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s)
            RETURNING id, created_at, updated_at
        """, (
            sensor_name, category, unit, min_range, max_range,
            low_threshold, high_threshold, 'admin'
        ))
        
        row = cursor.fetchone()
        sensor_id = row[0]
        created_at = row[1]
        updated_at = row[2]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'sensor': {
                'id': sensor_id,
                'sensor_name': sensor_name,
                'category': category,
                'unit': unit,
                'min_range': min_range,
                'max_range': max_range,
                'low_threshold': low_threshold,
                'high_threshold': high_threshold,
                'is_active': True,
                'created_at': str(created_at),
                'updated_at': str(updated_at),
                'created_by': 'admin'
            }
        }), 201
    except psycopg2.IntegrityError:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'error': f'sensor_name "{sensor_name}" already exists'}), 400
    except Exception as e:
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/custom-sensors/<int:sensor_id>', methods=['GET'])
@require_admin
@log_action('READ', resource_type='custom_sensor', resource_id=None)
def api_get_custom_sensor(sensor_id):
    """Get a specific custom sensor by ID."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sensor_name, category, unit, min_range, max_range,
                   low_threshold, high_threshold, is_active, created_at, updated_at, created_by
            FROM custom_sensors
            WHERE id = %s
        """, (sensor_id,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Sensor not found'}), 404
        
        return jsonify({
            'id': row[0],
            'sensor_name': row[1],
            'category': row[2] or 'custom',
            'unit': row[3] or '',
            'min_range': float(row[4]),
            'max_range': float(row[5]),
            'low_threshold': float(row[6]) if row[6] else None,
            'high_threshold': float(row[7]) if row[7] else None,
            'is_active': row[8],
            'created_at': str(row[9]) if row[9] else None,
            'updated_at': str(row[10]) if row[10] else None,
            'created_by': row[11] or 'admin'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/custom-sensors/<int:sensor_id>', methods=['PUT'])
@require_admin
@log_action('UPDATE', resource_type='custom_sensor', resource_id=None, capture_state=True)  # sensor_id extracted from kwargs
def api_update_custom_sensor(sensor_id):
    """Update a custom sensor."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing request data'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Check if sensor exists
        cursor.execute("SELECT sensor_name FROM custom_sensors WHERE id = %s", (sensor_id,))
        existing = cursor.fetchone()
        if not existing:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Sensor not found'}), 404
        
        # Build update query dynamically based on provided fields
        updates = []
        values = []
        
        if 'category' in data:
            updates.append("category = %s")
            values.append(data['category'])
        
        if 'unit' in data:
            updates.append("unit = %s")
            values.append(data['unit'])
        
        if 'min_range' in data:
            try:
                min_range = float(data['min_range'])
                updates.append("min_range = %s")
                values.append(min_range)
            except (ValueError, TypeError):
                return jsonify({'error': 'min_range must be a number'}), 400
        
        if 'max_range' in data:
            try:
                max_range = float(data['max_range'])
                updates.append("max_range = %s")
                values.append(max_range)
            except (ValueError, TypeError):
                return jsonify({'error': 'max_range must be a number'}), 400
        
        if 'low_threshold' in data:
            if data['low_threshold'] is None:
                updates.append("low_threshold = NULL")
            else:
                try:
                    low_threshold = float(data['low_threshold'])
                    updates.append("low_threshold = %s")
                    values.append(low_threshold)
                except (ValueError, TypeError):
                    return jsonify({'error': 'low_threshold must be a number'}), 400
        
        if 'high_threshold' in data:
            if data['high_threshold'] is None:
                updates.append("high_threshold = NULL")
            else:
                try:
                    high_threshold = float(data['high_threshold'])
                    updates.append("high_threshold = %s")
                    values.append(high_threshold)
                except (ValueError, TypeError):
                    return jsonify({'error': 'high_threshold must be a number'}), 400
        
        if 'is_active' in data:
            updates.append("is_active = %s")
            values.append(bool(data['is_active']))
        
        if not updates:
            cursor.close()
            conn.close()
            return jsonify({'error': 'No fields to update'}), 400
        
        # Validate min/max range if both are being updated
        if 'min_range' in data and 'max_range' in data:
            if float(data['min_range']) >= float(data['max_range']):
                return jsonify({'error': 'min_range must be less than max_range'}), 400
        
        values.append(sensor_id)
        query = f"UPDATE custom_sensors SET {', '.join(updates)} WHERE id = %s RETURNING *"
        
        cursor.execute(query, values)
        row = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'sensor': {
                'id': row[0],
                'sensor_name': row[1],
                'category': row[2] or 'custom',
                'unit': row[3] or '',
                'min_range': float(row[4]),
                'max_range': float(row[5]),
                'low_threshold': float(row[6]) if row[6] else None,
                'high_threshold': float(row[7]) if row[7] else None,
                'is_active': row[8],
                'created_at': str(row[9]) if row[9] else None,
                'updated_at': str(row[10]) if row[10] else None,
                'created_by': row[11] or 'admin'
            }
        })
    except Exception as e:
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/parse-sensor-file', methods=['POST'])
@require_admin
@log_action('PARSE', resource_type='sensor_file', resource_id=None)
def api_parse_sensor_file():
    """Parse uploaded file (PDF/TXT/CSV/JSON) and extract sensor specs using AI."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    filename = file.filename.lower()
    extracted_text = ""
    
    try:
        # Extract text based on file type
        if filename.endswith('.pdf'):
            if not PDF_AVAILABLE:
                return jsonify({'error': 'PDF parsing not available. Install PyPDF2.'}), 500
            
            # Reset file pointer to beginning
            file.seek(0)
            pdf_reader = PdfReader(file)
            # Extract text from first 2 pages
            for page_num in range(min(2, len(pdf_reader.pages))):
                page = pdf_reader.pages[page_num]
                extracted_text += page.extract_text() + "\n"
        
        elif filename.endswith('.txt') or filename.endswith('.csv'):
            # Read and decode text files
            file_bytes = file.read()
            extracted_text = file_bytes.decode('utf-8', errors='ignore')
        
        elif filename.endswith('.json'):
            # Read and decode JSON files
            file_bytes = file.read()
            extracted_text = file_bytes.decode('utf-8', errors='ignore')
            # Try to parse as JSON first - if valid, return it directly
            try:
                json_data = json.loads(extracted_text)
                # If it's already in the right format, return it
                if isinstance(json_data, dict) and 'sensor_name' in json_data:
                    return jsonify(json_data), 200
            except json.JSONDecodeError:
                pass  # Continue with AI parsing
        
        else:
            return jsonify({'error': 'Unsupported file type. Use PDF, TXT, CSV, or JSON.'}), 400
        
        if not extracted_text.strip():
            return jsonify({'error': 'No text extracted from file'}), 400
        
        # AI Processing with Groq
        groq_api_key = os.environ.get('GROQ_API_KEY')
        
        if groq_api_key and GROQ_AVAILABLE:
            try:
                client = Groq(api_key=groq_api_key)
                
                system_prompt = """You are an engineering assistant. Extract sensor specifications from this text. 
Return ONLY raw JSON (no markdown formatting) with these exact keys: 
- 'sensor_name' (snake_case string)
- 'min_range' (float)
- 'max_range' (float)
- 'unit' (string)
- 'low_threshold' (float or null)
- 'high_threshold' (float or null)
- 'category' (string: one of environmental, mechanical, thermal, electrical, or fluid)

Example output:
{"sensor_name": "pressure_sensor", "min_range": 0, "max_range": 250, "unit": "PSI", "low_threshold": 20, "high_threshold": 220, "category": "fluid"}"""
                
                user_prompt = extracted_text
                
                response = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                
                ai_response = response.choices[0].message.content.strip()
                
                # Remove markdown code blocks if present
                if ai_response.startswith('```'):
                    # Remove ```json or ``` at start
                    ai_response = ai_response.split('```', 1)[1]
                    if ai_response.startswith('json'):
                        ai_response = ai_response[4:]
                    # Remove ``` at end
                    if ai_response.endswith('```'):
                        ai_response = ai_response.rsplit('```', 1)[0]
                    ai_response = ai_response.strip()
                
                # Parse JSON response
                sensor_data = json.loads(ai_response)
                
                # Validate required fields
                required_fields = ['sensor_name', 'min_range', 'max_range', 'unit', 'category']
                for field in required_fields:
                    if field not in sensor_data:
                        raise ValueError(f"Missing required field: {field}")
                
                return jsonify(sensor_data), 200
                
            except Exception as e:
                # If AI parsing fails, fall through to mock response
                print(f"AI parsing failed: {e}")
                pass
        
        # Fallback: Return mock data for testing
        mock_response = {
            "sensor_name": "mock_pressure_sensor",
            "min_range": 0,
            "max_range": 250,
            "unit": "PSI",
            "low_threshold": 20,
            "high_threshold": 220,
            "category": "fluid"
        }
        return jsonify(mock_response), 200
        
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500


@app.route('/api/admin/custom-sensors/<int:sensor_id>', methods=['DELETE'])
@require_admin
@log_action('DELETE', resource_type='custom_sensor', resource_id=None)  # sensor_id extracted from kwargs
def api_delete_custom_sensor(sensor_id):
    """Soft delete a custom sensor (set is_active=false)."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not connected'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Check if sensor exists
        cursor.execute("SELECT sensor_name FROM custom_sensors WHERE id = %s", (sensor_id,))
        existing = cursor.fetchone()
        if not existing:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Sensor not found'}), 404
        
        # Soft delete (set is_active=false)
        cursor.execute("""
            UPDATE custom_sensors 
            SET is_active = FALSE 
            WHERE id = %s
            RETURNING sensor_name
        """, (sensor_id,))
        
        sensor_name = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Sensor "{sensor_name}" has been deactivated'
        })
    except Exception as e:
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()
        return jsonify({'error': str(e)}), 500


def check_custom_sensors_table():
    """Startup check: Verify custom_sensors table exists"""
    conn = get_db_connection()
    if not conn:
        print("WARNING: Cannot verify custom_sensors table - database not connected")
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'custom_sensors'
            )
        """)
        table_exists = cursor.fetchone()[0]
        db_name = conn.get_dsn_parameters().get('dbname')
        db_host = conn.get_dsn_parameters().get('host')
        
        cursor.close()
        conn.close()
        
        if not table_exists:
            print("=" * 80)
            print("ERROR: custom_sensors table does not exist!")
            print("=" * 80)
            print(f"Database: {db_name} on {db_host}")
            print("")
            print("The migration add_custom_sensors.sql has not been applied.")
            print("")
            print("To apply the migration, run one of these commands:")
            print("")
            print("  Option 1 (PowerShell, from stub directory):")
            print("    cd stub")
            print("    Get-Content migrations/add_custom_sensors.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb")
            print("")
            print("  Option 2 (PowerShell, from workspace root):")
            print("    Get-Content stub/migrations/add_custom_sensors.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb")
            print("")
            print("  Option 3 (psql directly, if installed):")
            print("    psql -h localhost -U sensoruser -d sensordb -f stub/migrations/add_custom_sensors.sql")
            print("")
            print("The Admin UI custom sensor features will not work until this migration is applied.")
            print("=" * 80)
            return False
        else:
            print(f"Verified: custom_sensors table exists in database '{db_name}'")
            return True
    except Exception as e:
        print(f"WARNING: Error checking custom_sensors table: {e}")
        conn.close()
        return False


# ============================================================================
# API V1 - External Data Ingestion Endpoint
# ============================================================================

# API Key for external ingestion (can be set via environment variable)
INGEST_API_KEY = os.environ.get('INGEST_API_KEY', 'rig-alpha-secret')

@app.route('/api/v1/ingest', methods=['POST'])
@log_action('INGEST', resource_type='ingest', resource_id=None)
def api_v1_ingest():
    """
    External API endpoint for ingesting sensor data.
    Requires X-API-KEY header for authentication.
    Accepts JSON payload with machine_id and sensor readings.
    """
    # Check API key
    api_key = request.headers.get('X-API-KEY', '')
    if api_key != INGEST_API_KEY:
        return jsonify({'error': 'Invalid or missing API key'}), 401
    
    # Parse JSON body
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        machine_id = data.get('machine_id', 'A')
        if not machine_id:
            return jsonify({'error': 'machine_id is required'}), 400
        
        # Build sensor reading with timestamp
        reading = {
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'),
            'machine_id': machine_id
        }
        
        # Add all sensor values from request (excluding machine_id)
        for key, value in data.items():
            if key != 'machine_id':
                reading[key] = value
        
        # Send to Kafka
        try:
            import config
            producer = KafkaProducer(**config.KAFKA_PRODUCER_CONFIG)
            
            # Serialize to JSON string (matching producer format)
            # The producer config already has value_serializer that encodes to bytes
            message = json.dumps(reading)
            
            # Send to Kafka topic (value_serializer will handle encoding)
            future = producer.send(config.KAFKA_TOPIC, value=message)
            
            # Wait for acknowledgment (with timeout)
            record_metadata = future.get(timeout=10)
            
            producer.close()
            
            return jsonify({
                'success': True,
                'message': 'Data ingested successfully',
                'topic': record_metadata.topic,
                'partition': record_metadata.partition,
                'offset': record_metadata.offset,
                'machine_id': machine_id,
                'timestamp': reading['timestamp']
            }), 200
            
        except KafkaError as e:
            return jsonify({
                'error': 'Failed to send data to Kafka',
                'details': str(e)
            }), 500
        except Exception as e:
            return jsonify({
                'error': 'Failed to process ingestion request',
                'details': str(e)
            }), 500
            
    except Exception as e:
        return jsonify({'error': 'Invalid request format', 'details': str(e)}), 400


# ============================================================================
# Predictive Health API - RUL (Remaining Useful Life) Prediction
# ============================================================================

@app.route('/api/v1/predictive-health', methods=['GET'])
@require_auth
def api_predictive_health():
    """
    Get Remaining Useful Life (RUL) predictions for all machines.
    Returns estimated hours until failure based on degradation trends.
    """
    try:
        from analytics.prediction_engine import get_predictor
        
        predictor = get_predictor()
        conn = get_db_connection()
        
        if not conn:
            return jsonify({'error': 'Database not connected'}), 500
        
        results = {}
        
        # Get predictions for each machine
        for machine_id in ['A', 'B', 'C']:
            try:
                cursor = conn.cursor()
                
                # Get last 100 readings for this machine (for trend analysis)
                cursor.execute("""
                    SELECT 
                        timestamp,
                        vibration, temperature, bearing_temp, rpm
                    FROM sensor_readings
                    WHERE machine_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, (machine_id,))
                
                rows = cursor.fetchall()
                cursor.close()
                
                if rows:
                    # Convert to list of dicts
                    sensor_sequence = []
                    for row in reversed(rows):  # Oldest first
                        sensor_sequence.append({
                            'timestamp': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                            'vibration': row[1],
                            'temperature': row[2],
                            'bearing_temp': row[3],
                            'rpm': row[4]
                        })
                    
                    # Get prediction
                    prediction = predictor.predict_rul(sensor_sequence, machine_id)
                    results[machine_id] = prediction
                else:
                    results[machine_id] = {
                        'rul_hours': None,
                        'confidence': 0.0,
                        'degradation_trend': 'no_data',
                        'critical_sensors': [],
                        'estimated_failure_time': None,
                        'machine_id': machine_id,
                        'message': 'No sensor data available'
                    }
                    
            except Exception as e:
                logging.error(f"Error predicting RUL for machine {machine_id}: {e}")
                results[machine_id] = {
                    'rul_hours': None,
                    'confidence': 0.0,
                    'degradation_trend': 'error',
                    'critical_sensors': [],
                    'estimated_failure_time': None,
                    'machine_id': machine_id,
                    'error': str(e)
                }
        
        return_db_connection(conn)
        return jsonify(results), 200
        
    except ImportError:
        return jsonify({'error': 'Prediction engine not available'}), 500
    except Exception as e:
        logging.error(f"Error in predictive health endpoint: {e}")
        try:
            if conn:
                return_db_connection(conn)
        except:
            pass
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Database Info Endpoint (for debugging)
# ============================================================================

@app.route('/api/debug/db-info', methods=['GET'])
@require_auth
def api_db_info():
    """Get database connection information and PostgreSQL version."""
    import config
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database not connected'}), 500
        
        cursor = conn.cursor()
        
        # Get PostgreSQL version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        # Get database info
        cursor.execute("SELECT current_database(), current_user, inet_server_addr(), inet_server_port();")
        db_info = cursor.fetchone()
        
        # Check if it's remote
        is_remote = config.DB_HOST not in ['localhost', '127.0.0.1']
        
        result = {
            'version': version,
            'database': db_info[0],
            'user': db_info[1],
            'server_address': db_info[2] or config.DB_HOST,
            'server_port': db_info[3] or config.DB_PORT,
            'is_remote': is_remote,
            'config': {
                'host': config.DB_HOST,
                'port': config.DB_PORT,
                'database': config.DB_NAME,
                'user': config.DB_USER,
                'has_database_url': bool(os.environ.get('DATABASE_URL', ''))
            }
        }
        
        cursor.close()
        conn.close()
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/emergency-stop', methods=['POST'])
@require_admin
@log_action('EMERGENCY_STOP', resource_type='system', resource_id=None)
def api_emergency_stop():
    """Emergency stop - freeze all systems."""
    try:
        # Stop producer and consumer
        stop_component('producer')
        stop_component('consumer')
        
        # Log the emergency stop
        logging.critical("EMERGENCY STOP ACTIVATED by user")
        
        return jsonify({
            'success': True,
            'message': 'All systems frozen. Producer and Consumer stopped.'
        }), 200
    except Exception as e:
        logging.error(f"Error during emergency stop: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/users', methods=['GET'])
@require_admin
@log_action('READ', resource_type='user', resource_id=None)
def api_list_users():
    """List all users (admin only)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, role, accessible_machines, created_at
            FROM users
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        cursor.close()
        
        users = []
        for row in rows:
            users.append({
                'id': row[0],
                'username': row[1],
                'role': row[2],
                'accessible_machines': row[3] if row[3] else [],
                'created_at': row[4].isoformat() if row[4] else None
            })
        
        return_db_connection(conn)
        return jsonify({'users': users}), 200
    except Exception as e:
        return_db_connection(conn)
        logging.error(f"Error listing users: {e}")
        return jsonify({'error': str(e)}), 500


# Bootstrap admin user on module load
bootstrap_admin_user()

if __name__ == '__main__':
    # Run startup check
    check_custom_sensors_table()
    app.run(debug=True, host='0.0.0.0', port=5000)
