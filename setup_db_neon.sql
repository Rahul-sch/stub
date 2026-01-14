-- =============================================================================
-- Enhanced Sensor Data Pipeline Database Schema
-- 50 sensor parameters across 5 categories
-- =============================================================================

-- Create sensor_readings table with all 50 parameters
CREATE TABLE IF NOT EXISTS sensor_readings (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,

    -- ENVIRONMENTAL SENSORS (10)
    temperature FLOAT NOT NULL,
    pressure FLOAT NOT NULL,
    humidity FLOAT NOT NULL,
    ambient_temp FLOAT,
    dew_point FLOAT,
    air_quality_index INT,
    co2_level INT,
    particle_count INT,
    noise_level INT,
    light_intensity INT,

    -- MECHANICAL SENSORS (10)
    vibration FLOAT NOT NULL,
    rpm FLOAT NOT NULL,
    torque INT,
    shaft_alignment FLOAT,
    bearing_temp INT,
    motor_current INT,
    belt_tension INT,
    gear_wear INT,
    coupling_temp INT,
    lubrication_pressure INT,

    -- THERMAL SENSORS (10)
    coolant_temp INT,
    exhaust_temp INT,
    oil_temp INT,
    radiator_temp INT,
    thermal_efficiency INT,
    heat_dissipation INT,
    inlet_temp INT,
    outlet_temp INT,
    core_temp INT,
    surface_temp INT,

    -- ELECTRICAL SENSORS (10)
    voltage INT,
    current INT,
    power_factor FLOAT,
    frequency FLOAT,
    resistance FLOAT,
    capacitance INT,
    inductance FLOAT,
    phase_angle INT,
    harmonic_distortion INT,
    ground_fault INT,

    -- FLUID DYNAMICS SENSORS (10)
    flow_rate INT,
    fluid_pressure INT,
    viscosity INT,
    density FLOAT,
    reynolds_number INT,
    pipe_pressure_drop INT,
    pump_efficiency INT,
    cavitation_index INT,
    turbulence INT,
    valve_position INT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for optimized queries
CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_readings(timestamp);
CREATE INDEX IF NOT EXISTS idx_created_at ON sensor_readings(created_at);
CREATE INDEX IF NOT EXISTS idx_rpm ON sensor_readings(rpm);
CREATE INDEX IF NOT EXISTS idx_temperature ON sensor_readings(temperature);

-- Create view for quick statistics (all 50 parameters)
CREATE OR REPLACE VIEW sensor_stats AS
SELECT
    COUNT(*) as total_readings,
    MIN(timestamp) as first_reading,
    MAX(timestamp) as last_reading,
    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) / 3600 as duration_hours,

    -- Environmental averages
    AVG(temperature)::NUMERIC(10,2) as avg_temperature,
    AVG(pressure)::NUMERIC(10,2) as avg_pressure,
    AVG(humidity)::NUMERIC(10,2) as avg_humidity,
    AVG(ambient_temp)::NUMERIC(10,2) as avg_ambient_temp,
    AVG(dew_point)::NUMERIC(10,2) as avg_dew_point,
    AVG(air_quality_index)::NUMERIC(10,2) as avg_air_quality_index,
    AVG(co2_level)::NUMERIC(10,2) as avg_co2_level,

    -- Mechanical averages
    AVG(vibration)::NUMERIC(10,2) as avg_vibration,
    AVG(rpm)::NUMERIC(10,2) as avg_rpm,
    AVG(torque)::NUMERIC(10,2) as avg_torque,
    AVG(bearing_temp)::NUMERIC(10,2) as avg_bearing_temp,
    AVG(motor_current)::NUMERIC(10,2) as avg_motor_current,

    -- Thermal averages
    AVG(coolant_temp)::NUMERIC(10,2) as avg_coolant_temp,
    AVG(exhaust_temp)::NUMERIC(10,2) as avg_exhaust_temp,
    AVG(oil_temp)::NUMERIC(10,2) as avg_oil_temp,
    AVG(thermal_efficiency)::NUMERIC(10,2) as avg_thermal_efficiency,

    -- Electrical averages
    AVG(voltage)::NUMERIC(10,2) as avg_voltage,
    AVG(current)::NUMERIC(10,2) as avg_current,
    AVG(power_factor)::NUMERIC(10,3) as avg_power_factor,
    AVG(frequency)::NUMERIC(10,3) as avg_frequency,

    -- Fluid averages
    AVG(flow_rate)::NUMERIC(10,2) as avg_flow_rate,
    AVG(fluid_pressure)::NUMERIC(10,2) as avg_fluid_pressure,
    AVG(pump_efficiency)::NUMERIC(10,2) as avg_pump_efficiency,
    AVG(valve_position)::NUMERIC(10,2) as avg_valve_position
FROM sensor_readings;

-- Grant permissions to sensoruser
-- GRANT removed for Neon compatibility
-- GRANT removed for Neon compatibility
-- GRANT removed for Neon compatibility

-- Store pipeline alerts (anomalies, heartbeat failures, etc.)
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(64) NOT NULL,
    source VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type);

-- GRANT removed for Neon compatibility
-- GRANT removed for Neon compatibility

-- =============================================================================
-- ML Anomaly Detection Tables
-- =============================================================================

-- Store ML-detected anomalies with scores
CREATE TABLE IF NOT EXISTS anomaly_detections (
    id SERIAL PRIMARY KEY,
    reading_id INT REFERENCES sensor_readings(id) ON DELETE CASCADE,
    detection_method VARCHAR(32) NOT NULL, -- 'isolation_forest' or 'lstm_autoencoder'
    anomaly_score FLOAT NOT NULL,
    is_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    detected_sensors TEXT[], -- which sensors contributed to the anomaly
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anomaly_detections_reading ON anomaly_detections(reading_id);
CREATE INDEX IF NOT EXISTS idx_anomaly_detections_created ON anomaly_detections(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_detections_is_anomaly ON anomaly_detections(is_anomaly);

-- GRANT removed for Neon compatibility
-- GRANT removed for Neon compatibility

-- Store ChatGPT-generated analysis reports
CREATE TABLE IF NOT EXISTS analysis_reports (
    id SERIAL PRIMARY KEY,
    anomaly_id INT REFERENCES anomaly_detections(id) ON DELETE CASCADE,
    context_data JSONB, -- 10 readings before/after
    correlations JSONB, -- parameter correlations
    chatgpt_analysis TEXT,
    root_cause TEXT,
    prevention_recommendations TEXT,
    status VARCHAR(32) DEFAULT 'pending', -- 'pending', 'generating', 'completed', 'failed'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_analysis_reports_anomaly ON analysis_reports(anomaly_id);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_status ON analysis_reports(status);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_created ON analysis_reports(created_at DESC);

-- GRANT removed for Neon compatibility
-- GRANT removed for Neon compatibility
