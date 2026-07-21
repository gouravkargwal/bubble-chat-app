-- Remove all LTD (Lifetime Deal) tables, columns, and convert existing
-- LTD users to free tier. Run this as a single transaction.
--
-- WARNING: Back up ltd_redemption_codes before running this in production.
BEGIN;

-- 1. Drop LTD redemption codes table entirely
DROP TABLE IF EXISTS ltd_redemption_codes;

-- 2. Remove LTD columns from user_quotas
ALTER TABLE user_quotas
    DROP COLUMN IF EXISTS is_ltd,
    DROP COLUMN IF EXISTS ltd_refill_credits,
    DROP COLUMN IF EXISTS ltd_refill_days;

-- 3. Snapshot LTD provider IDs BEFORE altering tier_source
CREATE TEMP TABLE _ltd_users ON COMMIT DROP AS
SELECT google_provider_id FROM users WHERE tier_source = 'ltd';

-- 4. Reset quota credit pools for formerly-LTD users
-- NOTE: signup_bonus_granted is reset to FALSE intentionally so these
-- users will receive the standard 10-credit signup bonus on next login
-- as a goodwill gesture for the involuntary tier downgrade.
UPDATE user_quotas
SET credits_remaining = 0,
    credits_period_limit = 0,
    credits_reset_at = NULL,
    signup_bonus_granted = FALSE
WHERE google_provider_id IN (SELECT google_provider_id FROM _ltd_users);

-- 5. Convert existing LTD users to free tier
UPDATE users
SET tier = 'free',
    tier_source = 'signup',
    tier_expires_at = NULL,
    plan_period_start = NULL
WHERE tier_source = 'ltd';

COMMIT;
