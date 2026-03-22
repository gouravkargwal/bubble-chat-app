package com.rizzbot.v2.domain.model

import java.time.Instant

data class UsageState(
    val isPremium: Boolean = false,
    val tier: String = "free",
    val dailyLimit: Int = 5,
    val dailyUsed: Int = 0,
    val weeklyUsed: Int = 0,
    val monthlyUsed: Int = 0,
    val profileAuditsPerWeek: Int = 1,  // From limits map
    val weeklyAuditsUsed: Int = 0,  // From backend
    val bonusReplies: Int = 0,
    val allowedDirections: List<String> = listOf("quick_reply", "keep_playful"),
    val customHintsEnabled: Boolean = false,
    val maxScreenshots: Int = 1,
    val premiumExpiresAt: Long? = null,
    val godModeExpiresAt: Instant? = null,  // UTC timestamp for 24-hour referral reward
    val totalRepliesGenerated: Int = 0,  // Total from backend
    val totalRepliesCopied: Int = 0,  // Total from backend
    val maxPhotosPerAudit: Int = 3,  // Default to free tier limit
    /** See [TierQuota]; default before first fetch = not on plan. */
    val profileBlueprintsPerWeek: Int = TierQuota.NOT_ON_PLAN,
    val weeklyBlueprintsUsed: Int = 0,  // From backend
    val billingPeriod: String = "daily"  // "daily", "weekly", or "monthly"
) {
    /** Paid entitlement or referral God Mode window (matches tier checks across the app). */
    val isGodModeActive: Boolean
        get() = tier == "premium" || tier == "god_mode"

    val dailyRemaining: Int
        get() =
            if (TierQuota.isUnlimited(dailyLimit)) Int.MAX_VALUE
            else (dailyLimit - dailyUsed).coerceAtLeast(0)

    val canGenerate: Boolean
        get() = TierQuota.isUnlimited(dailyLimit) || dailyRemaining > 0

    val trialDaysRemaining: Int
        get() {
            val expiresAt = premiumExpiresAt ?: return -1
            val nowSec = System.currentTimeMillis() / 1000
            val diffDays = ((expiresAt - nowSec) / 86400).toInt()
            return diffDays.coerceAtLeast(0)
        }
}

data class ReferralInfo(
    val referralCode: String = "",
    val totalReferrals: Int = 0,
    val bonusRepliesEarned: Int = 0,
    val maxReferrals: Int = 10
)
