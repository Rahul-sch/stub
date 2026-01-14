# Rig Alpha: Industrial Sensor Monitoring - Quick Overview

**Project Name:** Industrial Sensor Anomaly Detection Pipeline (Rig Alpha)  
**Version:** 2.0  
**Status:** Production Ready ✅

---

## 🎯 What Is This?

A **complete industrial IoT monitoring system** that:
1. **Collects** sensor data from 50+ parameters
2. **Streams** it through Kafka
3. **Detects** anomalies with ML (Isolation Forest + LSTM)
4. **Predicts** future failures (RUL estimation)
5. **Analyzes** root causes with AI (Groq/LLaMA)
6. **Displays** everything in a real-time dashboard
7. **Audits** all actions for compliance

---

## 🏗️ Architecture (5 Minutes)

```
Sensors → Kafka → Consumer → ML Detection → Database
                                    ↓
                              AI Analysis
                                    ↓
                              Dashboard ← User
```

**Key Components:**
- **Producer**: Generates 50+ sensor readings
- **Kafka**: Message broker (reliable streaming)
- **Consumer**: Processes data + runs ML detection
- **PostgreSQL**: Stores all readings + anomalies
- **ML Models**: Isolation Forest (instant) + LSTM (predictive)
- **AI Engine**: Groq/LLaMA for root cause analysis
- **Dashboard**: Flask web app with real-time UI

---

## 🚀 Quick Start (3 Steps)

### 1. Start Infrastructure
```powershell
cd stub
docker-compose up -d
Start-Sleep -Seconds 60
```

### 2. Train ML Models
```powershell
.\venv\Scripts\Activate.ps1
python train_combined_detector.py
```

### 3. Run Dashboard
```powershell
python dashboard.py
```

**Open:** http://localhost:5000  
**Login:** `admin` / `admin`

---

## ✨ Key Features

| Feature | What It Does |
|---------|--------------|
| **50+ Sensors** | Environmental, Mechanical, Thermal, Electrical, Fluid |
| **Multi-Machine** | Monitor Machine A, B, C separately |
| **Real-time** | Kafka streaming with exactly-once delivery |
| **ML Detection** | Isolation Forest (instant) + LSTM (predictive) |
| **RUL Prediction** | Estimates hours until failure |
| **AI Analysis** | Groq/LLaMA generates root cause reports |
| **AI Parser** | Extracts sensor specs from PDF/CSV/JSON |
| **Custom Sensors** | Add new parameters at runtime |
| **User Auth** | Admin/Operator roles with machine access control |
| **Audit Logging** | All actions logged to `audit_logs_v2` |
| **Cloud Ready** | Supports Neon.tech (DB) + Upstash (Kafka) |

---

## 📊 Dashboard Layout

**Left Panel:**
- **Health Matrix**: 6 category cards (ENVIRON, ELECTRIC, FLUID, MECH, THERMAL, CUSTOM)
  - Health percentage
  - Status LED (NOM/WRN/CRIT)
  - Anomaly log (last 3)
  - Uptime timer
  - RUL countdown
- **Command Deck**: START/STOP, Sampling Speed, Anomaly Injection

**Right Panel:**
- **Telemetry Grid**: Sensor cards with:
  - Real-time values (CURR) + averages (AVG)
  - Threshold coloring (Green/Yellow/Red)
  - Sparkline graphs
  - Status indicators

**Header:**
- Machine selector (A, B, C)
- Status dots (SYSTEM, COMM, POWER, SAFETY)
- Pipeline health (TOTAL messages, MPS)
- Alerts badge
- UTC time

---

## 🔐 Authentication

**Roles:**
- **Admin**: Full access to all machines + admin features
- **Operator**: Access only to assigned machines

**Default Admin:**
- Username: `admin`
- Password: `admin`

**Create Users:**
- Sign Up page (public)
- Admin panel (admin only)

---

## 🤖 AI Integration

**Groq AI:**
- **Model**: LLaMA 3.3 (70B for reports, 8B for parsing)
- **Features**:
  - Sensor spec parsing (PDF/CSV/JSON)
  - Root cause analysis
  - Prevention recommendations
  - Natural language explanations

**Configuration:**
```bash
GROQ_API_KEY=gsk_...
```

---

## 📈 ML & Prediction

**Hybrid Detection:**
1. **Isolation Forest**: Detects instant anomalies
2. **LSTM Autoencoder**: Predicts future anomalies

