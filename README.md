# Industrial Sensor Anomaly Detection Pipeline (Rig Alpha)

> Full-stack industrial IoT observability platform with streaming ingestion, hybrid ML anomaly detection, Groq-powered analysis, predictive maintenance, enterprise-grade audit logging, and a cinematic dashboard.

---

## Table of Contents

1. [Mission Primer](#mission-primer)
2. [Architecture & Data Flow](#architecture--data-flow)
3. [Feature Catalog](#feature-catalog)
4. [Component Reference](#component-reference)
5. [Operating the Stack](#operating-the-stack)
6. [Configuration & Secrets](#configuration--secrets)
7. [Database & Migrations](#database--migrations)
8. [Analytics, ML & AI](#analytics-ml--ai)
9. [Dashboard & UX Manual](#dashboard--ux-manual)
10. [API Surface](#api-surface)
11. [Observability & Auditing](#observability--auditing)
12. [Testing & Validation](#testing--validation)
13. [Troubleshooting & FAQ](#troubleshooting--faq)
14. [Deployment & Productionization](#deployment--productionization)
15. [Today’s Highlights](#todays-highlights)
16. [Resources](#resources)

---

## Mission Primer

Rig Alpha is a production-ready industrial monitoring platform purpose-built to showcase end-to-end mastery of modern data engineering, MLOps, and enterprise software practices. In one codebase you get:

- 50+ simulated industrial sensors split across Environmental, Mechanical, Thermal, Electrical, Fluid Dynamics, plus runtime-added custom channels.
- Edge producer with anomaly injection, command deck integration, and machine-specific frequency control.
- Kafka-backed streaming with exactly-once semantics, exponential backoff reconnect, and SASL-ready cloud configuration.
- Hybrid ML detection (Isolation Forest + optional LSTM Autoencoder) with contextual analytics, Groq/LLaMA reporting, and Remaining Useful Life predictions.
- Flask dashboard with live telemetry grid, machine controls, admin workflows, PDF sensor parser, AI summary panes, and cinematic “Rig Alpha” branding.
- Full authentication stack (signup/login/logout, hashed passwords, operator vs admin permissions, machine access control).
- Comprehensive audit logging (`audit_logs_v2`) with state capture, automatic operator attribution, and verification tooling.
- Cloud-aware configuration so the entire stack can swing between local Docker and Neon/Upstash/Render deployments with only `.env` changes.

---

## Architecture & Data Flow

```mermaid
flowchart TB
    subgraph Edge["Edge Layer"]
        Producer[Kafka Producer<br/>50+ Sensors + Custom Inputs]
        ExternalAPI[/api/v1/ingest<br/>API Key]
    end

    subgraph Stream["Streaming Layer"]
        Kafka[(Apache Kafka<br/>Exactly-once, SASL-ready)]
    end

    subgraph Process["Processing Layer"]
        Consumer[Kafka Consumer<br/>Validation + ML]
        IF[Isolation Forest]
        LSTM[LSTM Autoencoder<br/>(optional)]
        RUL[PTTF Predictor<br/>analytics/prediction_engine.py]
    end

    subgraph Store["Storage Layer"]
        DB[(PostgreSQL 15<br/>Docker/Neon)]
        Audit[(audit_logs_v2)]
    end

    subgraph Analyze["AI Layer"]
        Analyzer[analysis_engine.py<br/>Context & Correlations]
        Reports[report_generator.py<br/>Groq/LLaMA 3.3]
    end

    subgraph View["Presentation Layer"]
        Dashboard[dashboard.py<br/>Flask + Talisman + Limiter]
        Templates[templates/dashboard.html<br/>static/css/style.css]
    end

    Producer -->|JSON payload| Kafka
    ExternalAPI -->|API key ingest| Kafka
    Kafka -->|poll| Consumer
    Consumer -->|store| DB
    Consumer -->|detect| IF
    Consumer -->|sequence| LSTM
    Consumer -->|predict RUL| RUL
    IF -->|flag sensors| DB
    LSTM -->|temporal anomalies| DB
    RUL -->|health| DB
    DB -->|stats + history| Dashboard
    Dashboard -->|controls & admin| Producer
    Dashboard -->|audit events| Audit
    Analyzer -->|context windows| Reports
    Reports -->|Groq PDF/markdown| Dashboard
```

**Data journey (sensor → operator):**
1. `producer.py` pushes structured readings (50+ columns) + machine metadata to Kafka topic `sensor-data` every second (default) and honors per-sensor frequency overrides.
2. `consumer.py` reads batches, validates, writes to `sensor_readings`, executes hybrid ML detection, RUL predictions, anomaly logging, and triggers AI analysis.
3. `analysis_engine.py` fetches context windows, correlation matrices, severity scoring, and hands structured evidence to `report_generator.py`.
4. `dashboard.py` exposes REST APIs, manages auth, streams telemetry to the UI, surfaces anomalies, renders Groq reports, and exposes admin tooling (custom sensors, frequency plans, audit views).

---

## Feature Catalog

### Edge & Sensor Simulation

- **50+ built-in signals** covering temperature, torque, vibration, power, flow, cavitation, etc. (see `config.py` sensor threshold dictionary).
- **Multi-machine operation** (Machine A/B/C) with machine selectors in the UI and machine-specific access control in the DB (`user_machine_access`).
- **Per-sensor frequency control** (`machine_sensor_config`, `global_sensor_config`, `/api/machines/<id>/sensors/<sensor>/frequency`).
- **Custom sensors** stored in `custom_sensors` table, loaded dynamically into producer, consumer, and dashboard views; CRUD flows backed by admin APIs.
- **Anomaly injection engine** toggled via dashboard command deck or `/api/inject-anomaly`, with control over cadence, impacted sensors, and deviation magnitude.

### Streaming & Reliability

- Kafka producers and consumers configured for exactly-once semantics (manual commits after DB writes).
- Resilient connection handling with exponential backoff, bounded retries, Windows signal handling, and safe shutdown semantics.
- SASL/SCRAM support for Upstash/Confluent via `.env` toggles.
- `start-pipeline.ps1` bootstraps Docker Desktop, waits for Kafka readiness, and prints operator steps.

### Detection, Analytics & AI

- Isolation Forest detector (`ml_detector.AnomalyDetector`) covering all 50 columns, persisted via `models/isolation_forest.pkl`.
- LSTM Autoencoder support (`lstm_detector`, `lstm_predictor`) with `HYBRID_DETECTION_STRATEGY` (isolation-only, LSTM-only, hybrid OR / AND / smart).
- Context Analyzer computing z-scores, correlations, and severity metadata for each detected anomaly.
- Groq integration (llama-3.3-70b) via `report_generator.py` with automatic fallback reports when API unavailable.
- Predictive health engine (`analytics/prediction_engine.py`) returning Remaining Useful Life, degradation trends, critical sensors, and `/api/v1/predictive-health` responses.
- Automatic PDF/CSV/JSON sensor parser (`/api/admin/parse-sensor-file`) powered by PyPDF2 + Groq for uploading OEM specifications.

### Dashboard & UX

- Cinematic dual-panel layout: health matrix, command deck, telemetry grid, alerts, uptime timers, RUL countdown, machine cards.
- Realtime stats feed (`/api/stats`, `/api/system-metrics`, `/api/machines/<id>/stats`) polled by the frontend every few seconds.
- Embedded anomaly timeline with AI summaries, PDF exports, future anomaly predictions, and machine-level overrides (disable/enable sensors, adjust baselines, set custom thresholds).
- Admin-only panel for custom sensor CRUD, user management, audit log viewer, emergency stop.
- Security hardening: Flask-Talisman content security policy, Flask-Limiter (200 req/hour), secure cookies, connection pooling, structured logging.

### Security, Compliance & Operations

- Role-based access (admin/operator) with hashed credentials and machine scope enforcement.
- `/api/v1/ingest` API key authentication (`API_SECRET_KEY=rig-alpha-secret` default) for external IoT payloads.
- `@log_action` decorator attaches audit entries (user info, IP, resource, state diff) to `audit_logs_v2`.
- Health/diagnostic endpoints: `/api/status`, `/api/system-metrics`, `/api/debug/db-info`.
- Postgres connection pooling (ThreadedConnectionPool min 5/max 50) to support dashboard concurrency.

---

## Component Reference

| File / Directory | Purpose |
| ---------------- | ------- |
| `producer.py` | Edge simulator with 50+ sensors, anomaly injection, custom sensor loader, machine toggles, Kafka publisher. |
| `consumer.py` | Kafka consumer that validates payloads, writes to Postgres, runs hybrid ML detection, logs anomalies, dispatches AI + RUL tasks. |
| `config.py` | Central configuration (timing, Kafka, DB, sensor ranges, ML config, Groq, injection defaults). |
| `analytics/prediction_engine.py` | Remaining Useful Life / PTTF predictor exposed via dashboard APIs. |
| `analysis_engine.py` | Context windows, correlation matrices, severity scoring for anomalies. |
| `ml_detector.py`, `lstm_detector.py`, `lstm_predictor.py`, `combined_pipeline.py` | ML stack for anomaly detection and forecasting. |
| `report_generator.py` | Groq/LLaMA integration with markdown + PDF outputs and fallback copy. |
| `dashboard.py` | 4300+ lines covering Flask app, auth, rate limiting, admin APIs, audit logging, templating, PDF/CSV parsing, predictive health endpoints. |
| `templates/`, `static/` | 8k+ line dashboard template and 3.6k line CSS powering Rig Alpha’s UI. |
| `migrations/`, `setup_db.sql`, `setup_db_neon.sql`, `run_migration.py` | Schema creation and incremental changes (users, custom sensors, machine configs, audit tables, timestamps). |
| `docs/*` (`PROJECT_OVERVIEW.md`, `FINAL_PROJECT_REPORT.md`, `AUDIT_LOGGING_UPDATE.md`, etc.) | Narrative decks describing architecture, milestones, audit rollout, and interview prep. |
| `tests/*` (`test_audit_logging.py`, `test_consumer_insert.py`) | Regression scripts for audit logging coverage and DB insert verification. |
| `docker-compose.yml`, `Procfile`, `start-pipeline.ps1` | Local infrastructure, Render deployment config, and bootstrap automation. |

---

## Operating the Stack

### 1. Prerequisites

- Docker Desktop with WSL2 integration enabled.
- Python 3.13 (venv located at `stub/venv`).
- PowerShell 7+ (project scripts assume `pwsh`).
- Groq API key (optional but recommended for AI reports).

### 2. Environment & Dependencies

```powershell
cd C:\Users\rahul\Desktop\stubby\stub
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Populate `.env` (copy `.env.example`) with secrets like `GROQ_API_KEY`, `DATABASE_URL`, `KAFKA_BROKER_URL`, `API_SECRET_KEY`.

### 3. Start Infrastructure

```powershell
# Quick bootstrap
.\start-pipeline.ps1

# Manual alternative
docker-compose up -d
Start-Sleep -Seconds 60
```

### 4. Apply Schema

```powershell
# Local Docker database
docker exec -i stub-postgres psql -U sensoruser -d sensordb < setup_db.sql

# Apply migrations (examples)
Get-Content migrations/add_custom_sensors.sql | `
  docker exec -i stub-postgres psql -U sensoruser -d sensordb
python run_migration.py migrations/add_custom_sensors_column.sql
python run_migration.py migrations/add_last_login_column.py
```

### 5. Train ML Models

```powershell
.\venv\Scripts\Activate.ps1
python train_combined_detector.py
python lstm_detector.py  # optional if TensorFlow installed
```

### 6. Launch Services

Open three terminals (all in `stub/`):

```powershell
.\venv\Scripts\Activate.ps1
python consumer.py

.\venv\Scripts\Activate.ps1
python producer.py

.\venv\Scripts\Activate.ps1
python dashboard.py
```

Visit http://localhost:5000 (default admin credentials `admin` / `admin`). Assign machine access to operators via admin panel or SQL.

### 7. Stop / Clean

```powershell
docker-compose down            # stop services
docker-compose down -v         # stop + wipe volumes
```

---

## Configuration & Secrets

### `.env` Quick Reference

| Variable | Description |
| -------- | ----------- |
| `FLASK_APP`, `FLASK_ENV`, `DEBUG` | Dashboard runtime flags. |
| `SECRET_KEY`, `API_SECRET_KEY` | Flask session secret + ingest API key (`rig-alpha-secret` default). |
| `DATABASE_URL` | Optional Neon/Render string (`postgresql://...` with `?sslmode=require`). Fallback uses `config.DB_CONFIG`. |
| `KAFKA_BROKER_URL`, `KAFKA_SASL_USERNAME`, `KAFKA_SASL_PASSWORD` | Kafka connection (Upstash ready). |
| `GROQ_API_KEY` | Groq key (`gsk_...`). Optional `OPENAI_API_KEY` for legacy fallback. |
| `LSTM_ENABLED`, `HYBRID_DETECTION_STRATEGY`, `LSTM_SEQUENCE_LENGTH`, etc. | Toggle LSTM availability and detection strategy (defaults to `hybrid_smart`). |

`config.py` logs which path it is using and exposes safe defaults:

- `DEFAULT_DURATION_HOURS = 999` → producers run indefinitely until STOP.
- Kafka topic `sensor-data`, consumer group `sensor-consumer-group`.
- Rate limits for dashboard config updates (`CONFIG_LIMITS`).
- Sensor thresholds + units for all 50 metrics (used for UI coloring, injection, and detection heuristics).

---

## Database & Migrations

### Core Tables

- `sensor_readings` – primary telemetry (50+ columns + `custom_sensors` JSONB).
- `anomaly_detections` – ML events (score, detection method, sensors).
- `analysis_reports` – AI/Groq outputs.
- `predictive_health` – RUL snapshots per machine.
- `users`, `user_machine_access` – auth + machine scoping.
- `custom_sensors`, `machine_sensor_config`, `global_sensor_config` – extensibility controls.
- `audit_logs_v2` – compliance ledger with JSON state capture.

### Migration Artifacts

| File | Purpose |
| ---- | ------- |
| `setup_db.sql`, `setup_db_neon.sql`, `neon_complete_setup.sql` | Bootstrap schema for local Docker or Neon cloud. |
| `migrations/add_custom_sensors.sql` | Adds `custom_sensors` table + relationships. |
| `add_custom_sensors_column.sql` | Adds JSONB column to `sensor_readings` for inline custom data. |
| `add_last_login_column.py`, `add_updated_at_column.py` | Adds audit columns to `users`. |
| `run_migration.py` | Helper to execute SQL/py migrations safely against configured DB. |

### Verification Utilities

- `check_db_version.py` – prints connection target (local vs remote), Postgres version, and config.
- `/api/debug/db-info` – dashboard endpoint returning host, port, SSL, and connection metadata (auth required).
- `check_db_count.py`, `check_users_table.py`, `fix_users_email.py` – ad-hoc scripts available in repo for validation and fixes.

---

## Analytics, ML & AI

### Hybrid Detection Workflow

1. Consumer fetches reading, writes to DB.
2. `combined_pipeline.CombinedDetector` orchestrates Isolation Forest + (optional) LSTM:
   - `isolation_forest` → fast point anomalies.
   - `lstm` → temporal sequence deviations (TensorFlow optional).
   - `hybrid_or`, `hybrid_and`, `hybrid_smart` strategies combine scores/detections.
3. `ml_detector.record_anomaly_detection` persists sensor contribution details.
4. `analysis_engine.ContextAnalyzer` builds 10-reading window, z-scores, change percentages, and correlation list.
5. `report_generator.ReportGenerator` crafts Groq prompt and stores AI output or fallback data-driven report.
6. `/api/generate-report/<id>` and `/api/reports/<id>/pdf` expose results to UI.

### Model Training Commands

```powershell
# Isolation Forest
python train_combined_detector.py

# LSTM autoencoder (requires TensorFlow)
python lstm_detector.py --train

# Combined pipeline smoke test
python debug_pipeline.py
```

Trained artifacts land in `models/`. The consumer auto-loads them at startup.

### Predictive Health / RUL

- `analytics/prediction_engine.PTTFPredictor` monitors vibration, RPM, bearing temp, etc., tracks slopes, and estimates hours-to-failure.
- `/api/v1/predictive-health` surfaces aggregated machine health, critical sensors, and ETA (used in UI RUL countdown).
- `/api/generate-future-report` exports future-anomaly analysis (AI-assisted) for maintenance planning.

### AI Sensor Parser

- `/api/admin/parse-sensor-file` accepts PDF/CSV/JSON spec sheets, extracts sensor names/units/ranges, and seeds `custom_sensors`.
- Requires PyPDF2 (`pip install PyPDF2`) and Groq key; dashboard warns if unavailable.

---

## Dashboard & UX Manual

### Layout

- **Header:** Machine selector (A/B/C), system status LEDs (SYSTEM/COMM/POWER/SAFETY), pipeline throughput, UTC clock, alert badge.
- **Left Panel (“Ops Console”):**
  - Health cards per category (Environmental, Mechanical, Thermal, Electrical, Fluid, Custom).
  - Uptime timers, RUL countdown, severity badges, anomaly ticker.
  - Command deck (`START/STOP producer/consumer`, sampling rate slider, anomaly injection toggles, emergency stop).
  - Predictive health widget with RUL hours + critical sensor callouts.
- **Right Panel (“Telemetry Grid”):**
  - Sensor tiles with current value, rolling average, unit, threshold state, sparklines.
  - Custom sensors appear dynamically when created.
  - Machine-level actions (disable sensor, set baseline, adjust frequency).

### Authentication & Roles

- `/login`, `/signup`, `/logout` flows with hashed passwords (Werkzeug security).
- Admin capabilities: custom sensors CRUD, machine access assignment, audit viewing, emergency stop, parse sensor files.
- Operators: read-only telemetry + controls limited to assigned machines.

### Security Hardening

- Flask-Talisman CSP (script/style whitelists, frame busting).
- Flask-Limiter default 200 req/hour per IP (in-memory store, adjustable).
- Session cookies `HttpOnly` + `SameSite=Lax`.
- Structured logging for API errors and JSON responses for all `/api/*` routes.

---

## API Surface

> All endpoints defined in `dashboard.py`. Most require an authenticated session; admin-prefixed routes require admin role. `/api/v1/ingest` requires API key header `X-API-KEY`.

### Authentication

| Endpoint | Method | Description |
| -------- | ------ | ----------- |
| `/api/auth/signup` | POST | Create user. |
| `/api/auth/login` | POST | Authenticate, create session. |
| `/api/auth/logout` | POST | Destroy session. |
| `/api/auth/me` | GET | Return current user + accessible machines. |

### System & Stats

| Endpoint | Method | Description |
| -------- | ------ | ----------- |
| `/api/stats` | GET | Global telemetry counts, anomalies, throughput. |
| `/api/system-metrics` | GET | CPU, RAM, process info via `psutil`. |
| `/api/machines` | GET | Machine catalog + statuses. |
| `/api/machines/<id>/stats` | GET | Machine-specific stats including health, RUL. |
| `/api/status` | GET | Pipeline component heartbeat. |
| `/api/config` | GET/POST | View/adjust global duration/interval (with validation & logging). |
| `/api/config/reset` | POST | Restore defaults. |

### Control Plane

| Endpoint | Method | Description |
| -------- | ------ | ----------- |
| `/api/start/<component>` | POST | Start producer or consumer via subprocess. |
| `/api/stop/<component>` | POST | Gracefully stop component. |
| `/api/machines/<id>/start` | POST | Start producer limited to one machine. |
| `/api/machines/<id>/stop` | POST | Stop machine-specific producer. |
| `/api/admin/emergency-stop` | POST | Kill all managed processes (admin). |

### Anomalies, Reports & AI

| Endpoint | Method | Description |
| -------- | ------ | ----------- |
| `/api/anomalies` | GET | Paginated anomalies with filters. |
| `/api/anomalies/<id>` | GET | Detailed anomaly context. |
| `/api/generate-report/<id>` | POST | Kick off Groq/fallback analysis. |
| `/api/reports/<id>` | GET | Fetch stored report metadata. |
| `/api/reports/<id>/pdf` | GET | Download PDF rendition. |
| `/api/reports/by-anomaly/<id>` | GET | Fetch report tied to specific anomaly. |
| `/api/generate-full-report` | POST | Generate session-level PDF. |
| `/api/generate-future-report` | POST | Generate predictive maintenance report. |
| `/api/lstm-status`, `/api/lstm-predictions` | GET | Monitor LSTM training quality and future anomaly predictions. |
| `/api/v1/predictive-health` | GET | Aggregated RUL dataset. |

### Sensor & Machine Configuration

| Endpoint | Method | Description |
| -------- | ------ | ----------- |
| `/api/machines/<id>/sensors/<sensor_name>/toggle` | POST | Enable/disable built-in sensor for a machine. |
| `/api/machines/<id>/custom-sensors/<sensor_name>/toggle` | POST | Enable/disable custom sensor per machine. |
| `/api/machines/<id>/custom-sensors` | GET | Read machine-level custom sensor toggles. |
| `/api/machines/<id>/sensors/<sensor_name>/baseline` | POST | Rebaseline sensor values. |
| `/api/machines/<id>/sensors/<sensor_name>/frequency` | GET/POST | Override sampling cadence for a machine. |
| `/api/sensors/<sensor_name>/frequency` | GET/POST | Global default frequency updates. |
| `/api/thresholds` | GET/POST | Manage custom thresholds per sensor category. |
| `/api/injection-settings` | GET/POST | Toggle anomaly injection parameters. |
| `/api/inject-anomaly` | POST | Immediate anomaly injection. |

### Custom Sensors & Admin

| Endpoint | Method | Description |
| -------- | ------ | ----------- |
| `/api/admin/custom-sensors` | GET/POST | List/create custom sensors. |
| `/api/admin/custom-sensors/<id>` | GET/PUT/DELETE | Inspect/update/soft-delete sensor definitions (with state capture). |
| `/api/admin/parse-sensor-file` | POST | Upload sensor specification file for AI parsing. |
| `/api/admin/users` | GET | Admin-only list of users & access. |

### External Interfaces

| Endpoint | Method | Description |
| -------- | ------ | ----------- |
| `/api/v1/ingest` | POST | API-key authenticated ingestion for third-party devices. |
| `/api/audit-logs`, `/api/audit-log` | GET/POST | Admin audit log feed & manual entries. |
| `/api/export` | GET | Export dataset as CSV. |
| `/api/clear_data` | POST | Danger: wipe sensor data (admin only). |

---

## Observability & Auditing

### Audit Logging v2

- Decorator `@log_action` wraps critical routes (config changes, custom sensors, ingest, admin tools).
- When no session exists (API key ingest), logs default to `admin_rahul` (ID 1) or fallback `system`.
- Captures `user_id`, `username`, role, IP, user agent, action type, resource, optional `previous_state`/`new_state`.
- `AUDIT_LOGGING_UPDATE.md` documents design and manual test plan (`test_audit_logging.py` script).
- Query via `/api/audit-logs` or SQL:

```sql
SELECT username, action_type, resource_type, resource_id, timestamp
FROM audit_logs_v2
ORDER BY timestamp DESC
LIMIT 20;
```

### Logging & Files

- `consumer_output.log`, `consumer_service.log/.err` – service logs for ingestion pipeline.
- Dashboard logging uses Python logging with JSON-like patterns and prints Groq/PDF availability notes on startup.
- `.\.cursor\debug.log` receives debugging NDJSON from producer instrumentation.

### Health Checks

- `/api/status` returns component states and uptime.
- `/api/system-metrics` surfaces CPU, RAM, disk, process info for quick diagnostics.
- `check_db_version.py` ensures DB connectivity before running pipeline.

---

## Testing & Validation

| Script | Purpose |
| ------ | ------- |
| `test_audit_logging.py` | Calls `/api/v1/ingest`, verifies audit rows exist with correct attribution. |
| `test_consumer_insert.py` | Inserts sample message and ensures `sensor_readings` count increases. |
| `debug_pipeline.py` | Runs a local pipeline slice to validate ML components end-to-end. |
| `check_users_table.py` | Confirms `users` schema & indexes exist. |

### Usage

```powershell
.\venv\Scripts\Activate.ps1
python test_audit_logging.py
python test_consumer_insert.py
```

Add more validation with SQL snippets in `DATABASE_CONFIG.md` (checking counts, verifying partitions, etc.).

---

## Troubleshooting & FAQ

- **Docker not running** – launch Docker Desktop before `docker-compose up`.
- **Kafka connection refused** – wait 60s post `docker-compose up`; verify `stub-kafka-1` container with `docker ps`.
- **PyPDF2 / Groq missing warnings** – install optional dependencies or set `GROQ_API_KEY`.
- **LSTM disabled** – ensure TensorFlow installed and `LSTM_ENABLED=true`. Check `/api/lstm-status`.
- **Session expired** – clear browser cookies and log in again; rate limiting may also block repeated login attempts.
- **`custom_sensors` errors** – run `migrations/add_custom_sensors.sql` followed by `add_custom_sensors_column.sql`.
- **`DATABASE_URL` confusion** – see `DATABASE_CONFIG.md` for local vs Neon instructions; use `check_db_version.py`.
- **`psycopg2` SSL errors** – ensure Neon URL ends with `?sslmode=require`.
- **Producer stuck** – confirm `producer.py` can reach dashboard for injection settings; check Windows firewall if necessary.

---

## Deployment & Productionization

### Local vs Production

| Aspect | Dev Laptop | Production Recommendation |
| ------ | ---------- | ------------------------- |
| Runtime | Python venv + `python dashboard.py` | Docker images orchestrated via Kubernetes or Render/Gunicorn (see `Procfile`). |
| Kafka | Single broker via Docker Compose | Multi-broker cluster, managed Kafka (Confluent, MSK, Upstash). |
| Database | Docker Postgres 15 | Neon/Timescale/Postgres with replicas & PITR. |
| Secrets | `.env` file | Managed secret store (AWS SM, Vault). |
| Scaling | Single `dashboard.py` | Gunicorn + Eventlet workers, load balanced behind firewall. |
| Monitoring | Manual API checks | Prometheus + Grafana, ELK stack, alerting (PagerDuty/Slack). |

### Render / Cloud Notes

- `Procfile` uses `web: gunicorn -w 1 -k eventlet dashboard:app`.
- Minimal footprint works on Render free tier when pointing to Neon DB + Upstash Kafka; set env vars accordingly.
- Ensure `FLASK_ENV=production`, `SECRET_KEY` rotated, TLS forced (enable `force_https=True` in Talisman) for cloud.

### Backup & Recovery

- `docker-compose down -v` wipes volumes; use caution.
- For Neon, rely on built-in branching/snapshots. Locally, take dumps via `pg_dump` before experiments.
- Audit logs are append-only; never truncate outside retention policies.

---

## Today’s Highlights

Latest work session delivered the following upgrades (2026‑01‑09):

- **README overhaul** – this document captures every subsystem with actionable instructions.
- **Dashboard hardening** – Flask-Talisman CSP + Flask-Limiter integration plus database pooling to withstand heavy admin usage.
- **Custom sensor platform** – CRUD APIs, machine toggles, baseline control, and ingestion pipeline wiring so new sensors stream in without redeploying code.
- **Predictive maintenance UX** – `/api/v1/predictive-health`, `/api/generate-future-report`, and dashboard widgets now surface RUL estimates and future anomaly reports.
- **Audit logging v2** – decorator defaults to `admin_rahul`, captures state diffs, and covers ingest/admin/custom sensor routes (see `AUDIT_LOGGING_UPDATE.md`).
- **AI parser + Groq reporting** – PDF/CSV ingestion and Groq-based anomaly analysis with automatic fallbacks.
- **Operational scripts** – `start-pipeline.ps1`, `check_db_version.py`, migration helpers, and log files documented for day-2 operations.

---

## Resources

- `PROJECT_OVERVIEW.md` – lightning-start guide for stakeholders.
- `FINAL_PROJECT_REPORT.md` – 700-line deep dive with business pitch, risk grid, and appendices.
- `IMPLEMENTATION_VERIFICATION.md` – formal verification log of feature completion.
- `AUDIT_LOGGING_UPDATE.md` – compliance upgrade summary + manual verification steps.
- `FIXES_APPLIED.md`, `EMAIL_PHASE2_MILESTONE.md`, `PROJECT_MANIFEST.md` – historical references, release notes, and narratives for interviews.

---

**Status:** ✅ PRODUCTION READY  
**Last Updated:** 2026‑01‑09  
**Maintainer:** Rahul / Rig Alpha Team
