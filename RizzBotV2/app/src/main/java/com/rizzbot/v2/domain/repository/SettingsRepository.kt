package com.rizzbot.v2.domain.repository

import com.rizzbot.v2.domain.model.LlmModel
import com.rizzbot.v2.domain.model.LlmProvider
import kotlinx.coroutines.flow.Flow

interface SettingsRepository {
    val provider: Flow<LlmProvider?>
    val model: Flow<LlmModel?>
    val apiKey: Flow<String?>
    val serviceEnabled: Flow<Boolean>
    val onboardingCompleted: Flow<Boolean>
    val totalRepliesGenerated: Flow<Int>
    val totalRepliesCopied: Flow<Int>
    val firstCaptureDone: Flow<Boolean>

    suspend fun setProvider(provider: LlmProvider)
    suspend fun setModel(model: LlmModel)
    suspend fun setApiKey(key: String)
    suspend fun setServiceEnabled(enabled: Boolean)
    suspend fun setOnboardingCompleted(completed: Boolean)
    suspend fun incrementRepliesGenerated()
    suspend fun incrementRepliesCopied()
    suspend fun setFirstCaptureDone()
}
