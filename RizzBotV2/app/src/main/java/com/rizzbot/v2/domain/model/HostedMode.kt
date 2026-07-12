package com.rizzbot.v2.domain.model

data class UsageState(
    val tier: String = TierQuota.PLAN_FREE,
    val creditsRemaining: Int = 0,
    val creditsPeriodLimit: Int = 0,
    val billingPeriod: String = "monthly",
    val tierExpiresAt: Long? = null,
    val allowedDirections: List<String> = listOf("opener", "quick_reply", "keep_playful", "revive_chat"),
    val customHintsEnabled: Boolean = false,
    val maxScreenshots: Int = 2,
    val maxPhotosPerAudit: Int = 3,
    val isLtd: Boolean = false,
) {
    val isPaidPlan: Boolean
        get() = tier == TierQuota.PLAN_CRUSH || tier == TierQuota.PLAN_MATCH

    /** For free tier: credits include signup bonus (10) + daily free (2/day, max 8 accumulation).
     *  For paid tier: just the period pool credits. */
    val canGenerate: Boolean
        get() = creditsRemaining > 0
/** For free users: returns the daily free credits component. */
val dailyFreeCredits: Int
    get() = if (tier == TierQuota.PLAN_FREE) TierQuota.FREE_DAILY_CREDITS else 0

    val trialDaysRemaining: Int
        get() {
            val expiresAt = tierExpiresAt ?: return -1
            val nowSec = System.currentTimeMillis() / 1000
            val diffDays = ((expiresAt - nowSec) / 86400).toInt()
            return diffDays.coerceAtLeast(0)
        }

    val isOnTrial: Boolean
        get() = tier == TierQuota.PLAN_MATCH && trialDaysRemaining in 0..30 && creditsPeriodLimit == 15
}
