package com.rizzbot.v2.domain.repository

import com.rizzbot.v2.domain.model.HostedModeState
import com.rizzbot.v2.domain.model.SuggestionResult
import kotlinx.coroutines.flow.Flow

interface HostedRepository {
    val hostedState: Flow<HostedModeState>

    suspend fun authenticateAnonymous(): Boolean
    suspend fun generateHostedReply(
        systemPrompt: String,
        userPrompt: String,
        base64Image: String
    ): SuggestionResult
    suspend fun refreshUsage()
    suspend fun redeemReferral(code: String): Result<Int>
    fun getToken(): String?
}
