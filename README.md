# Sensor Data Pipeline

A simple Kafka pipeline that generates sensor data and saves it to a database.

---

## What Does It Do?

```
Producer  ➜  Kafka  ➜  Consumer  ➜  Database
(makes data)  (sends)  (receives)   (saves)
```

**Sensor Data:** Temperature, Pressure, Vibration, Humidity, RPM

---

## Quick Start (3 Steps)

### Step 1: Start Everything
```powershell
cd c:\Users\rahul\Desktop\stubby\stub
docker-compose up -d
Start-Sleep -Seconds 60
```

### Step 2: Open Dashboard
```powershell
.\venv\Scripts\Activate.ps1
python dashboard.py
```

### Step 3: Open Browser
Go to: **http://localhost:5000**

**That's it!** Use the dashboard to start/stop and monitor everything.

---

## Dashboard Controls

| Button | What It Does |
|--------|-------------|
| **Start Consumer** | Click FIRST - waits for data |
| **Start Producer** | Click SECOND - sends data |
| **Stop** | Stops the process |
| **Clear All Data** | Deletes all readings |
| **Update Config** | Changes duration/interval |

---

## Quick Presets

| Preset | Duration | Interval | Messages |
|--------|----------|----------|----------|
| Quick Test | 2 min | 10 sec | 12 |
| 1 Minute | 1 min | 5 sec | 12 |
| 1 Hour | 1 hour | 30 sec | 120 |
| 24 Hours | 24 hours | 30 sec | 2,880 |

---

## Common Issues

### "Docker not recognized"
- Open Docker Desktop first
- Wait for it to fully start

### "Kafka connection failed"
- Wait 60 seconds after starting Docker
- Run: `Start-Sleep -Seconds 60`

### "Consumer not receiving"
- Always start Consumer BEFORE Producer

### "Execution policy error"
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Stop Everything

```powershell
docker-compose down
```

To delete all data too:
```powershell
docker-compose down -v
```

---

## Files

| File | Purpose |
|------|---------|
| `dashboard.py` | Web control panel |
| `producer.py` | Makes sensor data |
| `consumer.py` | Saves to database |
| `config.py` | Settings |
| `docker-compose.yml` | Starts Kafka & Database |

---

## Manual Mode (Without Dashboard)

If you prefer command line:

**Terminal 1 - Consumer:**
```powershell
cd c:\Users\rahul\Desktop\stubby\stub
.\venv\Scripts\Activate.ps1
python consumer.py
```

**Terminal 2 - Producer:**
```powershell
cd c:\Users\rahul\Desktop\stubby\stub
.\venv\Scripts\Activate.ps1
python producer.py
```

**Stop:** Press `Ctrl+C` in each window

---

## Check Database

```powershell
docker exec stub-postgres psql -U sensoruser -d sensordb -c "SELECT COUNT(*) FROM sensor_readings;"
```

---

## Need Help?

1. Is Docker Desktop running?
2. Did you wait 60 seconds?
3. Did you start Consumer before Producer?

Most problems are solved by waiting for Kafka to start!

---

## Interview Questions & Answers

Questions someone might ask you about this project:

---

### Q: What is Kafka and why did you use it?

**A:** Kafka is a message broker - it sits between the producer and consumer so they don't have to talk directly. I used it because:
- If the database goes down, messages are saved in Kafka until it comes back
- Multiple consumers can read the same data
- It handles high-speed data better than direct database writes
- It's the industry standard for real-time data pipelines

---

### Q: What is a Producer and Consumer?

**A:**
- **Producer** = Creates data and sends it TO Kafka
- **Consumer** = Reads data FROM Kafka and does something with it (saves to database)

Think of it like a mailbox: Producer puts letters in, Consumer takes letters out.

---

### Q: Why start Consumer before Producer?

**A:** The Consumer needs to "subscribe" to the Kafka topic first. If the Producer sends messages before the Consumer is listening, those messages might be missed. It's like turning on your TV before the show starts.

---

### Q: What is Docker and why use it?

**A:** Docker runs applications in "containers" - isolated boxes with everything they need. I used it because:
- Don't need to install Kafka, Zookeeper, or PostgreSQL on my computer
- One command (`docker-compose up`) starts everything
- Works the same on any computer
- Easy to delete everything and start fresh

---

### Q: What is Zookeeper?

**A:** Zookeeper is Kafka's helper - it keeps track of which Kafka servers are running, who the leader is, and coordinates everything. Kafka needs it to function (though newer Kafka versions are removing this requirement).

---

### Q: What is PostgreSQL?

**A:** PostgreSQL is a database - it stores the sensor data permanently in tables. It's like a spreadsheet that can hold millions of rows and lets you search/filter quickly.

---

### Q: What does "exactly-once semantics" mean?

**A:** It means each message is processed exactly one time - not zero, not twice. I achieved this by:
1. Consumer reads message from Kafka
2. Consumer saves to database
3. Only THEN does Consumer tell Kafka "I got it" (commits offset)

If step 2 fails, the message stays in Kafka and gets retried.

