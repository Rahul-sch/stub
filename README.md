# Industrial Sensor Anomaly Detection Pipeline (Rig Alpha)

A comprehensive real-time industrial IoT monitoring system with ML anomaly detection, AI-powered analysis, predictive maintenance, and enterprise-grade audit logging.

---

## 🎯 Project Overview

**Rig Alpha** is an end-to-end industrial sensor monitoring platform that:

- **Ingests** real-time sensor data from 50+ parameters across 5 categories
- **Streams** data reliably through Apache Kafka with exactly-once semantics
- **Detects** anomalies using hybrid ML (Isolation Forest + LSTM Autoencoder)
- **Predicts** future failures with Remaining Useful Life (RUL) estimation
- **Analyzes** root causes using AI-powered natural language processing
- **Monitors** everything through a modern, real-time web dashboard
- **Audits** all actions with comprehensive logging for compliance

---

## 🏗️ System Architecture

```mermaid
flowchart TB
    subgraph Edge["🔧 Edge Layer"]
        Producer[Producer<br/>50+ Sensors]
        API[External API<br/>/api/v1/ingest]
    end

    subgraph Stream["📨 Streaming Layer"]
        Kafka[(Apache Kafka<br/>Message Broker)]
    end

    subgraph Process["⚙️ Processing Layer"]
        Consumer[Consumer]
        IF[Isolation Forest<br/>Point Detection]
        LSTM[LSTM Autoencoder<br/>Temporal Patterns]
        RUL[Prediction Engine<br/>RUL Estimation]
    end

    subgraph Store["💾 Storage Layer"]
        DB[(PostgreSQL<br/>Neon.tech Cloud)]
        Audit[(Audit Logs<br/>audit_logs_v2)]
    end

    subgraph Analyze["🤖 AI Layer"]
        Groq[Groq AI<br/>LLaMA 3.3]
        Parser[AI Sensor Parser<br/>PDF/CSV/JSON]
    end

    subgraph View["📊 Presentation Layer"]
        Dashboard[Web Dashboard<br/>Flask + Real-time UI]
    end

    Producer -->|publish| Kafka
    API -->|publish| Kafka
    Kafka -->|consume| Consumer
    Consumer -->|detect| IF
    Consumer -->|detect| LSTM
    Consumer -->|predict| RUL
    Consumer -->|INSERT| DB
    IF -->|anomalies| DB
    LSTM -->|predictions| DB
    RUL -->|estimates| DB
    DB -->|context| Groq
    Groq -->|reports| DB
    DB -->|stats| Dashboard
    Dashboard -->|control| Producer
    Dashboard -->|control| Consumer
    Dashboard -->|audit| Audit
    Parser -->|sensor specs| DB
```

---

## ✨ Key Features

### Core Capabilities

| Feature                          | Description                                                       |
| -------------------------------- | ----------------------------------------------------------------- |
| **50+ Sensor Parameters**        | Environmental, Mechanical, Thermal, Electrical, Fluid Dynamics    |
| **Multi-Machine Support**        | Monitor Machine A, B, C with per-machine configuration            |
| **Real-time Streaming**          | Apache Kafka for reliable, fault-tolerant message delivery        |
| **Hybrid ML Detection**          | Isolation Forest (point-based) + LSTM Autoencoder (temporal)      |
| **Future Anomaly Prediction**    | LSTM predicts anomalies before they occur                         |
| **Remaining Useful Life (RUL)**  | Estimates hours until failure based on sensor trends              |
| **AI-Powered Analysis**          | Groq/LLaMA generates root cause analysis and recommendations      |
| **AI Sensor Parser**             | Automatically extracts sensor specs from PDF/CSV/JSON files       |
| **Custom Sensors**               | Add new sensor parameters at runtime via Admin UI                 |
| **Dynamic Thresholds**           | Configure min/max thresholds per sensor                           |
| **Per-Sensor Frequency Control** | Adjust sampling rate per sensor (global + per-machine)            |
| **User Authentication**          | Login/signup with role-based access control (admin/operator)      |
| **Machine Access Control**       | Operators can only access assigned machines                       |
| **Comprehensive Audit Logging**  | All actions logged to `audit_logs_v2` for compliance              |
| **Cloud-Ready**                  | Supports Neon.tech (PostgreSQL) and Upstash (Kafka)               |
| **Modern Dashboard**             | Real-time updates, charts, controls, "Rig Alpha" industrial theme |

