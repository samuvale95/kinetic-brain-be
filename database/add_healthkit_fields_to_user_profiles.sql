-- Add HealthKit fields to user_profiles table
-- Run this script to add HealthKit integration support to user profiles

-- Add HealthKit fields
ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS healthkit_enabled BOOLEAN DEFAULT FALSE NOT NULL;

ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS healthkit_last_sync TIMESTAMP WITH TIME ZONE;

ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS healthkit_permissions JSONB;

ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS healthkit_workout_anchor VARCHAR(255);

ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS healthkit_health_anchor VARCHAR(255);

-- Add comments for documentation
COMMENT ON COLUMN user_profiles.healthkit_enabled IS 'Whether HealthKit integration is enabled for this user';
COMMENT ON COLUMN user_profiles.healthkit_permissions IS 'JSON object with HealthKit permission flags (workouts, heart_rate, hrv, sleep, weight, etc.)';
COMMENT ON COLUMN user_profiles.healthkit_workout_anchor IS 'Anchor object for incremental HealthKit workout sync';
COMMENT ON COLUMN user_profiles.healthkit_health_anchor IS 'Anchor object for incremental HealthKit health data sync';

