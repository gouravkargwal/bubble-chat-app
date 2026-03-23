package com.rizzbot.v2.data.repository

import android.content.Context
import android.content.Intent
import android.provider.Settings
import android.util.Log
import com.rizzbot.v2.data.auth.AuthManager
import com.rizzbot.v2.data.remote.api.HostedApi
import com.rizzbot.v2.data.remote.dto.ApplyReferralRequest
import com.rizzbot.v2.data.remote.dto.ApplyReferralResponse
import com.rizzbot.v2.data.remote.dto.AuditResponse
import com.rizzbot.v2.data.remote.dto.HistoryItemResponse
import com.rizzbot.v2.data.remote.dto.AuditedPhotoItemDto
import com.rizzbot.v2.data.remote.dto.TrackCopyRequest
import com.rizzbot.v2.data.remote.dto.TrackRatingRequest
import com.rizzbot.v2.data.remote.dto.ResolveConversationRequest
import com.rizzbot.v2.data.remote.dto.RequiresUserConfirmationResponse
import com.rizzbot.v2.data.remote.dto.UserPreferencesResponse
import com.rizzbot.v2.data.remote.dto.UsageResponse
import com.rizzbot.v2.data.remote.dto.VerifyPurchaseRequest
import com.rizzbot.v2.data.remote.dto.VisionGenerateRequest
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.ReferralInfo
import com.rizzbot.v2.domain.model.SuggestedMatch
import com.rizzbot.v2.domain.model.SuggestedMatchContextPreview
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.model.TierQuota
import com.rizzbot.v2.domain.model.UsageState
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.overlay.OverlayService
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.HttpException
import java.net.SocketTimeoutException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class HostedRepositoryImpl @Inject constructor(
    private val hostedApi: HostedApi,
    private val authManager: dagger.Lazy<AuthManager>,
    @ApplicationContext private val context: Context
) : HostedRepository {

    private val _usageState = MutableStateFlow(UsageState())
    override val usageState: StateFlow<UsageState> = _usageState.asStateFlow()
    
    // TTL cache for usage data to prevent over-fetching
    private var lastUsageFetchTime: Long = 0
    private val USAGE_CACHE_TTL_MS = 5 * 60 * 1000L // 5 minutes

    /**
     * Concurrent [refreshUsage] calls (Settings pull-to-refresh, Home, Paywall, etc.) could finish
     * out of order; a slower stale response would overwrite a newer one. Serialize refreshes.
     */
    private val refreshUsageLock = Mutex()

    private fun limitIntFromMap(
        limits: Map<String, JsonElement>,
        key: String,
        ifMissing: Int
    ): Int = limits[key]?.let { el ->
        if (el is JsonPrimitive) el.content.toIntOrNull() ?: ifMissing else ifMissing
    } ?: ifMissing

    /**
     * Backend ([tier_config.profile_blueprints_per_week]): `0` = feature not on tier (403 on generate);
     * positive = weekly cap. This differs from quotas where `0` may mean unlimited — normalize here.
     */
    private fun profileBlueprintsPerWeekFromMap(limits: Map<String, JsonElement>): Int {
        val raw = limits["profile_blueprints_per_week"]
            ?.let { el -> if (el is JsonPrimitive) el.content.toIntOrNull() else null }
            ?: return TierQuota.NOT_ON_PLAN
        return when {
            raw <= 0 -> TierQuota.NOT_ON_PLAN
            else -> raw
        }
    }

    private fun usageStateFromResponse(usage: UsageResponse): UsageState {
        val maxPhotosPerAudit = limitIntFromMap(usage.limits, "max_photos_per_audit", 3)
        val profileAuditsPerWeek = limitIntFromMap(usage.limits, "profile_audits_per_week", 1)
        val profileBlueprintsPerWeek = profileBlueprintsPerWeekFromMap(usage.limits)
        return UsageState(
            dailyLimit = usage.dailyLimit,
            dailyUsed = usage.dailyUsed,
            weeklyUsed = usage.weeklyUsed,
            monthlyUsed = usage.monthlyUsed,
            profileAuditsPerWeek = profileAuditsPerWeek,
            weeklyAuditsUsed = usage.weeklyAuditsUsed,
            isPremium = usage.isPremium,
            tier = usage.tier,
            bonusReplies = usage.bonusReplies,
            allowedDirections = usage.allowedDirections,
            customHintsEnabled = usage.customHints,
            maxScreenshots = usage.maxScreenshots,
            premiumExpiresAt = usage.tierExpiresAt,
            godModeExpiresAt = usage.godModeExpiresAt?.let { sec ->
                try {
                    java.time.Instant.ofEpochSecond(sec)
                } catch (e: Exception) {
                    android.util.Log.w("HostedRepo", "Failed to parse godModeExpiresAt: ${e.message}")
                    null
                }
            },
            totalRepliesGenerated = usage.totalRepliesGenerated,
            totalRepliesCopied = usage.totalRepliesCopied,
            maxPhotosPerAudit = maxPhotosPerAudit,
            profileBlueprintsPerWeek = profileBlueprintsPerWeek,
            weeklyBlueprintsUsed = usage.weeklyBlueprintsUsed,
            billingPeriod = usage.billingPeriod
        )
    }

    override suspend fun generateReply(
        base64Images: List<String>,
        direction: DirectionWithHint
    ): SuggestionResult {
        return try {
            val response = hostedApi.generateReply(
                VisionGenerateRequest(
                    images = base64Images,
                    direction = direction.direction.name.lowercase(),
                    customHint = direction.customHint
                )
            )

            _usageState.value = _usageState.value.copy(
                dailyUsed = _usageState.value.dailyLimit - response.usageRemaining
            )

            SuggestionResult.Success(
                replies = response.replies,
                summary = response.personName ?: "",
                personName = response.personName,
                interactionId = response.interactionId,
                stage = response.stage,
                usageRemaining = response.usageRemaining
            )
        } catch (e: HttpException) {
            // If tier dropped but UI cache hasn't updated, force refresh usage
            if (e.code() == 403 || e.code() == 429) {
                try {
                    refreshUsage(force = true)
                } catch (refreshError: Exception) {
                    Log.w("HostedRepo", "Failed to refresh usage after ${e.code()}: ${refreshError.message}")
                }
            }
            
            when (e.code()) {
                409 -> {
                    val rawBody = e.response()?.errorBody()?.string()
                    val parsed = rawBody?.let { body ->
                        runCatching {
                            Json { ignoreUnknownKeys = true }
                                .decodeFromString(RequiresUserConfirmationResponse.serializer(), body)
                        }.getOrNull()
                    }

                    if (parsed?.status == "REQUIRES_USER_CONFIRMATION") {
                        val ctx = parsed.suggestedMatch.contextPreview
                        val suggestedMatch = SuggestedMatch(
                            personName = parsed.suggestedMatch.personName,
                            conversationId = parsed.suggestedMatch.conversationId,
                            lastActive = parsed.suggestedMatch.lastActive,
                            contextPreview = SuggestedMatchContextPreview(
                                herLastMessage = ctx.herLastMessage,
                                yourLastReply = ctx.yourLastReply,
                                aiMemoryNote = ctx.aiMemoryNote
                            )
                        )
                        SuggestionResult.RequiresUserConfirmation(suggestedMatch)
                    } else {
                        SuggestionResult.Error(
                            message = "New chat detected. Please confirm.",
                            errorType = SuggestionResult.ErrorType.UNKNOWN
                        )
                    }
                }
                // 403 = Forbidden (tier/permission issue)
                403 -> SuggestionResult.Error(
                    "Access denied. Your tier may have changed. Please refresh.",
                    SuggestionResult.ErrorType.QUOTA_EXCEEDED
                )
                // 429 is *only* used by the backend for app-level daily quota
                // (DB-based check before calling Gemini).
                429 -> SuggestionResult.Error(
                    "Daily limit reached. Upgrade for a higher reply allowance.",
                    SuggestionResult.ErrorType.QUOTA_EXCEEDED
                )
                401 -> SuggestionResult.Error(
                    "Session expired. Please restart the app.",
                    SuggestionResult.ErrorType.INVALID_API_KEY
                )
                // 5xx (including Gemini rate limits) are treated as "our side" issues.
                502 -> SuggestionResult.Error(
                    "AI is temporarily unavailable. Try again.",
                    SuggestionResult.ErrorType.UNKNOWN
                )
                else -> SuggestionResult.Error(
                    "Server error: ${e.code()}",
                    SuggestionResult.ErrorType.UNKNOWN
                )
            }
        } catch (e: SocketTimeoutException) {
            SuggestionResult.Error("Request timed out. Try again.", SuggestionResult.ErrorType.TIMEOUT)
        } catch (e: Exception) {
            Log.e("RizzBotAPI", "Serialization failed", e)
            SuggestionResult.Error("Error: ${e.message ?: "Unknown error"}", SuggestionResult.ErrorType.UNKNOWN)
        }
    }

    override suspend fun resolveConversationMerge(
        suggestedConversationId: String,
        isMatch: Boolean,
        newOcrText: String
    ): SuggestionResult {
        val userId = authManager.get().getUserId()
        if (userId.isNullOrEmpty()) {
            return SuggestionResult.Error(
                message = "Session expired. Please restart the app.",
                errorType = SuggestionResult.ErrorType.INVALID_API_KEY
            )
        }

        return try {
            val response = hostedApi.resolveConversation(
                ResolveConversationRequest(
                    userId = userId,
                    suggestedConversationId = suggestedConversationId,
                    isMatch = isMatch,
                    newOcrText = newOcrText
                )
            )

            _usageState.value = _usageState.value.copy(
                dailyUsed = _usageState.value.dailyLimit - response.usageRemaining
            )

            SuggestionResult.Success(
                replies = response.replies,
                summary = response.personName ?: "",
                personName = response.personName,
                interactionId = response.interactionId,
                stage = response.stage,
                usageRemaining = response.usageRemaining
            )
        } catch (e: HttpException) {
            when (e.code()) {
                403 -> SuggestionResult.Error(
                    "Access denied. Your tier may have changed. Please refresh.",
                    SuggestionResult.ErrorType.QUOTA_EXCEEDED
                )
                429 -> SuggestionResult.Error(
                    "Daily limit reached. Upgrade for a higher reply allowance.",
                    SuggestionResult.ErrorType.QUOTA_EXCEEDED
                )
                401 -> SuggestionResult.Error(
                    "Session expired. Please restart the app.",
                    SuggestionResult.ErrorType.INVALID_API_KEY
                )
                502 -> SuggestionResult.Error(
                    "AI is temporarily unavailable. Try again.",
                    SuggestionResult.ErrorType.UNKNOWN
                )
                else -> SuggestionResult.Error(
                    "Server error: ${e.code()}",
                    SuggestionResult.ErrorType.UNKNOWN
                )
            }
        } catch (e: SocketTimeoutException) {
            SuggestionResult.Error(
                "Request timed out. Try again.",
                SuggestionResult.ErrorType.TIMEOUT
            )
        } catch (e: Exception) {
            Log.e("RizzBotAPI", "Serialization failed", e)
            SuggestionResult.Error(
                "Error: ${e.message ?: "Unknown error"}",
                SuggestionResult.ErrorType.UNKNOWN
            )
        }
    }

    override suspend fun trackCopy(interactionId: String, replyIndex: Int) {
        try {
            hostedApi.trackCopy(TrackCopyRequest(interactionId, replyIndex))
        } catch (e: Exception) {
            android.util.Log.w("HostedRepo", "trackCopy failed: ${e.message}")
        }
    }

    override suspend fun trackRating(interactionId: String, replyIndex: Int, isPositive: Boolean) {
        try {
            hostedApi.trackRating(TrackRatingRequest(interactionId, replyIndex, isPositive))
        } catch (e: Exception) {
            android.util.Log.w("HostedRepo", "trackRating failed: ${e.message}")
        }
    }

    override suspend fun refreshUsage(force: Boolean) {
        refreshUsageLock.withLock {
        // Check cache TTL - skip network call if cache is fresh and not forcing
        val currentTime = System.currentTimeMillis()
        if (!force && lastUsageFetchTime > 0 && (currentTime - lastUsageFetchTime < USAGE_CACHE_TTL_MS)) {
            // Cache is fresh, skip API call
            return@withLock
        }

        try {
            val usage = hostedApi.getUsage()
            _usageState.value = usageStateFromResponse(usage)

            // Update cache timestamp on successful fetch
            lastUsageFetchTime = System.currentTimeMillis()
        } catch (e: HttpException) {
            if (e.code() == 401) {
                // Backend rejected our JWT. If Firebase still has a valid signed-in session,
                // attempt to silently re-issue a backend JWT and retry once.
                val refreshed = authManager.get().refreshBackendTokenIfFirebaseSignedIn()
                if (refreshed) {
                    try {
                        val usage = hostedApi.getUsage()
                        _usageState.value = usageStateFromResponse(usage)

                        // Update cache timestamp on successful retry fetch
                        lastUsageFetchTime = System.currentTimeMillis()
                        return
                    } catch (_: Exception) {
                        // If retry still fails, fall through to hard logout below.
                    }
                }

                // Hard logout: backend no longer recognizes this user/token.
                authManager.get().clearAuth()
                // Stop overlay service so "Cookd is active" indicator goes off
                context.stopService(Intent(context, OverlayService::class.java))
                // Reset to initial usage state; UI should now behave as fully signed-out.
                _usageState.value = UsageState()

                // Restart app to trigger MainActivity's auth check → sends user to onboarding
                val intent = context.packageManager.getLaunchIntentForPackage(context.packageName)
                intent?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
                context.startActivity(intent)
                return
            }
            android.util.Log.w("HostedRepo", "refreshUsage http failed: ${e.message()}")
        } catch (e: Exception) {
            android.util.Log.w("HostedRepo", "refreshUsage failed: ${e.message}")
        }
        }
    }

    override suspend fun getReferralInfo(): ReferralInfo? {
        return try {
            val info = hostedApi.getReferralInfo()
            ReferralInfo(
                referralCode = info.referralCode,
                totalReferrals = info.totalReferrals,
                bonusRepliesEarned = info.bonusRepliesEarned,
                maxReferrals = info.maxReferrals
            )
        } catch (e: Exception) {
            android.util.Log.w("HostedRepo", "getReferralInfo failed: ${e.message}")
            null
        }
    }

    override suspend fun applyReferralCode(code: String): Result<ApplyReferralResponse> {
        return try {
            val deviceId = getAndroidDeviceId()
            val response = hostedApi.applyReferral(ApplyReferralRequest(code, deviceId))
            refreshUsage(force = true) // Force refresh after tier change
            Result.success(response)
        } catch (e: HttpException) {
            val msg = when (e.code()) {
                400 -> e.response()?.errorBody()?.string()?.let {
                    if ("own" in it) "You can't use your own code"
                    else if ("already" in it) "You've already used a referral code"
                    else if ("maximum" in it) "This code has reached its limit"
                    else "Invalid request"
                } ?: "Invalid request"
                404 -> "Invalid referral code"
                else -> "Something went wrong"
            }
            Result.failure(Exception(msg))
        } catch (e: Exception) {
            Result.failure(Exception("Network error. Try again."))
        }
    }


    override suspend fun verifyPurchase(
        purchaseToken: String,
        productId: String,
        orderId: String?
    ): Boolean {
        return try {
            val response = hostedApi.verifyPurchase(
                VerifyPurchaseRequest(purchaseToken, productId, orderId)
            )
            if (response.isValid) {
                refreshUsage(force = true) // Force refresh after purchase
            }
            response.isValid
        } catch (_: Exception) { false }
    }

    override suspend fun getHistory(limit: Int, offset: Int): List<HistoryItemResponse> {
        return try {
            hostedApi.getHistory(limit, offset).items
        } catch (e: Exception) {
            android.util.Log.w("HostedRepo", "getHistory failed: ${e.message}")
            emptyList()
        }
    }

    override suspend fun deleteHistoryItem(id: String) {
        try {
            hostedApi.deleteHistoryItem(id)
        } catch (e: Exception) {
            android.util.Log.w("HostedRepo", "deleteHistoryItem failed: ${e.message}")
        }
    }

    override suspend fun getUserPreferences(): UserPreferencesResponse? {
        return try {
            hostedApi.getUserPreferences()
        } catch (e: Exception) {
            android.util.Log.w("HostedRepo", "getUserPreferences failed: ${e.message}")
            null
        }
    }

    override suspend fun submitAuditJob(
        compressedPhotos: List<ByteArray>,
        lang: String?
    ): Result<String> {
        return try {
            if (compressedPhotos.isEmpty()) {
                return Result.failure(IllegalArgumentException("No photos to upload"))
            }

            val mediaType = "image/jpeg".toMediaType()
            val parts = compressedPhotos.mapIndexed { index, bytes ->
                val body = bytes.toRequestBody(mediaType)
                MultipartBody.Part.createFormData(
                    name = "images",
                    filename = "photo_${index + 1}.jpg",
                    body = body
                )
            }

            val response = hostedApi.submitAuditJob(parts, lang)
            if (response.isSuccessful) {
                val body = response.body()
                if (body != null) {
                    Result.success(body.jobId)
                } else {
                    Result.failure(Exception("Empty response from server"))
                }
            } else {
                val message = when (response.code()) {
                    429 -> "You've used your weekly photo audit limit. It resets every Monday — come back then!"
                    403 -> "Photo audits aren't available on your current plan. Please upgrade."
                    else -> "Server error: ${response.code()}"
                }
                Result.failure(Exception(message))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun pollAuditJobUntilDone(jobId: String): Result<com.rizzbot.v2.data.remote.dto.AuditResponse> {
        val maxAttempts = 60 // 60 * 2s = 2 minute timeout
        return try {
            repeat(maxAttempts) {
                val status = hostedApi.getAuditJobStatus(jobId)
                when (status.status) {
                    "completed" -> {
                        val result = status.result
                            ?: return Result.failure(Exception("Job completed but no result"))
                        return Result.success(result)
                    }
                    "failed" -> {
                        return Result.failure(Exception(status.error ?: "Audit processing failed"))
                    }
                    else -> {
                        kotlinx.coroutines.delay(2000)
                    }
                }
            }
            Result.failure(Exception("Audit timed out. Please try again."))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override fun streamAuditProgress(jobId: String): kotlinx.coroutines.flow.Flow<com.rizzbot.v2.data.remote.dto.AuditJobStatusResponse> {
        return kotlinx.coroutines.flow.flow {
            val maxAttempts = 90 // 90 * 1.5s = ~2 minute timeout
            var attempts = 0
            var consecutiveErrors = 0
            var delayMs = 1500L
            while (attempts < maxAttempts) {
                attempts++
                try {
                    val status = hostedApi.getAuditJobStatus(jobId)
                    consecutiveErrors = 0
                    delayMs = 1500L // Reset delay on success
                    emit(status)
                    if (status.status == "completed" || status.status == "failed") {
                        return@flow
                    }
                } catch (e: Exception) {
                    consecutiveErrors++
                    android.util.Log.w("HostedRepo", "streamAuditProgress poll error #$consecutiveErrors: ${e.message}")

                    // Back off on 429 rate limit
                    val is429 = e is retrofit2.HttpException && e.code() == 429
                    if (is429) {
                        delayMs = (delayMs * 2).coerceAtMost(10_000L) // exponential backoff, cap 10s
                        android.util.Log.w("HostedRepo", "Rate limited, backing off to ${delayMs}ms")
                    }

                    // Give up after 3 consecutive non-429 errors
                    if (!is429 && consecutiveErrors >= 3) {
                        emit(
                            com.rizzbot.v2.data.remote.dto.AuditJobStatusResponse(
                                jobId = jobId,
                                status = "failed",
                                error = "Connection lost. Please check your network and try again."
                            )
                        )
                        return@flow
                    }
                }
                kotlinx.coroutines.delay(delayMs)
            }
            // Timed out
            emit(
                com.rizzbot.v2.data.remote.dto.AuditJobStatusResponse(
                    jobId = jobId,
                    status = "failed",
                    error = "Audit timed out. Please try again."
                )
            )
        }
    }

    override suspend fun getProfileAuditHistory(limit: Int, offset: Int): List<AuditedPhotoItemDto> {
        return try {
            hostedApi.getProfileAuditHistory(limit, offset).items
        } catch (e: Exception) {
            android.util.Log.w("HostedRepo", "getProfileAuditHistory failed: ${e.message}")
            emptyList()
        }
    }

    override suspend fun deleteProfileAuditPhoto(photoId: String): Result<Unit> {
        return try {
            hostedApi.deleteProfileAuditPhoto(photoId)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun deleteAllUserData(): Result<Unit> {
        return try {
            hostedApi.deleteAllUserData()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    private fun getAndroidDeviceId(): String? {
        return try {
            Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
        } catch (e: Exception) {
            android.util.Log.w("HostedRepo", "Failed to get Android device ID: ${e.message}")
            null
        }
    }
}
