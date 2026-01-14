-- =============================================================================
-- Sensor Metadata Migration
-- Adds sensor_metadata table to enrich sensor data with location, equipment,
-- and criticality information
-- =============================================================================

-- Create sensor_metadata table
CREATE TABLE IF NOT EXISTS sensor_metadata (
    sensor_name VARCHAR(64) PRIMARY KEY,
    machine_type VARCHAR(32) DEFAULT 'industrial',
    category VARCHAR(32) NOT NULL,
    location VARCHAR(128),
    equipment_section VARCHAR(128),
    criticality VARCHAR(16) CHECK (criticality IN ('low', 'medium', 'high', 'critical')),
    unit VARCHAR(16),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sensor_metadata_category ON sensor_metadata(category);
CREATE INDEX IF NOT EXISTS idx_sensor_metadata_criticality ON sensor_metadata(criticality);
CREATE INDEX IF NOT EXISTS idx_sensor_metadata_machine_type ON sensor_metadata(machine_type);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE sensor_metadata TO sensoruser;

-- Seed with 50 existing sensors
-- ENVIRONMENTAL SENSORS (10)
INSERT INTO sensor_metadata (sensor_name, machine_type, category, location, equipment_section, criticality, unit) VALUES
('temperature', 'industrial', 'environmental', 'Main Floor', 'Environmental Control', 'high', '°F'),
('pressure', 'industrial', 'environmental', 'Main Floor', 'Environmental Control', 'medium', 'PSI'),
('humidity', 'industrial', 'environmental', 'Main Floor', 'Environmental Control', 'medium', '%'),
('ambient_temp', 'industrial', 'environmental', 'Main Floor', 'Environmental Control', 'low', '°F'),
('dew_point', 'industrial', 'environmental', 'Main Floor', 'Environmental Control', 'low', '°F'),
('air_quality_index', 'industrial', 'environmental', 'Main Floor', 'Environmental Control', 'high', 'AQI'),
('co2_level', 'industrial', 'environmental', 'Main Floor', 'Environmental Control', 'high', 'ppm'),
('particle_count', 'industrial', 'environmental', 'Main Floor', 'Environmental Control', 'medium', 'particles/m³'),
('noise_level', 'industrial', 'environmental', 'Main Floor', 'Environmental Control', 'medium', 'dB'),
('light_intensity', 'industrial', 'environmental', 'Main Floor', 'Environmental Control', 'low', 'lux'),

-- MECHANICAL SENSORS (10)
('vibration', 'industrial', 'mechanical', 'Production Line', 'Motor Assembly', 'critical', 'mm/s'),
('rpm', 'industrial', 'mechanical', 'Production Line', 'Motor Assembly', 'critical', 'RPM'),
('torque', 'industrial', 'mechanical', 'Production Line', 'Motor Assembly', 'high', 'Nm'),
('shaft_alignment', 'industrial', 'mechanical', 'Production Line', 'Motor Assembly', 'high', 'mm'),
('bearing_temp', 'industrial', 'mechanical', 'Production Line', 'Motor Assembly', 'critical', '°F'),
('motor_current', 'industrial', 'mechanical', 'Production Line', 'Motor Assembly', 'critical', 'A'),
('belt_tension', 'industrial', 'mechanical', 'Production Line', 'Motor Assembly', 'medium', 'lbf'),
('gear_wear', 'industrial', 'mechanical', 'Production Line', 'Motor Assembly', 'high', '%'),
('coupling_temp', 'industrial', 'mechanical', 'Production Line', 'Motor Assembly', 'high', '°F'),
('lubrication_pressure', 'industrial', 'mechanical', 'Production Line', 'Motor Assembly', 'high', 'PSI'),

-- THERMAL SENSORS (10)
('coolant_temp', 'industrial', 'thermal', 'Cooling System', 'Heat Exchanger', 'critical', '°F'),
('exhaust_temp', 'industrial', 'thermal', 'Cooling System', 'Heat Exchanger', 'critical', '°F'),
('oil_temp', 'industrial', 'thermal', 'Cooling System', 'Heat Exchanger', 'high', '°F'),
('radiator_temp', 'industrial', 'thermal', 'Cooling System', 'Heat Exchanger', 'high', '°F'),
('thermal_efficiency', 'industrial', 'thermal', 'Cooling System', 'Heat Exchanger', 'medium', '%'),
('heat_dissipation', 'industrial', 'thermal', 'Cooling System', 'Heat Exchanger', 'medium', 'W'),
('inlet_temp', 'industrial', 'thermal', 'Cooling System', 'Heat Exchanger', 'medium', '°F'),
('outlet_temp', 'industrial', 'thermal', 'Cooling System', 'Heat Exchanger', 'medium', '°F'),
('core_temp', 'industrial', 'thermal', 'Cooling System', 'Heat Exchanger', 'high', '°F'),
('surface_temp', 'industrial', 'thermal', 'Cooling System', 'Heat Exchanger', 'low', '°F'),

-- ELECTRICAL SENSORS (10)
('voltage', 'industrial', 'electrical', 'Electrical Panel', 'Power Distribution', 'critical', 'V'),
('current', 'industrial', 'electrical', 'Electrical Panel', 'Power Distribution', 'critical', 'A'),
('power_factor', 'industrial', 'electrical', 'Electrical Panel', 'Power Distribution', 'high', 'PF'),
('frequency', 'industrial', 'electrical', 'Electrical Panel', 'Power Distribution', 'critical', 'Hz'),
('resistance', 'industrial', 'electrical', 'Electrical Panel', 'Power Distribution', 'medium', 'Ω'),
('capacitance', 'industrial', 'electrical', 'Electrical Panel', 'Power Distribution', 'low', 'μF'),
('inductance', 'industrial', 'electrical', 'Electrical Panel', 'Power Distribution', 'low', 'mH'),
('phase_angle', 'industrial', 'electrical', 'Electrical Panel', 'Power Distribution', 'medium', '°'),
('harmonic_distortion', 'industrial', 'electrical', 'Electrical Panel', 'Power Distribution', 'high', '%'),
('ground_fault', 'industrial', 'electrical', 'Electrical Panel', 'Power Distribution', 'critical', 'mA'),

-- FLUID DYNAMICS SENSORS (10)
('flow_rate', 'industrial', 'fluid', 'Fluid System', 'Pump Station', 'critical', 'L/min'),
('fluid_pressure', 'industrial', 'fluid', 'Fluid System', 'Pump Station', 'critical', 'PSI'),
('viscosity', 'industrial', 'fluid', 'Fluid System', 'Pump Station', 'high', 'cP'),
('density', 'industrial', 'fluid', 'Fluid System', 'Pump Station', 'medium', 'g/cm³'),
('reynolds_number', 'industrial', 'fluid', 'Fluid System', 'Pump Station', 'low', ''),
('pipe_pressure_drop', 'industrial', 'fluid', 'Fluid System', 'Pump Station', 'high', 'PSI'),
('pump_efficiency', 'industrial', 'fluid', 'Fluid System', 'Pump Station', 'high', '%'),
('cavitation_index', 'industrial', 'fluid', 'Fluid System', 'Pump Station', 'high', ''),
('turbulence', 'industrial', 'fluid', 'Fluid System', 'Pump Station', 'medium', '%'),
('valve_position', 'industrial', 'fluid', 'Fluid System', 'Pump Station', 'medium', '%')
ON CONFLICT (sensor_name) DO NOTHING;

