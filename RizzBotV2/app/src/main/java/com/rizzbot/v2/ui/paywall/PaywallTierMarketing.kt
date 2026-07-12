package com.rizzbot.v2.ui.paywall

/**
 * Paywall marketing copy. Keep in sync with
 * `backend/app/core/tier_config.py` → BILLING_CREDITS / TIER_CONFIG.
 */
internal object PaywallTierMarketing {

    fun headlineForAppTier(appTier: String): String =
        when (appTier) {
            "crush" -> "Upgrade to Match"
            "match" -> "Manage your plan"
            else -> "Upgrade your wingman"
        }

    /** Is the given app tier an LTD (Lifetime Deal) purchase? */
    fun isLtdTier(appTier: String): Boolean =
        appTier == "match_ltd"

    fun sublineForAppTier(appTier: String): String =
        when (appTier) {
            "crush" -> "Crush unlocks 7 reply modes, custom hints, and photo audits. Match adds Ask Out + Get Number + blueprints."
            "match" -> "Match unlocks all 9 reply modes, blueprints, and photo audits."
            else -> "Free gives you Openers, Quick Replies, Keep Playful, and Revive Chat. Upgrade for the full toolkit."
        }

    fun featureLines(selected: PaywallTier): List<String> =
        when (selected) {
            PaywallTier.Crush -> crushLines
            PaywallTier.Match -> matchLines
        }

    /** 50 credits / 7 days — ₹99/week */
    private val crushLines = listOf(
        "50 credits every week",
        "All 7 reply modes — except Get Number & Ask Out",
        "Custom hints & chemistry tracking",
        "Photo audit — 8 credits per audit",
        "Up to 5 screenshots per reply",
    )

    /** 150 credits / 30 days — ₹179/month */
    private val matchLines = listOf(
        "150 credits every month",
        "All 9 reply modes — including Get Number & Ask Out",
        "Custom hints & chemistry tracking",
        "Photo audit & profile blueprint",
        "Up to 5 screenshots per reply",
    )
}
