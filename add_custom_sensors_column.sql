-- Add custom_sensors column to sensor_readings table if it doesn't exist
ALTER TABLE sensor_readings 
ADD COLUMN IF NOT EXISTS custom_sensors JSONB DEFAULT '{}'::jsonb;

-- Create GIN index for custom_sensors if it doesn't exist
CREATE INDEX IF NOT EXISTS idx_sensor_readings_custom_sensors 
ON sensor_readings USING GIN (custom_sensors);
