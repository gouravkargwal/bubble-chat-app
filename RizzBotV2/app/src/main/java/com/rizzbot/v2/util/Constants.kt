package com.rizzbot.v2.util

/**
 * Central constants file — single source of truth for all tunable values.
 *
 * ⚠️  Keep these in sync with backend values (see backend/app/core/tier_config.py
 *     and backend/app/infrastructure/database/models.py).
 */
object Constants {
    // ── Sync / Capture ──
    const val CAPTURE_COOLDOWN_MS = 3000L
    const val MEMORY_EXPIRY_HOURS = 1L
    const val IMAGE_QUALITY = 75
    const val IMAGE_MAX_WIDTH = 1080
    const val MAX_RETRIES = 2
    const val RETRY_INITIAL_DELAY_MS = 1000L
    const val SHARE_PROMPT_THRESHOLD = 5
    const val NOTIFICATION_CHANNEL_ID = "rizzbot_service"
    const val NOTIFICATION_ID = 1001
    const val CAPTURE_REQUEST_CODE = 2001

    // ── Features ──
    const val REPLY_HISTORY_MAX_ITEMS = 20
    const val REPLY_HISTORY_EXPIRY_DAYS = 7L
    const val MIN_RATINGS_FOR_PREFERENCES = 20

    // ── Credits & Tiers ──
    /** One-time signup bonus credits (matches backend FREE_SIGNUP_CREDITS=10 in tier_config.py). */
    const val SIGNUP_BONUS_CREDITS = 10

    /** Free tier daily credits (matches backend FREE_DAILY_CREDITS=1 in tier_config.py). */
    const val FREE_DAILY_CREDITS = 1

    /** Credit cost per chat generation (matches backend CREDIT_COSTS["chat_generation"]). */
    const val CREDIT_COST_CHAT = 1

    /** Credit cost per photo audit (matches backend CREDIT_COSTS["profile_audit"]). */
    const val CREDIT_COST_AUDIT = 8

    /** Credit cost per profile blueprint (matches backend CREDIT_COSTS["profile_blueprint"]). */
    const val CREDIT_COST_BLUEPRINT = 12

    /** Referral rewards (matches backend referral logic). */
    const val REFERRER_CREDITS = 10
    const val REFEREE_CREDITS = 5
    const val MAX_REFERRALS = 10

    // ── PayU / LTD ──
    /** URL to the landing page LTD section (opens in browser). */
    const val LTD_LANDING_URL = "https://cookd.app/#pricing"
}