### Advanced Features

- **Predictive Maintenance**: RUL predictions show estimated hours until failure
- **Anomaly Injection**: Simulate faults for testing and training
- **State Capture**: Audit logs capture before/after states for UPDATE operations
- **External API**: `/api/v1/ingest` endpoint for external sensor data ingestion
- **Boot Animation**: Cinematic startup sequence
- **Responsive UI**: 2-panel layout optimized for industrial monitoring

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (for Kafka and PostgreSQL)
- Python 3.13+
- PowerShell (Windows) or Bash (Linux/Mac)

### Step 1: Start Infrastructure

```powershell
cd c:\Users\rahul\Desktop\stubby\stub
docker-compose up -d
Start-Sleep -Seconds 60  # Wait for Kafka to start
```

### Step 2: Apply Database Migrations

```powershell
# User authentication
Get-Content migrations\add_user_auth.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb

# Custom sensors
Get-Content migrations\add_custom_sensors.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb

# Frequency control
Get-Content migrations\add_frequency_control.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb

# Audit logging (v2)
Get-Content migrations\add_audit_v2.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb
```

### Step 3: Install Dependencies

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 4: Train ML Models (First Time)

```powershell
python train_combined_detector.py
```

**Requirements:**

- **Isolation Forest**: Minimum 100 readings (recommended: 500+)
- **LSTM Autoencoder**: Minimum 100 readings (recommended: 500+ for best results)

### Step 5: Start Dashboard

```powershell
python dashboard.py
```

### Step 6: Open Browser

Go to: **http://localhost:5000**

**Default Admin Credentials:**

- Username: `admin`
- Password: `admin`

**Or create a new account:**

1. Click "Sign Up" on the login page
2. Enter username and password
3. Check "Create as Admin" for admin access
4. Click "Sign Up"

---

## 📊 Dashboard Overview

### Layout

**Left Panel (320px fixed width):**

- **Health Matrix**: 6 category cards (Environmental, Electrical, Fluid, Mechanical, Thermal, Custom)
  - Health percentage, status indicator (NOM/WRN/CRIT)
  - Anomaly log (last 3 anomalies per category)
  - Uptime timer (pauses when stopped)
  - RUL countdown (estimated life remaining)
- **System Command Deck**: Control panel with START/STOP, Sampling Speed slider, Anomaly Simulation

**Right Panel (Flexible width):**

- **Telemetry Grid**: Responsive grid of sensor cards
  - Real-time values (CURR) and averages (AVG)
  - Dynamic threshold coloring (Green/Yellow/Red)
  - Sparkline graphs with color-coded lines
  - Sensor metadata and status indicators

**Header:**

- Logo & branding
- Machine selector (A, B, C)
- Status dots (SYSTEM, COMM, POWER, SAFETY)
- Pipeline health (TOTAL messages, MPS counter)
- Alerts badge
- UTC time
- Logout button

### Key Controls

| Control              | Function                                    |
| -------------------- | ------------------------------------------- |
| **START**            | Starts producer and consumer                |
| **STOP**             | Pauses system (Yellow state, uptime pauses) |
| **Sampling Speed**   | Adjust MPS (Messages Per Second) from 1-20  |
| **Anomaly Trigger**  | Inject simulated faults for testing         |
| **Machine Selector** | Switch between Machine A, B, or C           |

---

## 🔐 Authentication & Authorization

### User Roles

| Role         | Access Level                                             |
| ------------ | -------------------------------------------------------- |
| **Admin**    | Full access to all machines (A, B, C) and admin features |
| **Operator** | Access only to assigned machines                         |

### Admin Features

- Create/edit/delete custom sensors
- AI-powered sensor file parsing (PDF/CSV/JSON)
- User management (create users, assign machines)
- View audit logs
- Configure global sensor frequencies
- Access all machines

### API Endpoints

