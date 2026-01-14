# Database Configuration Guide

## Current Configuration Status

### ✅ **Current Setup: LOCAL DOCKER CONTAINER**

Based on the database check:
- **Host:** `localhost` (Docker container)
- **Port:** `5432`
- **Database:** `sensordb`
- **User:** `sensoruser`
- **PostgreSQL Version:** `PostgreSQL 15.15` (Alpine Linux)

**Connection Type:** Local Docker container (not remote)

---

## How Database Configuration Works

The app uses **`config.py`** (NOT SQLAlchemy) to manage database connections:

1. **First Priority:** Checks `DATABASE_URL` environment variable
2. **Fallback:** Uses local defaults (`localhost:5432`)

**File:** `stub/config.py` (lines 114-152)

```python
# Check for DATABASE_URL environment variable (for Neon/Render)
DATABASE_URL = os.environ.get('DATABASE_URL', '')

if DATABASE_URL:
    # Parse and use cloud database
    # Automatically converts postgres:// to postgresql://
else:
    # Fallback to local defaults
    DB_HOST = 'localhost'
    DB_PORT = 5432
    DB_NAME = 'sensordb'
    DB_USER = 'sensoruser'
    DB_PASSWORD = 'sensorpass'
```

---

## Switching to Neon.tech

### Step 1: Update `.env` File

**Location:** `stub/.env`

Add or uncomment this line with your Neon connection string:

```bash
DATABASE_URL=postgresql://user:password@ep-cool-darkness-123.us-east-2.aws.neon.tech/neondb?sslmode=require
```

**Important Notes:**
- Neon connection strings already use `postgresql://` (correct format)
- The `?sslmode=require` parameter is included (required for Neon)
- Replace `user`, `password`, and the endpoint with your actual Neon credentials

### Step 2: Restart Flask Server

After updating `.env`, restart the Flask server:

```powershell
# Stop current server (Ctrl+C)
# Then restart:
cd C:\Users\rahul\Desktop\stubby\stub
.\venv\Scripts\python.exe dashboard.py
```

### Step 3: Verify Connection

Run the database check script:

```powershell
.\venv\Scripts\python.exe check_db_version.py
```

Or use the API endpoint (after logging in):

```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/debug/db-info" -Headers @{Cookie="session=your-session-cookie"}
```

---

## Example `.env` File

```bash
# AI/LLM Configuration
GROQ_API_KEY=gsk_...

# Core Config
FLASK_APP=dashboard.py
FLASK_ENV=development
DEBUG=True

# Security
API_SECRET_KEY=rig-alpha-secret

# Database Configuration
# For LOCAL (Docker): Leave commented out
# DATABASE_URL=...

# For NEON (Cloud): Uncomment and set your connection string
DATABASE_URL=postgresql://neondb_owner:your-password@ep-cool-darkness-123.us-east-2.aws.neon.tech/neondb?sslmode=require

# Kafka Configuration
# For LOCAL: Leave commented out
# KAFKA_BROKER_URL=localhost:9092

# For UPSTASH (Cloud): Uncomment and set
# KAFKA_BROKER_URL=your-upstash-endpoint:9092
# KAFKA_SASL_USERNAME=your-username
# KAFKA_SASL_PASSWORD=your-password
```

---

## Tools Available

### 1. Database Version Check Script

**File:** `stub/check_db_version.py`

```powershell
.\venv\Scripts\python.exe check_db_version.py
```

**Output:**
- Current `DATABASE_URL` status
- Config values (host, port, database, user)
- PostgreSQL version
- Connection test results
- Local vs Remote detection

### 2. Database Info API Endpoint

**Endpoint:** `GET /api/debug/db-info`

**Requires:** Authentication (logged in user)

**Returns:**
```json
{
  "version": "PostgreSQL 15.15...",
  "database": "sensordb",
  "user": "sensoruser",
  "server_address": "localhost",
  "server_port": 5432,
  "is_remote": false,
  "config": {
    "host": "localhost",
    "port": 5432,
    "database": "sensordb",
    "user": "sensoruser",
    "has_database_url": false
  }
}
```

---

## Troubleshooting

### Issue: "Connection refused"
- **Local:** Make sure Docker container is running: `docker ps`
- **Neon:** Check connection string format and credentials

### Issue: "Password authentication failed"
- Verify username and password in `DATABASE_URL`
- For Neon: Check your Neon dashboard for the correct credentials

### Issue: "SSL connection required"
- Neon requires SSL: Make sure `?sslmode=require` is in the connection string
- The app automatically handles this if `DATABASE_URL` is set correctly

---

## Summary

**Current Status:**
- ✅ Using **LOCAL Docker container** (PostgreSQL 15.15)
- ✅ No `DATABASE_URL` set (using defaults)
- ✅ Connection working correctly

**To Switch to Neon:**
1. Add `DATABASE_URL` to `.env` file
2. Restart Flask server
3. Run `check_db_version.py` to verify

The app will automatically detect and use the Neon database once `DATABASE_URL` is set!

