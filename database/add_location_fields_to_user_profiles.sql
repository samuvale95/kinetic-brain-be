-- Migration: Add location fields (city, latitude, longitude) to user_profiles table
-- Execute this manually on your RDS database

ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS city VARCHAR(100),
ADD COLUMN IF NOT EXISTS latitude FLOAT,
ADD COLUMN IF NOT EXISTS longitude FLOAT;

COMMENT ON COLUMN user_profiles.city IS 'City name for weather location';
COMMENT ON COLUMN user_profiles.latitude IS 'Latitude for weather (-90 to 90)';
COMMENT ON COLUMN user_profiles.longitude IS 'Longitude for weather (-180 to 180)';