---

### Q: Why are the sensor values correlated?

**A:** In real machinery:
- Higher **RPM** (speed) = More heat = Higher **temperature**
- Higher **RPM** = More shaking = Higher **vibration**
- Higher **temperature** = Drier air = Lower **humidity**
- Higher **temperature** = Gas expands = Higher **pressure**

Random values wouldn't be realistic for testing analytics.

---

### Q: What is exponential backoff?

**A:** When a connection fails, instead of retrying immediately (which could overload the server), we wait:
- 1st retry: wait 1 second
- 2nd retry: wait 2 seconds
- 3rd retry: wait 4 seconds
- ...up to 60 seconds max

This gives the server time to recover.

---

### Q: What happens if the database goes down during a run?

**A:**
1. Consumer tries to save, fails
2. Consumer does NOT commit to Kafka (message stays)
3. Consumer retries with exponential backoff
4. When database comes back, message is saved
5. No data is lost

---

### Q: Why use a virtual environment (venv)?

**A:** It keeps this project's Python packages separate from other projects. If another project needs a different version of a package, they won't conflict.

---

### Q: What is an API endpoint?

**A:** It's a URL that does something when you visit it. The dashboard uses these:
- `/api/stats` - Returns current statistics
- `/api/start/producer` - Starts the producer
- `/api/config` - Gets or updates settings

---

### Q: How would you scale this for more data?

**A:**
- Add more Kafka partitions (parallel processing)
- Run multiple consumers (each handles different partitions)
- Use a connection pool for database
- Add database replicas for reads
- Use Kafka clusters instead of single broker

---

### Q: What's the difference between Kafka and a regular database?

**A:**
| Kafka | Database |
|-------|----------|
| Temporary storage | Permanent storage |
| Optimized for streaming | Optimized for queries |
| Messages flow through | Data sits and waits |
| Append-only (fast writes) | Read/write/update/delete |

They work together: Kafka handles the flow, Database stores the result.

---

### Q: Why Flask for the dashboard?

**A:** Flask is a simple Python web framework. I used it because:
- Easy to create REST APIs
- Built-in development server
- Minimal code needed
- Same language as Producer/Consumer (Python)

---

### Q: What would you add to improve this project?

**A:**
- **Charts/graphs** showing data over time
- **Anomaly alerts** - if temperature spikes to 200°F suddenly, send email/SMS
- **Kafka health monitoring** - alert if Kafka goes down or gets slow
- **Authentication** to protect the dashboard
- **Multiple sensors** with unique IDs
- **Data export** to CSV or Excel
- **Unit tests** for the code

---

### Q: How would anomaly detection work?

**A:** Check each reading against expected ranges:
```python
if temperature > 150:  # Way too high!
    send_alert("CRITICAL: Temperature spike detected!")
```

Or compare to recent average:
```python
if current_value > (average * 1.5):  # 50% higher than normal
    send_alert("Anomaly detected!")
```

---

### Q: How would you know if Kafka goes down?

**A:** Several ways:
1. **Health check endpoint** - Kafka exposes metrics we can poll
2. **Connection errors** - If producer/consumer can't connect, log it
3. **Lag monitoring** - If consumer falls behind, something's wrong
4. **Heartbeat** - Send test messages and verify they arrive

In production, you'd use tools like **Prometheus + Grafana** or **Datadog** to monitor Kafka.

---

### Q: Would you use virtual environment (venv) in production?

**A:** No! In a real factory, you'd use **Docker containers** instead:

| Development (This Project) | Production (Real Factory) |
|---------------------------|--------------------------|
| Python venv on your laptop | Docker containers |
| docker-compose on one PC | Kubernetes cluster |
| Single Kafka broker | Kafka cluster (3+ brokers) |
| Single database | Database with replicas |
| Dashboard on localhost | Dashboard behind firewall with auth |

**Why Docker in production?**
- Same environment everywhere (no "works on my machine")
- Easy to scale up/down
- Easy to update and rollback
- Isolated from host system
- Can run on cloud (AWS, Azure, GCP)

---

### Q: How would this look in a real factory?

**A:**
```
Real Sensors (PLC/SCADA)  →  Edge Gateway  →  Kafka Cluster  →  Consumers  →  Database
        ↓                         ↓                ↓               ↓            ↓
  Actual machines           On-site server    Cloud or         Multiple      Time-series DB
  (not stub data)           converts signals  on-premise       workers       (InfluxDB/TimescaleDB)
                                                                    ↓
                                                              Alerting System
                                                              (PagerDuty/Slack)
```

The code structure would be similar, but:
- Real sensor data instead of random numbers
- Multiple Kafka brokers for redundancy
- Kubernetes to manage containers
- Monitoring dashboards (Grafana)
- Alert systems for anomalies and outages


If there's any big errors so there's like a random value that goes super high, then we'll get an alert. And then also if Capc goes down we have to know if Capc goes down we have to add that stuff the Python virtual environment, if I wanted to actually put this into a real production-level, like whatever factory, would I have to run a virtual environment? How would that go?