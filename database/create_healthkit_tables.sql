-- HealthKit Integration Tables
-- Run this script to create HealthKit tables manually

-- HealthKit Workouts Table
CREATE TABLE IF NOT EXISTS healthkit_workouts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workout_id INTEGER REFERENCES workouts(id) ON DELETE SET NULL,
    
    -- HealthKit Identifiers
    hk_workout_uuid VARCHAR(36) UNIQUE NOT NULL,
    hk_source_name VARCHAR(255),
    
    -- Workout Basic Info
    workout_type VARCHAR(50) NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_seconds INTEGER NOT NULL,
    
    -- Distance and Energy
    total_distance_meters FLOAT,
    total_energy_burned_kcal FLOAT,
    total_basal_energy_kcal FLOAT,
    
    -- Elevation
    elevation_gain_meters FLOAT,
    elevation_loss_meters FLOAT,
    
    -- Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word conflict)
    hk_metadata JSONB,
    
    -- Sync Status
    sync_status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    -- Values: 'pending', 'synced', 'matched', 'ignored'
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_healthkit_workouts_user_id ON healthkit_workouts(user_id);
CREATE INDEX IF NOT EXISTS idx_healthkit_workouts_workout_id ON healthkit_workouts(workout_id);
CREATE INDEX IF NOT EXISTS idx_healthkit_workouts_hk_workout_uuid ON healthkit_workouts(hk_workout_uuid);
CREATE INDEX IF NOT EXISTS idx_healthkit_workouts_workout_type ON healthkit_workouts(workout_type);
CREATE INDEX IF NOT EXISTS idx_healthkit_workouts_start_date ON healthkit_workouts(start_date);
CREATE INDEX IF NOT EXISTS idx_healthkit_workouts_sync_status ON healthkit_workouts(sync_status);

-- Add comments for documentation
COMMENT ON TABLE healthkit_workouts IS 'Stores workouts imported from Apple HealthKit';
COMMENT ON COLUMN healthkit_workouts.hk_workout_uuid IS 'Unique identifier from HealthKit (UUID)';
COMMENT ON COLUMN healthkit_workouts.sync_status IS 'Status: pending, synced, matched, ignored';
COMMENT ON COLUMN healthkit_workouts.hk_metadata IS 'Additional metadata from HealthKit (device, weather, etc.)';

