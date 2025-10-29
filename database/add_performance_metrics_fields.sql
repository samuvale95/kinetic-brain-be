-- Add new performance metrics fields to performance_metrics table
-- This script adds all the fields required for the new performance metrics structure

-- Make threshold_value and metric_type nullable (for backward compatibility)
ALTER TABLE performance_metrics ALTER COLUMN threshold_value DROP NOT NULL;
ALTER TABLE performance_metrics ALTER COLUMN metric_type DROP NOT NULL;

-- HR Metrics
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS hr_max FLOAT;
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS hr_rest FLOAT;
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS threshold_hr FLOAT;
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS hrr FLOAT;
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS custom_threshold_hr FLOAT;

-- Pace Metrics
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS threshold_pace VARCHAR(10);
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS critical_speed FLOAT;
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS vla FLOAT;

-- Power Metrics
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS ftp FLOAT;
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS wkg FLOAT;

-- Advanced Metrics
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS vo2max FLOAT;

-- Structured Zones
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS hr_zones JSONB;
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS hr_zones_source VARCHAR(10);
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS hr_threshold_used FLOAT;

ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS pace_zones JSONB;
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS pace_zones_source VARCHAR(10);
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS threshold_pace_used VARCHAR(10);

ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS power_zones JSONB;
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS power_zones_source VARCHAR(10);
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS ftp_used FLOAT;

-- Add updated_at column
ALTER TABLE performance_metrics ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;

-- Add comments for documentation
COMMENT ON COLUMN performance_metrics.hr_max IS 'Maximum heart rate';
COMMENT ON COLUMN performance_metrics.hr_rest IS 'Resting heart rate';
COMMENT ON COLUMN performance_metrics.threshold_hr IS 'Heart rate at lactate threshold';
COMMENT ON COLUMN performance_metrics.hrr IS 'Heart Rate Reserve (hr_max - hr_rest)';
COMMENT ON COLUMN performance_metrics.threshold_pace IS 'Pace at lactate threshold (format: mm:ss or mm.ss)';
COMMENT ON COLUMN performance_metrics.ftp IS 'Functional Threshold Power';
COMMENT ON COLUMN performance_metrics.wkg IS 'Watts per kilogram';
COMMENT ON COLUMN performance_metrics.hr_zones IS 'HR zones in format {z1: "120-135", z2: "135-150", ...}';
COMMENT ON COLUMN performance_metrics.hr_zones_source IS 'Source of HR zones: auto or manual';
COMMENT ON COLUMN performance_metrics.pace_zones IS 'Pace zones in format {z1: "5:00-4:45", z2: "4:45-4:30", ...}';
COMMENT ON COLUMN performance_metrics.pace_zones_source IS 'Source of pace zones: auto or manual';
COMMENT ON COLUMN performance_metrics.power_zones IS 'Power zones in format {z1: "0-165", ..., z7: "451-540"}';
COMMENT ON COLUMN performance_metrics.power_zones_source IS 'Source of power zones: auto or manual';

