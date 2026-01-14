-- =============================================================================
-- Audit Logs Table Migration
-- Creates table for tracking operator actions and system events
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    operator_name VARCHAR(255) NOT NULL,
    action TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    machine_id VARCHAR(10),
    metadata JSONB
);

-- Create indexes for optimized queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_operator ON audit_logs(operator_name);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_machine_id ON audit_logs(machine_id);

-- Add comment
COMMENT ON TABLE audit_logs IS 'Stores audit trail of all operator actions and system events';

