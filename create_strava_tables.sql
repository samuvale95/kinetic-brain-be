-- Strava Integration Tables
-- Run this script to create Strava tables manually

-- Strava Accounts Table
CREATE TABLE strava_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strava_id BIGINT UNIQUE NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    firstname VARCHAR(100),
    lastname VARCHAR(100),
    profile_medium VARCHAR(500),
    profile VARCHAR(500),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    sex VARCHAR(10),
    premium BOOLEAN DEFAULT FALSE,
    summit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Strava Activities Table
CREATE TABLE strava_activities (
    id SERIAL PRIMARY KEY,
    strava_account_id INTEGER NOT NULL REFERENCES strava_accounts(id) ON DELETE CASCADE,
    strava_activity_id BIGINT UNIQUE NOT NULL,
    workout_id INTEGER REFERENCES workouts(id) ON DELETE SET NULL,
    
    -- Basic activity info
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL,
    sport_type VARCHAR(50),
    
    -- Dates and times
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    start_date_local TIMESTAMP WITH TIME ZONE NOT NULL,
    timezone VARCHAR(100),
    
    -- Distance and duration
    distance FLOAT,
    moving_time INTEGER,
    elapsed_time INTEGER,
    
    -- Elevation and pace
    total_elevation_gain FLOAT,
    average_speed FLOAT,
    max_speed FLOAT,
    
    -- Heart rate data
    average_heartrate FLOAT,
    max_heartrate FLOAT,
    
    -- Power data (for cycling)
    average_watts FLOAT,
    max_watts FLOAT,
    weighted_average_watts FLOAT,
    
    -- Cadence
    average_cadence FLOAT,
    
    -- Temperature and weather
    temperature FLOAT,
    feels_like FLOAT,
    
    -- Additional data
    calories FLOAT,
    kilojoules FLOAT,
    
    -- Detailed data (JSON)
    splits_metric JSONB,
    splits_standard JSONB,
    best_efforts JSONB,
    segment_efforts JSONB,
    
    -- Status
    is_synced BOOLEAN DEFAULT FALSE,
    sync_status VARCHAR(50) DEFAULT 'pending',
    
    -- Raw Strava data
    raw_data JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Strava Webhooks Table
CREATE TABLE strava_webhooks (
    id SERIAL PRIMARY KEY,
    object_type VARCHAR(50) NOT NULL,
    object_id BIGINT NOT NULL,
    aspect_type VARCHAR(50) NOT NULL,
    event_time BIGINT NOT NULL,
    owner_id BIGINT NOT NULL,
    subscription_id INTEGER NOT NULL,
    
    -- Processing status
    is_processed BOOLEAN DEFAULT FALSE,
    processing_error TEXT,
    
    -- Raw webhook data
    raw_data JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for better performance
CREATE INDEX idx_strava_accounts_user_id ON strava_accounts(user_id);
CREATE INDEX idx_strava_accounts_strava_id ON strava_accounts(strava_id);
CREATE INDEX idx_strava_activities_account_id ON strava_activities(strava_account_id);
CREATE INDEX idx_strava_activities_strava_id ON strava_activities(strava_activity_id);
CREATE INDEX idx_strava_activities_workout_id ON strava_activities(workout_id);
CREATE INDEX idx_strava_activities_start_date ON strava_activities(start_date);
CREATE INDEX idx_strava_activities_sync_status ON strava_activities(sync_status);
CREATE INDEX idx_strava_webhooks_owner_id ON strava_webhooks(owner_id);
CREATE INDEX idx_strava_webhooks_processed ON strava_webhooks(is_processed);

-- Comments
COMMENT ON TABLE strava_accounts IS 'Strava OAuth accounts linked to users';
COMMENT ON TABLE strava_activities IS 'Strava activities synced from API';
COMMENT ON TABLE strava_webhooks IS 'Strava webhook notifications';



