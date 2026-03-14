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
import com.rizzbot.v2.data.remote.dto.CalibrationRequest
import com.rizzbot.v2.data.remote.dto.HistoryItemResponse
import com.rizzbot.v2.data.remote.dto.AuditedPhotoItemDto
import com.rizzbot.v2.data.remote.dto.TrackCopyRequest
import com.rizzbot.v2.data.remote.dto.TrackRatingRequest
import com.rizzbot.v2.data.remote.dto.UserPreferencesResponse
import com.rizzbot.v2.data.remote.dto.VerifyPurchaseRequest
import com.rizzbot.v2.data.remote.dto.VisionGenerateRequest
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.ReferralInfo
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.model.UsageState
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.overlay.OverlayService
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonPrimitive
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
                // 403 = Forbidden (tier/permission issue)
                403 -> SuggestionResult.Error(
                    "Access denied. Your tier may have changed. Please refresh.",
                    SuggestionResult.ErrorType.QUOTA_EXCEEDED
                )
                // 429 is *only* used by the backend for app-level daily quota
                // (DB-based check before calling Gemini).
                429 -> SuggestionResult.Error(
                    "Daily limit reached. Upgrade to Premium for unlimited replies.",
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
        // Check cache TTL - skip network call if cache is fresh and not forcing
        val currentTime = System.currentTimeMillis()
        if (!force && lastUsageFetchTime > 0 && (currentTime - lastUsageFetchTime < USAGE_CACHE_TTL_MS)) {
            // Cache is fresh, skip API call
            return
        }
        
        try {
            val usage = hostedApi.getUsage()
            // Extract max_photos_per_audit from limits map
            val maxPhotosPerAudit = usage.limits["max_photos_per_audit"]
                ?.let { 
                    if (it is JsonPrimitive) {
                        it.content.toIntOrNull() ?: 3
                    } else {
                        3
                    }
                } ?: 3
            
            // Extract profile_audits_per_week from limits map
            val profileAuditsPerWeek = usage.limits["profile_audits_per_week"]
                ?.let { 
                    if (it is JsonPrimitive) {
                        it.content.toIntOrNull() ?: 1
                    } else {
                        1
                    }
                } ?: 1
            
            _usageState.value = UsageState(
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
                godModeExpiresAt = usage.godModeExpiresAt?.let { 
                    try {
                        java.time.Instant.ofEpochSecond(it)
                    } catch (e: Exception) {
                        android.util.Log.w("HostedRepo", "Failed to parse godModeExpiresAt: ${e.message}")
                        null
                    }
                },
                totalRepliesGenerated = usage.totalRepliesGenerated,
                totalRepliesCopied = usage.totalRepliesCopied,
                maxPhotosPerAudit = maxPhotosPerAudit,
                billingPeriod = usage.billingPeriod
            )
            
            // Update cache timestamp on successful fetch
            lastUsageFetchTime = System.currentTimeMillis()
        } catch (e: HttpException) {
            if (e.code() == 401) {
                // Backend no longer recognizes this user/token → treat as hard logout.
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

    override suspend fun calibrateVoiceDNA(base64Images: List<String>): Result<Int> {
        return try {
            val response = hostedApi.calibrate(CalibrationRequest(images = base64Images))
            Result.success(response.messagesExtracted)
        } catch (e: HttpException) {
            val message = when (e.code()) {
                400 -> "Images required."
                else -> "Server error: ${e.code()}"
            }
            Result.failure(Exception(message))
        } catch (e: SocketTimeoutException) {
            Result.failure(Exception("Calibration timed out. Try again."))
        } catch (e: Exception) {
            Result.failure(Exception(e.message ?: "Unknown error during calibration"))
        }
    }

    override suspend fun uploadPhotosForAudit(
        compressedPhotos: List<ByteArray>,
        lang: String?
    ): Result<AuditResponse> {
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

            val response = hostedApi.auditProfilePhotos(parts, lang)
            if (response.isSuccessful) {
                val body = response.body()
                if (body != null) {
                    Result.success(body)
                } else {
                    Result.failure(Exception("Empty response from server"))
                }
            } else {
                Result.failure(Exception("Server error: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
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
