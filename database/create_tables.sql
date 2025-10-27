-- Kinetic Brain Backend Database Schema
-- This script creates all necessary tables for the backend application
-- Run this script on your PostgreSQL database to set up the complete schema

-- Enable UUID extension if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- USERS AND AUTHENTICATION TABLES
-- =====================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR,
    name VARCHAR NOT NULL,
    avatar_url VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE,
    auth_provider VARCHAR DEFAULT 'email'
);

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- User profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    age INTEGER,
    gender VARCHAR(10), -- male, female, other
    weight FLOAT, -- kg
    height FLOAT, -- cm
    sports JSONB, -- List of sports
    experience_years INTEGER,
    weekly_hours FLOAT,
    main_goal VARCHAR(100),
    physical_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    metric_type VARCHAR(20) NOT NULL, -- hr, pace, power
    threshold_value FLOAT NOT NULL,
    max_value FLOAT,
    rest_value FLOAT,
    zones_json JSONB, -- Z1-Z5 zones with min/max values
    test_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- OAuth accounts table
CREATE TABLE IF NOT EXISTS oauth_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR NOT NULL, -- google, facebook, etc.
    provider_account_id VARCHAR NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(provider, provider_account_id)
);

-- =====================================================
-- WORKOUT TABLES
-- =====================================================

