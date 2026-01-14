-- =============================================================================
-- User Authentication & Authorization Migration
-- Adds user management and machine access control
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_user_machine_access_user ON user_machine_access(user_id);
CREATE INDEX IF NOT EXISTS idx_user_machine_access_machine ON user_machine_access(machine_id);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE users TO sensoruser;
GRANT ALL PRIVILEGES ON SEQUENCE users_id_seq TO sensoruser;
GRANT ALL PRIVILEGES ON TABLE user_machine_access TO sensoruser;
GRANT ALL PRIVILEGES ON SEQUENCE user_machine_access_id_seq TO sensoruser;

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

-- Bootstrap initial admin user (password from env var, default 'admin')
-- Note: Password will be hashed in application code, not in SQL
-- This is a placeholder - actual user creation happens in Python

