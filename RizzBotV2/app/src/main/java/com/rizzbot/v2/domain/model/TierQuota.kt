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

    fun isUnlimited(limit: Int): Boolean = limit == UNLIMITED_CAP

    fun isNotOnPlan(limit: Int): Boolean = limit < 0

    fun isFinite(limit: Int): Boolean = limit > 0

    fun billingPeriodNoun(period: String): String =
        when (period.lowercase()) {
            "daily" -> "day"
            "weekly" -> "week"
            "monthly" -> "month"
            else -> period
        }
}
