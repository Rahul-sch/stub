# DASHBOARD CODE WALKTHROUGH
## Flask Web Application and API Endpoints

**Document 05 of 09**  
**Reading Time:** 60-90 minutes  
**Level:** Advanced  
**Prerequisites:** Documents 01-04  

---

## 📋 TABLE OF CONTENTS

1. [Flask Application Setup](#1-flask-application-setup)
2. [Authentication System](#2-authentication-system)
3. [Database Connection Pooling](#3-database-connection-pooling)
4. [API Endpoints](#4-api-endpoints)
5. [WebSocket Telemetry](#5-websocket-telemetry)
6. [Machine State Management](#6-machine-state-management)
7. [Custom Sensor Management](#7-custom-sensor-management)
8. [Audit Logging](#8-audit-logging)

---

## 1. FLASK APPLICATION SETUP

### 1.1 Imports and Initialization

**Lines 1-86 (dashboard.py):**
```python
from flask import Flask, render_template, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit
import psycopg2
from psycopg2 import pool

app = Flask(__name__)

# SocketIO for real-time 3D updates
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    logger=False,
    engineio_logger=False
)
```

**Purpose:**
- Flask: Web framework
- SocketIO: WebSocket support for 3D twin
- psycopg2: PostgreSQL database driver
- Connection pool: Reusable database connections

### 1.2 Security Configuration

**Lines 198-224:**
```python
# Content Security Policy
if TALISMAN_AVAILABLE:
    csp = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com",
        'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com",
        'connect-src': "'self' https://*.neon.tech",
    }
    
    Talisman(app, content_security_policy=csp, force_https=False)

# Session configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-me-in-production')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
```

**Security Features:**
- **CSP Headers**: Prevent XSS attacks
- **HTTPOnly Cookies**: Prevent JavaScript access
- **SameSite**: CSRF protection
- **Session Lifetime**: Auto-logout after 24 hours

---

## 2. AUTHENTICATION SYSTEM

### 2.1 Login Endpoint

**Lines (API endpoint example):**
```python
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password_hash, role, machines_access FROM users WHERE username = %s",
            (username,)
        )
        user = cursor.fetchone()
        
        if user and check_password_hash(user[2], password):
            # Create session
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            session['machines'] = user[4] or []
            
            # Update last_login
            cursor.execute(
                "UPDATE users SET last_login = NOW() WHERE id = %s",
                (user[0],)
            )
            conn.commit()
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user[0],
                    'username': user[1],
                    'role': user[3],
                    'machines': user[4] or []
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            
    finally:
        return_db_connection(conn)
```

**How It Works:**
1. **Receive credentials** (username/password)
2. **Query database** for user
3. **Verify password** using werkzeug hash check
4. **Create session** if valid
5. **Update last_login** timestamp
6. **Return user info**

**Password Security:**
- Passwords stored as bcrypt hashes
- Never stored in plaintext
- `check_password_hash()` compares safely

### 2.2 Authorization Decorator

```python
def requires_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def requires_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        if session.get('role') != 'admin':
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Usage
@app.route('/api/stats')
@requires_auth  # Must be logged in
def get_stats():
    # ...

@app.route('/api/admin/custom-sensors')
@requires_admin  # Must be admin
def manage_sensors():
    # ...
```

---

## 3. DATABASE CONNECTION POOLING

### 3.1 Pool Initialization

**Lines 169-193:**
```python
db_pool = None

def init_db_pool():
    """Initialize database connection pool."""
    global db_pool
    try:
        import config
        db_pool = pool.ThreadedConnectionPool(
            minconn=5,   # Keep 5 connections warm
            maxconn=50,  # Max 50 concurrent connections
            **config.DB_CONFIG
        )
        logger.info("Database connection pool initialized (minconn=5, maxconn=50)")
    except Exception as e:
        logger.error(f"Failed to initialize pool: {e}")
        db_pool = None

# Initialize on module load
init_db_pool()
```

**Benefits:**
- **50% faster** API responses
- **No connection exhaustion**
- **Thread-safe** for Flask

### 3.2 Connection Usage Pattern

```python
def get_db_connection():
    """Get connection from pool."""
    global db_pool
    if db_pool:
        try:
            conn = db_pool.getconn()
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection: {e}")
            return None
    else:
        # Fallback to direct connection
        try:
            import config
            conn = psycopg2.connect(**config.DB_CONFIG)
            return conn
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            return None

def return_db_connection(conn):
    """Return connection to pool."""
    global db_pool
    if db_pool and conn:
        try:
            db_pool.putconn(conn)  # NOT conn.close()!
        except Exception as e:
            logger.error(f"Failed to return connection: {e}")
            try:
                conn.close()
            except:
                pass

# Usage pattern
conn = get_db_connection()
try:
    cursor = conn.cursor()
    cursor.execute("SELECT ...")
    results = cursor.fetchall()
    cursor.close()
    return results
finally:
    return_db_connection(conn)  # ALWAYS return to pool
```

---

## 4. API ENDPOINTS

### 4.1 Statistics Endpoint

**Purpose:** Return overall system statistics

```python
@app.route('/api/stats')
@requires_auth
def get_stats():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Total readings
        cursor.execute("SELECT COUNT(*) FROM sensor_readings")
        total_readings = cursor.fetchone()[0]
        
        # Recent anomalies
        cursor.execute("""
            SELECT COUNT(*) FROM anomaly_detections
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)
        anomalies_24h = cursor.fetchone()[0]
        
        # Average temperature (last hour)
        cursor.execute("""
            SELECT AVG(temperature) FROM sensor_readings
            WHERE created_at > NOW() - INTERVAL '1 hour'
        """)
        avg_temp = cursor.fetchone()[0] or 0
        
        cursor.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_readings': total_readings,
                'anomalies_24h': anomalies_24h,
                'avg_temperature': round(avg_temp, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        return_db_connection(conn)
```

### 4.2 Machine Stats Endpoint

**Purpose:** Get statistics for specific machine

```python
@app.route('/api/machines/<machine_id>/stats')
@requires_auth
def get_machine_stats(machine_id):
    # Check access
    if session.get('role') != 'admin':
        if machine_id not in session.get('machines', []):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Latest reading for this machine
        cursor.execute("""
            SELECT temperature, pressure, humidity, vibration, rpm, bearing_temp,
                   created_at
            FROM sensor_readings
            WHERE machine_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (machine_id,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'No data for machine'}), 404
        
        latest = {
            'temperature': row[0],
            'pressure': row[1],
            'humidity': row[2],
            'vibration': row[3],
            'rpm': row[4],
            'bearing_temp': row[5],
            'timestamp': row[6].isoformat()
        }
        
        # Recent anomalies
        cursor.execute("""
            SELECT COUNT(*) FROM anomaly_detections ad
            JOIN sensor_readings sr ON ad.reading_id = sr.id
            WHERE sr.machine_id = %s
            AND ad.created_at > NOW() - INTERVAL '1 hour'
        """, (machine_id,))
        
        anomalies_1h = cursor.fetchone()[0]
        
        cursor.close()
        
        return jsonify({
            'success': True,
            'machine_id': machine_id,
            'latest': latest,
            'anomalies_1h': anomalies_1h
        })
        
    except Exception as e:
        logger.error(f"Machine stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        return_db_connection(conn)
```

### 4.3 Anomaly List Endpoint

```python
@app.route('/api/anomalies')
@requires_auth
def get_anomalies():
    limit = request.args.get('limit', 50, type=int)
    machine_id = request.args.get('machine', None)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        query = """
            SELECT ad.id, ad.reading_id, ad.detection_method, ad.anomaly_score,
                   ad.is_anomaly, ad.detected_sensors, ad.created_at,
                   sr.machine_id, sr.temperature, sr.vibration, sr.bearing_temp
            FROM anomaly_detections ad
            JOIN sensor_readings sr ON ad.reading_id = sr.id
            WHERE ad.is_anomaly = TRUE
        """
        
        params = []
        if machine_id:
            query += " AND sr.machine_id = %s"
            params.append(machine_id)
        
        query += " ORDER BY ad.created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        
        anomalies = []
        for row in rows:
            anomalies.append({
                'id': row[0],
                'reading_id': row[1],
                'method': row[2],
                'score': float(row[3]),
                'sensors': row[5] or [],
                'timestamp': row[6].isoformat(),
                'machine_id': row[7],
                'temperature': row[8],
                'vibration': row[9],
                'bearing_temp': row[10]
            })
        
        cursor.close()
        
        return jsonify({
            'success': True,
            'anomalies': anomalies
        })
        
    except Exception as e:
        logger.error(f"Anomalies error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        return_db_connection(conn)
```

---

## 5. WEBSOCKET TELEMETRY

### 5.1 Telemetry Cache Structure

**Lines 286-294:**
```python
telemetry_cache = {
    'A': {'rpm': 0, 'temperature': 70, 'vibration': 0, 'anomaly_score': 0},
    'B': {'rpm': 0, 'temperature': 70, 'vibration': 0, 'anomaly_score': 0},
    'C': {'rpm': 0, 'temperature': 70, 'vibration': 0, 'anomaly_score': 0}
}
telemetry_lock = threading.Lock()
```

**Purpose:**
- In-memory cache of latest sensor values
- Updated by consumer via internal API
- Broadcast to 3D frontend via WebSocket

### 5.2 Background Broadcast Worker

**Lines 309-332:**
```python
def telemetry_broadcast_worker():
    """Broadcast telemetry at 10 Hz."""
    if not SOCKETIO_AVAILABLE or not socketio:
        return

    while True:
        try:
            with telemetry_lock:
                for machine_id, data in telemetry_cache.items():
                    socketio.emit('rig_telemetry', {
                        'machine_id': machine_id,
                        'rpm': data.get('rpm', 0),
                        'temperature': data.get('temperature', 70),
                        'vibration': data.get('vibration', 0),
                        'pressure': data.get('pressure', 100),
                        'bearing_temp': data.get('bearing_temp', 120),
                        'anomaly_score': data.get('anomaly_score', 0),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
            time.sleep(0.1)  # 10 Hz = 100ms interval
        except Exception as e:
            logging.error(f"Telemetry broadcast error: {e}")
            time.sleep(1)
```

**How It Works:**
1. **Infinite loop** in background thread
2. **Lock cache** (thread-safe read)
3. **Emit via SocketIO** for each machine
4. **Sleep 100ms** (10 Hz update rate)
5. **Repeat forever**

### 5.3 Internal Telemetry Update Endpoint

```python
@app.route('/api/internal/telemetry-update', methods=['POST'])
def update_telemetry():
    """Consumer calls this to update telemetry cache."""
    try:
        data = request.get_json()
        machine_id = data.get('machine_id', 'A')
        
        with telemetry_lock:
            telemetry_cache[machine_id] = {
                'rpm': data.get('rpm', 0),
                'temperature': data.get('temperature', 70),
                'vibration': data.get('vibration', 0),
                'pressure': data.get('pressure', 100),
                'bearing_temp': data.get('bearing_temp', 120),
                'anomaly_score': data.get('anomaly_score', 0)
            }
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Telemetry update error: {e}")
        return jsonify({'success': False}), 500
```

**Data Flow:**
```
Consumer detects anomaly
    ↓
POST /api/internal/telemetry-update
    ↓
Update telemetry_cache (thread-safe)
    ↓
Background thread reads cache
    ↓
SocketIO emits 'rig_telemetry'
    ↓
3D Frontend receives update
    ↓
3D scene animates
```

---

## 6. MACHINE STATE MANAGEMENT

### 6.1 In-Memory State

**Lines 241-254:**
```python
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
machine_state_lock = threading.Lock()
```

### 6.2 Start Machine Endpoint

```python
@app.route('/api/machines/<machine_id>/start', methods=['POST'])
@requires_auth
def start_machine(machine_id):
    # Check authorization
    if session.get('role') != 'admin':
        if machine_id not in session.get('machines', []):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    with machine_state_lock:
        if machine_state[machine_id]['running']:
            return jsonify({'success': False, 'error': 'Already running'}), 400
        
        # Update state
        machine_state[machine_id]['running'] = True
    
    # Record audit
    record_audit_log(
        user_id=session['user_id'],
        action='START_MACHINE',
        resource_type='machine',
        resource_id=machine_id
    )
    
    return jsonify({
        'success': True,
        'machine_id': machine_id,
        'status': 'running'
    })
```

---

## 7. CUSTOM SENSOR MANAGEMENT

### 7.1 List Custom Sensors

```python
@app.route('/api/admin/custom-sensors', methods=['GET'])
@requires_admin
def get_custom_sensors():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sensor_name, category, unit, min_range, max_range,
                   low_threshold, high_threshold, is_active, created_at
            FROM custom_sensors
            ORDER BY sensor_name
        """)
        rows = cursor.fetchall()
        
        sensors = []
        for row in rows:
            sensors.append({
                'id': row[0],
                'name': row[1],
                'category': row[2],
                'unit': row[3],
                'min_range': float(row[4]),
                'max_range': float(row[5]),
                'low_threshold': float(row[6]) if row[6] else None,
                'high_threshold': float(row[7]) if row[7] else None,
                'is_active': row[8],
                'created_at': row[9].isoformat()
            })
        
        cursor.close()
        return jsonify({'success': True, 'sensors': sensors})
        
    except Exception as e:
        logger.error(f"Get sensors error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        return_db_connection(conn)
```

### 7.2 Create Custom Sensor

```python
@app.route('/api/admin/custom-sensors', methods=['POST'])
@requires_admin
def create_custom_sensor():
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO custom_sensors 
            (sensor_name, category, unit, min_range, max_range, 
             low_threshold, high_threshold, is_active, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data['sensor_name'],
            data.get('category', 'custom'),
            data.get('unit', ''),
            float(data['min_range']),
            float(data['max_range']),
            float(data['low_threshold']) if data.get('low_threshold') else None,
            float(data['high_threshold']) if data.get('high_threshold') else None,
            data.get('is_active', True),
            session['user_id']
        ))
        
        sensor_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        
        # Record audit
        record_audit_log(
            user_id=session['user_id'],
            action='CREATE',
            resource_type='custom_sensor',
            resource_id=str(sensor_id),
            new_state=data
        )
        
        return jsonify({'success': True, 'id': sensor_id})
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Create sensor error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        return_db_connection(conn)
```

### 7.3 AI Sensor File Parsing

```python
@app.route('/api/admin/parse-sensor-file', methods=['POST'])
@requires_admin
def parse_sensor_file():
    """Parse sensor specs from uploaded file using AI."""
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    # Extract text from file
    if file.filename.endswith('.pdf'):
        text = extract_pdf_text(file)
    elif file.filename.endswith('.csv'):
        text = file.read().decode('utf-8')
    else:
        text = file.read().decode('utf-8')
    
    # Call Groq API to parse
    try:
        from groq import Groq
        client = Groq(api_key=config.GROQ_API_KEY)
        
        prompt = f"""
        Extract sensor specifications from this text and format as JSON:
        
        {text[:2000]}  # First 2000 chars
        
        Format:
        {{
            "sensor_name": "...",
            "category": "environmental|mechanical|thermal|electrical|fluid",
            "unit": "...",
            "min_range": float,
            "max_range": float,
            "low_threshold": float,
            "high_threshold": float
        }}
        """
        
        response = client.chat.completions.create(
            model='llama3-8b-8192',  # Fast model for parsing
            messages=[
                {'role': 'system', 'content': 'You are a sensor specification parser.'},
                {'role': 'user', 'content': prompt}
            ]
        )
        
        # Parse response
        specs = json.loads(response.choices[0].message.content)
        
        return jsonify({'success': True, 'specs': specs})
        
    except Exception as e:
        logger.error(f"AI parsing error: {e}")
        # Fallback to mock data
        return jsonify({
            'success': True,
            'specs': {
                'sensor_name': 'custom_sensor_1',
                'category': 'custom',
                'unit': '',
                'min_range': 0,
                'max_range': 100
            }
        })
```

---

## 8. AUDIT LOGGING

### 8.1 Audit Log Function

```python
def record_audit_log(user_id, action, resource_type, resource_id=None,
                     previous_state=None, new_state=None):
    """Record action in audit log."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get user details
        cursor.execute("SELECT username, role FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        username = user[0] if user else 'unknown'
        role = user[1] if user else 'unknown'
        
        # Get request info
        ip_address = request.remote_addr if request else None
        user_agent = request.headers.get('User-Agent') if request else None
        
        # Calculate retention (7 years for compliance)
        retention_until = datetime.now() + timedelta(days=7*365)
        
        cursor.execute("""
            INSERT INTO audit_logs_v2 
            (user_id, username, role, ip_address, user_agent, action_type,
             resource_type, resource_id, previous_state, new_state, retention_until)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            username,
            role,
            ip_address,
            user_agent,
            action,
            resource_type,
            resource_id,
            json.dumps(previous_state) if previous_state else None,
            json.dumps(new_state) if new_state else None,
            retention_until
        ))
        
        conn.commit()
        cursor.close()
        
    except Exception as e:
        logger.error(f"Audit log error: {e}")
    finally:
        return_db_connection(conn)
```

### 8.2 Audit Log Queries

```python
@app.route('/api/audit-logs')
@requires_admin
def get_audit_logs():
    limit = request.args.get('limit', 100, type=int)
    user_id = request.args.get('user_id', None, type=int)
    action = request.args.get('action', None)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        query = """
            SELECT id, user_id, username, role, ip_address, action_type,
                   resource_type, resource_id, timestamp
            FROM audit_logs_v2
            WHERE 1=1
        """
        params = []
        
        if user_id:
            query += " AND user_id = %s"
            params.append(user_id)
        
        if action:
            query += " AND action_type = %s"
            params.append(action)
        
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        
        logs = []
        for row in rows:
            logs.append({
                'id': row[0],
                'user_id': row[1],
                'username': row[2],
                'role': row[3],
                'ip_address': row[4],
                'action': row[5],
                'resource_type': row[6],
                'resource_id': row[7],
                'timestamp': row[8].isoformat()
            })
        
        cursor.close()
        return jsonify({'success': True, 'logs': logs})
        
    except Exception as e:
        logger.error(f"Audit logs error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        return_db_connection(conn)
```

---

## 🎓 SUMMARY

You now understand the Flask dashboard:

✅ **Flask Setup**: App initialization and security  
✅ **Authentication**: Login, sessions, authorization  
✅ **Connection Pool**: Efficient database access  
✅ **API Endpoints**: Stats, anomalies, machines  
✅ **WebSocket**: Real-time telemetry broadcast  
✅ **Machine State**: Process management  
✅ **Custom Sensors**: CRUD operations  
✅ **Audit Logging**: Compliance tracking  

**Next Document:** [06-CODE-3D-FRONTEND.md](06-CODE-3D-FRONTEND.md)
- React Three Fiber components
- WebSocket integration
- 3D animation logic

---

*Continue to Document 06: 3D Frontend Code Walkthrough →*
