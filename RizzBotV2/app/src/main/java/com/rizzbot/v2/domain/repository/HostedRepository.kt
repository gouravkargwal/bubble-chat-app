package com.rizzbot.v2.domain.repository

import com.rizzbot.v2.data.remote.dto.ApplyReferralResponse
import com.rizzbot.v2.data.remote.dto.AuditResponse
import com.rizzbot.v2.data.remote.dto.HistoryItemResponse
import com.rizzbot.v2.data.remote.dto.UserPreferencesResponse
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.ReferralInfo
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.model.UsageState
import kotlinx.coroutines.flow.StateFlow

interface HostedRepository {
    val usageState: StateFlow<UsageState>

    suspend fun generateReply(base64Images: List<String>, direction: DirectionWithHint): SuggestionResult
    suspend fun trackCopy(interactionId: String, replyIndex: Int)
    suspend fun trackRating(interactionId: String, replyIndex: Int, isPositive: Boolean)
    suspend fun refreshUsage(force: Boolean = false)

    // History
    suspend fun getHistory(limit: Int = 20, offset: Int = 0): List<HistoryItemResponse>
    suspend fun deleteHistoryItem(id: String)

    // Preferences
    suspend fun getUserPreferences(): UserPreferencesResponse?

    // Voice DNA calibration
    suspend fun calibrateVoiceDNA(base64Images: List<String>): Result<Int>

    // Referral
    suspend fun getReferralInfo(): ReferralInfo?
    suspend fun applyReferralCode(code: String): Result<ApplyReferralResponse>

    // Billing
    suspend fun verifyPurchase(purchaseToken: String, productId: String, orderId: String?): Boolean

    // Profile Auditor
    suspend fun uploadPhotosForAudit(
        compressedPhotos: List<ByteArray>,
        lang: String? = null
    ): Result<AuditResponse>
    suspend fun getProfileAuditHistory(limit: Int = 20, offset: Int = 0): List<com.rizzbot.v2.data.remote.dto.AuditedPhotoItemDto>
    suspend fun deleteProfileAuditPhoto(photoId: String): Result<Unit>
    suspend fun deleteAllUserData(): Result<Unit>
}
