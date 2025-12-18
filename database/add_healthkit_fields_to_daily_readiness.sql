-- Add HealthKit fields to daily_readiness_metrics table
-- Run this script to add HealthKit sync support to daily readiness metrics

-- Add source column to track data origin
ALTER TABLE daily_readiness_metrics 
ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'manual' NOT NULL;

-- Add HealthKit sync fields
ALTER TABLE daily_readiness_metrics 
ADD COLUMN IF NOT EXISTS healthkit_sync_date TIMESTAMP WITH TIME ZONE;

ALTER TABLE daily_readiness_metrics 
ADD COLUMN IF NOT EXISTS healthkit_sync_anchor VARCHAR(255);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_daily_readiness_metrics_source ON daily_readiness_metrics(source);

-- Add comments for documentation
COMMENT ON COLUMN daily_readiness_metrics.source IS 'Source of data: manual, healthkit';
COMMENT ON COLUMN daily_readiness_metrics.healthkit_sync_anchor IS 'HealthKit anchor object for incremental sync';

