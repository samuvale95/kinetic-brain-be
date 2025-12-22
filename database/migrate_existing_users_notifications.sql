-- Migration script to create default notification preferences for existing users
-- Run this script after creating the notification_preferences table

-- Insert default notification preferences for all existing users who don't have them yet
INSERT INTO notification_preferences (user_id, created_at, updated_at)
SELECT id, created_at, created_at
FROM users
WHERE id NOT IN (SELECT user_id FROM notification_preferences WHERE user_id IS NOT NULL);

-- Display how many users were updated
DO $$
DECLARE
    users_updated INTEGER;
BEGIN
    SELECT COUNT(*) INTO users_updated
    FROM notification_preferences;
    
    RAISE NOTICE '====================================================';
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE 'Total users with notification preferences: %', users_updated;
    RAISE NOTICE '====================================================';
END $$;

