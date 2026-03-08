package com.rizzbot.v2.domain.model

data class HostedModeState(
    val isAuthenticated: Boolean = false,
    val isPremium: Boolean = false,
    val dailyLimit: Int = 5,
    val dailyUsed: Int = 0,
    val bonusReplies: Int = 0,
    val referralCode: String? = null
) {
    val dailyRemaining: Int
        get() = if (isPremium) Int.MAX_VALUE else (dailyLimit - dailyUsed + bonusReplies).coerceAtLeast(0)

    val canGenerate: Boolean
        get() = isPremium || dailyRemaining > 0
}

enum class UserTier {
    FREE_BYOK,      // Bring Your Own Key — unlimited
    FREE_HOSTED,    // Hosted — 3-5 free/day
    PREMIUM,        // $4.99/mo — unlimited hosted
    PRO             // $9.99/mo — everything + analytics
}
