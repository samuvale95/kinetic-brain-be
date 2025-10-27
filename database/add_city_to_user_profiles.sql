-- Migration: Add city field to user_profiles table
-- Execute this manually on your RDS database

ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS city VARCHAR(100);

COMMENT ON COLUMN user_profiles.city IS 'City for weather location';


