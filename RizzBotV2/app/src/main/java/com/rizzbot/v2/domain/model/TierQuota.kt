package com.rizzbot.v2.domain.model

/**
 * Numeric quota convention from the backend (usage `limits` map), after client normalization:
 * - [UNLIMITED_CAP] (0) — no cap for that quota (show “Unlimited”, skip progress bar).
 * - Negative values — feature not included on this plan (show “Not on your plan” / gate paywall).
 * - Positive values — finite cap (“used / limit” + progress).
 *
 * Exception: API `profile_blueprints_per_week` uses `0` for “not available on tier” (see
 * `tier_config.py` / profile optimizer 403). [HostedRepositoryImpl] maps that to [NOT_ON_PLAN].
 *
 * If a limit key is omitted in the API payload, the client chooses a default per field
 * (see [HostedRepositoryImpl] mapping).
 */
object TierQuota {
    const val UNLIMITED_CAP: Int = 0
    const val NOT_ON_PLAN: Int = -1

    // Plan name constants — match backend tier strings exactly
    const val PLAN_FREE: String = "free"
    const val PLAN_CRUSH: String = "crush"
    const val PLAN_MATCH: String = "match"
    const val PLAN_RIZZ: String = "rizz"

    // Credit cost per feature
    const val CREDIT_COST_CHAT: Int = 1
    const val CREDIT_COST_AUDIT: Int = 5
    const val CREDIT_COST_BLUEPRINT: Int = 8

    // Referral credit rewards
    const val REFERRER_CREDITS: Int = 10
    const val REFEREE_CREDITS: Int = 5

    fun isUnlimited(limit: Int): Boolean = limit == UNLIMITED_CAP

    fun isNotOnPlan(limit: Int): Boolean = limit < 0

    fun isFinite(limit: Int): Boolean = limit > 0

    fun billingPeriodNoun(period: String): String =
        when (period.lowercase()) {
            "weekly" -> "week"
            "monthly" -> "month"
            else -> period
        }
}
