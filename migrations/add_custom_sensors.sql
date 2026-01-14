-- =============================================================================
-- Custom Sensor Parameters Migration
-- Adds support for dynamic custom sensor parameters at runtime
-- Phase 1: Database Foundation
-- =============================================================================

-- Create custom_sensors table - Metadata registry for custom sensors
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

-- Create indexes for custom_sensors table
CREATE INDEX IF NOT EXISTS idx_custom_sensors_name ON custom_sensors(sensor_name);
CREATE INDEX IF NOT EXISTS idx_custom_sensors_category ON custom_sensors(category);
CREATE INDEX IF NOT EXISTS idx_custom_sensors_active ON custom_sensors(is_active);
CREATE INDEX IF NOT EXISTS idx_custom_sensors_updated ON custom_sensors(updated_at);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE custom_sensors TO sensoruser;
GRANT ALL PRIVILEGES ON SEQUENCE custom_sensors_id_seq TO sensoruser;

-- Create machine_sensor_config table - Machine-specific sensor settings
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

-- Create indexes for machine_sensor_config table
CREATE INDEX IF NOT EXISTS idx_machine_sensor_config_machine ON machine_sensor_config(machine_id);
CREATE INDEX IF NOT EXISTS idx_machine_sensor_config_sensor ON machine_sensor_config(sensor_name);
CREATE INDEX IF NOT EXISTS idx_machine_sensor_config_enabled ON machine_sensor_config(enabled);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE machine_sensor_config TO sensoruser;
GRANT ALL PRIVILEGES ON SEQUENCE machine_sensor_config_id_seq TO sensoruser;

-- Add custom_sensors JSONB column to sensor_readings table
ALTER TABLE sensor_readings 
ADD COLUMN IF NOT EXISTS custom_sensors JSONB DEFAULT '{}'::jsonb;

-- Create GIN index on custom_sensors JSONB column for efficient queries
CREATE INDEX IF NOT EXISTS idx_sensor_readings_custom_sensors 
ON sensor_readings USING GIN (custom_sensors);

-- Create function to update updated_at timestamp for custom_sensors
CREATE OR REPLACE FUNCTION update_custom_sensors_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
DROP TRIGGER IF EXISTS trigger_update_custom_sensors_updated_at ON custom_sensors;
CREATE TRIGGER trigger_update_custom_sensors_updated_at
    BEFORE UPDATE ON custom_sensors
    FOR EACH ROW
    EXECUTE FUNCTION update_custom_sensors_updated_at();

-- Create function to update updated_at timestamp for machine_sensor_config
CREATE OR REPLACE FUNCTION update_machine_sensor_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
DROP TRIGGER IF EXISTS trigger_update_machine_sensor_config_updated_at ON machine_sensor_config;
CREATE TRIGGER trigger_update_machine_sensor_config_updated_at
    BEFORE UPDATE ON machine_sensor_config
    FOR EACH ROW
    EXECUTE FUNCTION update_machine_sensor_config_updated_at();

