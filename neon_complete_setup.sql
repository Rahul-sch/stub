-- =============================================================================
-- COMPLETE DATABASE SETUP FOR NEON
-- Paste this entire script into Neon SQL Editor
-- =============================================================================

-- =============================================================================
-- 1. USER AUTHENTICATION TABLES (must be first - other tables reference users)
-- =============================================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(16) NOT NULL DEFAULT 'operator' CHECK (role IN ('admin', 'operator')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- User machine access (which machines each user can access)
CREATE TABLE IF NOT EXISTS user_machine_access (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    machine_id VARCHAR(1) NOT NULL CHECK (machine_id IN ('A', 'B', 'C')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, machine_id)
);

-- Create indexes for users
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_user_machine_access_user ON user_machine_access(user_id);
CREATE INDEX IF NOT EXISTS idx_user_machine_access_machine ON user_machine_access(machine_id);

-- Create function to update updated_at timestamp for users
CREATE OR REPLACE FUNCTION update_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
DROP TRIGGER IF EXISTS trigger_update_users_updated_at ON users;
CREATE TRIGGER trigger_update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_users_updated_at();

-- =============================================================================
-- 2. SENSOR READINGS TABLE (main data table)
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

    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Custom sensors stored as JSONB
    custom_sensors JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for sensor_readings
CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_readings(timestamp);
CREATE INDEX IF NOT EXISTS idx_created_at ON sensor_readings(created_at);
CREATE INDEX IF NOT EXISTS idx_rpm ON sensor_readings(rpm);
CREATE INDEX IF NOT EXISTS idx_temperature ON sensor_readings(temperature);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_custom_sensors ON sensor_readings USING GIN (custom_sensors);

-- Create view for quick statistics
CREATE OR REPLACE VIEW sensor_stats AS
SELECT
    COUNT(*) as total_readings,
    MIN(timestamp) as first_reading,
    MAX(timestamp) as last_reading,
    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) / 3600 as duration_hours,
    AVG(temperature)::NUMERIC(10,2) as avg_temperature,
    AVG(pressure)::NUMERIC(10,2) as avg_pressure,
    AVG(humidity)::NUMERIC(10,2) as avg_humidity,
    AVG(vibration)::NUMERIC(10,2) as avg_vibration,
    AVG(rpm)::NUMERIC(10,2) as avg_rpm
FROM sensor_readings;

-- =============================================================================
-- 3. ALERTS TABLE
-- =============================================================================

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

-- =============================================================================
-- 4. ML ANOMALY DETECTION TABLES
-- =============================================================================

CREATE TABLE IF NOT EXISTS anomaly_detections (
    id SERIAL PRIMARY KEY,
    reading_id INT REFERENCES sensor_readings(id) ON DELETE CASCADE,
    detection_method VARCHAR(32) NOT NULL,
    anomaly_score FLOAT NOT NULL,
    is_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    detected_sensors TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anomaly_detections_reading ON anomaly_detections(reading_id);
CREATE INDEX IF NOT EXISTS idx_anomaly_detections_created ON anomaly_detections(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_detections_is_anomaly ON anomaly_detections(is_anomaly);

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

CREATE INDEX IF NOT EXISTS idx_analysis_reports_anomaly ON analysis_reports(anomaly_id);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_status ON analysis_reports(status);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_created ON analysis_reports(created_at DESC);

-- =============================================================================
-- 5. CUSTOM SENSORS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS custom_sensors (
    id SERIAL PRIMARY KEY,
    sensor_name VARCHAR(64) UNIQUE NOT NULL,
    category VARCHAR(32) DEFAULT 'custom',
    unit VARCHAR(16),
    min_range FLOAT NOT NULL,
    max_range FLOAT NOT NULL,
    low_threshold FLOAT,
    high_threshold FLOAT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_custom_sensors_name ON custom_sensors(sensor_name);
CREATE INDEX IF NOT EXISTS idx_custom_sensors_category ON custom_sensors(category);
CREATE INDEX IF NOT EXISTS idx_custom_sensors_active ON custom_sensors(is_active);
CREATE INDEX IF NOT EXISTS idx_custom_sensors_updated ON custom_sensors(updated_at);

CREATE TABLE IF NOT EXISTS machine_sensor_config (
    id SERIAL PRIMARY KEY,
    machine_id VARCHAR(1) NOT NULL,
    sensor_name VARCHAR(64) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    baseline FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(machine_id, sensor_name)
);

CREATE INDEX IF NOT EXISTS idx_machine_sensor_config_machine ON machine_sensor_config(machine_id);
CREATE INDEX IF NOT EXISTS idx_machine_sensor_config_sensor ON machine_sensor_config(sensor_name);
CREATE INDEX IF NOT EXISTS idx_machine_sensor_config_enabled ON machine_sensor_config(enabled);

-- Functions for custom_sensors
CREATE OR REPLACE FUNCTION update_custom_sensors_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_custom_sensors_updated_at ON custom_sensors;
CREATE TRIGGER trigger_update_custom_sensors_updated_at
    BEFORE UPDATE ON custom_sensors
    FOR EACH ROW
    EXECUTE FUNCTION update_custom_sensors_updated_at();

CREATE OR REPLACE FUNCTION update_machine_sensor_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_machine_sensor_config_updated_at ON machine_sensor_config;
CREATE TRIGGER trigger_update_machine_sensor_config_updated_at
    BEFORE UPDATE ON machine_sensor_config
    FOR EACH ROW
    EXECUTE FUNCTION update_machine_sensor_config_updated_at();

-- =============================================================================
-- 6. AUDIT LOGS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_logs_v2 (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
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

CREATE INDEX IF NOT EXISTS idx_audit_v2_timestamp ON audit_logs_v2(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_v2_user_id ON audit_logs_v2(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_v2_action_type ON audit_logs_v2(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_v2_resource_type ON audit_logs_v2(resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_v2_resource_id ON audit_logs_v2(resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_v2_previous_state ON audit_logs_v2 USING GIN (previous_state);
CREATE INDEX IF NOT EXISTS idx_audit_v2_new_state ON audit_logs_v2 USING GIN (new_state);

-- =============================================================================
-- COMPLETE!
-- =============================================================================
-- All tables created. You can now run producer.py and consumer.py
-- =============================================================================
