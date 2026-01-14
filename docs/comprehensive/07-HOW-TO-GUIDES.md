# HOW-TO GUIDES
## Practical Step-by-Step Tutorials

**Document 07 of 09**  
**Reading Time:** 45-60 minutes  
**Level:** Beginner to Intermediate  
**Use Case:** Getting started, deployment, troubleshooting  

---

## 📋 TABLE OF CONTENTS

1. [Getting Started](#1-getting-started)
2. [Training ML Models](#2-training-ml-models)
3. [Adding Custom Sensors](#3-adding-custom-sensors)
4. [Deploying to Cloud](#4-deploying-to-cloud)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. GETTING STARTED

### 1.1 Prerequisites Installation

**What You Need:**
- Computer (Windows/Mac/Linux)
- 8 GB RAM minimum (16 GB recommended)
- 5 GB free disk space
- Internet connection

#### Step 1: Install Docker Desktop

**Why Docker?**
- Runs Kafka and PostgreSQL in containers
- No complex setup
- Same environment on all machines

**Download:**
- Windows/Mac: https://www.docker.com/products/docker-desktop
- Linux: `sudo apt-get install docker.io docker-compose`

**Verify Installation:**
```bash
docker --version
# Should show: Docker version 20.x.x or higher

docker-compose --version
# Should show: Docker Compose version v2.x.x or higher
```

**Troubleshooting:**
- Windows: Enable WSL2 (Windows Subsystem for Linux)
- Mac: Grant Docker disk access in Settings
- Linux: Add user to docker group: `sudo usermod -aG docker $USER`

#### Step 2: Install Python 3.13+

**Check if installed:**
```bash
python --version
# or
python3 --version
```

**Download if needed:**
- Windows: https://www.python.org/downloads/
- Mac: `brew install python@3.13`
- Linux: `sudo apt-get install python3.13`

**Verify pip:**
```bash
pip --version
# Should show: pip 23.x or higher
```

#### Step 3: Install Node.js (for 3D Twin)

**Check if installed:**
```bash
node --version
# Should show: v18.x or higher

npm --version
# Should show: 9.x or higher
```

**Download:**
- All platforms: https://nodejs.org/ (LTS version)

### 1.2 Complete Setup Process

#### Step 1: Start Infrastructure

**Navigate to project:**
```bash
cd /Users/arnavgolia/Desktop/Winter/stub
```

**Start Docker services:**
```bash
docker-compose up -d
```

**What this does:**
- Starts Zookeeper (Kafka coordinator)
- Starts Kafka broker
- Starts PostgreSQL database
- All run in background (`-d` = detached)

**Wait 60 seconds:**
```bash
# Mac/Linux
sleep 60

# Windows PowerShell
Start-Sleep -Seconds 60
```

**Why wait?**
- Kafka needs time to fully start
- Zookeeper must initialize first
- PostgreSQL must create databases
- 60 seconds ensures everything ready

**Verify services:**
```bash
docker ps
```

**Expected output:**
```
CONTAINER ID   IMAGE                            STATUS
abc123...      confluentinc/cp-kafka:latest    Up 1 minute
def456...      confluentinc/cp-zookeeper       Up 1 minute
ghi789...      postgres:15                      Up 1 minute
```

#### Step 2: Apply Database Migrations

**Why migrations?**
- Creates tables (sensor_readings, users, etc.)
- Adds columns for new features
- Ensures database structure correct

**Run migrations:**

**Mac/Linux:**
```bash
cat migrations/add_user_auth.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb
cat migrations/add_custom_sensors.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb
cat migrations/add_frequency_control.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb
cat migrations/add_audit_v2.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb
```

**Windows PowerShell:**
```powershell
Get-Content migrations\add_user_auth.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb
Get-Content migrations\add_custom_sensors.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb
Get-Content migrations\add_frequency_control.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb
Get-Content migrations\add_audit_v2.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb
```

**What each migration does:**
- `add_user_auth.sql`: Creates users table, authentication
- `add_custom_sensors.sql`: Custom sensor definitions
- `add_frequency_control.sql`: Per-sensor sampling rates
- `add_audit_v2.sql`: Audit logging for compliance

**Verify:**
```bash
docker exec stub-postgres psql -U sensoruser -d sensordb -c "\dt"
```

**Should see tables:**
- sensor_readings
- anomaly_detections
- users
- custom_sensors
- audit_logs_v2
- alerts

#### Step 3: Install Python Dependencies

**Create virtual environment:**
```bash
python -m venv venv
```

**Activate virtual environment:**

**Mac/Linux:**
```bash
source venv/bin/activate
```

**Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**If execution policy error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Install requirements:**
```bash
pip install -r requirements.txt
```

**What gets installed:**
- flask: Web framework
- kafka-python: Kafka client
- psycopg2-binary: PostgreSQL driver
- scikit-learn: Machine learning
- numpy, pandas: Data processing
- tensorflow: LSTM (optional)
- groq: AI API client
- flask-socketio: WebSocket support

**Time:** 2-5 minutes depending on connection

#### Step 4: Install 3D Frontend Dependencies

**Navigate to frontend:**
```bash
cd frontend-3d
```

**Install npm packages:**
```bash
npm install
```

**What gets installed:**
- react: UI framework
- three: 3D graphics library
- @react-three/fiber: React renderer for Three.js
- @react-three/drei: Helper components
- socket.io-client: WebSocket client
- zustand: State management
- vite: Build tool

**Time:** 1-3 minutes

**Return to root:**
```bash
cd ..
```

#### Step 5: Train ML Models (First Time)

**Why train first?**
- ML models need training data
- Can't detect anomalies without trained model
- Takes 5-10 minutes first time

**Run training:**
```bash
python train_combined_detector.py
```

**What happens:**
```
1. Starts producer (generates 500 normal readings)
2. Starts consumer (processes and stores in database)
3. Fetches data from database
4. Trains Isolation Forest
5. Trains LSTM Autoencoder
6. Saves models to disk
7. Done!
```

**Expected output:**
```
Generating 500 training samples...
[Producer] Message 1/500 sent...
[Consumer] Message 1/500 processed...
...
[Producer] Message 500/500 sent
[Consumer] Message 500/500 processed

Training Isolation Forest...
Trained on 500 samples
Saved model to models/isolation_forest.pkl

Training LSTM Autoencoder...
Epoch 1/50 - loss: 0.0234
Epoch 2/50 - loss: 0.0156
...
Epoch 20/50 - loss: 0.0012 (early stopping)
Trained LSTM on 480 sequences
Threshold: 0.0023
Saved model to models/lstm_autoencoder.keras

Training complete!
```

#### Step 6: Start All Services

**You need 4 terminals:**

**Terminal 1 - Flask Dashboard:**
```bash
python dashboard.py
```

**Expected output:**
```
[OK] PyPDF2 loaded
[OK] Database pool initialized (5-50 connections)
[OK] Groq API key loaded
 * Running on http://127.0.0.1:5000
```

**Keep running!** (Don't close)

**Terminal 2 - Producer:**
```bash
python producer.py
```

**Expected output:**
```
Producer initialized - Duration: 999 hours, Interval: 1s
Attempting to connect to Kafka...
Successfully connected to Kafka at localhost:9092
Starting data generation...
Message 1/3596400 sent: timestamp=2026-01-12T15:30:01, rpm=3245.67, temp=78.3°F
Message 2/3596400 sent: timestamp=2026-01-12T15:30:02, rpm=2987.23, temp=75.1°F
...
```

**Keep running!**

**Terminal 3 - Consumer:**
```bash
python consumer.py
```

**Expected output:**
```
Consumer initialized
Attempting to connect to Kafka...
[SUCCESS] Connected to Kafka topic: sensor-data
Attempting to connect to PostgreSQL...
[SUCCESS] Connected to database: sensordb
Consumer ready. Waiting for messages...
[OK] Message 1 processed: DB_ID=1
[OK] Message 2 processed: DB_ID=2
...
```

**Keep running!**

**Terminal 4 - 3D Frontend:**
```bash
cd frontend-3d
npm run dev
```

**Expected output:**
```
VITE v5.x.x  ready in 1234 ms

➜  Local:   http://localhost:3000/
➜  Network: use --host to expose
```

**Keep running!**

#### Step 7: Open and Use

**Classic Dashboard:**
1. Open browser: http://localhost:5000
2. Login: `admin` / `admin`
3. See real-time sensor data
4. Watch anomaly detection

**3D Digital Twin:**
1. Open browser: http://localhost:3000
2. Click "CLICK TO ENTER"
3. Use WASD to move, mouse to look
4. Watch rigs animate in real-time

**Success!** You're running the complete Rig Alpha system.

---

## 2. TRAINING ML MODELS

### 2.1 When to Train

**Initial Training:**
- First time running system
- Need at least 100 readings
- Takes 5-10 minutes

**Retraining:**
- After significant data collection (1000+ new readings)
- When adding new sensor types
- If detection accuracy degrades
- Periodically (monthly recommended)

### 2.2 Training Commands

**Train both models:**
```bash
python train_combined_detector.py
```

**Train only Isolation Forest:**
```bash
python train_combined_detector.py --if-only
```

**Train only LSTM:**
```bash
python train_combined_detector.py --lstm-only
```

**Force retrain (ignore existing):**
```bash
python train_combined_detector.py --force
```

### 2.3 Training Process Details

**What happens:**

```
1. Check existing models
   ├── isolation_forest.pkl exists? → Skip (unless --force)
   └── lstm_autoencoder.keras exists? → Skip (unless --force)

2. Check database data
   ├── Query: SELECT COUNT(*) FROM sensor_readings
   ├── Need at least 100 readings
   └── If not enough → Generate training data

3. Generate training data (if needed)
   ├── Start producer (generates normal readings)
   ├── Start consumer (processes and stores)
   ├── Run for 500 readings
   └── Stop both processes

4. Train Isolation Forest
   ├── Fetch 1000 most recent readings
   ├── Extract 50 sensor features
   ├── Scale features (StandardScaler)
   ├── Fit IsolationForest(n_estimators=100)
   ├── Save model
   └── Done (takes ~10 seconds)

5. Train LSTM Autoencoder
   ├── Fetch 2000 most recent readings
   ├── Create sequences (length=20)
   ├── Build LSTM architecture
   ├── Train for max 50 epochs (early stopping)
   ├── Calculate threshold (95th percentile)
   ├── Save model, scaler, threshold
   └── Done (takes 2-5 minutes)
```

### 2.4 Monitoring Training

**Watch for:**

**Isolation Forest:**
```
Training Isolation Forest on 1000 samples
Trained Isolation Forest on 1000 samples
Saved model to models/isolation_forest.pkl
```
- Very fast (< 30 seconds)
- No epochs (decision trees don't iterate)

**LSTM:**
```
Training LSTM Autoencoder on 980 sequences...
Epoch 1/50 - loss: 0.0234 - val_loss: 0.0245
Epoch 2/50 - loss: 0.0156 - val_loss: 0.0167
...
Epoch 15/50 - loss: 0.0012 - val_loss: 0.0015
Early stopping triggered (patience=5)
```

**Good training:**
- Loss decreases steadily
- val_loss similar to loss (not overfitting)
- Early stopping around epoch 15-30 (optimal)

**Bad training:**
```
Epoch 50/50 - loss: 0.0234 - val_loss: 0.0456
```
- Loss still high (model not learning)
- val_loss >> loss (overfitting)
- No early stopping (need more data)

### 2.5 Verifying Models

**Check models exist:**
```bash
ls -la models/
```

**Should see:**
```
isolation_forest.pkl          (Isolation Forest model)
lstm_autoencoder.keras        (LSTM model)
lstm_autoencoder_scaler.pkl   (Feature scaler)
lstm_autoencoder_threshold.pkl (Anomaly threshold)
```

**Test detection:**
```bash
python consumer.py
# Watch for anomaly detection messages
```

---

## 3. ADDING CUSTOM SENSORS

### 3.1 Via Dashboard UI

**Step-by-Step:**

1. **Login as Admin:**
   - Go to http://localhost:5000
   - Login: `admin` / `admin`

2. **Navigate to Custom Sensors:**
   - Click "Admin" in header
   - Click "Custom Sensors"

3. **Click "Add New Sensor"**

4. **Fill Form:**
   ```
   Sensor Name: oil_quality
   Category: mechanical
   Unit: %
   Min Range: 0
   Max Range: 100
   Low Threshold: 60
   High Threshold: 95
   ```

5. **Click "Create Sensor"**

6. **Verify:**
   - Sensor appears in list
   - Status: Active
   - Producer will include in next reload (60 seconds)

### 3.2 Via AI File Parsing

**Step-by-Step:**

1. **Prepare Sensor Spec File:**

**Example PDF/Text content:**
```
Sensor Specification Sheet

Oil Quality Monitor OQ-3000

Measurement Range: 0-100%
  - 0% = Completely degraded
  - 100% = New/clean oil

Operating Parameters:
  - Minimum acceptable: 60%
  - Optimal range: 80-95%
  - Replace oil when < 60%

Units: Percentage (%)
Category: Lubrication System
```

2. **Upload via UI:**
   - Click "Parse Sensor File"
   - Choose file (PDF, CSV, TXT, JSON)
   - Click "Upload and Parse"

3. **AI Extracts Specs:**
   - Groq/LLaMA reads document
   - Identifies key parameters
   - Auto-fills form

4. **Review and Save:**
   - Check extracted values
   - Adjust if needed
   - Click "Create Sensor"

### 3.3 Programmatically (API)

**Using cURL:**
```bash
curl -X POST http://localhost:5000/api/admin/custom-sensors \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -d '{
    "sensor_name": "oil_quality",
    "category": "mechanical",
    "unit": "%",
    "min_range": 0,
    "max_range": 100,
    "low_threshold": 60,
    "high_threshold": 95,
    "is_active": true
  }'
```

**Using Python:**
```python
import requests

# Login first
login_response = requests.post(
    'http://localhost:5000/api/auth/login',
    json={'username': 'admin', 'password': 'admin'}
)
session_cookie = login_response.cookies['session']

# Create sensor
response = requests.post(
    'http://localhost:5000/api/admin/custom-sensors',
    json={
        'sensor_name': 'oil_quality',
        'category': 'mechanical',
        'unit': '%',
        'min_range': 0,
        'max_range': 100,
        'low_threshold': 60,
        'high_threshold': 95
    },
    cookies={'session': session_cookie}
)

print(response.json())
# {'success': True, 'id': 1}
```

### 3.4 Custom Sensor Behavior

**Producer (after 60-second reload):**
```python
# Includes custom sensor in readings
{
    'timestamp': '2026-01-12T15:30:00',
    'temperature': 75.5,
    'rpm': 3500,
    ...
    'custom_sensors': {
        'oil_quality': 87.3  # Your custom sensor!
    }
}
```

**Consumer:**
- Validates custom sensor against registry
- Stores in JSONB column
- Includes in ML detection

**Dashboard:**
- Shows in telemetry grid
- Color-coded by threshold
- Charts available

---

## 4. DEPLOYING TO CLOUD

### 4.1 Neon.tech Database Setup

**Step 1: Create Neon Account**
1. Go to https://neon.tech
2. Sign up (free tier available)
3. Create new project
4. Name: "rig-alpha"

**Step 2: Get Connection String**
1. Click "Connection Details"
2. Copy connection string:
   ```
   postgresql://user:pass@ep-xxx-123.aws.neon.tech/neondb?sslmode=require
   ```

**Step 3: Configure Rig Alpha**

**Create .env file:**
```bash
cd /Users/arnavgolia/Desktop/Winter/stub
nano .env
```

**Add:**
```
DATABASE_URL=postgresql://user:pass@ep-xxx-123.aws.neon.tech/neondb?sslmode=require
```

**Save and exit:**
- Press `Ctrl+X`
- Press `Y`
- Press `Enter`

**Step 4: Apply Migrations to Neon**

**Install psql locally:**
- Mac: `brew install postgresql`
- Ubuntu: `sudo apt-get install postgresql-client`
- Windows: Download from postgresql.org

**Run migrations:**
```bash
PGPASSWORD=your-password psql -h ep-xxx-123.aws.neon.tech -U your-username -d neondb < migrations/add_user_auth.sql
PGPASSWORD=your-password psql -h ep-xxx-123.aws.neon.tech -U your-username -d neondb < migrations/add_custom_sensors.sql
# ... repeat for all migrations
```

**Or use GUI:**
1. Neon console → SQL Editor
2. Paste migration SQL
3. Click "Run"

**Step 5: Verify**
```bash
python check_db_version.py
```

**Should show:**
```
Connected to: postgresql://xxx...
PostgreSQL version: PostgreSQL 15.x on x86_64-pc-linux-gnu
Connection successful!
```

### 4.2 Upstash Kafka Setup

**Step 1: Create Upstash Account**
1. Go to https://upstash.com
2. Sign up
3. Create Kafka cluster
4. Region: Choose nearest

**Step 2: Get Credentials**
1. Click cluster
2. Copy:
   - Endpoint: `xxx.upstash.io:9092`
   - Username: `xxx`
   - Password: `xxx`

**Step 3: Configure**

**Add to .env:**
```
KAFKA_BROKER_URL=xxx.upstash.io:9092
KAFKA_SASL_USERNAME=your-username
KAFKA_SASL_PASSWORD=your-password
```

**Step 4: Create Topic**

**Via Upstash Console:**
1. Click "Topics"
2. Click "Create Topic"
3. Name: `sensor-data`
4. Partitions: 3
5. Retention: 24 hours

**Step 5: Test Connection**
```bash
python producer.py
```

**Should see:**
```
Attempting to connect to Kafka...
Successfully connected to Kafka at xxx.upstash.io:9092
```

### 4.3 Render Deployment

**Step 1: Prepare Repository**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/rig-alpha.git
git push -u origin main
```

**Step 2: Create Render Account**
1. Go to https://render.com
2. Sign up
3. Connect GitHub

**Step 3: Create Web Service**
1. Click "New +"
2. Select "Web Service"
3. Connect your repository
4. Configuration:
   ```
   Name: rig-alpha-dashboard
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn --worker-class eventlet -w 1 dashboard:app
   ```

**Step 4: Add Environment Variables**
```
DATABASE_URL=postgresql://...  (Neon connection)
KAFKA_BROKER_URL=xxx.upstash.io:9092
KAFKA_SASL_USERNAME=xxx
KAFKA_SASL_PASSWORD=xxx
GROQ_API_KEY=gsk_xxx
SECRET_KEY=random-secret-key-change-me
```

**Step 5: Deploy**
- Click "Create Web Service"
- Wait 5-10 minutes
- Done! Your dashboard is live

**Access:**
- URL: https://rig-alpha-dashboard.onrender.com

### 4.4 Deploy 3D Frontend

**Option A: Vercel (Recommended)**

1. **Install Vercel CLI:**
   ```bash
   npm install -g vercel
   ```

2. **Deploy:**
   ```bash
   cd frontend-3d
   vercel
   ```

3. **Configure:**
   - Follow prompts
   - Link to GitHub (optional)
   - Production deployment

4. **Update Socket URL:**
   ```jsx
   // In useSocket.js
   const socket = io('https://rig-alpha-dashboard.onrender.com', {
     // ...
   })
   ```

**Option B: Netlify**

1. Build production:
   ```bash
   npm run build
   ```

2. Upload `dist/` folder to Netlify

3. Configure redirects for SPA

---

## 5. TROUBLESHOOTING

### 5.1 Docker Issues

**Problem: "Docker not recognized"**

**Solution:**
1. Make sure Docker Desktop is running
2. Restart terminal
3. On Windows, check PATH includes Docker

**Problem: "Kafka connection failed"**

**Cause:** Kafka not fully started

**Solution:**
```bash
# Wait longer
sleep 120  # 2 minutes

# Check Kafka logs
docker logs stub-kafka

# Restart if needed
docker-compose restart kafka
```

**Problem: "Port 9092 already in use"**

**Cause:** Another Kafka instance running

**Solution:**
```bash
# Find process
lsof -i :9092  # Mac/Linux
netstat -ano | findstr :9092  # Windows

# Kill process
kill -9 <PID>  # Mac/Linux
taskkill /PID <PID> /F  # Windows

# Restart
docker-compose restart kafka
```

### 5.2 Python Issues

**Problem: "Module not found"**

**Cause:** Dependencies not installed

**Solution:**
```bash
# Activate venv
source venv/bin/activate  # Mac/Linux
.\venv\Scripts\Activate.ps1  # Windows

# Install
pip install -r requirements.txt
```

**Problem: "Consumer not receiving messages"**

**Cause:** Started in wrong order

**Solution:**
```
Correct order:
1. Start consumer FIRST
2. Start producer SECOND

Why?
- Consumer subscribes to topic
- Producer sends messages
- If producer starts first, messages might be missed
```

**Problem: "LSTM not working"**

**Cause:** TensorFlow not installed

**Solution:**
```bash
pip install tensorflow==2.15.0
```

**Verify:**
```bash
python -c "import tensorflow as tf; print(tf.__version__)"
# Should print: 2.15.0
```

### 5.3 3D Frontend Issues

**Problem: "Blank screen after clicking ENTER"**

**Solutions:**
1. **Check console** (F12)
   - Look for errors
   - Common: WebSocket connection failed

2. **Verify backend running:**
   ```bash
   curl http://localhost:5000/api/stats
   ```

3. **Check Socket.IO:**
   ```bash
   # In browser console
   window.location.reload()
   ```

4. **Disable browser extensions:**
   - Ad blockers can interfere
   - Try incognito mode

**Problem: "Can't move with WASD"**

**Solutions:**
1. **Click in canvas** to ensure focus
2. **Check pointer lock:**
   - Should see locked cursor
   - ESC to exit, click to re-enter

3. **Try different browser:**
   - Chrome recommended
   - Firefox may have issues

**Problem: "Rigs not animating"**

**Solutions:**
1. **Check producer running:**
   ```bash
   # Should see:
   Message X sent: rpm=3245.67
   ```

2. **Check consumer running:**
   ```bash
   # Should see:
   Message X processed: DB_ID=Y
   ```

3. **Check WebSocket:**
   ```javascript
   // Browser console
   // Should see:
   [Socket] Connected
   [Socket] Subscribed to machines: ["A", "B", "C"]
   ```

4. **Check telemetry:**
   ```bash
   curl http://localhost:5000/api/machines/A/stats
   # Should show recent data
   ```

### 5.4 Database Issues

**Problem: "Database connection failed"**

**Solutions:**
1. **Check PostgreSQL running:**
   ```bash
   docker ps | grep postgres
   ```

2. **Check credentials:**
   ```bash
   docker exec stub-postgres psql -U sensoruser -d sensordb -c "SELECT 1"
   ```

3. **Reset database:**
   ```bash
   docker-compose down -v
   docker-compose up -d
   # Wait 60 seconds
   # Re-run migrations
   ```

**Problem: "Table doesn't exist"**

**Cause:** Migrations not applied

**Solution:**
```bash
# Run all migrations
cat migrations/*.sql | docker exec -i stub-postgres psql -U sensoruser -d sensordb
```

### 5.5 Performance Issues

**Problem: "Dashboard slow"**

**Solutions:**
1. **Check database size:**
   ```sql
   SELECT COUNT(*) FROM sensor_readings;
   -- If > 1 million, consider archiving
   ```

2. **Archive old data:**
   ```sql
   DELETE FROM sensor_readings
   WHERE created_at < NOW() - INTERVAL '30 days';
   ```

3. **Vacuum database:**
   ```bash
   docker exec stub-postgres psql -U sensoruser -d sensordb -c "VACUUM ANALYZE"
   ```

**Problem: "3D visualization laggy"**

**Solutions:**
1. **Lower particle count:**
   ```jsx
   // In RigModel.jsx
   <Sparkles count={25} />  // Was 50
   ```

2. **Disable post-processing:**
   ```jsx
   // In App.jsx
   {/* <Effects /> */}  // Comment out
   ```

3. **Reduce shadow quality:**
   ```jsx
   <Canvas shadows={false}>
   ```

4. **Check GPU:**
   ```javascript
   // Browser console
   const canvas = document.querySelector('canvas')
   const gl = canvas.getContext('webgl')
   console.log(gl.getParameter(gl.VERSION))
   // Should show WebGL version
   ```

---

## 🎓 SUMMARY

You can now:

✅ **Install and setup** Rig Alpha completely  
✅ **Train ML models** for accurate detection  
✅ **Add custom sensors** three different ways  
✅ **Deploy to cloud** (Neon, Upstash, Render)  
✅ **Troubleshoot** common issues  

**Next Document:** [08-REFERENCE-APPENDIX.md](08-REFERENCE-APPENDIX.md)
- Complete glossary
- API reference
- Database schema
- Quick reference tables

---

*Continue to Document 08: Reference & Appendix →*