| Endpoint                       | Method   | Auth    | Description                     |
| ------------------------------ | -------- | ------- | ------------------------------- |
| `/api/auth/login`              | POST     | No      | Authenticate and create session |
| `/api/auth/logout`             | POST     | Yes     | Destroy session                 |
| `/api/auth/me`                 | GET      | Yes     | Get current user info           |
| `/api/auth/signup`             | POST     | No      | Create new user account         |
| `/api/v1/ingest`               | POST     | API Key | External sensor data ingestion  |
| `/api/admin/custom-sensors`    | GET/POST | Admin   | Manage custom sensors           |
| `/api/admin/parse-sensor-file` | POST     | Admin   | AI-powered sensor spec parsing  |
| `/api/v1/predictive-health`    | GET      | Yes     | Get RUL predictions             |

---

## 🤖 AI Integration

### Groq AI Configuration

**File:** `stub/config.py`

```python
AI_PROVIDER = "groq"
AI_MODEL_PARSING = "llama3-8b-8192"  # Fast, spec extraction
AI_MODEL_REPORTS = "llama-3.3-70b-versatile"  # Deep analysis
```

**Environment Variable:**

```bash
GROQ_API_KEY=gsk_...
```

### AI Sensor Parser

**Endpoint:** `POST /api/admin/parse-sensor-file`

**Supported Formats:**

- PDF (PyPDF2 - extracts first 2 pages)
- CSV (direct text parsing)
- TXT (raw specification sheets)
- JSON (passthrough or AI enhancement)

**Features:**

- Automatically extracts sensor specifications
- Auto-fills "Add New Sensor" form
- Handles missing API key with fallback mock data

### AI Report Generation

- Root cause analysis of anomalies
- Prevention recommendations
- Sensor correlation insights
- Natural language explanations

---

## 📈 ML & Predictive Analytics

### Hybrid Detection System

**1. Isolation Forest (Point-Based)**

- Detects single abnormal readings
- Fast and effective for instant anomalies
- Identifies contributing sensors

**2. LSTM Autoencoder (Temporal)**

- Analyzes sequences of readings over time
- Detects gradual degradation and pattern changes
- Predicts future anomalies before they occur
- Identifies which sensors will cause problems and why

### Remaining Useful Life (RUL) Prediction

**Endpoint:** `GET /api/v1/predictive-health`

**Features:**

- Estimates hours until failure based on sensor trends
- Uses linear regression/exponential decay model
- Displays countdown in health cards (EST. LIFE)
- Color-coded by severity (Green/Yellow/Red)

**Display Format:**

- `< 24 hours`: Shows "X HRS" (Red)
- `< 1 week`: Shows "X DAYS" (Yellow)
- `>= 1 week`: Shows "X WEEKS" (Green)

### Training Models

```powershell
# Train both models
python train_combined_detector.py

# Train only one
python train_combined_detector.py --if-only    # Only Isolation Forest
python train_combined_detector.py --lstm-only  # Only LSTM

# Force retrain
python train_combined_detector.py --force
```

---

## 🔍 Audit Logging

### Comprehensive Action Tracking

All actions are logged to `audit_logs_v2` table:

| Action Type | Endpoints                               | Resource Type   |
| ----------- | --------------------------------------- | --------------- |
| `INGEST`    | `/api/v1/ingest`                        | `ingest`        |
| `CREATE`    | `POST /api/admin/custom-sensors`        | `custom_sensor` |
| `READ`      | `GET /api/admin/custom-sensors`         | `custom_sensor` |
| `UPDATE`    | `PUT /api/admin/custom-sensors/<id>`    | `custom_sensor` |
| `DELETE`    | `DELETE /api/admin/custom-sensors/<id>` | `custom_sensor` |
| `PARSE`     | `POST /api/admin/parse-sensor-file`     | `sensor_file`   |

### Audit Log Schema

```sql
CREATE TABLE audit_logs_v2 (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    username VARCHAR(64) NOT NULL,
    role VARCHAR(16),
    ip_address INET,
    user_agent TEXT,
    action_type VARCHAR(32) NOT NULL,
    resource_type VARCHAR(64),
    resource_id VARCHAR(128),
    previous_state JSONB,
    new_state JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    retention_until TIMESTAMPTZ,
    hash_chain VARCHAR(64)
);
```

### Default User Handling

When no session exists (e.g., API key auth), the system automatically uses `admin_rahul` (ID: 1) as the default operator.

**Query Audit Logs:**

