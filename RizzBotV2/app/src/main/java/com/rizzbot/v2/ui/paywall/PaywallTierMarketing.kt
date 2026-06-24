package com.rizzbot.v2.ui.paywall

/**
 * Paywall marketing copy. Keep in sync with
 * `backend/app/core/tier_config.py` → BILLING_CREDITS / TIER_CONFIG.
 */
internal object PaywallTierMarketing {

    fun headlineForAppTier(appTier: String): String =
        when (appTier) {
            "crush" -> "Upgrade to Match or Rizz"
            "match" -> "Upgrade to Rizz"
            "rizz" -> "Manage your plan"
            else -> "Upgrade your wingman"
        }

    fun sublineForAppTier(appTier: String): String =
        when (appTier) {
            "crush" -> "Crush unlocks 7 reply modes, custom hints, and photo audits. Match adds Ask Out + Get Number + blueprints."
            "match" -> "Match unlocks all 9 reply modes, blueprints, and photo audits. Rizz gives you the most credits and max limits."
            "rizz" -> "You're on the top tier. Every feature, unlimited potential."
            else -> "Free gives you Openers, Quick Replies, Keep Playful, and Revive Chat. Upgrade for the full toolkit."
        }

    fun featureLines(selected: PaywallTier): List<String> =
        when (selected) {
            PaywallTier.Crush -> crushLines
            PaywallTier.Match -> matchLines
            PaywallTier.Rizz -> rizzLines
        }

    /** 60 credits / 7 days — ₹99/week */
    private val crushLines = listOf(
        "60 credits every week",
        "All 7 reply modes — except Get Number & Ask Out",
        "Custom hints & chemistry tracking",
        "Photo audit — 5 credits per audit",
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

    /** 250 credits / 30 days — ₹299/month */
    private val rizzLines = listOf(
        "250 credits every month",
        "All 9 reply modes — including Get Number & Ask Out",
        "Custom hints & chemistry tracking",
        "Photo audit & profile blueprint",
        "Up to 7 screenshots per reply — max everything",
    )
}
