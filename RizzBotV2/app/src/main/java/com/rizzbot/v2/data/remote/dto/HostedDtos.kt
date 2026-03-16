package com.rizzbot.v2.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ── Auth ──

@Serializable
data class FirebaseAuthRequest(
    @SerialName("firebase_token") val firebaseToken: String,
    // Stable Google provider ID taken from FirebaseUser.providerData where providerId == "google.com".
    // This is the primary key for the server-side user_quotas table and MUST remain stable even if
    // the Firebase UID or account on this device changes.
    @SerialName("google_provider_id") val googleProviderId: String? = null
)

@Serializable
data class AuthResponse(
    val token: String,
    @SerialName("user_id") val userId: String,
    @SerialName("expires_at") val expiresAt: Long,
    val email: String? = null,
    @SerialName("display_name") val displayName: String? = null,
    @SerialName("is_new_user") val isNewUser: Boolean = false
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
    val replies: List<ReplyOption>,
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
    @SerialName("weekly_used") val weeklyUsed: Int = 0,
    @SerialName("monthly_used") val monthlyUsed: Int = 0,
    @SerialName("weekly_audits_used") val weeklyAuditsUsed: Int = 0,
    @SerialName("weekly_blueprints_used") val weeklyBlueprintsUsed: Int = 0,
    @SerialName("is_premium") val isPremium: Boolean,
    val tier: String = "free",
    @SerialName("allowed_directions") val allowedDirections: List<String> = emptyList(),
    @SerialName("max_screenshots") val maxScreenshots: Int = 1,
    @SerialName("custom_hints") val customHints: Boolean = false,
    @SerialName("tier_expires_at") val tierExpiresAt: Long? = null,
    @SerialName("god_mode_expires_at") val godModeExpiresAt: Long? = null,
    @SerialName("bonus_replies") val bonusReplies: Int = 0,
    @SerialName("total_replies_generated") val totalRepliesGenerated: Int = 0,
    @SerialName("total_replies_copied") val totalRepliesCopied: Int = 0,
    val limits: Map<String, kotlinx.serialization.json.JsonElement> = emptyMap(),
    val features: Map<String, kotlinx.serialization.json.JsonElement> = emptyMap(),
    @SerialName("billing_period") val billingPeriod: String = "daily"
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
    val items: List<ConversationItem>,
    @SerialName("total_count") val totalCount: Int,
    val limit: Int,
    val offset: Int
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
    val code: String,
    @SerialName("device_id") val deviceId: String? = null
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

// ── History ──

@Serializable
data class HistoryItemResponse(
    val id: String,
    @SerialName("person_name") val personName: String? = null,
    val direction: String,
    @SerialName("custom_hint") val customHint: String? = null,
    val replies: List<ReplyOption>,
    @SerialName("copied_index") val copiedIndex: Int? = null,
    @SerialName("created_at") val createdAt: Long,
    @SerialName("user_organic_text") val userOrganicText: String? = null
)

@Serializable
data class HistoryListResponse(
    val items: List<HistoryItemResponse>,
    @SerialName("total_count") val totalCount: Int,
    val limit: Int,
    val offset: Int
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

// ── Profile Auditor ──

@Serializable
data class PhotoFeedbackDto(
    @SerialName("photo_id") val photoId: String,
    val score: Int,
    val tier: String,
    @SerialName("brutal_feedback") val brutalFeedback: String,
    @SerialName("improvement_tip") val improvementTip: String
)

@Serializable
data class AuditResponse(
    @SerialName("total_analyzed") val totalAnalyzed: Int,
    @SerialName("passed_count") val passedCount: Int,
    @SerialName("is_hard_reset") val isHardReset: Boolean,
    @SerialName("archetype_title") val archetypeTitle: String = "",
    @SerialName("roast_summary") val roastSummary: String = "",
    @SerialName("share_card_color") val shareCardColor: String = "#FFD700",
    val photos: List<PhotoFeedbackDto>
)

@Serializable
data class AuditedPhotoItemDto(
    val id: String,
    val score: Int,
    val tier: String,
    @SerialName("brutal_feedback") val brutalFeedback: String,
    @SerialName("improvement_tip") val improvementTip: String,
    @SerialName("archetype_title") val archetypeTitle: String = "",
    @SerialName("roast_summary") val roastSummary: String = "",
    @SerialName("share_card_color") val shareCardColor: String = "#FFD700",
    @SerialName("image_url") val imageUrl: String,
    @SerialName("created_at") val createdAt: Long
)

@Serializable
data class AuditedPhotoListResponse(
    val items: List<AuditedPhotoItemDto>,
    @SerialName("total_count") val totalCount: Int,
    val limit: Int,
    val offset: Int
)

// ── Profile Optimizer ──

@Serializable
data class OptimizedSlotDto(
    val id: String,
    @SerialName("photo_id") val photoId: String,
    @SerialName("image_url") val imageUrl: String,
    @SerialName("slot_number") val slotNumber: Int,
    val role: String,
    val caption: String,
    @SerialName("universal_hook") val universalHook: String,
    @SerialName("hinge_prompt") val hingePrompt: String = "",
    @SerialName("aisle_prompt") val aislePrompt: String = ""
)

@Serializable
data class UniversalPromptDto(
    val category: String,
    @SerialName("suggested_text") val suggestedText: String
)

@Serializable
data class ProfileBlueprintDto(
    val id: String,
    @SerialName("user_id") val userId: String,
    @SerialName("overall_theme") val overallTheme: String,
    val bio: String = "",
    @SerialName("created_at") val createdAt: String,
    @SerialName("universal_prompts") val universalPrompts: List<UniversalPromptDto>? = null,
    val slots: List<OptimizedSlotDto>
)

@Serializable
data class ProfileBlueprintListResponse(
    val items: List<ProfileBlueprintDto>,
    @SerialName("total_count") val totalCount: Int,
    val limit: Int,
    val offset: Int
)