```sql
SELECT id, user_id, username, action_type, resource_type, timestamp
FROM audit_logs_v2
ORDER BY timestamp DESC
LIMIT 10;
```

---

## ☁️ Cloud Deployment

### Database (Neon.tech)

**Configuration:**

1. Add `DATABASE_URL` to `.env`:
   ```bash
   DATABASE_URL=postgresql://user:password@ep-xxx.aws.neon.tech/neondb?sslmode=require
   ```
2. Restart Flask server
3. The app automatically detects and uses Neon database

**Verify Connection:**

```powershell
.\venv\Scripts\python.exe check_db_version.py
```

### Kafka (Upstash)

**Configuration:**

1. Add to `.env`:
   ```bash
   KAFKA_BROKER_URL=your-upstash-endpoint:9092
   KAFKA_SASL_USERNAME=your-username
   KAFKA_SASL_PASSWORD=your-password
   ```
2. Restart Flask server
3. The app automatically uses SASL_SSL authentication

### Deployment Files

- **`requirements.txt`**: All Python dependencies
- **`Procfile`**: Gunicorn + Eventlet for production
- **`docker-compose.yml`**: Local development setup

**Deploy to Render:**

1. Connect GitHub repository
2. Set environment variables (DATABASE_URL, KAFKA_BROKER_URL, etc.)
3. Deploy automatically on push

---

## 📁 Project Structure

```
stub/
├── dashboard.py              # Flask web application
├── producer.py               # Sensor data generator
├── consumer.py               # Kafka consumer + ML detection
├── config.py                 # Configuration (Kafka, DB, AI)
├── ml_detector.py           # Isolation Forest detector
├── lstm_detector.py         # LSTM Autoencoder
├── lstm_predictor.py        # Future anomaly prediction
├── analytics/
│   └── prediction_engine.py # RUL prediction engine
├── analysis_engine.py       # Context & correlation analysis
├── report_generator.py      # AI-powered report generation
├── train_combined_detector.py # ML model training
├── migrations/              # Database migrations
│   ├── add_user_auth.sql
│   ├── add_custom_sensors.sql
│   ├── add_frequency_control.sql
│   └── add_audit_v2.sql
├── templates/
│   ├── dashboard.html       # Main dashboard UI
│   └── login.html          # Authentication UI
├── static/
│   └── css/
│       └── style.css       # "Rig Alpha" industrial theme
├── requirements.txt         # Python dependencies
├── Procfile                # Production deployment
└── docker-compose.yml      # Local infrastructure
```

---

## 🔧 Configuration

### Environment Variables

**File:** `stub/.env`

```bash
# AI/LLM Configuration
GROQ_API_KEY=gsk_...

# Security
API_SECRET_KEY=rig-alpha-secret
SECRET_KEY=change-me-in-production

# Database (Cloud)
DATABASE_URL=postgresql://user:password@host:port/dbname?sslmode=require

# Kafka (Cloud)
KAFKA_BROKER_URL=your-endpoint:9092
KAFKA_SASL_USERNAME=your-username
KAFKA_SASL_PASSWORD=your-password

# External API
INGEST_API_KEY=rig-alpha-secret
```

### Database Configuration

The app uses `config.py` (NOT SQLAlchemy) to manage connections:

1. **First Priority:** `DATABASE_URL` environment variable
2. **Fallback:** Local defaults (`localhost:5432`)

**Check Current Config:**

```powershell
.\venv\Scripts\python.exe check_db_version.py
```

---

## 🧪 Testing

### Test Audit Logging

```powershell
.\venv\Scripts\python.exe test_audit_logging.py
```

### Test External API

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/v1/ingest" `
  -Method Post `
  -ContentType "application/json" `
  -Headers @{ "X-API-KEY" = "rig-alpha-secret" } `
  -Body '{"machine_id": "A", "temperature": 75.5, "pressure": 120.3}'
```

### Check Database

```powershell
docker exec stub-postgres psql -U sensoruser -d sensordb -c "SELECT COUNT(*) FROM sensor_readings;"
```

---

## 📚 Documentation