-- Workout plans table
CREATE TABLE IF NOT EXISTS workout_plans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_weeks INTEGER NOT NULL,
    goal VARCHAR(200),
    sport_type VARCHAR(50),
    level VARCHAR(20), -- beginner, intermediate, advanced
    status VARCHAR(20) DEFAULT 'active', -- active, completed, paused
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Workouts table
CREATE TABLE IF NOT EXISTS workouts (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES workout_plans(id) ON DELETE SET NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL, -- endurance, interval, strength, etc.
    day_number INTEGER, -- Day within the plan
    scheduled_date DATE,
    duration_minutes INTEGER NOT NULL,
    intensity VARCHAR(20), -- easy, moderate, hard
    zone VARCHAR(10), -- Z1, Z2, Z3, Z4, Z5
    structure_json JSONB, -- warmup/main/cooldown structure
    status VARCHAR(20) DEFAULT 'scheduled', -- scheduled, completed, skipped
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Workout sessions table
CREATE TABLE IF NOT EXISTS workout_sessions (
    id SERIAL PRIMARY KEY,
    workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    actual_date TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER NOT NULL,
    avg_hr FLOAT, -- Average heart rate
    max_hr FLOAT, -- Maximum heart rate
    avg_pace FLOAT, -- Average pace in min/km
    avg_power FLOAT, -- Average power in watts
    perceived_exertion INTEGER, -- RPE scale 1-10
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- CALENDAR TABLES
-- =====================================================

-- Calendar events table
CREATE TABLE IF NOT EXISTS calendar_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workout_id INTEGER REFERENCES workouts(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- workout, rest, race, etc.
    scheduled_date DATE NOT NULL,
    duration_minutes INTEGER NOT NULL,
    is_recurring BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- User-related indexes
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_user_id ON performance_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_oauth_accounts_user_id ON oauth_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_oauth_accounts_provider ON oauth_accounts(provider);

-- Workout-related indexes
CREATE INDEX IF NOT EXISTS idx_workout_plans_user_id ON workout_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_workout_plans_status ON workout_plans(status);
CREATE INDEX IF NOT EXISTS idx_workouts_user_id ON workouts(user_id);
CREATE INDEX IF NOT EXISTS idx_workouts_plan_id ON workouts(plan_id);
CREATE INDEX IF NOT EXISTS idx_workouts_scheduled_date ON workouts(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_workouts_status ON workouts(status);
CREATE INDEX IF NOT EXISTS idx_workout_sessions_user_id ON workout_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_workout_sessions_workout_id ON workout_sessions(workout_id);
CREATE INDEX IF NOT EXISTS idx_workout_sessions_actual_date ON workout_sessions(actual_date);

-- Calendar-related indexes
CREATE INDEX IF NOT EXISTS idx_calendar_events_user_id ON calendar_events(user_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_workout_id ON calendar_events(workout_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_scheduled_date ON calendar_events(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_calendar_events_event_type ON calendar_events(event_type);

-- =====================================================
-- CONSTRAINTS AND VALIDATIONS
-- =====================================================

-- Add check constraints for data validation (only if they don't exist)
DO $$
BEGIN
    -- Users constraints
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_users_email_format') THEN
        ALTER TABLE users ADD CONSTRAINT chk_users_email_format 
            CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
    END IF;

    -- User profiles constraints
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_user_profiles_gender') THEN
        ALTER TABLE user_profiles ADD CONSTRAINT chk_user_profiles_gender 
            CHECK (gender IN ('male', 'female', 'other') OR gender IS NULL);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_user_profiles_age') THEN
        ALTER TABLE user_profiles ADD CONSTRAINT chk_user_profiles_age 
            CHECK (age IS NULL OR (age >= 0 AND age <= 150));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_user_profiles_weight') THEN
        ALTER TABLE user_profiles ADD CONSTRAINT chk_user_profiles_weight 
            CHECK (weight IS NULL OR (weight > 0 AND weight <= 1000));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_user_profiles_height') THEN
        ALTER TABLE user_profiles ADD CONSTRAINT chk_user_profiles_height 
            CHECK (height IS NULL OR (height > 0 AND height <= 300));
    END IF;

    -- Performance metrics constraints
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_performance_metrics_type') THEN
        ALTER TABLE performance_metrics ADD CONSTRAINT chk_performance_metrics_type 
            CHECK (metric_type IN ('hr', 'pace', 'power'));
    END IF;

    -- Workout plans constraints
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_workout_plans_level') THEN
        ALTER TABLE workout_plans ADD CONSTRAINT chk_workout_plans_level 
            CHECK (level IN ('beginner', 'intermediate', 'advanced') OR level IS NULL);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_workout_plans_status') THEN
        ALTER TABLE workout_plans ADD CONSTRAINT chk_workout_plans_status 
            CHECK (status IN ('active', 'completed', 'paused'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_workout_plans_dates') THEN
        ALTER TABLE workout_plans ADD CONSTRAINT chk_workout_plans_dates 
            CHECK (end_date >= start_date);
    END IF;

    -- Workouts constraints
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_workouts_intensity') THEN
        ALTER TABLE workouts ADD CONSTRAINT chk_workouts_intensity 
            CHECK (intensity IN ('easy', 'moderate', 'hard') OR intensity IS NULL);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_workouts_zone') THEN
        ALTER TABLE workouts ADD CONSTRAINT chk_workouts_zone 
            CHECK (zone IN ('Z1', 'Z2', 'Z3', 'Z4', 'Z5') OR zone IS NULL);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_workouts_status') THEN
        ALTER TABLE workouts ADD CONSTRAINT chk_workouts_status 
            CHECK (status IN ('scheduled', 'completed', 'skipped'));
    END IF;

    -- Workout sessions constraints
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_workout_sessions_duration') THEN
        ALTER TABLE workout_sessions ADD CONSTRAINT chk_workout_sessions_duration 
            CHECK (duration_minutes > 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_workout_sessions_rpe') THEN
        ALTER TABLE workout_sessions ADD CONSTRAINT chk_workout_sessions_rpe 
            CHECK (perceived_exertion IS NULL OR (perceived_exertion >= 1 AND perceived_exertion <= 10));
    END IF;

    -- Calendar events constraints
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_calendar_events_duration') THEN
        ALTER TABLE calendar_events ADD CONSTRAINT chk_calendar_events_duration 
            CHECK (duration_minutes > 0);
    END IF;
END $$;

-- =====================================================
-- TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at 
    BEFORE UPDATE ON user_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_oauth_accounts_updated_at 
    BEFORE UPDATE ON oauth_accounts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workout_plans_updated_at 
    BEFORE UPDATE ON workout_plans 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workouts_updated_at 
    BEFORE UPDATE ON workouts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_calendar_events_updated_at 
    BEFORE UPDATE ON calendar_events 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- SAMPLE DATA (Optional - Comment out if not needed)
-- =====================================================

-- Insert a sample user for testing
-- INSERT INTO users (email, name, is_verified) 
-- VALUES ('test@kineticbrain.com', 'Test User', TRUE)
-- ON CONFLICT (email) DO NOTHING;

-- =====================================================
-- GRANTS AND PERMISSIONS
-- =====================================================

-- Grant permissions to the application user
-- Replace 'kineticbrain' with your actual database user
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO kineticbrain;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO kineticbrain;

-- =====================================================
-- COMPLETION MESSAGE
-- =====================================================

-- Display completion message
DO $$
BEGIN
    RAISE NOTICE '====================================================';
    RAISE NOTICE 'Kinetic Brain Database Schema Created Successfully!';
    RAISE NOTICE '====================================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '- users';
    RAISE NOTICE '- user_profiles';
    RAISE NOTICE '- performance_metrics';
    RAISE NOTICE '- oauth_accounts';
    RAISE NOTICE '- workout_plans';
    RAISE NOTICE '- workouts';
    RAISE NOTICE '- workout_sessions';
    RAISE NOTICE '- calendar_events';
    RAISE NOTICE '====================================================';
    RAISE NOTICE 'All indexes, constraints, and triggers have been created.';
    RAISE NOTICE 'The database is ready for the Kinetic Brain Backend!';
    RAISE NOTICE '====================================================';
END $$;
