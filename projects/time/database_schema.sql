-- Task Management & Calendar Integration Platform
-- Database Schema Design
-- PostgreSQL 15+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- USERS TABLE
-- ============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    timezone VARCHAR(100) NOT NULL DEFAULT 'UTC',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE
);

-- Indexes for users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_active ON users(is_active);

-- ============================================================================
-- PROJECTS TABLE
-- ============================================================================
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#3B82F6', -- Hex color code
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_color_format CHECK (color ~ '^#[0-9A-Fa-f]{6}$')
);

-- Indexes for projects
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_archived ON projects(is_archived);

-- ============================================================================
-- TAGS TABLE
-- ============================================================================
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    color VARCHAR(7) DEFAULT '#6B7280',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_tag_name UNIQUE (user_id, name),
    CONSTRAINT chk_tag_color_format CHECK (color ~ '^#[0-9A-Fa-f]{6}$')
);

-- Indexes for tags
CREATE INDEX idx_tags_user_id ON tags(user_id);
CREATE INDEX idx_tags_name ON tags(name);

-- ============================================================================
-- TASKS TABLE
-- ============================================================================
CREATE TYPE task_status AS ENUM ('TODO', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED');
CREATE TYPE task_priority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'URGENT');

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status task_status NOT NULL DEFAULT 'TODO',
    priority task_priority NOT NULL DEFAULT 'MEDIUM',
    due_date TIMESTAMP WITH TIME ZONE,
    start_date TIMESTAMP WITH TIME ZONE,
    estimated_duration INTEGER, -- in minutes
    actual_duration INTEGER DEFAULT 0, -- in minutes, calculated
    parent_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    calendar_event_id VARCHAR(255), -- External calendar event ID
    recurrence_rule TEXT, -- iCal RRULE format
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_estimated_duration CHECK (estimated_duration > 0),
    CONSTRAINT chk_actual_duration CHECK (actual_duration >= 0),
    CONSTRAINT chk_completed_at CHECK (
        (status = 'COMPLETED' AND completed_at IS NOT NULL) OR
        (status != 'COMPLETED' AND completed_at IS NULL)
    )
);

-- Indexes for tasks
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_user_status ON tasks(user_id, status);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_due_date ON tasks(due_date) WHERE due_date IS NOT NULL;
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_parent_id ON tasks(parent_task_id);
CREATE INDEX idx_tasks_calendar_event ON tasks(calendar_event_id) WHERE calendar_event_id IS NOT NULL;
CREATE INDEX idx_tasks_created_at ON tasks(created_at);

-- ============================================================================
-- TASK_TAGS JUNCTION TABLE (Many-to-Many)
-- ============================================================================
CREATE TABLE task_tags (
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (task_id, tag_id)
);

-- Indexes for task_tags
CREATE INDEX idx_task_tags_task_id ON task_tags(task_id);
CREATE INDEX idx_task_tags_tag_id ON task_tags(tag_id);

-- ============================================================================
-- CALENDAR_CONNECTIONS TABLE
-- ============================================================================
CREATE TYPE calendar_provider AS ENUM ('GOOGLE', 'MICROSOFT', 'ICAL');
CREATE TYPE sync_status AS ENUM ('SUCCESS', 'FAILED', 'PENDING');

CREATE TABLE calendar_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider calendar_provider NOT NULL,
    provider_account_id VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL, -- Encrypted in application layer
    refresh_token TEXT NOT NULL, -- Encrypted in application layer
    token_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    calendar_id VARCHAR(255) NOT NULL,
    sync_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    sync_status sync_status DEFAULT 'PENDING',
    sync_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_provider_calendar UNIQUE (user_id, provider, provider_account_id, calendar_id)
);

-- Indexes for calendar_connections
CREATE INDEX idx_calendar_connections_user_id ON calendar_connections(user_id);
CREATE INDEX idx_calendar_connections_provider ON calendar_connections(provider);
CREATE INDEX idx_calendar_connections_sync_enabled ON calendar_connections(sync_enabled);
CREATE INDEX idx_calendar_connections_token_expiry ON calendar_connections(token_expires_at);

-- ============================================================================
-- TIME_ENTRIES TABLE
-- ============================================================================
CREATE TABLE time_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration INTEGER GENERATED ALWAYS AS (
        CASE
            WHEN end_time IS NOT NULL
            THEN EXTRACT(EPOCH FROM (end_time - start_time))::INTEGER
            ELSE 0
        END
    ) STORED, -- in seconds
    description TEXT,
    is_manual BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_time_range CHECK (end_time IS NULL OR end_time > start_time),
    CONSTRAINT chk_one_active_entry_per_user EXCLUDE USING gist (
        user_id WITH =,
        tstzrange(start_time, COALESCE(end_time, 'infinity'::timestamp)) WITH &&
    ) WHERE (end_time IS NULL)
);

-- Indexes for time_entries
CREATE INDEX idx_time_entries_user_id ON time_entries(user_id);
CREATE INDEX idx_time_entries_task_id ON time_entries(task_id);
CREATE INDEX idx_time_entries_user_task ON time_entries(user_id, task_id);
CREATE INDEX idx_time_entries_start_time ON time_entries(start_time);
CREATE INDEX idx_time_entries_active ON time_entries(user_id) WHERE end_time IS NULL;

-- Partition time_entries by month for performance
-- (Partitioning strategy for large datasets)
-- ALTER TABLE time_entries PARTITION BY RANGE (start_time);

-- ============================================================================
-- REFRESH_TOKENS TABLE (for JWT refresh token management)
-- ============================================================================
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE
);

