-- Add HealthKit fields to workout_sessions table
-- Run this script to add HealthKit support to workout sessions

-- Add source column to track workout origin
ALTER TABLE workout_sessions 
ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'manual' NOT NULL;

-- Add HealthKit foreign key and UUID
ALTER TABLE workout_sessions 
ADD COLUMN IF NOT EXISTS healthkit_workout_id INTEGER REFERENCES healthkit_workouts(id) ON DELETE SET NULL;

ALTER TABLE workout_sessions 
ADD COLUMN IF NOT EXISTS healthkit_uuid VARCHAR(36);

-- Add HealthKit specific fields
ALTER TABLE workout_sessions 
ADD COLUMN IF NOT EXISTS active_energy_kcal FLOAT;

ALTER TABLE workout_sessions 
ADD COLUMN IF NOT EXISTS basal_energy_kcal FLOAT;

ALTER TABLE workout_sessions 
ADD COLUMN IF NOT EXISTS vo2_max FLOAT;

ALTER TABLE workout_sessions 
ADD COLUMN IF NOT EXISTS running_power_avg FLOAT;

ALTER TABLE workout_sessions 
ADD COLUMN IF NOT EXISTS running_power_max FLOAT;

ALTER TABLE workout_sessions 
ADD COLUMN IF NOT EXISTS ground_contact_time_avg FLOAT;

ALTER TABLE workout_sessions 
ADD COLUMN IF NOT EXISTS vertical_oscillation_avg FLOAT;

ALTER TABLE workout_sessions 
ADD COLUMN IF NOT EXISTS stride_length_avg FLOAT;

-- Add intervals data (JSON)
ALTER TABLE workout_sessions 
ADD COLUMN IF NOT EXISTS intervals_data JSONB;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_workout_sessions_source ON workout_sessions(source);
CREATE INDEX IF NOT EXISTS idx_workout_sessions_healthkit_workout_id ON workout_sessions(healthkit_workout_id);
CREATE INDEX IF NOT EXISTS idx_workout_sessions_healthkit_uuid ON workout_sessions(healthkit_uuid);

-- Add comments for documentation
COMMENT ON COLUMN workout_sessions.source IS 'Source of workout: plan, strava, healthkit, manual, apple_watch';
COMMENT ON COLUMN workout_sessions.healthkit_uuid IS 'HealthKit workout UUID if synced from Apple HealthKit';
COMMENT ON COLUMN workout_sessions.intervals_data IS 'Structured intervals data (warmup/main/cooldown) from HealthKit';

