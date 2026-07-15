-- 009_marketing_consent.sql
-- Add marketing_consent column to users table (default: true)
-- This flag is synced from the Android app's DataStore when the user toggles
-- the "Allow marketing use of my data" setting.

ALTER TABLE users ADD COLUMN IF NOT EXISTS marketing_consent BOOLEAN NOT NULL DEFAULT TRUE;
