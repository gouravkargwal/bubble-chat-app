package com.rizzbot.v2.ui.paywall

/**
 * Paywall marketing copy and numeric limits. Keep in sync with
 * `backend/app/core/tier_config.py` → [TIER_CONFIG] for `pro` and `premium`.
 */
internal object PaywallTierMarketing {

    fun headlineForAppTier(appTier: String): String =
        when (appTier) {
            "pro" -> "Go beyond Pro"
            "premium", "god_mode" -> "Manage your plan"
            else -> "Upgrade your wingman"
        }

    fun sublineForAppTier(appTier: String): String =
        when (appTier) {
            "pro" ->
                "You’re on Pro — Premium unlocks higher caps, more profile tools, and God-Mode Auditor."
            "premium", "god_mode" ->
                "You already have top-tier limits. Renew or switch billing below."
            else ->
                "Pro and Premium use the same app — pick the limits that fit how you chat."
        }

    fun featureLines(selected: PaywallTier): List<String> =
        when (selected) {
            PaywallTier.Pro -> proLines
            PaywallTier.Premium -> premiumLines
        }

    /** Mirrors TIER_CONFIG["pro"].limits + key features */
    private val proLines = listOf(
        "Up to 20 AI replies per day",
        "Up to 5 screenshots per reply",
        "Up to 3 profile photo audits per week (6 photos each)",
        "Up to 1 profile optimizer blueprint per week",
        "Custom hints and expanded reply vibes",
    )

    /** Mirrors TIER_CONFIG["premium"].limits + product extras */
    private val premiumLines = listOf(
        "Up to 50 AI replies per day",
        "Up to 7 screenshots per reply",
        "Up to 10 profile photo audits per week (10 photos each)",
        "Up to 3 profile optimizer blueprints per week",
        "Everything in Pro, plus higher caps & God-Mode Auditor",
    )
}
