package com.rizzbot.v2.domain.repository

import kotlinx.coroutines.flow.Flow

interface SettingsRepository {
    val serviceEnabled: Flow<Boolean>
    val onboardingCompleted: Flow<Boolean>
    // Removed: totalRepliesGenerated, totalRepliesCopied (now sourced from backend)
    val firstCaptureDone: Flow<Boolean>
    val highValueCopyCount: Flow<Int>

    suspend fun setServiceEnabled(enabled: Boolean)
    suspend fun setOnboardingCompleted(completed: Boolean)
    // Removed: incrementRepliesGenerated, incrementRepliesCopied (backend tracks via interactions table)
    suspend fun setFirstCaptureDone()
    suspend fun incrementHighValueCopyCount(): Int
}
