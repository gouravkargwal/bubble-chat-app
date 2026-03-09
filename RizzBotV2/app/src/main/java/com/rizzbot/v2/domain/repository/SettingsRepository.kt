package com.rizzbot.v2.domain.repository

import kotlinx.coroutines.flow.Flow

interface SettingsRepository {
    val serviceEnabled: Flow<Boolean>
    val onboardingCompleted: Flow<Boolean>
    val totalRepliesGenerated: Flow<Int>
    val totalRepliesCopied: Flow<Int>
    val firstCaptureDone: Flow<Boolean>

    suspend fun setServiceEnabled(enabled: Boolean)
    suspend fun setOnboardingCompleted(completed: Boolean)
    suspend fun incrementRepliesGenerated()
    suspend fun incrementRepliesCopied()
    suspend fun setFirstCaptureDone()
}
