-- =============================================================================
-- Frequency Control Migration
-- Adds per-sensor frequency control (global + per-machine override)
-- Phase 1: Database Foundation
-- =============================================================================

-- Add frequency_seconds to machine_sensor_config (machine-specific override)
ALTER TABLE machine_sensor_config 
ADD COLUMN IF NOT EXISTS frequency_seconds INTEGER;

-- Add default_frequency_seconds to custom_sensors (global default for custom sensors)
ALTER TABLE custom_sensors 
ADD COLUMN IF NOT EXISTS default_frequency_seconds INTEGER;

-- Create global_sensor_config table for built-in sensors (global defaults)
CREATE TABLE IF NOT EXISTS global_sensor_config (
    id SERIAL PRIMARY KEY,
    sensor_name VARCHAR(64) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    default_frequency_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for global_sensor_config
CREATE INDEX IF NOT EXISTS idx_global_sensor_config_name ON global_sensor_config(sensor_name);
CREATE INDEX IF NOT EXISTS idx_global_sensor_config_enabled ON global_sensor_config(enabled);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE global_sensor_config TO sensoruser;
GRANT ALL PRIVILEGES ON SEQUENCE global_sensor_config_id_seq TO sensoruser;

-- Create function to update updated_at timestamp for global_sensor_config
CREATE OR REPLACE FUNCTION update_global_sensor_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
DROP TRIGGER IF EXISTS trigger_update_global_sensor_config_updated_at ON global_sensor_config;
CREATE TRIGGER trigger_update_global_sensor_config_updated_at
    BEFORE UPDATE ON global_sensor_config
    FOR EACH ROW
    EXECUTE FUNCTION update_global_sensor_config_updated_at();

