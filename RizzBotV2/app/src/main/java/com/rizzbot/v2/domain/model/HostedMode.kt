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
) {
    val isPaidPlan: Boolean
        get() = tier == TierQuota.PLAN_CRUSH || tier == TierQuota.PLAN_MATCH || tier == TierQuota.PLAN_RIZZ

    val canGenerate: Boolean
        get() = creditsRemaining > 0

    val trialDaysRemaining: Int
        get() {
            val expiresAt = tierExpiresAt ?: return -1
            val nowSec = System.currentTimeMillis() / 1000
            val diffDays = ((expiresAt - nowSec) / 86400).toInt()
            return diffDays.coerceAtLeast(0)
        }

    val isOnTrial: Boolean
        get() = tier == TierQuota.PLAN_RIZZ && trialDaysRemaining in 0..3 && creditsPeriodLimit == 15
}

data class ReferralInfo(
    val referralCode: String = "",
    val totalReferrals: Int = 0,
    val bonusRepliesEarned: Int = 0,
    val maxReferrals: Int = 10
)
