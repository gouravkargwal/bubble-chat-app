package com.rizzbot.v2.data.remote.api

import com.rizzbot.v2.data.remote.dto.ApplyPromoRequest
import com.rizzbot.v2.data.remote.dto.ApplyPromoResponse
import com.rizzbot.v2.data.remote.dto.ApplyReferralRequest
import com.rizzbot.v2.data.remote.dto.ApplyReferralResponse
import com.rizzbot.v2.data.remote.dto.AuditResponse
import com.rizzbot.v2.data.remote.dto.AuthResponse
import com.rizzbot.v2.data.remote.dto.BillingStatusResponse
import com.rizzbot.v2.data.remote.dto.CalibrationRequest
import com.rizzbot.v2.data.remote.dto.CalibrationResponse
import com.rizzbot.v2.data.remote.dto.ConversationListResponse
import com.rizzbot.v2.data.remote.dto.FirebaseAuthRequest
import com.rizzbot.v2.data.remote.dto.HistoryListResponse
import com.rizzbot.v2.data.remote.dto.AuditedPhotoListResponse
import com.rizzbot.v2.data.remote.dto.ReferralInfoResponse
import com.rizzbot.v2.data.remote.dto.TrackCopyRequest
import com.rizzbot.v2.data.remote.dto.TrackRatingRequest
import com.rizzbot.v2.data.remote.dto.UsageResponse
import com.rizzbot.v2.data.remote.dto.UserPreferencesResponse
import com.rizzbot.v2.data.remote.dto.VerifyPurchaseRequest
import com.rizzbot.v2.data.remote.dto.VerifyPurchaseResponse
import com.rizzbot.v2.data.remote.dto.VisionGenerateRequest
import com.rizzbot.v2.data.remote.dto.VisionGenerateResponse
import com.rizzbot.v2.data.remote.dto.ProfileBlueprintDto
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface HostedApi {

    // Auth (no Authorization header — handled by AuthInterceptor skip list)
    @POST("api/v1/auth/firebase")
    suspend fun authenticateFirebase(@Body request: FirebaseAuthRequest): AuthResponse

    // Vision
    @POST("api/v1/vision/generate")
    suspend fun generateReply(@Body request: VisionGenerateRequest): VisionGenerateResponse

    @POST("api/v1/vision/calibrate")
    suspend fun calibrate(@Body request: CalibrationRequest): CalibrationResponse

    // Tracking
    @POST("api/v1/track/copy")
    suspend fun trackCopy(@Body request: TrackCopyRequest)

    @POST("api/v1/track/rating")
    suspend fun trackRating(@Body request: TrackRatingRequest)

    // Usage
    @GET("api/v1/usage")
    suspend fun getUsage(): UsageResponse

    // Conversations
    @GET("api/v1/conversations")
    suspend fun getConversations(): ConversationListResponse

    @DELETE("api/v1/conversations/{id}")
    suspend fun deleteConversation(@Path("id") id: String)

    // Referral
    @GET("api/v1/referral/me")
    suspend fun getReferralInfo(): ReferralInfoResponse

    @POST("api/v1/referral/apply")
    suspend fun applyReferral(@Body request: ApplyReferralRequest): ApplyReferralResponse

    // Billing
    @POST("api/v1/billing/verify")
    suspend fun verifyPurchase(@Body request: VerifyPurchaseRequest): VerifyPurchaseResponse

    @GET("api/v1/billing/status")
    suspend fun getBillingStatus(): BillingStatusResponse

    // Promo
    @POST("api/v1/promo/apply")
    suspend fun applyPromo(@Body request: ApplyPromoRequest): ApplyPromoResponse

    // History
    @GET("api/v1/history")
    suspend fun getHistory(@retrofit2.http.Query("limit") limit: Int = 20): HistoryListResponse

    @DELETE("api/v1/history/{id}")
    suspend fun deleteHistoryItem(@Path("id") id: String)

    // Preferences
    @GET("api/v1/preferences")
    suspend fun getUserPreferences(): UserPreferencesResponse

    // Profile Auditor
    @Multipart
    @POST("api/v1/profile-audit")
    suspend fun auditProfilePhotos(
        @Part images: List<MultipartBody.Part>,
        @Query("lang") lang: String? = null
    ): Response<AuditResponse>

    @GET("api/v1/profile-audit/history")
    suspend fun getProfileAuditHistory(): AuditedPhotoListResponse

    // Profile Optimizer
    @GET("api/v1/profile-audit/optimize")
    suspend fun optimizeProfile(
        @Query("lang") lang: String? = null
    ): Response<ProfileBlueprintDto>
}
