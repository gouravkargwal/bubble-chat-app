package com.rizzbot.app.domain.repository

import com.rizzbot.app.domain.model.TonePreference
import kotlinx.coroutines.flow.Flow

interface SettingsRepository {
    val apiKey: Flow<String>
    val isServiceEnabled: Flow<Boolean>
    val tonePreference: Flow<String>
    val hasCompletedOnboarding: Flow<Boolean>
    suspend fun setApiKey(key: String)
    suspend fun setServiceEnabled(enabled: Boolean)
    suspend fun setTonePreference(tone: TonePreference)
    suspend fun setOnboardingComplete()
}
