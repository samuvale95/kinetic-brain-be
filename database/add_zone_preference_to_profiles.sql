-- Add zone preference field to user_profiles table

ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS preferred_zone_type VARCHAR(10) DEFAULT 'hr' CHECK (preferred_zone_type IN ('hr', 'pace', 'power'));

-- Add comment
COMMENT ON COLUMN user_profiles.preferred_zone_type IS 'User preference for zone calculation: hr, pace, or power';

