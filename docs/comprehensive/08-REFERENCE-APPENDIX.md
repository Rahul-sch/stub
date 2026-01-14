# REFERENCE & APPENDIX
## Complete Quick Reference Guide

**Document 08 of 09**  
**Reading Time:** As needed (reference material)  
**Level:** All levels  
**Use Case:** Quick lookups, API reference, database schema  

---

## 📋 TABLE OF CONTENTS

1. [Complete Glossary (A-Z)](#1-complete-glossary-a-z)
2. [API Reference](#2-api-reference)
3. [Database Schema](#3-database-schema)
4. [Configuration Reference](#4-configuration-reference)
5. [Environment Variables](#5-environment-variables)
6. [Keyboard Shortcuts](#6-keyboard-shortcuts)
7. [Port Reference](#7-port-reference)
8. [Error Codes](#8-error-codes)

---

## 1. COMPLETE GLOSSARY (A-Z)

### A

**ACESFilmicToneMapping**: Tone mapping algorithm from film industry for realistic HDR rendering

**Acknowledgment (ack)**: Confirmation that message received. Kafka `acks='all'` = wait for all replicas

**Ambient Temperature**: Air temperature surrounding equipment (vs machinery temperature)

**Anomaly**: Data point or pattern deviating from expected behavior

**Anomaly Detection**: Process of identifying unusual patterns in data

**Anomaly Score**: Numerical measure of how anomalous a reading is (lower/negative = more anomalous)

**Apache Kafka**: Open-source distributed event streaming platform for real-time data pipelines

**API (Application Programming Interface)**: Set of protocols for software communication

**API Key**: Secret token for authenticating API requests

**Atmospheric Pressure**: Force per unit area exerted by weight of atmosphere (~14.7 PSI at sea level)

**Audit Log**: Chronological record of system activities for compliance and investigation

**Authentication**: Verifying user identity (username/password)

**Authorization**: Verifying user permissions (what they can access)

**Autoencoder**: Neural network learning compressed representation of data

**Auto-commit**: Kafka feature automatically committing offsets (disabled in Rig Alpha for exactly-once)

---

### B

**Backoff (Exponential)**: Retry strategy with exponentially increasing delays (1s, 2s, 4s, 8s...)

**Baseline**: Normal/expected value for a parameter used as comparison reference

**Batch Size**: Number of samples processed together in ML training (32 in Rig Alpha)

**Bearing**: Machine component constraining motion and reducing friction

**Bloom Effect**: Graphics technique making bright areas glow/bleed

**Bootstrap Servers**: Initial Kafka servers client connects to for cluster discovery

**Bottleneck**: System component limiting overall throughput

**Broker (Kafka)**: Server storing and serving messages in Kafka cluster

**Buffer**: Temporary storage area for data in transit

---

### C

**Canvas (React Three Fiber)**: Component creating WebGL rendering context

**Cascading Failure**: When one component failure causes subsequent failures

**Cavitation**: Formation of vapor bubbles in liquid causing damage to pumps

**CBM (Condition-Based Monitoring)**: Monitoring actual equipment condition vs fixed schedule

**Clamp**: Limit value to min/max range

**Commit (Kafka)**: Mark message as successfully processed

**Compression**: Reducing data size for storage/transmission

**Connection Pool**: Cache of reusable database connections

**Contamination (ML)**: Expected proportion of outliers in Isolation Forest (0.05 = 5%)

**Context Window**: Range of readings before/after event for analysis

**Correlation**: Statistical measure of relationship between variables (-1 to +1)

**CSP (Content Security Policy)**: HTTP headers preventing XSS attacks

**Consumer (Kafka)**: Application reading messages from topics

**Consumer Group**: Multiple consumers sharing workload

---

### D

**Dashboard**: Visual interface displaying key metrics and controls

**Database**: Organized collection of structured data

**Decibel (dB)**: Logarithmic unit for sound level

**Degradation**: Gradual deterioration of performance over time

**Deserialization**: Converting bytes back to structured data

**Dew Point**: Temperature at which water vapor condenses

**Digital Twin**: Virtual representation of physical asset

**Docker**: Platform for running applications in containers

**Docker Compose**: Tool for defining multi-container applications

**Downtime**: Period when equipment is not operational

---

### E

**Early Stopping**: Training technique stopping when validation loss stops improving

**Embedding**: Compressed representation in neural networks

**Emissive**: Self-illuminating material property in 3D graphics

**Encoder**: Part of autoencoder compressing input

**Encoding Dimension**: Size of compressed representation (32 in Rig Alpha LSTM)

**Endpoint**: URL where API function is accessed

**Epoch**: Complete pass through training dataset

**Event**: Occurrence triggering action (e.g., 'rig_telemetry' WebSocket event)

**Exactly-Once Semantics**: Guarantee each message processed exactly once

**Exponential Backoff**: See Backoff

---

### F

**Failure Mode**: Specific way something can fail

**False Positive**: Normal reading incorrectly flagged as anomaly

**Feature**: Individual measurable property (each sensor = feature)

**Field of View (FOV)**: Camera's visible angle (65° in Rig Alpha)

**Flask**: Lightweight Python web framework

**Flow Rate**: Volume of fluid per time unit (L/min)

**Flush**: Force send buffered messages immediately

**FPS (Frames Per Second)**: Rendering rate (60 FPS = smooth)

**Future (Kafka)**: Promise object representing eventual result

---

### G

**GPU (Graphics Processing Unit)**: Specialized processor for graphics and parallel computation

**Graceful Shutdown**: Clean process termination preserving data integrity

**Groq**: AI infrastructure company providing fast LLM inference

**Ground Fault**: Unintended electrical path to ground

---

### H

**Hash**: Fixed-size output from cryptographic function

**Heartbeat**: Periodic signal indicating system alive

**High Availability**: System remaining operational despite component failures

**Horizontal Scaling**: Adding more machines vs upgrading existing

**HTTP**: Hypertext Transfer Protocol for web communication

**HTTPS**: Secure version of HTTP with encryption

**HUD (Heads-Up Display)**: Overlay UI showing key information

**Hybrid Detection**: Combining multiple detection methods (IF + LSTM)

**Hyperparameter**: ML model configuration (not learned from data)

---

### I

**Idempotent**: Operation that can be applied multiple times without changing result

**Imbalance (Mechanical)**: Uneven mass distribution in rotating part

**Inference**: Using trained ML model to make predictions

**Ingestion**: Importing data into system

**Injection (Anomaly)**: Deliberately creating abnormal readings for testing

**Isolation Forest**: ML algorithm detecting outliers by isolating points

**IoT (Internet of Things)**: Network of physical devices with sensors/connectivity

---

### J

**JSON (JavaScript Object Notation)**: Lightweight data interchange format

**JSONB**: PostgreSQL binary JSON format (faster than text JSON)

**JWT (JSON Web Token)**: Compact token for secure information transmission

---

### K

**Kafka**: See Apache Kafka

**Kafka Topic**: Category/feed where messages published

**KPI (Key Performance Indicator)**: Measurable value indicating success

---

### L

**Latency**: Delay between action and effect

**LLaMA (Large Language Model Meta AI)**: Open-source LLM by Meta

**LLM (Large Language Model)**: AI model trained on massive text for language understanding/generation

**Load Balancing**: Distributing work across multiple resources

**Logging**: Recording system events for debugging/auditing

**LSTM (Long Short-Term Memory)**: Neural network architecture for sequence learning

**Lubrication**: Reducing friction with lubricant (oil/grease)

---

### M

**Machine Learning (ML)**: Algorithms learning patterns from data

**Materialized View**: Cached query result updated periodically

**Mean**: Average value

**Mean Squared Error (MSE)**: Average squared difference (loss function)

**Mesh (3D)**: Geometry + material forming 3D object

**Message Broker**: Software routing messages between applications (Kafka)

**Metadata**: Data about data (e.g., timestamp, source)

**Middleware**: Software layer between components

**Migration**: Database schema change script

**Misalignment**: Shafts not properly aligned

**MPS (Messages Per Second)**: Throughput rate

**MTBF (Mean Time Between Failures)**: Average time between failures

---

### N

**Neon.tech**: Serverless PostgreSQL platform

**Neural Network**: ML model with interconnected layers of neurons

**NLP (Natural Language Processing)**: AI understanding/generating human language

**Noise (Data)**: Random variation in measurements

**Noise Level**: Sound intensity (decibels)

**Normalization**: Scaling values to common range (0-1 or standard score)

---

### O

**Offset (Kafka)**: Unique sequential ID for message position in partition

**Outlier**: Data point significantly different from others

**Overfitting**: ML model too specific to training data

---

### P

**Partition (Kafka)**: Topic subdivision for parallelization

**Password Hash**: One-way encrypted password (bcrypt in Rig Alpha)

**PBR (Physically Based Rendering)**: Realistic material/lighting simulation

**Percentile**: Value below which percentage of data falls (95th = top 5%)

**PdM (Predictive Maintenance)**: Predicting when equipment will fail

**Pointer Lock**: Browser API capturing mouse for first-person controls

**Poll (Kafka)**: Request for new messages

**PostgreSQL**: Open-source relational database

**Power Factor**: Ratio of real to apparent power (0.7-1.0)

**Predictive Analytics**: Using data to predict future outcomes

**Producer (Kafka)**: Application publishing messages to topics

**Prometheus**: Monitoring system and time-series database

**Prompt**: Text input to LLM for generation

**PSI (Pounds per Square Inch)**: Pressure unit

---

### R

**RBAC (Role-Based Access Control)**: Access based on user roles

**React**: JavaScript library for building UIs

**React Three Fiber (R3F)**: React renderer for Three.js

**Real-time**: Processing with minimal delay (< 1 second)

**Reconstruction Error**: Difference between autoencoder input/output

**Redis**: In-memory data structure store

**Regression (Linear)**: Statistical method modeling relationships

**Remaining Useful Life (RUL)**: Estimated time until failure

**Render (Deployment)**: Cloud platform for web services

**Replica**: Data copy on multiple servers

**Retry**: Repeated attempt after failure

**Reynolds Number**: Dimensionless fluid flow characterization

**RMS (Root Mean Square)**: Type of average for oscillating values

**Rollback**: Undo database transaction

**RPM (Revolutions Per Minute)**: Rotational speed

---

### S

**SASL**: Simple Authentication and Security Layer

**Scaler (StandardScaler)**: Normalizes features to mean=0, std=1

**Schema**: Database structure definition

**Sensor**: Device detecting/measuring physical properties

**Sequence**: Ordered list of data points

**Serialization**: Converting data to bytes for transmission

**Session**: Temporary user interaction state

**Severity**: Criticality level (Critical/High/Medium/Low)

**Shadow Map**: Texture storing depth for shadow rendering

**Signal Handler**: Function responding to OS signals (SIGINT, SIGTERM)

**Socket.IO**: Library for real-time bidirectional communication

**SQL (Structured Query Language)**: Language for database queries

**SSL/TLS**: Security protocols for encrypted communication

**Standard Deviation**: Measure of data dispersion

**State**: Data that can change over time

**Synchronous**: Operation blocking until complete

---

### T

**Telemetry**: Automated data collection/transmission

**TensorFlow**: Open-source ML framework

**Thermal Efficiency**: Ratio of useful to total heat

**Thermocouple**: Temperature sensor using voltage from joined metals

**Threshold**: Value triggering action when exceeded

**Throughput**: Amount of work per time unit

**Time Series**: Data indexed in time order

**Tone Mapping**: Converting HDR to displayable range

**Topic (Kafka)**: Message category/feed

**Torque**: Rotational force (Nm)

**Transient State**: Temporary state not triggering re-renders

**TTF (Time To Failure)**: Estimated time until equipment fails

**Turbulence**: Chaotic fluid flow

---

### U

**Upstash**: Serverless data platform (Kafka/Redis)

**Uptime**: Percentage of time operational

**URI/URL**: Address of web resource

**UTC (Coordinated Universal Time)**: International time standard

**UUID**: Universally Unique Identifier

---

### V

**Validation**: Checking data correctness

**Vibration**: Oscillating machinery motion (mm/s)

**Virtual Environment (venv)**: Isolated Python environment

**Viscosity**: Fluid's resistance to flow (cP)

**Vite**: Modern JavaScript build tool

---

### W

**WebGL**: JavaScript API for 3D graphics in browsers

**WebSocket**: Protocol for full-duplex communication

**Werkzeug**: Python WSGI utility library (used by Flask)

---

### X

**XSS (Cross-Site Scripting)**: Security vulnerability injecting malicious scripts

---

### Z

**Z-Score**: Number of standard deviations from mean

**Zookeeper**: Kafka coordination service

**Zustand**: Lightweight React state management

---

## 2. API REFERENCE

### 2.1 Authentication Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/login` | POST | No | Authenticate user |
| `/api/auth/logout` | POST | Yes | Destroy session |
| `/api/auth/me` | GET | Yes | Get current user |
| `/api/auth/signup` | POST | No | Create new user |

**POST /api/auth/login**
```json
Request:
{
  "username": "admin",
  "password": "admin"
}

Response (200):
{
  "success": true,
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "machines": ["A", "B", "C"]
  }
}

Response (401):
{
  "success": false,
  "error": "Invalid credentials"
}
```

### 2.2 Statistics Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/stats` | GET | Yes | Overall system stats |
| `/api/machines/<id>/stats` | GET | Yes | Machine-specific stats |
| `/api/anomalies` | GET | Yes | Recent anomalies |

**GET /api/stats**
```json
Response (200):
{
  "success": true,
  "stats": {
    "total_readings": 12534,
    "anomalies_24h": 15,
    "avg_temperature": 75.3,
    "messages_per_second": 1.2
  }
}
```

**GET /api/machines/A/stats**
```json
Response (200):
{
  "success": true,
  "machine_id": "A",
  "latest": {
    "temperature": 75.5,
    "pressure": 120.3,
    "rpm": 3500,
    "vibration": 2.5,
    "timestamp": "2026-01-12T15:30:00Z"
  },
  "anomalies_1h": 3
}
```

### 2.3 Admin Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/admin/custom-sensors` | GET | Admin | List custom sensors |
| `/api/admin/custom-sensors` | POST | Admin | Create custom sensor |
| `/api/admin/custom-sensors/<id>` | PUT | Admin | Update custom sensor |
| `/api/admin/custom-sensors/<id>` | DELETE | Admin | Delete custom sensor |
| `/api/admin/parse-sensor-file` | POST | Admin | AI parse sensor file |

**POST /api/admin/custom-sensors**
```json
Request:
{
  "sensor_name": "oil_quality",
  "category": "mechanical",
  "unit": "%",
  "min_range": 0,
  "max_range": 100,
  "low_threshold": 60,
  "high_threshold": 95
}

Response (200):
{
  "success": true,
  "id": 1
}
```

### 2.4 External API

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/ingest` | POST | API Key | External sensor data ingestion |

**POST /api/v1/ingest**
```bash
curl -X POST http://localhost:5000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: rig-alpha-secret" \
  -d '{
    "machine_id": "A",
    "temperature": 75.5,
    "pressure": 120.3,
    "vibration": 2.5,
    "rpm": 3500
  }'
```

Response:
```json
{
  "success": true,
  "message": "Data ingested successfully"
}
```

---

## 3. DATABASE SCHEMA

### 3.1 Core Tables

**sensor_readings**
```sql
CREATE TABLE sensor_readings (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    machine_id VARCHAR(16) DEFAULT 'A',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Environmental (10)
    temperature DOUBLE PRECISION NOT NULL,
    pressure DOUBLE PRECISION NOT NULL,
    humidity DOUBLE PRECISION NOT NULL,
    ambient_temp DOUBLE PRECISION,
    dew_point DOUBLE PRECISION,
    air_quality_index INTEGER,
    co2_level INTEGER,
    particle_count INTEGER,
    noise_level INTEGER,
    light_intensity INTEGER,
    
    -- Mechanical (10)
    vibration DOUBLE PRECISION NOT NULL,
    rpm DOUBLE PRECISION NOT NULL,
    torque INTEGER,
    shaft_alignment DOUBLE PRECISION,
    bearing_temp INTEGER,
    motor_current INTEGER,
    belt_tension INTEGER,
    gear_wear INTEGER,
    coupling_temp INTEGER,
    lubrication_pressure INTEGER,
    
    -- Thermal (10)
    coolant_temp INTEGER,
    exhaust_temp INTEGER,
    oil_temp INTEGER,
    radiator_temp INTEGER,
    thermal_efficiency INTEGER,
    heat_dissipation INTEGER,
    inlet_temp INTEGER,
    outlet_temp INTEGER,
    core_temp INTEGER,
    surface_temp INTEGER,
    
    -- Electrical (10)
    voltage INTEGER,
    current INTEGER,
    power_factor DOUBLE PRECISION,
    frequency DOUBLE PRECISION,
    resistance DOUBLE PRECISION,
    capacitance INTEGER,
    inductance DOUBLE PRECISION,
    phase_angle INTEGER,
    harmonic_distortion INTEGER,
    ground_fault INTEGER,
    
    -- Fluid (10)
    flow_rate INTEGER,
    fluid_pressure INTEGER,
    viscosity INTEGER,
    density DOUBLE PRECISION,
    reynolds_number INTEGER,
    pipe_pressure_drop INTEGER,
    pump_efficiency INTEGER,
    cavitation_index INTEGER,
    turbulence INTEGER,
    valve_position INTEGER,
    
    -- Custom sensors (flexible)
    custom_sensors JSONB DEFAULT '{}'::JSONB
);

CREATE INDEX idx_readings_created ON sensor_readings(created_at DESC);
CREATE INDEX idx_readings_machine ON sensor_readings(machine_id, created_at DESC);
```

**anomaly_detections**
```sql
CREATE TABLE anomaly_detections (
    id BIGSERIAL PRIMARY KEY,
    reading_id BIGINT REFERENCES sensor_readings(id),
    detection_method VARCHAR(32) NOT NULL,  -- 'isolation_forest', 'lstm_autoencoder', 'hybrid'
    anomaly_score DOUBLE PRECISION,
    is_anomaly BOOLEAN DEFAULT FALSE,
    detected_sensors TEXT[],  -- Array of sensor names
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_detections_reading ON anomaly_detections(reading_id);
CREATE INDEX idx_detections_created ON anomaly_detections(created_at DESC);
CREATE INDEX idx_detections_anomaly ON anomaly_detections(is_anomaly, created_at DESC);
```

**users**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(16) DEFAULT 'operator',  -- 'admin' or 'operator'
    machines_access TEXT[],  -- Array of machine IDs
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

CREATE INDEX idx_users_username ON users(username);
```

**custom_sensors**
```sql
CREATE TABLE custom_sensors (
    id SERIAL PRIMARY KEY,
    sensor_name VARCHAR(64) UNIQUE NOT NULL,
    category VARCHAR(32),
    unit VARCHAR(16),
    min_range DOUBLE PRECISION NOT NULL,
    max_range DOUBLE PRECISION NOT NULL,
    low_threshold DOUBLE PRECISION,
    high_threshold DOUBLE PRECISION,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**alerts**
```sql
CREATE TABLE alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_type VARCHAR(64) NOT NULL,
    source VARCHAR(32) DEFAULT 'system',
    severity VARCHAR(16) DEFAULT 'INFO',  -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'
    message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_created ON alerts(created_at DESC);
CREATE INDEX idx_alerts_severity ON alerts(severity, created_at DESC);
```

**audit_logs_v2**
```sql
CREATE TABLE audit_logs_v2 (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    username VARCHAR(64) NOT NULL,
    role VARCHAR(16),
    ip_address INET,
    user_agent TEXT,
    action_type VARCHAR(32) NOT NULL,  -- 'CREATE', 'READ', 'UPDATE', 'DELETE', 'INGEST'
    resource_type VARCHAR(64),  -- 'custom_sensor', 'sensor_file', 'machine'
    resource_id VARCHAR(128),
    previous_state JSONB,
    new_state JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    retention_until TIMESTAMPTZ,
    hash_chain VARCHAR(64)
);

CREATE INDEX idx_audit_timestamp ON audit_logs_v2(timestamp DESC);
CREATE INDEX idx_audit_user ON audit_logs_v2(user_id, timestamp DESC);
CREATE INDEX idx_audit_action ON audit_logs_v2(action_type, timestamp DESC);
```

**ai_reports**
```sql
CREATE TABLE ai_reports (
    id BIGSERIAL PRIMARY KEY,
    anomaly_id INTEGER REFERENCES anomaly_detections(id),
    report_type VARCHAR(32),
    analysis_text TEXT,
    severity VARCHAR(16),
    recommendations TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. CONFIGURATION REFERENCE

### 4.1 config.py Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DURATION_HOURS` | 999 | How long producer runs |
| `INTERVAL_SECONDS` | 1 | Time between readings |
| `KAFKA_BOOTSTRAP_SERVERS` | localhost:9092 | Kafka broker address |
| `KAFKA_TOPIC` | sensor-data | Main topic name |
| `DB_HOST` | localhost | Database hostname |
| `DB_PORT` | 5432 | PostgreSQL port |
| `DB_NAME` | sensordb | Database name |
| `DB_USER` | sensoruser | Database user |
| `ML_DETECTION_ENABLED` | True | Enable ML detection |
| `ISOLATION_FOREST_CONTAMINATION` | 0.05 | Expected anomaly rate |
| `ISOLATION_FOREST_N_ESTIMATORS` | 100 | Number of trees |
| `MIN_TRAINING_SAMPLES` | 100 | Min data for training |
| `LSTM_ENABLED` | True | Enable LSTM |
| `LSTM_SEQUENCE_LENGTH` | 20 | Readings in sequence |
| `LSTM_ENCODING_DIM` | 32 | Bottleneck size |
| `LSTM_THRESHOLD_PERCENTILE` | 95 | Anomaly threshold |
| `HYBRID_DETECTION_STRATEGY` | hybrid_smart | Detection strategy |
| `GROQ_API_KEY` | (from env) | Groq API key |
| `AI_MODEL` | llama-3.3-70b-versatile | LLM model |

### 4.2 Sensor Ranges Summary

| Sensor | Min | Max | Unit | Low Threshold | High Threshold |
|--------|-----|-----|------|---------------|----------------|
| temperature | 60 | 100 | °F | 65 | 85 |
| pressure | 0 | 15 | PSI | 2 | 12 |
| humidity | 20 | 80 | % | 30 | 65 |
| vibration | 0 | 10 | mm/s | 0 | 4.5 |
| rpm | 1000 | 5000 | RPM | 1200 | 4200 |
| bearing_temp | 70 | 180 | °F | 80 | 160 |
| voltage | 110 | 130 | V | 114 | 126 |
| flow_rate | 0 | 500 | L/min | 50 | 400 |

*(See Document 03 for all 50 sensors)*

---

## 5. ENVIRONMENT VARIABLES

### 5.1 Required Variables

**None!** System works with defaults.

### 5.2 Optional Variables (.env file)

**AI Configuration:**
```bash
GROQ_API_KEY=gsk_xxxxxxxxxxxxx
# Get free key at: https://console.groq.com/keys
```

**Security:**
```bash
SECRET_KEY=change-me-in-production-random-string-here
API_SECRET_KEY=rig-alpha-secret
```

**Cloud Database (Neon.tech):**
```bash
DATABASE_URL=postgresql://user:pass@ep-xxx.aws.neon.tech/neondb?sslmode=require
```

**Cloud Kafka (Upstash):**
```bash
KAFKA_BROKER_URL=xxx.upstash.io:9092
KAFKA_SASL_USERNAME=your-username
KAFKA_SASL_PASSWORD=your-password
```

**ML Configuration:**
```bash
LSTM_ENABLED=true
LSTM_SEQUENCE_LENGTH=20
LSTM_ENCODING_DIM=32
LSTM_THRESHOLD_PERCENTILE=95
HYBRID_DETECTION_STRATEGY=hybrid_smart
```

**Example .env file:**
```bash
# AI
GROQ_API_KEY=gsk_abc123def456

# Security
SECRET_KEY=super-secret-key-12345
API_SECRET_KEY=rig-alpha-secret

# Cloud Database
DATABASE_URL=postgresql://user:pass@ep-xxx.aws.neon.tech/neondb

# Cloud Kafka
KAFKA_BROKER_URL=xxx.upstash.io:9092
KAFKA_SASL_USERNAME=username
KAFKA_SASL_PASSWORD=password
```

---

## 6. KEYBOARD SHORTCUTS

### 6.1 3D Digital Twin Controls

| Key | Action |
|-----|--------|
| **W** | Move forward |
| **S** | Move backward |
| **A** | Strafe left |
| **D** | Strafe right |
| **Mouse** | Look around |
| **ESC** | Exit pointer lock |
| **Click** | Enter pointer lock |

### 6.2 Dashboard Shortcuts

| Key | Action |
|-----|--------|
| **Ctrl+R** | Refresh data |
| **Ctrl+K** | Open search |
| **ESC** | Close modal |

---

## 7. PORT REFERENCE

| Port | Service | URL |
|------|---------|-----|
| **5000** | Flask Dashboard | http://localhost:5000 |
| **3000** | 3D Digital Twin | http://localhost:3000 |
| **9092** | Kafka Broker | localhost:9092 |
| **5432** | PostgreSQL | localhost:5432 |
| **2181** | Zookeeper | localhost:2181 |

**Port Conflicts:**

If port already in use:

**Change Flask port:**
```python
# In dashboard.py, change last line:
socketio.run(app, host='0.0.0.0', port=5001)  # Use 5001 instead
```

**Change Vite port:**
```javascript
// In vite.config.js:
export default {
  server: {
    port: 3001  // Use 3001 instead
  }
}
```

---

## 8. ERROR CODES

### 8.1 HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| **200** | OK | Successful request |
| **201** | Created | Resource created |
| **400** | Bad Request | Invalid input |
| **401** | Unauthorized | Not logged in |
| **403** | Forbidden | No permission |
| **404** | Not Found | Endpoint/resource doesn't exist |
| **500** | Server Error | Backend exception |

### 8.2 Common Errors

**"Kafka connection failed"**
- **Cause**: Broker not started or wrong address
- **Solution**: Check `docker ps`, wait 60 seconds after `docker-compose up`

**"Database connection failed"**
- **Cause**: PostgreSQL not running or wrong credentials
- **Solution**: Check Docker container, verify DB_CONFIG in config.py

**"Model not trained"**
- **Cause**: ML models don't exist
- **Solution**: Run `python train_combined_detector.py`

**"Session expired"**
- **Cause**: Session timeout (24 hours)
- **Solution**: Login again

**"Access denied"**
- **Cause**: Insufficient permissions
- **Solution**: Login as admin or request machine access

---

## 🎓 FINAL SUMMARY

You now have complete documentation for Rig Alpha:

✅ **Document 00**: Overview and navigation  
✅ **Document 01**: Core concepts (Kafka, LSTM, ML, AI)  
✅ **Document 02**: System architecture  
✅ **Document 03**: All 50 sensors explained  
✅ **Document 04**: Backend code line-by-line  
✅ **Document 05**: Dashboard code walkthrough  
✅ **Document 06**: 3D frontend code walkthrough  
✅ **Document 07**: Practical how-to guides  
✅ **Document 08**: This reference guide  

**Total Documentation:**
- 9 comprehensive documents
- ~50,000+ words
- 100+ pages equivalent
- Complete system coverage

---

## 📞 QUICK REFERENCE CARDS

### Starting System (Quick Reference)
```bash
# 1. Start infrastructure
docker-compose up -d && sleep 60

# 2. Start services (4 terminals)
python dashboard.py     # Terminal 1
python producer.py      # Terminal 2
python consumer.py      # Terminal 3
cd frontend-3d && npm run dev  # Terminal 4

# 3. Open browsers
# Dashboard: http://localhost:5000
# 3D Twin: http://localhost:3000
```

### Stopping System
```bash
# Stop Python processes: Ctrl+C in each terminal

# Stop Docker:
docker-compose down

# Stop and delete data:
docker-compose down -v
```

### Emergency Reset
```bash
# Nuclear option - reset everything
docker-compose down -v
rm -rf models/*.pkl models/*.keras
rm -f .env
docker-compose up -d
sleep 60
# Re-run migrations
# Re-train models
```

---

**🎉 CONGRATULATIONS!**

You now have **complete understanding** of the Rig Alpha Industrial IoT Sensor Monitoring Platform from first principles to advanced implementation details.

**What you can do now:**
- ✅ Understand every technology used
- ✅ Explain how the system works
- ✅ Install and run the system
- ✅ Modify and extend the code
- ✅ Deploy to production
- ✅ Troubleshoot any issue

**Thank you for reading!**

---

*End of Documentation Series*  
*Version 1.0 - January 2026*
