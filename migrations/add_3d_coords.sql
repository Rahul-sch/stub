-- Migration: Add 3D coordinates for machine positioning in Digital Twin
-- Version: 2.0.0
-- Date: 2026-01-11
-- Description: Creates machine_3d_config table for storing 3D world positions
--              of industrial rigs without modifying existing sensor tables.
--
-- SAFE: Creates new table only, does not alter existing schema.

-- ============================================================================
-- MACHINE 3D CONFIGURATION TABLE
-- ============================================================================
-- Stores the 3D world position, rotation, and visual configuration for each
-- industrial machine. Used by the React Three Fiber frontend to position
-- rig models in the virtual factory floor.

CREATE TABLE IF NOT EXISTS machine_3d_config (
    id SERIAL PRIMARY KEY,

    -- Machine identifier (matches machine_id in sensor_readings)
    machine_id VARCHAR(10) NOT NULL UNIQUE,

    -- 3D World Position (in meters, Y is up)
    position_x DOUBLE PRECISION DEFAULT 0,
    position_y DOUBLE PRECISION DEFAULT 0,  -- Usually 0 for floor-level
    position_z DOUBLE PRECISION DEFAULT 0,

    -- Rotation (radians, Y-axis rotation for facing direction)
    rotation_y DOUBLE PRECISION DEFAULT 0,

    -- Scale (uniform scale factor, 1.0 = normal size)
    scale DOUBLE PRECISION DEFAULT 1.0,

    -- Visual Configuration
    model_path VARCHAR(255) DEFAULT '/models/turbine.glb',
    label VARCHAR(100),
    color_accent VARCHAR(7) DEFAULT '#00ffff',  -- Hex color for accent lighting

    -- Visibility flags
    visible BOOLEAN DEFAULT true,
    show_label BOOLEAN DEFAULT true,
    show_particles BOOLEAN DEFAULT true,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INSERT DEFAULT RIG POSITIONS
-- ============================================================================
-- Factory floor layout: Three rigs spaced 20 meters apart along X-axis

INSERT INTO machine_3d_config (machine_id, position_x, position_z, label, color_accent) VALUES
    ('A', -20, 0, 'RIG ALPHA', '#00ffff'),   -- Cyan accent (left)
    ('B',   0, 0, 'RIG BETA',  '#00ff41'),   -- Green accent (center)
    ('C',  20, 0, 'RIG GAMMA', '#ff6600')    -- Orange accent (right)
ON CONFLICT (machine_id) DO NOTHING;

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_machine_3d_config_machine_id
    ON machine_3d_config(machine_id);

CREATE INDEX IF NOT EXISTS idx_machine_3d_config_visible
    ON machine_3d_config(visible)
    WHERE visible = true;

-- ============================================================================
-- TRIGGER: Auto-update updated_at timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_machine_3d_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_machine_3d_config_updated_at ON machine_3d_config;

CREATE TRIGGER trigger_machine_3d_config_updated_at
    BEFORE UPDATE ON machine_3d_config
    FOR EACH ROW
    EXECUTE FUNCTION update_machine_3d_config_updated_at();

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE machine_3d_config IS
    '3D world configuration for industrial machines in the Digital Twin visualization';

COMMENT ON COLUMN machine_3d_config.position_x IS
    'X-axis position in meters (left-right in factory floor)';

COMMENT ON COLUMN machine_3d_config.position_y IS
    'Y-axis position in meters (height, usually 0 for floor-level)';

COMMENT ON COLUMN machine_3d_config.position_z IS
    'Z-axis position in meters (front-back in factory floor)';

COMMENT ON COLUMN machine_3d_config.rotation_y IS
    'Rotation around Y-axis in radians (facing direction)';

COMMENT ON COLUMN machine_3d_config.model_path IS
    'Path to GLTF/GLB model file relative to public directory';

COMMENT ON COLUMN machine_3d_config.color_accent IS
    'Hex color code for accent lighting and UI elements';

-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================
-- Run this to verify the migration succeeded:
-- SELECT machine_id, position_x, position_z, label, color_accent FROM machine_3d_config;