-- Indexes for refresh_tokens
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- ============================================================================
-- NOTIFICATIONS TABLE
-- ============================================================================
CREATE TYPE notification_type AS ENUM ('TASK_DUE', 'TASK_ASSIGNED', 'SYNC_FAILED', 'SYNC_SUCCESS', 'GENERAL');
CREATE TYPE notification_channel AS ENUM ('EMAIL', 'PUSH', 'IN_APP');

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type notification_type NOT NULL,
    channel notification_channel NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    related_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for notifications
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);

-- ============================================================================
-- AUDIT_LOG TABLE (for tracking changes)
-- ============================================================================
CREATE TYPE audit_action AS ENUM ('CREATE', 'UPDATE', 'DELETE');

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    entity_type VARCHAR(50) NOT NULL, -- e.g., 'task', 'project'
    entity_id UUID NOT NULL,
    action audit_action NOT NULL,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for audit_log
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- Partition audit_log by month for performance
-- ALTER TABLE audit_log PARTITION BY RANGE (created_at);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_calendar_connections_updated_at BEFORE UPDATE ON calendar_connections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_time_entries_updated_at BEFORE UPDATE ON time_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically set completed_at when task status changes to COMPLETED
CREATE OR REPLACE FUNCTION set_task_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'COMPLETED' AND OLD.status != 'COMPLETED' THEN
        NEW.completed_at = CURRENT_TIMESTAMP;
    ELSIF NEW.status != 'COMPLETED' THEN
        NEW.completed_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_task_completed_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION set_task_completed_at();

-- Function to update task actual_duration from time_entries
CREATE OR REPLACE FUNCTION update_task_actual_duration()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE tasks
    SET actual_duration = (
        SELECT COALESCE(SUM(duration), 0) / 60
        FROM time_entries
        WHERE task_id = COALESCE(NEW.task_id, OLD.task_id)
        AND end_time IS NOT NULL
    )
    WHERE id = COALESCE(NEW.task_id, OLD.task_id);
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_task_duration_insert AFTER INSERT ON time_entries
    FOR EACH ROW EXECUTE FUNCTION update_task_actual_duration();

CREATE TRIGGER trigger_update_task_duration_update AFTER UPDATE ON time_entries
    FOR EACH ROW EXECUTE FUNCTION update_task_actual_duration();

CREATE TRIGGER trigger_update_task_duration_delete AFTER DELETE ON time_entries
    FOR EACH ROW EXECUTE FUNCTION update_task_actual_duration();

-- ============================================================================
-- VIEWS FOR ANALYTICS
-- ============================================================================

-- View for task completion statistics
CREATE OR REPLACE VIEW task_completion_stats AS
SELECT
    user_id,
    DATE(completed_at) as completion_date,
    COUNT(*) as tasks_completed,
    AVG(actual_duration) as avg_duration,
    SUM(actual_duration) as total_duration
FROM tasks
WHERE status = 'COMPLETED'
GROUP BY user_id, DATE(completed_at);

-- View for active time tracking sessions
CREATE OR REPLACE VIEW active_time_entries AS
SELECT
    te.id,
    te.user_id,
    te.task_id,
    te.start_time,
    t.title as task_title,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - te.start_time))::INTEGER as current_duration
FROM time_entries te
JOIN tasks t ON te.task_id = t.id
WHERE te.end_time IS NULL;

-- View for task productivity metrics
CREATE OR REPLACE VIEW task_productivity_metrics AS
SELECT
    t.user_id,
    t.project_id,
    t.priority,
    t.status,
    COUNT(*) as task_count,
    AVG(t.actual_duration) as avg_actual_duration,
    AVG(t.estimated_duration) as avg_estimated_duration,
    AVG(
        CASE
            WHEN t.estimated_duration > 0
            THEN (t.actual_duration::FLOAT / t.estimated_duration) * 100
            ELSE NULL
        END
    ) as accuracy_percentage
FROM tasks t
GROUP BY t.user_id, t.project_id, t.priority, t.status;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on all user-specific tables
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Create policies (example for tasks table)
-- Note: In production, these would be used with application-level user context
CREATE POLICY tasks_user_isolation ON tasks
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::UUID);

CREATE POLICY projects_user_isolation ON projects
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::UUID);

CREATE POLICY tags_user_isolation ON tags
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::UUID);

CREATE POLICY time_entries_user_isolation ON time_entries
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::UUID);

CREATE POLICY calendar_connections_user_isolation ON calendar_connections
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::UUID);

CREATE POLICY notifications_user_isolation ON notifications
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::UUID);

-- ============================================================================
-- SAMPLE DATA (for development/testing)
-- ============================================================================

-- Insert sample user
INSERT INTO users (email, username, password_hash, full_name, timezone)
VALUES (
    'demo@example.com',
    'demouser',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lAXJXkPq.5S6', -- password: demo123
    'Demo User',
    'America/New_York'
);

-- ============================================================================
-- DATABASE MAINTENANCE
-- ============================================================================

-- Vacuum and analyze for optimal performance
COMMENT ON DATABASE current_database() IS 'Run VACUUM ANALYZE weekly for optimal performance';

-- Create indexes concurrently in production
COMMENT ON SCHEMA public IS 'Use CREATE INDEX CONCURRENTLY in production to avoid locks';

-- ============================================================================
-- SECURITY NOTES
-- ============================================================================
/*
1. Access tokens and refresh tokens in calendar_connections should be encrypted
   using application-level encryption before storage
2. Password hashing should use bcrypt with appropriate cost factor (12+)
3. Implement connection pooling (e.g., PgBouncer) for production
4. Use prepared statements to prevent SQL injection
5. Regularly rotate encryption keys
6. Enable SSL/TLS for database connections
7. Implement rate limiting at application layer
8. Use read replicas for analytics queries
*/
