# ML-Based Anomaly Detection System

A complete guide to understanding the machine learning anomaly detection implementation in this sensor data pipeline.

---

## Table of Contents

1. [Overview](#overview)
2. [What is Anomaly Detection?](#what-is-anomaly-detection)
3. [How It Works (Big Picture)](#how-it-works-big-picture)
4. [The Two Detection Methods](#the-two-detection-methods)
5. [Detailed Component Breakdown](#detailed-component-breakdown)
6. [Data Flow Diagram](#data-flow-diagram)
7. [File Structure](#file-structure)
8. [Database Tables](#database-tables)
9. [Configuration Options](#configuration-options)
10. [API Endpoints](#api-endpoints)
11. [Dashboard UI](#dashboard-ui)
12. [How to Use](#how-to-use)
13. [Troubleshooting](#troubleshooting)

---

## Overview

This system adds **machine learning-based anomaly detection** to the existing sensor data pipeline. Instead of just checking if values are within predefined ranges (rule-based), it learns what "normal" looks like from your data and flags anything unusual.

### What Gets Added

| Component | Purpose |
|-----------|---------|
| **Isolation Forest** | Fast ML model that detects outliers in real-time |
| **LSTM Autoencoder** | Optional deep learning model for sequence patterns |
| **Context Analyzer** | Fetches 10 readings before/after an anomaly |
| **Correlation Engine** | Finds relationships between sensor parameters |
| **Report Generator** | Uses ChatGPT to explain anomalies in plain English |
| **Dashboard UI** | Shows anomalies and lets you generate reports |

---

## What is Anomaly Detection?

### The Problem

Your pipeline generates 50 sensor readings every 30 seconds. Sometimes, equipment malfunctions or degrades. You need to catch these issues BEFORE they cause damage.

### Rule-Based vs ML-Based Detection

**Rule-Based (What You Already Have):**
```
IF temperature > 100°F THEN alert
IF pressure > 15 PSI THEN alert
```
- Simple to understand
- Only catches obvious problems
- Can't detect subtle patterns
- Requires manually setting thresholds for all 50 sensors

**ML-Based (What This Adds):**
```
Learn what "normal" looks like from 100+ readings
Flag anything that deviates from normal patterns
```
- Catches subtle anomalies across all 50 sensors at once
- Learns correlations (high RPM should mean high temperature)
- Detects unusual combinations even if individual values are "normal"
- No manual threshold setting required

### Example

Imagine these readings are "normal":
- RPM: 3000, Temperature: 85°F, Vibration: 5 mm/s

This reading would be flagged as anomalous:
- RPM: 3000, Temperature: 85°F, Vibration: 2 mm/s

Why? Because the ML model learned that high RPM always correlates with higher vibration. Low vibration at high RPM is suspicious - maybe the vibration sensor failed, or something is dampening vibrations unexpectedly.

---

## How It Works (Big Picture)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NORMAL OPERATION                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Producer ──► Kafka ──► Consumer ──► Database                              │
│                              │                                               │
│                              ▼                                               │
│                     ┌───────────────┐                                        │
│                     │ Insert Reading │                                       │
│                     │ (Returns ID)   │                                       │
│                     └───────┬───────┘                                        │
│                             │                                                │
│                             ▼                                                │
│                   ┌─────────────────────┐                                    │
│                   │  Isolation Forest   │                                    │
│                   │  Anomaly Detection  │                                    │
│                   └─────────┬───────────┘                                    │
│                             │                                                │
│              ┌──────────────┴──────────────┐                                 │
│              ▼                             ▼                                 │
│        ┌──────────┐                 ┌─────────────┐                          │
│        │  Normal  │                 │  ANOMALY!   │                          │
│        │ (do nothing)               │  detected   │                          │
│        └──────────┘                 └──────┬──────┘                          │
│                                            │                                 │
│                                            ▼                                 │
│                                   ┌────────────────┐                         │
│                                   │ Save to        │                         │
│                                   │ anomaly_       │                         │
│                                   │ detections     │                         │
│                                   └────────┬───────┘                         │
│                                            │                                 │
│                                            ▼                                 │
│                                   ┌────────────────┐                         │
│                                   │ Create Alert   │                         │
│                                   │ (shows in UI)  │                         │
│                                   └────────────────┘                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        REPORT GENERATION (User-Triggered)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   User clicks "Generate Report" on an anomaly                               │
│                            │                                                 │
│                            ▼                                                 │
│                   ┌─────────────────┐                                        │
│                   │ Context Analyzer│                                        │
│                   │ Fetch 10 before │                                        │
│                   │ Fetch 10 after  │                                        │
│                   └────────┬────────┘                                        │
│                            │                                                 │
│                            ▼                                                 │
│                   ┌─────────────────┐                                        │
│                   │  Correlation    │                                        │
│                   │  Engine         │                                        │
│                   │  (Find patterns)│                                        │
│                   └────────┬────────┘                                        │
│                            │                                                 │
│                            ▼                                                 │
│                   ┌─────────────────┐                                        │
│                   │  ChatGPT API    │                                        │
│                   │  (Analyze &     │                                        │
│                   │   Explain)      │                                        │
│                   └────────┬────────┘                                        │
│                            │                                                 │
│                            ▼                                                 │
│                   ┌─────────────────┐                                        │
│                   │ Save Report to  │                                        │
│                   │ analysis_reports│                                        │
│                   └────────┬────────┘                                        │
│                            │                                                 │
│                            ▼                                                 │
│                   ┌─────────────────┐                                        │
│                   │ Display in      │                                        │
│                   │ Modal (UI)      │                                        │
│                   └─────────────────┘                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## The Two Detection Methods

### 1. Isolation Forest (Primary - Always Active)

**What It Is:**
An unsupervised machine learning algorithm that isolates anomalies by randomly partitioning data.

**How It Works (Simplified):**
1. Imagine plotting all your sensor readings as points in 50-dimensional space
2. The algorithm randomly draws lines to split the data
3. "Normal" points are clustered together (takes many splits to isolate)
4. "Anomalous" points are isolated (takes few splits to isolate)
5. Points that get isolated quickly = anomalies

**Pros:**
- Very fast (O(n log n) complexity)
- Works with all 50 sensors at once
- No labels needed (learns from your data)
- Low memory usage
- Handles correlated features well

**Cons:**
- Treats each reading independently (no time awareness)
- Can't explain WHY something is anomalous
- Needs tuning of "contamination" parameter
- May miss slow degradation patterns

**When It Trains:**
- Automatically trains after you have 100+ readings
- Model is saved to `models/isolation_forest.pkl`
- Reuses saved model on restart

---

### 2. LSTM Autoencoder (Optional - Requires TensorFlow)

**What It Is:**
A deep learning model that learns temporal sequences and detects anomalies based on reconstruction error.

**How It Works (Simplified):**
1. Takes sequences of 20 readings (not individual points)
2. Compresses the sequence to a small representation (encoding)
3. Tries to reconstruct the original sequence from the encoding
4. If reconstruction error is high = the pattern is unusual = anomaly

**Pros:**
- Understands temporal patterns (sequences over time)
- Detects gradual degradation
- Can learn cyclical patterns (day/night, weekday/weekend)
- Better for slow-developing issues

**Cons:**
- Requires TensorFlow (large dependency)
- Needs more training data (500+ readings)
- Slower training and inference
- More complex to tune

**When to Use:**
- If you need sequence-aware detection
- If Isolation Forest misses gradual changes
- If you have GPU acceleration available

---

## Detailed Component Breakdown

### ml_detector.py - Isolation Forest Detector

```python
class AnomalyDetector:
    """Main detection class"""
    
    # Uses all 50 sensor columns
    SENSOR_COLUMNS = ['temperature', 'pressure', ..., 'valve_position']
    
    def train(self, data):
        """
        Train the model on historical data
        - Fetches last 1000 readings from database
        - Scales data using StandardScaler (normalizes to mean=0, std=1)
        - Fits Isolation Forest model
        - Saves model to disk
        """
    
    def detect(self, reading):
        """
        Check if a single reading is anomalous
        - Converts reading dict to feature array
        - Scales using fitted scaler
        - Returns: (is_anomaly, score, contributing_sensors)
        
        Score interpretation:
        - Positive scores = more normal
        - Negative scores = more anomalous
        - Around 0 = borderline
        """
    
    def _identify_contributing_sensors(self, reading):
        """
        Find which sensors caused the anomaly
        - Compares each sensor to its historical mean
        - Returns sensors with z-score > 2 (2 std deviations from mean)
        """
```

**Key Parameters:**
- `contamination=0.05`: Expects 5% of readings to be anomalies
- `n_estimators=100`: Number of trees in the forest
- `MIN_TRAINING_SAMPLES=100`: Minimum readings before training

---

### analysis_engine.py - Context and Correlation Analysis

```python
class ContextAnalyzer:
    """Analyzes the context around anomalies"""
    
    def get_context_window(self, reading_id):
        """
        Fetches readings around an anomaly:
        - 10 readings BEFORE the anomaly
        - The anomalous reading itself
        - 10 readings AFTER the anomaly
        
        Returns dict with 'before', 'anomaly', 'after' DataFrames
        """
    
    def compute_correlations(self, context_data):
        """
        Computes Pearson correlations between all 50 sensors
        - Uses readings from context window
        - Filters for significant correlations (|r| > 0.5, p < 0.05)
        - Returns top 20 strongest correlations
        
        Example output:
        - rpm ↔ temperature: r=0.85 (strong positive)
        - rpm ↔ humidity: r=-0.72 (strong negative)
        """
    
    def identify_anomalous_patterns(self, context_data):
        """
        Finds which sensors deviated most from baseline:
        - Calculates z-score for each sensor
        - Calculates percent change from baseline
        - Identifies trend direction (increasing/decreasing)
        
        Returns list sorted by z-score magnitude
        """
```

---

### report_generator.py - ChatGPT Integration

```python
class ReportGenerator:
    """Generates detailed reports using ChatGPT"""
    
    def _build_prompt(self, anomaly_data, analysis_summary):
        """
        Builds a detailed prompt for ChatGPT including:
        - Anomaly detection details (score, method, timestamp)
        - Top 10 sensor deviations with z-scores
        - Significant correlations found
        - Context window information
        
        Asks ChatGPT to provide:
        1. Root Cause Analysis
        2. Affected Systems
        3. Severity Assessment
        4. Prevention Recommendations
        5. Immediate Actions Required
        """
    
    def generate_report(self, anomaly_id):
        """
        Full report generation pipeline:
        1. Fetch anomaly details from database
        2. Get context window (10 before/after)
        3. Compute correlations
        4. Identify patterns
        5. Call ChatGPT API
        6. Parse and return report
        """
    
    def _generate_fallback_report(self):
        """
        If ChatGPT is unavailable, returns a template report
        with instructions for manual analysis
        """
```

---

### lstm_detector.py - LSTM Autoencoder (Optional)

```python
class LSTMAutoencoder:
    """Sequence-based anomaly detection"""
    
    def __init__(self, sequence_length=20):
        """
        Architecture:
        - Input: 20 timesteps × 50 features
        - Encoder: LSTM(128) → LSTM(64) → Dense(32)
        - Decoder: RepeatVector → LSTM(64) → LSTM(128) → Dense(50)
        - Output: 20 timesteps × 50 features (reconstruction)
        """
    
    def train(self, epochs=50):
        """
        Training process:
        1. Fetch 2000 readings from database
        2. Create sliding window sequences (length=20)
        3. Train autoencoder to reconstruct sequences
        4. Calculate reconstruction errors on training data
        5. Set threshold at 95th percentile of errors
        """
    
    def detect(self, sequence_data):
        """
        Detection process:
        1. Take last 20 readings
        2. Feed through encoder-decoder
        3. Calculate mean squared error between input and output
        4. If error > threshold → anomaly
        """
```

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE TABLES                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  sensor_readings                  anomaly_detections                          │
│  ┌─────────────────────┐          ┌────────────────────────┐                  │
│  │ id                  │◄────────┐│ id                     │                  │
│  │ timestamp           │         ││ reading_id (FK)────────┘                  │
│  │ temperature         │         │├────────────────────────┤                  │
│  │ pressure            │         ││ detection_method       │                  │
│  │ humidity            │         ││ anomaly_score          │                  │
│  │ ... (50 sensors)    │         ││ is_anomaly             │                  │
│  │ created_at          │         ││ detected_sensors[]     │                  │
│  └─────────────────────┘         ││ created_at             │                  │
│                                   │└──────────┬─────────────┘                  │
│                                   │           │                                │
│                                   │           ▼                                │
│                                   │  analysis_reports                          │
│                                   │  ┌────────────────────────┐                │
│                                   │  │ id                     │                │
│                                   └──│ anomaly_id (FK)────────┘                │
│                                      ├────────────────────────┤                │
│                                      │ context_data (JSON)    │                │
│                                      │ correlations (JSON)    │                │
│                                      │ chatgpt_analysis       │                │
│                                      │ root_cause             │                │
│                                      │ prevention_recommendations              │
│                                      │ status                 │                │
│                                      │ created_at             │                │
│                                      │ completed_at           │                │
│                                      └────────────────────────┘                │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
stub/
├── config.py                 # Configuration (ML settings added)
│   ├── ML_DETECTION_ENABLED = True
│   ├── ISOLATION_FOREST_CONTAMINATION = 0.05
│   ├── MIN_TRAINING_SAMPLES = 100
│   ├── CONTEXT_WINDOW_SIZE = 10
│   ├── OPENAI_API_KEY = (from environment)
│   └── CHATGPT_MODEL = 'gpt-4'
│
├── consumer.py               # Modified to call ML detection
│   └── run_ml_detection()    # Called after each insert
│
├── dashboard.py              # Modified with new API endpoints
│   ├── /api/anomalies        # List ML anomalies
│   ├── /api/anomalies/<id>   # Get anomaly details
│   ├── /api/generate-report/<id>  # Generate report
│   ├── /api/reports/<id>     # Get report
│   └── /api/ml-stats         # Get ML statistics
│
├── ml_detector.py            # NEW: Isolation Forest implementation
│   ├── AnomalyDetector class
│   ├── record_anomaly_detection()
│   └── get_detector()
│
├── analysis_engine.py        # NEW: Context and correlation analysis
│   ├── ContextAnalyzer class
│   └── get_anomaly_details()
│
├── report_generator.py       # NEW: ChatGPT report generation
│   ├── ReportGenerator class
│   ├── get_report()
│   └── get_report_by_anomaly()
│
├── lstm_detector.py          # NEW: Optional LSTM Autoencoder
│   ├── LSTMAutoencoder class
│   └── get_lstm_detector()
│
├── models/                   # NEW: Trained model storage
│   ├── isolation_forest.pkl  # Saved Isolation Forest model
│   └── (lstm files if used)
│
├── setup_db.sql              # Modified with new tables
│   ├── anomaly_detections table
│   └── analysis_reports table
│
├── requirements.txt          # Modified with new dependencies
│   ├── scikit-learn
│   ├── numpy, pandas, scipy
│   ├── joblib
│   └── openai
│
└── templates/
    └── dashboard.html        # Modified with ML UI
        ├── ML Anomaly Detection card
        ├── Generate Report button
        └── Report modal
```

---

## Database Tables

### anomaly_detections

Stores every ML detection result (both normal and anomalous readings).

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `reading_id` | INT (FK) | Links to sensor_readings.id |
| `detection_method` | VARCHAR(32) | 'isolation_forest' or 'lstm_autoencoder' |
| `anomaly_score` | FLOAT | Score from the model (lower = more anomalous) |
| `is_anomaly` | BOOLEAN | True if classified as anomaly |
| `detected_sensors` | TEXT[] | Array of sensor names that contributed |
| `created_at` | TIMESTAMPTZ | When detection occurred |

### analysis_reports

Stores ChatGPT-generated analysis reports.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `anomaly_id` | INT (FK) | Links to anomaly_detections.id |
| `context_data` | JSONB | 10 readings before/after (serialized) |
| `correlations` | JSONB | Significant correlations found |
| `chatgpt_analysis` | TEXT | Full ChatGPT response |
| `root_cause` | TEXT | Extracted root cause section |
| `prevention_recommendations` | TEXT | Extracted recommendations |
| `status` | VARCHAR(32) | 'pending', 'generating', 'completed', 'failed' |
| `created_at` | TIMESTAMPTZ | When report was requested |
| `completed_at` | TIMESTAMPTZ | When report finished generating |

---

## Configuration Options

In `config.py`:

```python
# ============================================================================
# ML DETECTION CONFIGURATION
# ============================================================================

# Enable/disable ML-based anomaly detection
ML_DETECTION_ENABLED = True          # Set to False to disable ML

# Isolation Forest parameters
ISOLATION_FOREST_CONTAMINATION = 0.05  # Expected % of anomalies (5%)
ISOLATION_FOREST_N_ESTIMATORS = 100    # Number of trees (more = slower but better)
MIN_TRAINING_SAMPLES = 100             # Wait for this many readings before training

# Context analysis settings
CONTEXT_WINDOW_SIZE = 10               # Readings before/after to analyze

# Model storage path
MODELS_DIR = './models'                # Where trained models are saved

# ============================================================================
# CHATGPT API CONFIGURATION
# ============================================================================

# Set via environment variable for security:
# Windows: $env:OPENAI_API_KEY = "sk-..."
# Linux/Mac: export OPENAI_API_KEY="sk-..."
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# Model to use
CHATGPT_MODEL = 'gpt-4'       # Best quality, higher cost
# CHATGPT_MODEL = 'gpt-3.5-turbo'  # Faster, cheaper, slightly lower quality
```

---

## API Endpoints

### GET /api/anomalies

List detected anomalies.

**Query Parameters:**
- `limit` (int, default=50): Maximum anomalies to return
- `only_anomalies` (bool, default=true): Only show actual anomalies

**Response:**
```json
{
  "anomalies": [
    {
      "id": 42,
      "reading_id": 1234,
      "detection_method": "isolation_forest",
      "anomaly_score": -0.2341,
      "is_anomaly": true,
      "detected_sensors": ["temperature", "vibration", "rpm"],
      "created_at": "2024-01-15T10:30:00",
      "report_id": 5,
      "report_status": "completed"
    }
  ]
}
```

### POST /api/generate-report/{anomaly_id}

Generate a ChatGPT analysis report for an anomaly.

**Response:**
```json
{
  "success": true,
  "report_id": 5,
  "message": "Report generated successfully"
}
```

### GET /api/reports/{report_id}

Get a generated report.

**Response:**
```json
{
  "id": 5,
  "anomaly_id": 42,
  "context_data": { ... },
  "correlations": { ... },
  "chatgpt_analysis": "### 1. ROOT CAUSE ANALYSIS\n...",
  "root_cause": "The temperature spike...",
  "prevention_recommendations": "1. Adjust cooling...",
  "status": "completed",
  "created_at": "2024-01-15T10:31:00",
  "completed_at": "2024-01-15T10:31:15"
}
```

### GET /api/ml-stats

Get ML detection statistics.

**Response:**
```json
{
  "total_detections": 500,
  "total_anomalies": 23,
  "avg_score": 0.1234,
  "min_score": -0.5621,
  "max_score": 0.4532,
  "recent_anomaly_rate": 4.5,
  "total_reports": 10,
  "completed_reports": 8,
  "ml_available": true
}
```

---

## Dashboard UI

### ML Anomaly Detection Card

Located below the main grid, shows:
- **Anomalies Detected**: Total count of ML-detected anomalies
- **Recent Rate**: Percentage of recent readings flagged as anomalies
- **Reports Generated**: Number of ChatGPT reports created

### Anomaly List

Each anomaly shows:
- **Score**: The anomaly score (more negative = more anomalous)
- **Method**: Which detection method was used
- **Timestamp**: When it was detected
- **Contributing Sensors**: Which sensors triggered the anomaly
- **Generate Report** button: Click to create ChatGPT analysis

### Report Modal

When you click "View Report", a modal appears with:
- Report metadata (ID, anomaly ID, generation time, status)
- Full ChatGPT analysis with:
  - Root Cause Analysis
  - Affected Systems
  - Severity Assessment
  - Prevention Recommendations
  - Immediate Actions Required

---

## How to Use

### Step 1: Update Database Schema

The new tables need to be created. Run this in your PostgreSQL container:

```sql
-- Add to your database (run via psql or pgAdmin)

CREATE TABLE IF NOT EXISTS anomaly_detections (
    id SERIAL PRIMARY KEY,
    reading_id INT REFERENCES sensor_readings(id) ON DELETE CASCADE,
    detection_method VARCHAR(32) NOT NULL,
    anomaly_score FLOAT NOT NULL,
    is_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    detected_sensors TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analysis_reports (
    id SERIAL PRIMARY KEY,
    anomaly_id INT REFERENCES anomaly_detections(id) ON DELETE CASCADE,
    context_data JSONB,
    correlations JSONB,
    chatgpt_analysis TEXT,
    root_cause TEXT,
    prevention_recommendations TEXT,
    status VARCHAR(32) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_anomaly_detections_reading ON anomaly_detections(reading_id);
CREATE INDEX IF NOT EXISTS idx_anomaly_detections_is_anomaly ON anomaly_detections(is_anomaly);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_anomaly ON analysis_reports(anomaly_id);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE anomaly_detections TO sensoruser;
GRANT ALL PRIVILEGES ON SEQUENCE anomaly_detections_id_seq TO sensoruser;
GRANT ALL PRIVILEGES ON TABLE analysis_reports TO sensoruser;
GRANT ALL PRIVILEGES ON SEQUENCE analysis_reports_id_seq TO sensoruser;
```

### Step 2: Install New Dependencies

```powershell
cd C:\Users\rahul\Desktop\dta\stub
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

This installs:
- `scikit-learn`: For Isolation Forest
- `numpy`, `pandas`, `scipy`: Data manipulation
- `joblib`: Model serialization
- `openai`: ChatGPT API

### Step 3: Set OpenAI API Key (Optional, for Reports)

```powershell
# In PowerShell (temporary, for this session)
$env:OPENAI_API_KEY = "sk-your-api-key-here"

# Or permanently in Windows Environment Variables
```

Without an API key, reports will use a fallback template.

### Step 4: Run the Pipeline

Start as normal:
```powershell
python dashboard.py
```

Then start Consumer and Producer from the dashboard.

### Step 5: Wait for Training

The Isolation Forest model auto-trains after 100 readings. With default settings (30s interval), this takes about **50 minutes**.

For faster testing, use "Quick Test" preset (10s interval) = **17 minutes**.

### Step 6: View Anomalies

Once trained, anomalies appear in the "ML Anomaly Detection" card. Click "Generate Report" on any anomaly to get ChatGPT analysis.

---

## Troubleshooting

### "No ML anomalies detected yet"

1. **Not enough data**: Need 100+ readings before training starts
2. **All normal**: If your data is consistent, there may be no anomalies
3. **Check logs**: Look for "Trained Isolation Forest" message

### "ML components not available"

1. **Missing dependencies**: Run `pip install -r requirements.txt`
2. **Import error**: Check console for specific error messages

### "Failed to generate report"

1. **No API key**: Set `OPENAI_API_KEY` environment variable
2. **API quota exceeded**: Check your OpenAI account
3. **Network issue**: Verify internet connection

### "Model not trained"

1. **Not enough samples**: Wait for 100+ readings
2. **Database connection**: Verify PostgreSQL is running
3. **Check models/ directory**: Should contain `isolation_forest.pkl` after training

### High False Positive Rate

1. **Adjust contamination**: Lower `ISOLATION_FOREST_CONTAMINATION` in config.py
2. **More training data**: Let it collect more normal readings before judging
3. **Retrain**: Delete `models/isolation_forest.pkl` and restart

---

## Understanding Anomaly Scores

The Isolation Forest returns a **decision function score**:

| Score Range | Meaning | Action |
|-------------|---------|--------|
| > 0 | Normal (inside the learned distribution) | No action |
| Around 0 | Borderline | Monitor closely |
| < 0 | Anomalous (outside the learned distribution) | Investigate |
| < -0.3 | Highly anomalous | Urgent investigation |

The model classifies readings with score < 0 (approximately) as anomalies, based on the contamination parameter.

---

## Summary

This ML system transforms your sensor pipeline from a simple data collector into an intelligent monitoring system that:

1. **Learns** what normal looks like from your actual data
2. **Detects** subtle anomalies across all 50 sensors simultaneously
3. **Analyzes** the context around anomalies (before/after readings)
4. **Correlates** sensor parameters to identify patterns
5. **Explains** anomalies in plain English using ChatGPT
6. **Recommends** actions to prevent future issues

All of this happens automatically after you collect enough baseline data, with no manual threshold configuration required.

