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
            "crush" -> "You're on Crush — Match and Rizz unlock more credits and premium tools."
            "match" -> "You're on Match — Rizz gives you the most credits and every feature unlocked."
            "rizz" -> "You're already on the top tier. Renew or extend below."
            else -> "Pick a plan and start winning more conversations."
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
        "1 credit per AI reply, 5 per photo audit, 8 per blueprint",
        "Up to 5 screenshots per reply",
        "Custom hints & all reply vibes",
        "Chemistry tracking across conversations",
    )

    /** 150 credits / 30 days — ₹179/month */
    private val matchLines = listOf(
        "150 credits every month",
        "1 credit per AI reply, 5 per photo audit, 8 per blueprint",
        "Up to 5 screenshots per reply",
        "Custom hints & all reply vibes",
        "Chemistry tracking across conversations",
    )

    /** 250 credits / 30 days — ₹299/month */
    private val rizzLines = listOf(
        "250 credits every month",
        "1 credit per AI reply, 5 per photo audit, 8 per blueprint",
        "Up to 7 screenshots per reply",
        "Get Number & Ask Out reply modes",
        "Everything in Match, plus maximum credits",
    )
}
