-- Enhanced Audit Log System (v2)
-- Supports compliance, tamper detection, and before/after state tracking

CREATE TABLE IF NOT EXISTS audit_logs_v2 (
    id BIGSERIAL PRIMARY KEY,

    -- WHO
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(64) NOT NULL,
    role VARCHAR(16),
    ip_address INET,
    user_agent TEXT,

    -- WHAT
    action_type VARCHAR(32) NOT NULL,  -- 'CREATE', 'READ', 'UPDATE', 'DELETE', 'INGEST', 'PARSE'
    resource_type VARCHAR(64),         -- 'sensor', 'threshold', 'user', 'sensor_file', 'ingest'
    resource_id VARCHAR(128),

    -- BEFORE/AFTER (for UPDATE/DELETE operations)
    previous_state JSONB,
    new_state JSONB,

    -- WHEN
    timestamp TIMESTAMPTZ DEFAULT NOW(),

    -- COMPLIANCE
    retention_until TIMESTAMPTZ,       -- GDPR/SOX compliance (NULL = permanent)
    hash_chain VARCHAR(64)             -- Tamper detection (future: SHA-256 hash)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_audit_v2_timestamp ON audit_logs_v2(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_v2_user_id ON audit_logs_v2(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_v2_action_type ON audit_logs_v2(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_v2_resource_type ON audit_logs_v2(resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_v2_resource_id ON audit_logs_v2(resource_id);

-- GIN index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_audit_v2_previous_state ON audit_logs_v2 USING GIN (previous_state);
CREATE INDEX IF NOT EXISTS idx_audit_v2_new_state ON audit_logs_v2 USING GIN (new_state);

-- Comments
COMMENT ON TABLE audit_logs_v2 IS 'Enhanced audit trail with compliance and state tracking';
COMMENT ON COLUMN audit_logs_v2.action_type IS 'CRUD operation or system action';
COMMENT ON COLUMN audit_logs_v2.resource_type IS 'Type of resource being acted upon';
COMMENT ON COLUMN audit_logs_v2.previous_state IS 'State before modification (for UPDATE/DELETE)';
COMMENT ON COLUMN audit_logs_v2.new_state IS 'State after modification (for CREATE/UPDATE)';
COMMENT ON COLUMN audit_logs_v2.retention_until IS 'GDPR/SOX compliance: auto-delete after this date (NULL = permanent)';
COMMENT ON COLUMN audit_logs_v2.hash_chain IS 'Tamper detection: hash of previous log entry (future implementation)';

