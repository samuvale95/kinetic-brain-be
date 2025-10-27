-- Create weekly_performance_summary table
-- Stores weekly snapshots of CTL/ATL/TSB and aggregated statistics

CREATE TABLE IF NOT EXISTS weekly_performance_summary (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,
    
    -- Training metrics
    weekly_tss FLOAT DEFAULT 0,
    weekly_trimp FLOAT DEFAULT 0,
    volume_hours FLOAT DEFAULT 0,
    volume_kilometers FLOAT DEFAULT 0,
    
    -- Performance metrics (CTL/ATL/TSB)
    ctl FLOAT,  -- Chronic Training Load (fitness)
    atl FLOAT,  -- Acute Training Load (fatigue)
    tsb FLOAT,  -- Training Stress Balance (form)
    
    -- Workout statistics
    workouts_completed INTEGER DEFAULT 0,
    workouts_planned INTEGER DEFAULT 0,
    completion_rate FLOAT,
    avg_rpe FLOAT,
    
    -- Zone distribution
    zone_distribution JSON,
    
    -- Additional metrics
    avg_hr FLOAT,
    max_hr FLOAT,
    avg_pace FLOAT,
    total_elevation_gain FLOAT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Ensure one summary per user per week
    CONSTRAINT unique_user_week UNIQUE(user_id, week_start_date)
);

-- Indexes for performance
CREATE INDEX idx_weekly_summary_user ON weekly_performance_summary(user_id);
CREATE INDEX idx_weekly_summary_week_start ON weekly_performance_summary(week_start_date);
CREATE INDEX idx_weekly_summary_user_week ON weekly_performance_summary(user_id, week_start_date);

-- Add comments
COMMENT ON TABLE weekly_performance_summary IS 'Stores weekly performance summaries with CTL/ATL/TSB metrics';
COMMENT ON COLUMN weekly_performance_summary.ctl IS 'Chronic Training Load - 42-day exponential moving average of TSS';
COMMENT ON COLUMN weekly_performance_summary.atl IS 'Acute Training Load - 7-day exponential moving average of TSS';
COMMENT ON COLUMN weekly_performance_summary.tsb IS 'Training Stress Balance - CTL minus ATL';

