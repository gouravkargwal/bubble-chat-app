package com.rizzbot.v2.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class HostedAuthResponse(
    val token: String,
    @SerialName("user_id") val userId: String,
    @SerialName("expires_at") val expiresAt: Long
)

@Serializable
data class HostedVisionRequest(
    val image: String,
    @SerialName("system_prompt") val systemPrompt: String,
    @SerialName("user_prompt") val userPrompt: String,
    val direction: String? = null
)

@Serializable
data class HostedVisionResponse(
    val replies: List<String>,
    val summary: String,
    @SerialName("person_name") val personName: String? = null,
    @SerialName("usage_remaining") val usageRemaining: Int
)

@Serializable
data class HostedUsageResponse(
    @SerialName("daily_limit") val dailyLimit: Int,
    @SerialName("daily_used") val dailyUsed: Int,
    @SerialName("is_premium") val isPremium: Boolean,
    @SerialName("premium_expires_at") val premiumExpiresAt: Long? = null
)

@Serializable
data class ReferralRequest(
    @SerialName("referral_code") val referralCode: String
)

@Serializable
data class ReferralResponse(
    @SerialName("bonus_replies") val bonusReplies: Int,
    val message: String
)