- **[AUDIT_LOGGING_UPDATE.md](AUDIT_LOGGING_UPDATE.md)** - Audit logging system details
- **[DATABASE_CONFIG.md](DATABASE_CONFIG.md)** - Database configuration guide
- **[docs/FINAL_PROJECT_REPORT.md](docs/FINAL_PROJECT_REPORT.md)** - Complete project report
- **[docs/ARCHITECTURE_AND_DEVELOPMENT_PLAN.md](docs/ARCHITECTURE_AND_DEVELOPMENT_PLAN.md)** - Architecture details
- **[docs/uml_diagrams.md](docs/uml_diagrams.md)** - UML diagrams
- **[PROJECT_MANIFEST.md](../PROJECT_MANIFEST.md)** - Technical DNA and roadmap

---

## 🐛 Troubleshooting

### Common Issues

**"Docker not recognized"**

- Open Docker Desktop first
- Wait for it to fully start

**"Kafka connection failed"**

- Wait 60 seconds after starting Docker
- Run: `Start-Sleep -Seconds 60`

**"Consumer not receiving"**

- Always start Consumer BEFORE Producer

**"Execution policy error"**

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**"PDF parsing not available"**

- Install PyPDF2: `pip install PyPDF2`
- Restart Flask server

**"Session expired"**

- Clear browser cookies
- Login again

---

## 🛑 Stop Everything

```powershell
docker-compose down
```

To delete all data too:

```powershell
docker-compose down -v
```

---

## 🚀 Production Deployment

### Virtual Environment in Production?

**No!** In production, use **Docker containers**:

| Development              | Production                 |
| ------------------------ | -------------------------- |
| Python venv on laptop    | Docker containers          |
| docker-compose on one PC | Kubernetes cluster         |
| Single Kafka broker      | Kafka cluster (3+ brokers) |
| Single database          | Database with replicas     |
| Dashboard on localhost   | Dashboard behind firewall  |

### Monitoring in Production

- **Health check endpoints** - Monitor Kafka, database, services
- **Alerting system** - PagerDuty, Slack, email notifications
- **Metrics dashboard** - Prometheus + Grafana
- **Log aggregation** - ELK stack (Elasticsearch, Logstash, Kibana)
- **Automated recovery** - Auto-restart failed services

---

## 📊 API Reference

### LSTM Endpoints

| Endpoint                      | Method | Description                                          |
| ----------------------------- | ------ | ---------------------------------------------------- |
| `/api/lstm-status`            | GET    | Returns training quality, threshold, sequence length |
| `/api/lstm-predictions`       | GET    | Returns current future anomaly prediction            |
| `/api/generate-future-report` | POST   | Generates and downloads PDF report                   |

### Machine Endpoints

| Endpoint                    | Method | Description                |
| --------------------------- | ------ | -------------------------- |
| `/api/machines/<id>/start`  | POST   | Start producer for machine |
| `/api/machines/<id>/stop`   | POST   | Stop producer for machine  |
| `/api/machines/<id>/status` | GET    | Get machine status         |
| `/api/machines/<id>/stats`  | GET    | Get machine statistics     |

### Stats Endpoints

| Endpoint      | Method   | Description              |
| ------------- | -------- | ------------------------ |
| `/api/stats`  | GET      | Get overall statistics   |
| `/api/config` | GET/POST | Get/update configuration |

---

## 🎓 Learning Resources

### Key Concepts

- **Kafka**: Message broker for reliable streaming
- **Isolation Forest**: Point-based anomaly detection
- **LSTM Autoencoder**: Temporal pattern detection
- **RUL Prediction**: Remaining Useful Life estimation
- **Exactly-Once Semantics**: Each message processed exactly once
- **Exponential Backoff**: Retry strategy for connection failures

### Interview Questions

See the [README Interview Questions section](#interview-questions--answers) for detailed explanations of:

- Why Kafka?
- Producer vs Consumer
- Isolation Forest vs LSTM
- Exactly-once semantics
- And more...

---

## 📝 License

This project is part of the **Industrial Sensor Anomaly Detection Pipeline** portfolio.

---

## 🤝 Contributing

This is a portfolio project demonstrating:

- Real-time data streaming
- ML anomaly detection
- AI-powered analysis
- Cloud deployment
- Enterprise audit logging
- Modern web development

---

**Status:** ✅ **PRODUCTION READY** - All features implemented and tested.

**Last Updated:** 2026-01-07
