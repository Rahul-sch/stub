-- Create sensor_readings table
CREATE TABLE IF NOT EXISTS sensor_readings (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    temperature FLOAT NOT NULL,
    pressure FLOAT NOT NULL,
    vibration FLOAT NOT NULL,
    humidity FLOAT NOT NULL,
    rpm FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for optimized queries
CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_readings(timestamp);
CREATE INDEX IF NOT EXISTS idx_created_at ON sensor_readings(created_at);

-- Add constraints for data quality
ALTER TABLE sensor_readings
    DROP CONSTRAINT IF EXISTS chk_temperature,
    DROP CONSTRAINT IF EXISTS chk_pressure,
    DROP CONSTRAINT IF EXISTS chk_vibration,
    DROP CONSTRAINT IF EXISTS chk_humidity,
    DROP CONSTRAINT IF EXISTS chk_rpm;

ALTER TABLE sensor_readings
    ADD CONSTRAINT chk_temperature CHECK (temperature >= 60 AND temperature <= 100),
    ADD CONSTRAINT chk_pressure CHECK (pressure >= 0 AND pressure <= 15),
    ADD CONSTRAINT chk_vibration CHECK (vibration >= 0 AND vibration <= 10),
    ADD CONSTRAINT chk_humidity CHECK (humidity >= 20 AND humidity <= 80),
    ADD CONSTRAINT chk_rpm CHECK (rpm >= 1000 AND rpm <= 5000);

-- Create view for quick statistics
CREATE OR REPLACE VIEW sensor_stats AS
SELECT
    COUNT(*) as total_readings,
    MIN(timestamp) as first_reading,
    MAX(timestamp) as last_reading,
    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) / 3600 as duration_hours,
    AVG(temperature)::NUMERIC(10,2) as avg_temperature,
    AVG(pressure)::NUMERIC(10,2) as avg_pressure,
    AVG(vibration)::NUMERIC(10,2) as avg_vibration,
    AVG(humidity)::NUMERIC(10,2) as avg_humidity,
    AVG(rpm)::NUMERIC(10,2) as avg_rpm
FROM sensor_readings;

-- Grant permissions to sensoruser
GRANT ALL PRIVILEGES ON TABLE sensor_readings TO sensoruser;
GRANT ALL PRIVILEGES ON SEQUENCE sensor_readings_id_seq TO sensoruser;
GRANT SELECT ON sensor_stats TO sensoruser;
