-- Notification System Tables
-- This script creates tables for notification preferences and device tokens

-- =====================================================
-- NOTIFICATION PREFERENCES TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS notification_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    
    -- Email preferences
    email_enabled BOOLEAN DEFAULT true,
    email_workout_reminders BOOLEAN DEFAULT true,
    email_new_workout BOOLEAN DEFAULT true,
    email_workout_completed BOOLEAN DEFAULT true,
    email_plan_updates BOOLEAN DEFAULT true,
    email_weekly_generation BOOLEAN DEFAULT true,
    
    -- Push preferences
    push_enabled BOOLEAN DEFAULT true,
    push_workout_reminders BOOLEAN DEFAULT true,
    push_new_workout BOOLEAN DEFAULT true,
    push_workout_completed BOOLEAN DEFAULT true,
    push_plan_updates BOOLEAN DEFAULT true,
    push_weekly_generation BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_notification_preferences_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_notification_preferences_user_id ON notification_preferences(user_id);

-- =====================================================
-- DEVICE TOKENS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS device_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_token TEXT NOT NULL,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('ios', 'android', 'web')),
    device_id VARCHAR(255), -- Identificatore univoco del device (opzionale)
    app_version VARCHAR(50), -- Versione app (opzionale, utile per debug)
    is_active BOOLEAN DEFAULT true, -- Per disabilitare token senza cancellarli
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE, -- Ultima volta che il token è stato usato
    
    UNIQUE(user_id, device_token, platform)
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_device_tokens_user_id ON device_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_device_tokens_active ON device_tokens(user_id, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_device_tokens_platform ON device_tokens(platform, is_active) WHERE is_active = true;

-- =====================================================
-- TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- =====================================================

-- Function to update updated_at timestamp (should already exist from create_tables.sql)
-- CREATE OR REPLACE FUNCTION update_updated_at_column()
-- RETURNS TRIGGER AS $$
-- BEGIN
--     NEW.updated_at = NOW();
--     RETURN NEW;
-- END;
-- $$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_notification_preferences_updated_at 
    BEFORE UPDATE ON notification_preferences 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_tokens_updated_at 
    BEFORE UPDATE ON device_tokens 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- COMPLETION MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '====================================================';
    RAISE NOTICE 'Notification System Tables Created Successfully!';
    RAISE NOTICE '====================================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '- notification_preferences';
    RAISE NOTICE '- device_tokens';
    RAISE NOTICE '====================================================';
    RAISE NOTICE 'All indexes and triggers have been created.';
    RAISE NOTICE 'The notification system is ready!';
    RAISE NOTICE '====================================================';
END $$;

