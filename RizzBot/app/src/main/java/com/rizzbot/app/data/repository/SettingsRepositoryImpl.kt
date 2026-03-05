package com.rizzbot.app.data.repository

import com.rizzbot.app.data.local.datastore.SettingsDataStore
import com.rizzbot.app.domain.model.TonePreference
import com.rizzbot.app.domain.repository.SettingsRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SettingsRepositoryImpl @Inject constructor(
    private val settingsDataStore: SettingsDataStore
) : SettingsRepository {

    override val apiKey: Flow<String> = settingsDataStore.apiKey
    override val isServiceEnabled: Flow<Boolean> = settingsDataStore.isServiceEnabled
    override val tonePreference: Flow<String> = settingsDataStore.tonePreference
    override val hasCompletedOnboarding: Flow<Boolean> = settingsDataStore.hasCompletedOnboarding

    override suspend fun setApiKey(key: String) = settingsDataStore.setApiKey(key)
    override suspend fun setServiceEnabled(enabled: Boolean) = settingsDataStore.setServiceEnabled(enabled)
    override suspend fun setTonePreference(tone: TonePreference) = settingsDataStore.setTonePreference(tone.name)
    override suspend fun setOnboardingComplete() = settingsDataStore.setOnboardingComplete()

    override val selectedProvider: Flow<String> = settingsDataStore.selectedProvider
    override val selectedModel: Flow<String> = settingsDataStore.selectedModel
    override suspend fun setSelectedProvider(provider: String) = settingsDataStore.setSelectedProvider(provider)
    override suspend fun setSelectedModel(model: String) = settingsDataStore.setSelectedModel(model)
    override val repliesGenerated: Flow<Int> = settingsDataStore.repliesGenerated
    override val hasSeenGuide: Flow<Boolean> = settingsDataStore.hasSeenGuide
    override suspend fun setGuideComplete() = settingsDataStore.setGuideComplete()
}
