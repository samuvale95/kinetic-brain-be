-- Add calculated metrics fields to strava_activities table
-- These fields store the calculated values for quick access

ALTER TABLE strava_activities 
ADD COLUMN IF NOT EXISTS tss FLOAT,
ADD COLUMN IF NOT EXISTS normalized_power FLOAT,
ADD COLUMN IF NOT EXISTS intensity_factor FLOAT,
ADD COLUMN IF NOT EXISTS trimp FLOAT,
ADD COLUMN IF NOT EXISTS time_in_zone_1 INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS time_in_zone_2 INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS time_in_zone_3 INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS time_in_zone_4 INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS time_in_zone_5 INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS metrics_calculated BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS zone_distribution JSON;

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_strava_activities_tss ON strava_activities(tss);
CREATE INDEX IF NOT EXISTS idx_strava_activities_metrics_calculated ON strava_activities(metrics_calculated);

-- Add comments
COMMENT ON COLUMN strava_activities.tss IS 'Training Stress Score - calculated from duration and IF';
COMMENT ON COLUMN strava_activities.normalized_power IS 'Normalized power (cycling)';
COMMENT ON COLUMN strava_activities.intensity_factor IS 'Intensity Factor - ratio of normalized power to threshold';
COMMENT ON COLUMN strava_activities.trimp IS 'Training Impulse - HR-based training load metric';
COMMENT ON COLUMN strava_activities.metrics_calculated IS 'Flag indicating if metrics have been calculated';
COMMENT ON COLUMN strava_activities.zone_distribution IS 'JSON object with time spent in each zone';

