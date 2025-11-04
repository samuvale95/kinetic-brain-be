-- Migration: Make strava_account_id nullable in strava_activities table
-- Purpose: Allow preserving Strava activities when disconnecting Strava account
-- Date: 2025-11-04
-- 
-- This migration allows strava_account_id to be NULL so that activities
-- can be preserved in the database when a user disconnects their Strava account.
-- This preserves historical metrics (TSS, TRIMP, etc.) even after disconnection.

-- Check if the column is already nullable (safe to run multiple times)
DO $$
BEGIN
    -- Check if column exists and is NOT NULL
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'strava_activities' 
        AND column_name = 'strava_account_id'
        AND is_nullable = 'NO'
    ) THEN
        -- Make the column nullable
        ALTER TABLE strava_activities 
        ALTER COLUMN strava_account_id DROP NOT NULL;
        
        RAISE NOTICE 'Column strava_account_id is now nullable';
    ELSE
        RAISE NOTICE 'Column strava_account_id is already nullable or does not exist';
    END IF;
END $$;

-- Add a comment to document the change
COMMENT ON COLUMN strava_activities.strava_account_id IS 
'Foreign key to strava_accounts. Can be NULL to preserve activities when account is disconnected.';

