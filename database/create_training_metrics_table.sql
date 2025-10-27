-- Create training_metrics table
-- Stores calculated metrics for each Strava activity

CREATE TABLE IF NOT EXISTS training_metrics (
    id SERIAL PRIMARY KEY,
    strava_activity_id INTEGER REFERENCES strava_activities(id) ON DELETE CASCADE,
    workout_session_id INTEGER REFERENCES workout_sessions(id) ON DELETE CASCADE,
    
    -- Training Stress Score
    tss FLOAT,
    normalized_power FLOAT,
    intensity_factor FLOAT,
    trimp FLOAT,  -- Training Impulse
    
    -- Time in zones (minutes)
    time_in_zone_1 INTEGER DEFAULT 0,
    time_in_zone_2 INTEGER DEFAULT 0,
    time_in_zone_3 INTEGER DEFAULT 0,
    time_in_zone_4 INTEGER DEFAULT 0,
    time_in_zone_5 INTEGER DEFAULT 0,
    
    -- Store zone distribution as JSON for flexibility
    zone_distribution JSON,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Ensure one metric per activity
    CONSTRAINT unique_strava_activity UNIQUE(strava_activity_id),
    CONSTRAINT unique_workout_session UNIQUE(workout_session_id)
);

-- Indexes for performance
CREATE INDEX idx_training_metrics_strava_activity ON training_metrics(strava_activity_id);
CREATE INDEX idx_training_metrics_workout_session ON training_metrics(workout_session_id);
CREATE INDEX idx_training_metrics_tss ON training_metrics(tss);

-- Add comment
COMMENT ON TABLE training_metrics IS 'Stores calculated training metrics (TSS, IF, TRIMP, zone distribution) for Strava activities';

