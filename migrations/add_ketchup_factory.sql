-- ============================================================================
-- KETCHUP FACTORY DIGITAL TWIN - DATABASE MIGRATION
-- ============================================================================
-- SAFE: Creates NEW tables only. Does NOT modify existing sensor_readings.
-- Run with: psql -d your_database -f add_ketchup_factory.sql
-- ============================================================================

-- -----------------------------------------------------------------------------
-- Table: sensor_readings_ketchup
-- Stores ketchup bottling line sensor data (parallel to sensor_readings)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sensor_readings_ketchup (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    timestamp VARCHAR(30) NOT NULL,
    line_id VARCHAR(10) NOT NULL,  -- L01-L25 (25 production lines)

    -- KETCHUP-SPECIFIC SENSORS (6 core params)
    fill_level FLOAT,              -- 0-100% bottle fill level
    viscosity FLOAT,               -- cP (centipoise) - sauce thickness
    sauce_temp FLOAT,              -- °F - sauce temperature in pipes
    cap_torque FLOAT,              -- Nm - cap tightening torque
    bottle_flow_rate FLOAT,        -- bottles/min throughput
    label_alignment FLOAT,         -- degrees offset from center (0 = perfect)

    -- QUALITY METRICS
    bottle_count INT DEFAULT 0,    -- Total bottles produced this session
    reject_count INT DEFAULT 0,    -- Rejected bottles (quality fails)
    efficiency FLOAT,              -- Line efficiency percentage

    -- ENVIRONMENTAL CONDITIONS
    ambient_temp FLOAT,            -- Factory ambient temperature °F
    humidity FLOAT,                -- Relative humidity %

    -- EQUIPMENT STATUS
    tank_level FLOAT,              -- Ketchup tank fill % (0-100)
    conveyor_speed FLOAT,          -- Belt speed m/s
    pump_pressure FLOAT,           -- Sauce pump pressure PSI

    -- ANOMALY TRACKING
    anomaly_score FLOAT DEFAULT 0, -- ML anomaly score (0-1)
    anomaly_type VARCHAR(32),      -- 'overfill', 'underfill', 'viscosity', 'torque', 'label', 'thermal'
    detected_sensors TEXT[],       -- Array of sensors that triggered anomaly

    -- METADATA
    custom_sensors JSONB DEFAULT '{}'::jsonb,

    -- Constraints
    CONSTRAINT valid_line_id CHECK (line_id ~ '^L[0-9]{2}$'),
    CONSTRAINT valid_fill_level CHECK (fill_level IS NULL OR (fill_level >= 0 AND fill_level <= 120)),
    CONSTRAINT valid_anomaly_score CHECK (anomaly_score >= 0 AND anomaly_score <= 1)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_ketchup_line_id ON sensor_readings_ketchup(line_id);
CREATE INDEX IF NOT EXISTS idx_ketchup_timestamp ON sensor_readings_ketchup(timestamp);
CREATE INDEX IF NOT EXISTS idx_ketchup_created_at ON sensor_readings_ketchup(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ketchup_anomaly ON sensor_readings_ketchup(anomaly_score) WHERE anomaly_score > 0.5;
CREATE INDEX IF NOT EXISTS idx_ketchup_line_time ON sensor_readings_ketchup(line_id, created_at DESC);

-- Partial index for recent data queries
CREATE INDEX IF NOT EXISTS idx_ketchup_recent ON sensor_readings_ketchup(created_at DESC)
    WHERE created_at > NOW() - INTERVAL '24 hours';

-- -----------------------------------------------------------------------------
-- Table: ketchup_line_3d_config
-- 3D positioning and visual configuration for each production line
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ketchup_line_3d_config (
    id SERIAL PRIMARY KEY,
    line_id VARCHAR(10) UNIQUE NOT NULL,

    -- Grid position (5x5 layout)
    row_index INT NOT NULL,        -- 0-4 (5 rows)
    col_index INT NOT NULL,        -- 0-4 (5 columns)

    -- 3D World Position (meters)
    position_x FLOAT NOT NULL,
    position_y FLOAT DEFAULT 0,
    position_z FLOAT NOT NULL,
    rotation_y FLOAT DEFAULT 0,    -- Radians

    -- Visual configuration
    label VARCHAR(100),
    color_accent VARCHAR(7) DEFAULT '#ff0000',  -- Hex color
    glow_intensity FLOAT DEFAULT 1.0,

    -- Visibility flags
    visible BOOLEAN DEFAULT true,
    show_label BOOLEAN DEFAULT true,
    show_particles BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_ketchup_line_id CHECK (line_id ~ '^L[0-9]{2}$'),
    CONSTRAINT valid_row_index CHECK (row_index >= 0 AND row_index <= 4),
    CONSTRAINT valid_col_index CHECK (col_index >= 0 AND col_index <= 4)
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_ketchup_3d_line_id ON ketchup_line_3d_config(line_id);

-- -----------------------------------------------------------------------------
-- Insert 25 production line positions (5x5 grid layout)
-- Layout:  X spacing = 30m, Z spacing = 25m
--          Center at (0,0,0), Player spawn at (0, 2, 80)
-- -----------------------------------------------------------------------------
INSERT INTO ketchup_line_3d_config (line_id, row_index, col_index, position_x, position_z, label, color_accent)
SELECT
    'L' || LPAD(((r * 5) + c + 1)::text, 2, '0') AS line_id,
    r AS row_index,
    c AS col_index,
    (c - 2) * 30.0 AS position_x,    -- X: -60, -30, 0, 30, 60
    (r - 2) * 25.0 AS position_z,    -- Z: -50, -25, 0, 25, 50
    'LINE ' || ((r * 5) + c + 1) AS label,
    CASE
        WHEN (r + c) % 3 = 0 THEN '#ff0000'  -- Red
        WHEN (r + c) % 3 = 1 THEN '#ff3300'  -- Orange-red
        ELSE '#cc0000'                        -- Dark red
    END AS color_accent
FROM generate_series(0, 4) AS r, generate_series(0, 4) AS c
ON CONFLICT (line_id) DO UPDATE SET
    position_x = EXCLUDED.position_x,
    position_z = EXCLUDED.position_z,
    label = EXCLUDED.label,
    updated_at = NOW();

-- -----------------------------------------------------------------------------
-- Table: ketchup_anomaly_log
-- Dedicated log for ketchup factory anomalies (for detailed analytics)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ketchup_anomaly_log (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    line_id VARCHAR(10) NOT NULL,
    reading_id INT REFERENCES sensor_readings_ketchup(id) ON DELETE CASCADE,

    -- Anomaly details
    anomaly_type VARCHAR(32) NOT NULL,
    anomaly_score FLOAT NOT NULL,
    detection_method VARCHAR(32),  -- 'rule_based', 'isolation_forest', 'lstm', 'hybrid'

    -- Sensor values at anomaly time
    fill_level FLOAT,
    viscosity FLOAT,
    sauce_temp FLOAT,
    cap_torque FLOAT,
    bottle_flow_rate FLOAT,
    label_alignment FLOAT,

    -- Contributing factors
    detected_sensors TEXT[],
    description TEXT,

    -- Resolution tracking
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMPTZ,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_ketchup_anomaly_line ON ketchup_anomaly_log(line_id);
CREATE INDEX IF NOT EXISTS idx_ketchup_anomaly_time ON ketchup_anomaly_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ketchup_anomaly_unresolved ON ketchup_anomaly_log(resolved) WHERE resolved = false;

-- -----------------------------------------------------------------------------
-- Table: ketchup_production_stats
-- Aggregated hourly statistics per line
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ketchup_production_stats (
    id SERIAL PRIMARY KEY,
    line_id VARCHAR(10) NOT NULL,
    hour_start TIMESTAMPTZ NOT NULL,

    -- Production metrics
    total_bottles INT DEFAULT 0,
    rejected_bottles INT DEFAULT 0,
    avg_fill_level FLOAT,
    avg_flow_rate FLOAT,
    avg_efficiency FLOAT,

    -- Quality metrics
    anomaly_count INT DEFAULT 0,
    max_anomaly_score FLOAT,
    avg_anomaly_score FLOAT,

    -- Sensor averages
    avg_viscosity FLOAT,
    avg_sauce_temp FLOAT,
    avg_cap_torque FLOAT,
    avg_label_alignment FLOAT,

    -- Downtime
    downtime_seconds INT DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(line_id, hour_start)
);

CREATE INDEX IF NOT EXISTS idx_ketchup_stats_line_hour ON ketchup_production_stats(line_id, hour_start DESC);

-- -----------------------------------------------------------------------------
-- View: ketchup_line_status
-- Real-time status view for dashboard queries
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW ketchup_line_status AS
SELECT
    c.line_id,
    c.label,
    c.position_x,
    c.position_z,
    c.color_accent,
    r.fill_level,
    r.viscosity,
    r.sauce_temp,
    r.cap_torque,
    r.bottle_flow_rate,
    r.label_alignment,
    r.anomaly_score,
    r.anomaly_type,
    r.bottle_count,
    r.efficiency,
    r.created_at AS last_reading_at,
    CASE
        WHEN r.anomaly_score > 0.7 THEN 'CRITICAL'
        WHEN r.anomaly_score > 0.5 THEN 'WARNING'
        WHEN r.created_at < NOW() - INTERVAL '30 seconds' THEN 'OFFLINE'
        ELSE 'NORMAL'
    END AS status
FROM ketchup_line_3d_config c
LEFT JOIN LATERAL (
    SELECT * FROM sensor_readings_ketchup s
    WHERE s.line_id = c.line_id
    ORDER BY s.created_at DESC
    LIMIT 1
) r ON true;

-- -----------------------------------------------------------------------------
-- Function: Update timestamp trigger
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_ketchup_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to 3d config table
DROP TRIGGER IF EXISTS trigger_ketchup_3d_timestamp ON ketchup_line_3d_config;
CREATE TRIGGER trigger_ketchup_3d_timestamp
    BEFORE UPDATE ON ketchup_line_3d_config
    FOR EACH ROW
    EXECUTE FUNCTION update_ketchup_timestamp();

-- -----------------------------------------------------------------------------
-- Seed sensor metadata for ketchup sensors
-- -----------------------------------------------------------------------------
INSERT INTO sensor_metadata (sensor_name, machine_type, category, location, equipment_section, criticality, unit)
VALUES
    ('fill_level', 'ketchup_line', 'quality', 'Filling Station', 'Bottle Filler', 'critical', '%'),
    ('viscosity', 'ketchup_line', 'fluid', 'Sauce Tank', 'Pump System', 'high', 'cP'),
    ('sauce_temp', 'ketchup_line', 'thermal', 'Heating System', 'Heat Exchanger', 'high', '°F'),
    ('cap_torque', 'ketchup_line', 'mechanical', 'Capping Station', 'Cap Applicator', 'critical', 'Nm'),
    ('bottle_flow_rate', 'ketchup_line', 'production', 'Conveyor', 'Main Belt', 'medium', 'bottles/min'),
    ('label_alignment', 'ketchup_line', 'quality', 'Labeling Station', 'Label Applicator', 'medium', '°')
ON CONFLICT (sensor_name) DO UPDATE SET
    machine_type = EXCLUDED.machine_type,
    category = EXCLUDED.category,
    location = EXCLUDED.location,
    equipment_section = EXCLUDED.equipment_section,
    criticality = EXCLUDED.criticality,
    unit = EXCLUDED.unit;

-- -----------------------------------------------------------------------------
-- Grant permissions (adjust as needed for your setup)
-- -----------------------------------------------------------------------------
-- GRANT SELECT, INSERT, UPDATE ON sensor_readings_ketchup TO sensoruser;
-- GRANT SELECT, INSERT, UPDATE ON ketchup_line_3d_config TO sensoruser;
-- GRANT SELECT, INSERT, UPDATE ON ketchup_anomaly_log TO sensoruser;
-- GRANT SELECT, INSERT, UPDATE ON ketchup_production_stats TO sensoruser;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sensoruser;

-- -----------------------------------------------------------------------------
-- Verification queries
-- -----------------------------------------------------------------------------
-- SELECT COUNT(*) as line_count FROM ketchup_line_3d_config;  -- Should be 25
-- SELECT * FROM ketchup_line_3d_config ORDER BY row_index, col_index;
-- SELECT * FROM ketchup_line_status;

COMMENT ON TABLE sensor_readings_ketchup IS 'Ketchup bottling line sensor readings - parallel to sensor_readings for generic rig data';
COMMENT ON TABLE ketchup_line_3d_config IS '3D visualization configuration for 25 ketchup production lines';
COMMENT ON TABLE ketchup_anomaly_log IS 'Detailed anomaly logging for ketchup factory incidents';
COMMENT ON VIEW ketchup_line_status IS 'Real-time status view joining line config with latest readings';

-- Migration complete!
SELECT 'Ketchup Factory migration completed successfully!' AS status;
SELECT COUNT(*) || ' production lines configured' AS lines FROM ketchup_line_3d_config;
