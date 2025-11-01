-- Create daily_performance_metrics table
-- Stores daily CTL/ATL/TSB calculated incrementally

CREATE TABLE IF NOT EXISTS daily_performance_metrics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    
    -- Daily TSS (sum of all activities for this day)
    daily_tss FLOAT DEFAULT 0,
    
    -- Calculated metrics (incremental EMA)
    ctl FLOAT,  -- Chronic Training Load (fitness) - 42-day EMA
    atl FLOAT,  -- Acute Training Load (fatigue) - 7-day EMA
    tsb FLOAT,  -- Training Stress Balance (form) - CTL - ATL
    
    -- Previous day values (for incremental calculation)
    prev_ctl FLOAT,  -- CTL del giorno precedente
    prev_atl FLOAT,  -- ATL del giorno precedente
    
    -- Metadata
    activities_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Ensure one record per user per day
    CONSTRAINT unique_user_date UNIQUE(user_id, metric_date)
);

-- Indexes for performance
CREATE INDEX idx_daily_metrics_user ON daily_performance_metrics(user_id);
CREATE INDEX idx_daily_metrics_date ON daily_performance_metrics(metric_date);
CREATE INDEX idx_daily_metrics_user_date ON daily_performance_metrics(user_id, metric_date);

-- Comments
COMMENT ON TABLE daily_performance_metrics IS 'Stores daily CTL/ATL/TSB metrics calculated incrementally';
COMMENT ON COLUMN daily_performance_metrics.ctl IS 'Chronic Training Load - 42-day exponential moving average of TSS';
COMMENT ON COLUMN daily_performance_metrics.atl IS 'Acute Training Load - 7-day exponential moving average of TSS';
COMMENT ON COLUMN daily_performance_metrics.tsb IS 'Training Stress Balance - CTL minus ATL';

