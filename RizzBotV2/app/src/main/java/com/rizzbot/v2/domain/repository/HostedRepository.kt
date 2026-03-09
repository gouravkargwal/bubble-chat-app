package com.rizzbot.v2.domain.repository

import com.rizzbot.v2.data.remote.dto.ApplyPromoResponse
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
    suspend fun refreshUsage()

    // History
    suspend fun getHistory(limit: Int = 20): List<HistoryItemResponse>
    suspend fun deleteHistoryItem(id: String)

    // Preferences
    suspend fun getUserPreferences(): UserPreferencesResponse?

    // Referral
    suspend fun getReferralInfo(): ReferralInfo?
    suspend fun applyReferralCode(code: String): Result<Int>

    // Promo
    suspend fun applyPromoCode(code: String): Result<ApplyPromoResponse>

    // Billing
    suspend fun verifyPurchase(purchaseToken: String, productId: String, orderId: String?): Boolean
}
