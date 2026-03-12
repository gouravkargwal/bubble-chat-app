package com.rizzbot.v2.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ── Auth ──

@Serializable
data class FirebaseAuthRequest(
    @SerialName("firebase_token") val firebaseToken: String
)

@Serializable
data class AuthResponse(
    val token: String,
    @SerialName("user_id") val userId: String,
    @SerialName("expires_at") val expiresAt: Long,
    val email: String? = null,
    @SerialName("display_name") val displayName: String? = null
)

// ── Vision / Generate ──

@Serializable
data class VisionGenerateRequest(
    val image: String? = null,
    val images: List<String>? = null,
    val direction: String = "quick_reply",
    @SerialName("custom_hint") val customHint: String? = null
)

@Serializable
data class VisionGenerateResponse(
    val replies: List<String>,
    @SerialName("person_name") val personName: String? = null,
    val stage: String? = null,
    @SerialName("interaction_id") val interactionId: String,
    @SerialName("usage_remaining") val usageRemaining: Int
)

// ── Vision / Calibration (Voice DNA) ──

@Serializable
data class CalibrationRequest(
    val images: List<String>
)

@Serializable
data class CalibrationResponse(
    @SerialName("messages_extracted") val messagesExtracted: Int,
    val success: Boolean
)

// ── Tracking ──

@Serializable
data class TrackCopyRequest(
    @SerialName("interaction_id") val interactionId: String,
    @SerialName("reply_index") val replyIndex: Int
)

@Serializable
data class TrackRatingRequest(
    @SerialName("interaction_id") val interactionId: String,
    @SerialName("reply_index") val replyIndex: Int,
    @SerialName("is_positive") val isPositive: Boolean
)

// ── Usage ──

@Serializable
data class UsageResponse(
    @SerialName("daily_limit") val dailyLimit: Int,
    @SerialName("daily_used") val dailyUsed: Int,
    @SerialName("is_premium") val isPremium: Boolean,
    val tier: String = "free",
    @SerialName("allowed_directions") val allowedDirections: List<String> = emptyList(),
    @SerialName("max_screenshots") val maxScreenshots: Int = 1,
    @SerialName("custom_hints") val customHints: Boolean = false,
    @SerialName("tier_expires_at") val tierExpiresAt: Long? = null,
    @SerialName("bonus_replies") val bonusReplies: Int = 0,
    @SerialName("total_replies_generated") val totalRepliesGenerated: Int = 0,
    @SerialName("total_replies_copied") val totalRepliesCopied: Int = 0
)

// ── Conversations ──

@Serializable
data class ConversationItem(
    val id: String,
    @SerialName("person_name") val personName: String? = null,
    val stage: String? = null,
    @SerialName("tone_trend") val toneTrend: String? = null,
    @SerialName("interaction_count") val interactionCount: Int = 0
)

@Serializable
data class ConversationListResponse(
    val conversations: List<ConversationItem>
)

// ── Referral ──

@Serializable
data class ReferralInfoResponse(
    @SerialName("referral_code") val referralCode: String,
    @SerialName("total_referrals") val totalReferrals: Int,
    @SerialName("bonus_replies_earned") val bonusRepliesEarned: Int,
    @SerialName("max_referrals") val maxReferrals: Int = 10
)

@Serializable
data class ApplyReferralRequest(
    val code: String
)

@Serializable
data class ApplyReferralResponse(
    @SerialName("tier_granted") val tierGranted: String,
    @SerialName("duration_hours") val durationHours: Int,
    @SerialName("expires_at") val expiresAt: Long
)

// ── Billing ──

@Serializable
data class VerifyPurchaseRequest(
    @SerialName("purchase_token") val purchaseToken: String,
    @SerialName("product_id") val productId: String,
    @SerialName("order_id") val orderId: String? = null
)

@Serializable
data class VerifyPurchaseResponse(
    @SerialName("is_valid") val isValid: Boolean,
    @SerialName("premium_until") val premiumUntil: Long? = null
)

@Serializable
data class BillingStatusResponse(
    @SerialName("is_premium") val isPremium: Boolean,
    val tier: String = "free",
    @SerialName("product_id") val productId: String? = null,
    @SerialName("expires_at") val expiresAt: Long? = null,
    @SerialName("auto_renewing") val autoRenewing: Boolean = false
)

// ── Promo ──

@Serializable
data class ApplyPromoRequest(
    val code: String
)

@Serializable
data class ApplyPromoResponse(
    @SerialName("tier_granted") val tierGranted: String,
    @SerialName("duration_days") val durationDays: Int,
    @SerialName("expires_at") val expiresAt: Long
)

// ── History ──

@Serializable
data class HistoryItemResponse(
    val id: String,
    @SerialName("person_name") val personName: String? = null,
    val direction: String,
    @SerialName("custom_hint") val customHint: String? = null,
    val replies: List<String>,
    @SerialName("copied_index") val copiedIndex: Int? = null,
    @SerialName("created_at") val createdAt: Long,
    @SerialName("user_organic_text") val userOrganicText: String? = null
)

@Serializable
data class HistoryListResponse(
    val items: List<HistoryItemResponse>
)

// ── User Preferences ──

@Serializable
data class VibeBreakdownItem(
    val name: String,
    val percentage: Float
)

@Serializable
data class UserPreferencesResponse(
    @SerialName("total_ratings") val totalRatings: Int,
    @SerialName("has_enough_data") val hasEnoughData: Boolean,
    @SerialName("vibe_breakdown") val vibeBreakdown: List<VibeBreakdownItem>,
    @SerialName("preferred_length") val preferredLength: String = "medium"
)