**RUL Prediction:**
- Estimates hours until failure
- Based on sensor trends (vibration, temperature, etc.)
- Displays in health cards as "EST. LIFE"
- Color-coded: Red (<24hrs), Yellow (<1 week), Green (>=1 week)

**Training:**
```powershell
python train_combined_detector.py
```
- **Isolation Forest**: 100+ readings
- **LSTM**: 500+ readings (recommended)

---

## 🔍 Audit Logging

**All Actions Logged:**
- `/api/v1/ingest` → `INGEST`
- `/api/admin/custom-sensors` → `CREATE/READ/UPDATE/DELETE`
- `/api/admin/parse-sensor-file` → `PARSE`

**Table:** `audit_logs_v2`
- User ID, username, role
- Action type, resource type, resource ID
- Before/after state (for UPDATE)
- IP address, user agent, timestamp

**Default User:**
- API key auth uses `admin_rahul` (ID: 1) as default operator

---

## ☁️ Cloud Deployment

**Database (Neon.tech):**
```bash
DATABASE_URL=postgresql://user:password@ep-xxx.aws.neon.tech/neondb?sslmode=require
```

**Kafka (Upstash):**
```bash
KAFKA_BROKER_URL=your-endpoint:9092
KAFKA_SASL_USERNAME=your-username
KAFKA_SASL_PASSWORD=your-password
```

**Deploy:**
- `requirements.txt`: Dependencies
- `Procfile`: Gunicorn + Eventlet
- Render.com compatible

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `dashboard.py` | Flask web app (3633 lines) |
| `producer.py` | Sensor data generator |
| `consumer.py` | Kafka consumer + ML |
| `config.py` | Configuration (Kafka, DB, AI) |
| `ml_detector.py` | Isolation Forest |
| `lstm_detector.py` | LSTM Autoencoder |
| `analytics/prediction_engine.py` | RUL prediction |
| `migrations/` | Database migrations |
| `templates/dashboard.html` | Main UI (8001 lines) |
| `static/css/style.css` | "Rig Alpha" theme (3672 lines) |

---

## 🧪 Testing

**Test Audit Logging:**
```powershell
.\venv\Scripts\python.exe test_audit_logging.py
```

**Test External API:**
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/v1/ingest" `
  -Method Post -ContentType "application/json" `
  -Headers @{ "X-API-KEY" = "rig-alpha-secret" } `
  -Body '{"machine_id": "A", "temperature": 75.5}'
```

**Check Database:**
```powershell
docker exec stub-postgres psql -U sensoruser -d sensordb -c "SELECT COUNT(*) FROM sensor_readings;"
```

---

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| Docker not recognized | Open Docker Desktop, wait for startup |
| Kafka connection failed | Wait 60 seconds after `docker-compose up` |
| Consumer not receiving | Start Consumer BEFORE Producer |
| PDF parsing error | Install PyPDF2: `pip install PyPDF2` |
| Session expired | Clear cookies, login again |

---

## 📚 Documentation

- **README.md**: Full documentation (3000+ lines)
- **AUDIT_LOGGING_UPDATE.md**: Audit system details
- **DATABASE_CONFIG.md**: Database setup guide
- **docs/FINAL_PROJECT_REPORT.md**: Complete project report
- **PROJECT_MANIFEST.md**: Technical DNA

---

## 🎓 Key Concepts

**Kafka**: Message broker for reliable streaming  
**Isolation Forest**: Point-based anomaly detection  
**LSTM**: Temporal pattern detection + prediction  
**RUL**: Remaining Useful Life estimation  
**Exactly-Once**: Each message processed exactly once  
**Exponential Backoff**: Retry strategy for failures

---

## 🚀 Production Notes

**Not for Production:**
- Python venv (use Docker containers)
- Single Kafka broker (use cluster)
- Single database (use replicas)

**Production Setup:**
- Docker containers + Kubernetes
- Kafka cluster (3+ brokers)
- Database with replicas
- Monitoring (Prometheus + Grafana)
- Alerting (PagerDuty/Slack)

---

## ✅ Status

**Completed:**
- ✅ Real-time sensor monitoring
- ✅ Hybrid ML anomaly detection
- ✅ Future anomaly prediction
- ✅ RUL estimation
- ✅ AI-powered analysis
- ✅ User authentication
- ✅ Audit logging
- ✅ Cloud deployment ready
- ✅ Modern dashboard UI

**Ready for:**
- Production deployment
- Portfolio demonstration
- Technical interviews
- Further development

---

**Last Updated:** 2026-01-07  
**Project:** Industrial Sensor Anomaly Detection Pipeline (Rig Alpha)

