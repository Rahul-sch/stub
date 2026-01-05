# Sensor Data Pipeline - Comprehensive UML Diagrams & Architecture Documentation

> **Render these diagrams** using any Mermaid-compatible viewer (VS Code Mermaid extension, mermaid.live, GitHub, etc.)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Component Diagram](#3-component-diagram)
4. [Data Flow Diagram](#4-data-flow-diagram)
5. [Sequence Diagrams](#5-sequence-diagrams)
6. [Class Diagrams](#6-class-diagrams)
7. [Database Schema (ERD)](#7-database-schema-erd)
8. [Deployment Diagram](#8-deployment-diagram)
9. [State Machine Diagrams](#9-state-machine-diagrams)
10. [Activity Diagrams](#10-activity-diagrams)
11. [Package/Module Structure](#11-packagemodule-structure)

---

## 1. System Overview

### What is this project?

The **Sensor Data Pipeline** is a real-time industrial monitoring system that:

- **Generates** simulated sensor data (50 parameters across 5 categories)
- **Streams** data through Apache Kafka for reliable message delivery
- **Stores** readings in PostgreSQL for persistence and analysis
- **Detects** anomalies using ML (Isolation Forest algorithm)
- **Analyzes** patterns with context-aware correlation analysis
- **Reports** insights via AI-powered analysis (Groq/LLaMA)
- **Visualizes** everything through a modern web dashboard

### Key Technologies

| Layer                | Technology                                            |
| -------------------- | ----------------------------------------------------- |
| **Message Broker**   | Apache Kafka (with Zookeeper)                         |
| **Database**         | PostgreSQL 15                                         |
| **Backend**          | Python 3.13, Flask                                    |
| **ML/AI**            | scikit-learn (Isolation Forest), Groq API (LLaMA 3.3) |
| **Frontend**         | Vanilla HTML/CSS/JS with modern UI                    |
| **Containerization** | Docker Compose                                        |

### Sensor Categories (50 Parameters)

| Category          | Parameters                                                                                                                                        | Count |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| 🌍 Environmental  | temperature, pressure, humidity, ambient_temp, dew_point, air_quality_index, co2_level, particle_count, noise_level, light_intensity              | 10    |
| ⚙️ Mechanical     | vibration, rpm, torque, shaft_alignment, bearing_temp, motor_current, belt_tension, gear_wear, coupling_temp, lubrication_pressure                | 10    |
| 🔥 Thermal        | coolant_temp, exhaust_temp, oil_temp, radiator_temp, thermal_efficiency, heat_dissipation, inlet_temp, outlet_temp, core_temp, surface_temp       | 10    |
| ⚡ Electrical     | voltage, current, power_factor, frequency, resistance, capacitance, inductance, phase_angle, harmonic_distortion, ground_fault                    | 10    |
| 💧 Fluid Dynamics | flow_rate, fluid_pressure, viscosity, density, reynolds_number, pipe_pressure_drop, pump_efficiency, cavitation_index, turbulence, valve_position | 10    |

---

## 2. High-Level Architecture

```mermaid
flowchart TB
    subgraph UserLayer["👤 User Interface Layer"]
        Browser["Web Browser"]
        Dashboard["Flask Dashboard<br/>dashboard.py"]
    end

    subgraph ApplicationLayer["🔧 Application Layer"]
        Producer["SensorDataProducer<br/>producer.py"]
        Consumer["SensorDataConsumer<br/>consumer.py"]
        MLDetector["AnomalyDetector<br/>ml_detector.py"]
        Analyzer["ContextAnalyzer<br/>analysis_engine.py"]
        Reporter["ReportGenerator<br/>report_generator.py"]
    end

    subgraph MessagingLayer["📨 Messaging Layer"]
        Kafka["Apache Kafka<br/>sensor-data topic"]
        Zookeeper["Zookeeper<br/>Coordination"]
    end

    subgraph DataLayer["💾 Data Layer"]
        PostgreSQL["PostgreSQL<br/>sensordb"]
        ModelStore["Model Storage<br/>isolation_forest.pkl"]
    end

    subgraph ExternalServices["🌐 External Services"]
        GroqAPI["Groq API<br/>LLaMA 3.3-70B"]
    end

    Browser <-->|HTTP/REST| Dashboard
    Dashboard -->|subprocess| Producer
    Dashboard -->|subprocess| Consumer
    Dashboard <-->|SQL queries| PostgreSQL
    Dashboard -->|heartbeat| Kafka

    Producer -->|publish| Kafka
    Kafka -->|consume| Consumer

    Consumer -->|INSERT| PostgreSQL
    Consumer -->|detect| MLDetector

    MLDetector -->|load/save| ModelStore
    MLDetector -->|training data| PostgreSQL
    MLDetector -->|INSERT anomaly| PostgreSQL

    Analyzer <-->|context queries| PostgreSQL
    Reporter -->|analysis request| GroqAPI
    Reporter -->|store report| PostgreSQL
    Reporter <-->|get context| Analyzer

    Zookeeper -.->|coordinates| Kafka
```

---

## 3. Component Diagram

```mermaid
graph LR
    subgraph Operator_Machine["🖥️ Operator Machine"]
        subgraph Dashboard_Component["Dashboard Component"]
            FlaskApp["Flask App<br/>(dashboard.py)"]
            Templates["HTML Templates<br/>(dashboard.html)"]
            StaticJS["JavaScript<br/>(Embedded)"]
        end

        subgraph Pipeline_Processes["Pipeline Processes"]
            ProducerProc["Producer Process<br/>(producer.py)"]
            ConsumerProc["Consumer Process<br/>(consumer.py)"]
        end

        subgraph ML_Components["ML Components"]
            IsolationForest["Isolation Forest<br/>(ml_detector.py)"]
            ContextEngine["Context Analyzer<br/>(analysis_engine.py)"]
            AIReporter["Report Generator<br/>(report_generator.py)"]
        end

        Config["Configuration<br/>(config.py)"]
    end

    subgraph Docker_Stack["🐳 Docker Compose Stack"]
        KafkaBroker["Kafka Broker<br/>:9092"]
        ZK["Zookeeper<br/>:2181"]
        PG["PostgreSQL<br/>:5432"]
    end

    subgraph Cloud_Services["☁️ Cloud Services"]
        Groq["Groq API<br/>(LLaMA 3.3)"]
    end

    FlaskApp --> Templates
    FlaskApp --> StaticJS
    FlaskApp -->|manage| ProducerProc
    FlaskApp -->|manage| ConsumerProc
    FlaskApp -->|query| PG
    FlaskApp -->|heartbeat| KafkaBroker

    ProducerProc -->|publish| KafkaBroker
    ProducerProc -->|read| Config
    ProducerProc -->|injection settings| FlaskApp

    ConsumerProc -->|subscribe| KafkaBroker
    ConsumerProc -->|write| PG
    ConsumerProc -->|detect| IsolationForest
    ConsumerProc -->|read| Config

    IsolationForest -->|train/query| PG
    ContextEngine -->|analyze| PG
    AIReporter -->|get context| ContextEngine
    AIReporter -->|AI analysis| Groq
    AIReporter -->|store report| PG

    ZK -.->|coordinate| KafkaBroker
```

---

## 4. Data Flow Diagram

```mermaid
flowchart LR
    subgraph Generation["Data Generation"]
        SensorSim["Sensor Simulator<br/>(Correlated Values)"]
        AnomalyInject["Anomaly Injector<br/>(Optional)"]
    end

    subgraph Streaming["Message Streaming"]
        KafkaTopic["sensor-data<br/>Kafka Topic"]
    end

    subgraph Processing["Data Processing"]
        Validation["Message Validation"]
        RuleCheck["Rule-Based<br/>Anomaly Check"]
        DBInsert["Database Insert"]
        MLCheck["ML Anomaly<br/>Detection"]
    end

    subgraph Storage["Data Storage"]
        Readings["sensor_readings<br/>Table"]
        Anomalies["anomaly_detections<br/>Table"]
        Reports["analysis_reports<br/>Table"]
        Alerts["alerts<br/>Table"]
    end

    subgraph Analysis["Analysis & Reporting"]
        Context["Context Window<br/>Extraction"]
        Correlation["Correlation<br/>Analysis"]
        AIAnalysis["AI Report<br/>Generation"]
    end

    subgraph Presentation["Presentation"]
        StatsAPI["Stats API"]
        AnomalyAPI["Anomaly API"]
        ReportAPI["Report API"]
        DashboardUI["Dashboard UI"]
    end

    SensorSim --> AnomalyInject
    AnomalyInject -->|JSON message| KafkaTopic

    KafkaTopic --> Validation
    Validation -->|valid| RuleCheck
    Validation -->|invalid| Alerts

    RuleCheck -->|normal| DBInsert
    RuleCheck -->|out of range| Alerts

    DBInsert --> Readings
    DBInsert --> MLCheck

    MLCheck -->|is_anomaly=true| Anomalies
    MLCheck -->|score| Anomalies

    Anomalies --> Context
    Context --> Correlation
    Correlation --> AIAnalysis
    AIAnalysis --> Reports

    Readings --> StatsAPI
    Anomalies --> AnomalyAPI
    Reports --> ReportAPI
    Alerts --> DashboardUI

    StatsAPI --> DashboardUI
    AnomalyAPI --> DashboardUI
    ReportAPI --> DashboardUI
```

---

## 5. Sequence Diagrams

### 5.1 Complete Pipeline Flow

```mermaid
sequenceDiagram
    actor Operator
    participant UI as Dashboard UI
    participant API as Flask API
    participant Producer as SensorDataProducer
    participant Kafka as Kafka Broker
    participant Consumer as SensorDataConsumer
    participant ML as AnomalyDetector
    participant DB as PostgreSQL
    participant Groq as Groq AI API

    Note over Operator,DB: === STARTUP PHASE ===

    Operator->>UI: Open Dashboard
    UI->>API: GET /
    API->>UI: Render dashboard.html

    Operator->>UI: Click "Start Consumer"
    UI->>API: GET /api/start/consumer
    API->>Consumer: subprocess.Popen()
    Consumer->>Kafka: Subscribe to 'sensor-data'
    Consumer->>DB: Open connection
    API->>UI: {success: true, pid: X}

    Operator->>UI: Click "Start Producer"
    UI->>API: GET /api/start/producer
    API->>Producer: subprocess.Popen()
    Producer->>Kafka: Connect to broker
    API->>UI: {success: true, pid: Y}

    Note over Operator,DB: === DATA FLOW LOOP ===

    loop Every INTERVAL_SECONDS
        Producer->>API: GET /api/injection-settings
        API->>Producer: {inject_now: bool, thresholds: {...}}

        alt Normal Reading
            Producer->>Producer: generate_sensor_reading()
        else Inject Anomaly
            Producer->>Producer: generate_anomalous_reading()
        end

        Producer->>Kafka: Publish JSON message
        Kafka->>Consumer: Deliver message

        Consumer->>Consumer: validate_message()
        Consumer->>Consumer: detect_anomalies() [Rule-based]

        alt Values in range
            Consumer->>DB: INSERT sensor_readings
            DB->>Consumer: RETURNING id

            Consumer->>ML: detect(reading)
            ML->>ML: _reading_to_features()
            ML->>ML: model.predict()

            alt Is Anomaly
                ML->>DB: INSERT anomaly_detections
                Consumer->>DB: INSERT alerts
            end

            Consumer->>Kafka: commit offset
        else Values out of range
            Consumer->>DB: INSERT alerts
            Consumer->>Kafka: commit offset
        end
    end

    Note over Operator,DB: === DASHBOARD POLLING ===

    loop Every 2 seconds
        UI->>API: GET /api/stats
        API->>DB: SELECT aggregates
        DB->>API: Results
        API->>UI: JSON stats

        UI->>API: GET /api/status
        API->>Kafka: Check connection
        API->>UI: {producer_running, consumer_running, kafka}

        UI->>API: GET /api/anomalies
        API->>DB: SELECT from anomaly_detections
        DB->>API: Results
        API->>UI: JSON anomalies
    end

    Note over Operator,DB: === REPORT GENERATION ===

    Operator->>UI: Click "Generate Report"
    UI->>API: POST /api/generate-report/{anomaly_id}
    API->>DB: Get anomaly details
    API->>DB: Get context window (10 before/after)
    API->>API: Compute correlations
    API->>Groq: POST chat/completions (prompt)
    Groq->>API: AI analysis response
    API->>DB: INSERT analysis_reports
    API->>UI: {success: true, report: {...}}
```

### 5.2 ML Training & Detection Flow

```mermaid
sequenceDiagram
    participant Consumer
    participant Detector as AnomalyDetector
    participant Scaler as StandardScaler
    participant Model as IsolationForest
    participant DB as PostgreSQL
    participant Disk as Model Storage

    Note over Consumer,Disk: === MODEL INITIALIZATION ===

    Consumer->>Detector: get_detector()
    Detector->>Disk: Check for isolation_forest.pkl

    alt Model Exists
        Disk->>Detector: Load saved model
        Detector->>Detector: is_trained = True
    else No Model
        Detector->>Detector: is_trained = False
    end

    Note over Consumer,Disk: === DETECTION CALL ===

    Consumer->>Detector: detect(reading)

    alt Not Trained
        Detector->>DB: SELECT last 1000 readings
        DB->>Detector: DataFrame
        Detector->>Scaler: fit_transform(features)
        Detector->>Model: fit(scaled_data)
        Detector->>Disk: Save model + scaler
        Detector->>Detector: is_trained = True
    end

    Detector->>Detector: _reading_to_features(reading)
    Detector->>Scaler: transform(features)
    Detector->>Model: predict(scaled)
    Model->>Detector: prediction (-1=anomaly, 1=normal)
    Detector->>Model: decision_function(scaled)
    Model->>Detector: anomaly_score

    alt Is Anomaly (prediction == -1)
        Detector->>Detector: _identify_contributing_sensors()
        Note over Detector: Z-score analysis per sensor
    end

    Detector->>Consumer: (is_anomaly, score, sensors)
```

### 5.3 Full Session Report Generation

```mermaid
sequenceDiagram
    participant UI as Dashboard
    participant API as Flask
    participant Gen as FullSessionReportGenerator
    participant DB as PostgreSQL
    participant Groq as Groq AI

    UI->>API: POST /api/generate-full-report
    API->>Gen: generate_full_session_report()

    Gen->>DB: Get all session anomalies
    Note over DB: SELECT from anomaly_detections<br/>JOIN sensor_readings
    DB->>Gen: List of anomalies with readings

    Gen->>DB: Get session stats
    Note over DB: COUNT, AVG, severity distribution
    DB->>Gen: Stats dict

    Gen->>Gen: compute_cross_anomaly_correlations()
    Note over Gen: Sensor co-occurrence matrix<br/>Pattern detection

    Gen->>Gen: _build_full_session_prompt()
    Note over Gen: Format stats, top sensors,<br/>correlations for AI

    alt Groq API Available
        Gen->>Groq: POST /chat/completions
        Groq->>Gen: Comprehensive analysis
    else No API Key
        Gen->>Gen: _generate_fallback_full_report()
    end

    Gen->>API: {success, stats, correlations, analysis}
    API->>UI: JSON response
    UI->>UI: displayFullSessionReport()
```

---

## 6. Class Diagrams

### 6.1 Core Classes

```mermaid
classDiagram
    class Config {
        <<module>>
        +DURATION_HOURS: float
        +INTERVAL_SECONDS: int
        +KAFKA_BOOTSTRAP_SERVERS: str
        +KAFKA_TOPIC: str
        +KAFKA_PRODUCER_CONFIG: dict
        +KAFKA_CONSUMER_CONFIG: dict
        +DB_CONFIG: dict
        +SENSOR_RANGES: dict
        +SENSOR_THRESHOLDS: dict
        +SENSOR_CATEGORIES: dict
        +ML_DETECTION_ENABLED: bool
        +GROQ_API_KEY: str
        +AI_MODEL: str
    }

    class SensorDataProducer {
        -producer: KafkaProducer
        -message_count: int
        -total_messages: int
        -should_shutdown: bool
        -custom_thresholds: dict
        -logger: Logger
        +__init__()
        +setup_logging()
        +signal_handler(signum, frame)
        +connect_to_kafka() KafkaProducer
        +generate_sensor_reading() dict
        +generate_anomalous_reading() dict
        +check_injection_settings() bool
        +send_message(data) bool
        +run()
        +shutdown()
    }

    class SensorDataConsumer {
        -consumer: KafkaConsumer
        -db_conn: Connection
        -db_cursor: Cursor
        -message_count: int
        -should_shutdown: bool
        -logger: Logger
        +__init__()
        +setup_logging()
        +signal_handler(signum, frame)
        +connect_to_kafka() KafkaConsumer
        +connect_to_database() tuple
        +validate_message(data) bool
        +detect_anomalies(reading) list
        +record_alert(type, msg, severity)
        +insert_reading(reading) int
        +run_ml_detection(reading, id)
        +process_message(message) bool
        +run()
        +shutdown()
    }

    class AnomalyDetector {
        -model: IsolationForest
        -scaler: StandardScaler
        -is_trained: bool
        -feature_means: dict
        -feature_stds: dict
        -contamination: float
        -n_estimators: int
        -logger: Logger
        +SENSOR_COLUMNS: list
        +__init__(contamination, n_estimators)
        +_get_model_path() str
        +_load_model()
        +_save_model()
        +_fetch_training_data(limit) DataFrame
        +train(data) bool
        +_reading_to_features(reading) ndarray
        +_identify_contributing_sensors(reading) list
        +detect(reading) tuple
        +retrain_if_needed(min_samples) bool
    }

    class ContextAnalyzer {
        -window_size: int
        -logger: Logger
        +SENSOR_COLUMNS: list
        +SENSOR_CATEGORIES: dict
        +__init__(window_size)
        +get_context_window(reading_id) dict
        +compute_correlations(context, threshold) dict
        +identify_anomalous_patterns(context, sensors) dict
        +generate_analysis_summary(reading_id, sensors) dict
    }

    class ReportGenerator {
        -api_key: str
        -model: str
        -base_url: str
        -client: OpenAI
        -analyzer: ContextAnalyzer
        -logger: Logger
        +__init__(api_key)
        +_build_prompt(anomaly, summary) str
        +_call_ai(prompt) str
        +_classify_severity(analysis, score) str
        +generate_report(anomaly_id) dict
        +generate_and_save_report(anomaly_id) tuple
    }

    class FullSessionReportGenerator {
        -client: OpenAI
        -model: str
        -logger: Logger
        +__init__()
        +get_all_session_anomalies() list
        +get_session_stats() dict
        +compute_cross_anomaly_correlations(anomalies) dict
        +_build_full_session_prompt(stats, anomalies, corrs) str
        +generate_full_session_report() dict
        +_generate_fallback_full_report(stats, anomalies, corrs) str
    }

    SensorDataProducer --> Config : uses
    SensorDataConsumer --> Config : uses
    SensorDataConsumer --> AnomalyDetector : uses
    AnomalyDetector --> Config : uses
    ContextAnalyzer --> Config : uses
    ReportGenerator --> ContextAnalyzer : uses
    ReportGenerator --> Config : uses
    FullSessionReportGenerator --> Config : uses
```

### 6.2 Dashboard Controller (Flask Routes)

```mermaid
classDiagram
    class FlaskApp {
        <<Flask Application>>
        +processes: dict
        +kafka_health: dict
        +custom_thresholds: dict
        +injection_settings: dict
    }

    class Routes {
        <<API Endpoints>>
        +index() GET /
        +api_stats() GET /api/stats
        +api_alerts() GET /api/alerts
        +api_config() GET|POST /api/config
        +reset_config() POST /api/config/reset
        +start_component(name) GET /api/start/~name~
        +stop_component(name) GET /api/stop/~name~
        +api_status() GET /api/status
        +clear_data() GET /api/clear_data
        +api_anomalies() GET /api/anomalies
        +api_anomaly_detail(id) GET /api/anomalies/~id~
        +api_generate_report(id) POST /api/generate-report/~id~
        +api_get_report(id) GET /api/reports/~id~
        +api_get_thresholds() GET /api/thresholds
        +api_set_threshold() POST /api/thresholds
        +api_inject_anomaly_now() POST /api/inject-anomaly
        +export_data() GET /api/export
        +api_ml_stats() GET /api/ml-stats
        +api_generate_full_report() POST /api/generate-full-report
    }

    class HelperFunctions {
        <<Utility Functions>>
        +get_db_connection() Connection
        +record_alert(type, msg, severity)
        +get_alerts(limit) list
        +check_kafka_health()
        +heartbeat_worker()
        +start_kafka_monitor()
        +get_stats() dict
        +get_config() dict
        +update_config(hours, mins, interval) tuple
        +is_component_running(name) bool
    }

    FlaskApp --> Routes : defines
    Routes --> HelperFunctions : uses
```

---

## 7. Database Schema (ERD)

```mermaid
erDiagram
    sensor_readings {
        int id PK
        timestamptz timestamp
        float temperature
        float pressure
        float humidity
        float ambient_temp
        float dew_point
        int air_quality_index
        int co2_level
        int particle_count
        int noise_level
        int light_intensity
        float vibration
        float rpm
        int torque
        float shaft_alignment
        int bearing_temp
        int motor_current
        int belt_tension
        int gear_wear
        int coupling_temp
        int lubrication_pressure
        int coolant_temp
        int exhaust_temp
        int oil_temp
        int radiator_temp
        int thermal_efficiency
        int heat_dissipation
        int inlet_temp
        int outlet_temp
        int core_temp
        int surface_temp
        int voltage
        int current
        float power_factor
        float frequency
        float resistance
        int capacitance
        float inductance
        int phase_angle
        int harmonic_distortion
        int ground_fault
        int flow_rate
        int fluid_pressure
        int viscosity
        float density
        int reynolds_number
        int pipe_pressure_drop
        int pump_efficiency
        int cavitation_index
        int turbulence
        int valve_position
        timestamptz created_at
    }

    anomaly_detections {
        int id PK
        int reading_id FK
        varchar detection_method
        float anomaly_score
        boolean is_anomaly
        text_array detected_sensors
        timestamptz created_at
    }

    analysis_reports {
        int id PK
        int anomaly_id FK
        jsonb context_data
        jsonb correlations
        text chatgpt_analysis
        text root_cause
        text prevention_recommendations
        varchar status
        timestamptz created_at
        timestamptz completed_at
    }

    alerts {
        int id PK
        varchar alert_type
        varchar source
        varchar severity
        text message
        timestamptz created_at
    }

    sensor_stats {
        int total_readings
        timestamptz first_reading
        timestamptz last_reading
        float duration_hours
        float avg_temperature
        float avg_pressure
        float avg_humidity
        float avg_vibration
        float avg_rpm
    }

    sensor_readings ||--o{ anomaly_detections : "has many"
    anomaly_detections ||--o| analysis_reports : "has one"
```

---

## 8. Deployment Diagram

```mermaid
graph TB
    subgraph Development["💻 Development Machine"]
        subgraph VirtualEnv["Python Virtual Environment (venv)"]
            DashboardApp["dashboard.py<br/>Flask :5000"]
            ProducerApp["producer.py"]
            ConsumerApp["consumer.py"]
            MLModules["ML Modules<br/>(ml_detector, analysis_engine, report_generator)"]
        end

        subgraph ModelStorage["File System"]
            PKLFile["models/isolation_forest.pkl"]
            ConfigFile["config.py"]
        end

        Browser["Web Browser<br/>localhost:5000"]
    end

    subgraph DockerCompose["🐳 Docker Compose Network"]
        subgraph KafkaContainer["stub-kafka"]
            KafkaBroker["Kafka Broker<br/>:9092"]
        end

        subgraph ZKContainer["stub-zookeeper"]
            Zookeeper["Zookeeper<br/>:2181"]
        end

        subgraph PGContainer["stub-postgres"]
            PostgreSQL["PostgreSQL 15<br/>:5432<br/>sensordb"]
        end
    end

    subgraph Cloud["☁️ Cloud API"]
        GroqCloud["Groq Cloud<br/>api.groq.com"]
    end

    Browser <-->|HTTP| DashboardApp
    DashboardApp -->|spawn| ProducerApp
    DashboardApp -->|spawn| ConsumerApp
    DashboardApp <-->|SQL| PostgreSQL
    DashboardApp -->|health check| KafkaBroker

    ProducerApp -->|publish| KafkaBroker
    ProducerApp -->|read| ConfigFile

    ConsumerApp <-->|subscribe| KafkaBroker
    ConsumerApp -->|write| PostgreSQL
    ConsumerApp -->|detect| MLModules

    MLModules <-->|read/write| PKLFile
    MLModules <-->|train/query| PostgreSQL
    MLModules -->|AI request| GroqCloud

    Zookeeper -.->|coordinate| KafkaBroker

    style DockerCompose fill:#e1f5fe
    style VirtualEnv fill:#f3e5f5
    style Cloud fill:#fff3e0
```

---

## 9. State Machine Diagrams

### 9.1 Producer Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Initializing: main()

    Initializing --> ConnectingKafka: setup_logging()

    ConnectingKafka --> Connected: Success
    ConnectingKafka --> RetryWait: Failed
    RetryWait --> ConnectingKafka: retry < MAX_RETRIES
    RetryWait --> [*]: retry >= MAX_RETRIES

    Connected --> GeneratingData: enter main loop

    state GeneratingData {
        [*] --> CheckInjection
        CheckInjection --> NormalReading: inject=false
        CheckInjection --> AnomalousReading: inject=true
        NormalReading --> SendMessage
        AnomalousReading --> SendMessage
        SendMessage --> Sleep
        Sleep --> [*]
    }

    GeneratingData --> GeneratingData: time < end_time
    GeneratingData --> Completed: time >= end_time
    GeneratingData --> ShuttingDown: SIGINT/SIGTERM

    Completed --> ShuttingDown
    ShuttingDown --> [*]: flush & close
```

### 9.2 Consumer Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Initializing

    Initializing --> ConnectingKafka

    ConnectingKafka --> ConnectingDB: Kafka connected
    ConnectingKafka --> RetryKafka: Kafka failed
    RetryKafka --> ConnectingKafka: retry
    RetryKafka --> [*]: max retries

    ConnectingDB --> Ready: DB connected
    ConnectingDB --> RetryDB: DB failed
    RetryDB --> ConnectingDB: retry
    RetryDB --> [*]: max retries

    Ready --> Polling: Start consuming

    state Polling {
        [*] --> WaitForMessage
        WaitForMessage --> ProcessMessage: message received
        WaitForMessage --> WaitForMessage: timeout (1s)

        ProcessMessage --> Validate
        Validate --> RuleCheck: valid
        Validate --> Skip: invalid

        RuleCheck --> InsertDB: in range
        RuleCheck --> RecordAlert: out of range

        InsertDB --> MLDetection
        MLDetection --> CommitOffset
        RecordAlert --> CommitOffset
        Skip --> CommitOffset
        CommitOffset --> [*]
    }

    Polling --> Polling: !should_shutdown
    Polling --> ShuttingDown: should_shutdown

    ShuttingDown --> [*]: close connections
```

### 9.3 Anomaly Detection State

```mermaid
stateDiagram-v2
    [*] --> CheckModel

    CheckModel --> LoadModel: Model file exists
    CheckModel --> Untrained: No model file

    LoadModel --> Ready: Load successful
    LoadModel --> Untrained: Load failed

    Untrained --> FetchData: detect called
    FetchData --> CheckSamples

    CheckSamples --> Training: samples >= MIN_TRAINING_SAMPLES
    CheckSamples --> NoDetection: samples < MIN_TRAINING_SAMPLES

    Training --> SaveModel: Training complete
    SaveModel --> Ready

    NoDetection --> [*]: Return false

    Ready --> FeatureExtract: detect called
    FeatureExtract --> Scaling
    Scaling --> Predict
    Predict --> ScoreCalc
    ScoreCalc --> IdentifySensors: is_anomaly true
    ScoreCalc --> ReturnResult: is_anomaly false
    IdentifySensors --> ReturnResult

    ReturnResult --> [*]: Return result tuple
```

---

## 10. Activity Diagrams

### 10.1 Message Processing Flow

```mermaid
flowchart TD
    Start([Message Received]) --> Parse[Parse JSON]
    Parse --> ValidCheck{Valid Message?}

    ValidCheck -->|No| LogInvalid[Log Warning]
    LogInvalid --> Commit1[Commit Offset]
    Commit1 --> End1([Skip Message])

    ValidCheck -->|Yes| RuleCheck[Check Sensor Ranges]
    RuleCheck --> InRange{All Values In Range?}

    InRange -->|No| RecordAlert[Record Alert to DB]
    RecordAlert --> Commit2[Commit Offset]
    Commit2 --> End2([Alert Recorded])

    InRange -->|Yes| InsertDB[INSERT sensor_readings]
    InsertDB --> GetID[Get reading_id]
    GetID --> CommitDB[Commit Transaction]
    CommitDB --> MLEnabled{ML Detection Enabled?}

    MLEnabled -->|No| Commit3[Commit Offset]
    Commit3 --> End3([Reading Stored])

    MLEnabled -->|Yes| GetDetector[Get AnomalyDetector]
    GetDetector --> Trained{Model Trained?}

    Trained -->|No| TrainModel[Train on Historical Data]
    TrainModel --> SaveModel[Save Model to Disk]
    SaveModel --> Detect

    Trained -->|Yes| Detect[Run Detection]
    Detect --> IsAnomaly{Is Anomaly?}

    IsAnomaly -->|No| RecordNormal[Record Detection]
    RecordNormal --> Commit4[Commit Offset]
    Commit4 --> End4([Normal Reading])

    IsAnomaly -->|Yes| RecordAnomaly[Record Anomaly Detection]
    RecordAnomaly --> CreateAlert[Create ML Alert]
    CreateAlert --> LogAnomaly[Log Warning]
    LogAnomaly --> Commit5[Commit Offset]
    Commit5 --> End5([Anomaly Detected])
```

### 10.2 Report Generation Flow

```mermaid
flowchart TD
    Start([Generate Report Request]) --> GetAnomaly[Fetch Anomaly Details]
    GetAnomaly --> Found{Anomaly<br/>Found?}

    Found -->|No| Error1([Return 404 Error])

    Found -->|Yes| GetContext[Get Context Window]
    GetContext --> HasContext{Has Before/<br/>After Readings?}

    HasContext -->|No| Error2([Return Error])

    HasContext -->|Yes| ComputeCorr[Compute Correlations]
    ComputeCorr --> IdentifyPatterns[Identify Anomalous Patterns]
    IdentifyPatterns --> BuildPrompt[Build AI Prompt]

    BuildPrompt --> HasAPIKey{Groq API<br/>Configured?}

    HasAPIKey -->|No| Fallback[Generate Fallback Report]
    Fallback --> SaveReport

    HasAPIKey -->|Yes| CallAI[Call Groq API]
    CallAI --> AISuccess{API Call<br/>Successful?}

    AISuccess -->|No| FallbackAI[Generate Fallback Report]
    FallbackAI --> SaveReport

    AISuccess -->|Yes| ParseResponse[Parse AI Response]
    ParseResponse --> ClassifySeverity[Classify Severity]
    ClassifySeverity --> SaveReport[Save to analysis_reports]

    SaveReport --> ReturnReport([Return Report Data])
```

---

## 11. Package/Module Structure

```mermaid
flowchart TB
    subgraph Core["Core Modules"]
        config[config.py<br/>Settings & Constants]
        producer[producer.py<br/>SensorDataProducer]
        consumer[consumer.py<br/>SensorDataConsumer]
        dashboard[dashboard.py<br/>Flask Web Server]
    end

    subgraph ML["ML & AI Modules"]
        ml_detector[ml_detector.py<br/>Isolation Forest]
        analysis_engine[analysis_engine.py<br/>Context Analyzer]
        report_generator[report_generator.py<br/>AI Report Generator]
        lstm_detector[lstm_detector.py<br/>LSTM Autoencoder]
    end

    subgraph Frontend["Frontend"]
        dashboard_html[dashboard.html<br/>UI Template]
    end

    subgraph Infrastructure["Infrastructure"]
        setup_db[setup_db.sql<br/>DB Schema]
        docker_compose[docker-compose.yml<br/>Container Config]
        requirements[requirements.txt<br/>Dependencies]
    end

    producer --> config
    consumer --> config
    consumer --> ml_detector
    dashboard --> config
    dashboard --> report_generator
    dashboard --> analysis_engine
    dashboard --> dashboard_html
    ml_detector --> config
    analysis_engine --> config
    report_generator --> config
    report_generator --> analysis_engine
    lstm_detector --> config
```

---

## Quick Reference: File → Responsibility

| File                       | Primary Responsibility                                           |
| -------------------------- | ---------------------------------------------------------------- |
| `config.py`                | All configuration constants (timing, Kafka, DB, sensors, ML, AI) |
| `producer.py`              | Generate and publish sensor data to Kafka                        |
| `consumer.py`              | Consume from Kafka, validate, store, trigger ML detection        |
| `dashboard.py`             | Flask web server, REST APIs, process management                  |
| `ml_detector.py`           | Isolation Forest training and anomaly detection                  |
| `analysis_engine.py`       | Context analysis and correlation computation                     |
| `report_generator.py`      | AI-powered report generation via Groq                            |
| `lstm_detector.py`         | (Optional) LSTM Autoencoder for sequence anomalies               |
| `setup_db.sql`             | PostgreSQL schema definition                                     |
| `docker-compose.yml`       | Container orchestration for Kafka, Zookeeper, PostgreSQL         |
| `templates/dashboard.html` | Complete frontend UI with real-time updates                      |

---

## API Endpoint Summary

| Method | Endpoint                    | Description                         |
| ------ | --------------------------- | ----------------------------------- |
| GET    | `/`                         | Dashboard HTML page                 |
| GET    | `/api/stats`                | Current sensor statistics           |
| GET    | `/api/status`               | Producer/consumer/Kafka status      |
| GET    | `/api/alerts`               | Recent alert messages               |
| GET    | `/api/anomalies`            | ML-detected anomalies list          |
| GET    | `/api/anomalies/{id}`       | Specific anomaly details            |
| GET    | `/api/ml-stats`             | ML detection statistics             |
| GET    | `/api/config`               | Current configuration               |
| POST   | `/api/config`               | Update configuration                |
| POST   | `/api/config/reset`         | Reset to defaults                   |
| GET    | `/api/start/{component}`    | Start producer or consumer          |
| GET    | `/api/stop/{component}`     | Stop producer or consumer           |
| GET    | `/api/clear_data`           | Delete all sensor readings          |
| GET    | `/api/export`               | Export readings as CSV              |
| GET    | `/api/thresholds`           | Get custom thresholds               |
| POST   | `/api/thresholds`           | Set custom threshold                |
| POST   | `/api/inject-anomaly`       | Trigger immediate anomaly injection |
| POST   | `/api/generate-report/{id}` | Generate AI report for anomaly      |
| GET    | `/api/reports/{id}`         | Get generated report                |
| POST   | `/api/generate-full-report` | Generate full session report        |

---

_This document provides a comprehensive architectural view of the Sensor Data Pipeline. Use these diagrams for system understanding, onboarding, and design discussions._
