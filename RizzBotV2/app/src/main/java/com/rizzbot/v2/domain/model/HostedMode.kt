package com.rizzbot.v2.domain.model

data class UsageState(
    val isPremium: Boolean = false,
    val tier: String = "free",
    val dailyLimit: Int = 5,
    val dailyUsed: Int = 0,
    val bonusReplies: Int = 0,
    val allowedDirections: List<String> = listOf("quick_reply", "keep_playful"),
    val customHintsEnabled: Boolean = false,
    val maxScreenshots: Int = 1,
    val premiumExpiresAt: Long? = null
) {
    val dailyRemaining: Int
        get() = if (dailyLimit == 0) Int.MAX_VALUE else (dailyLimit - dailyUsed).coerceAtLeast(0)

    val canGenerate: Boolean
        get() = dailyLimit == 0 || dailyRemaining > 0

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
