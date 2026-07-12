package com.rizzbot.v2.domain.model

data class ReferralInfo(
    val referralCode: String,
    val totalReferrals: Int,
    val bonusRepliesEarned: Int,
    val maxReferrals: Int = 10
)
