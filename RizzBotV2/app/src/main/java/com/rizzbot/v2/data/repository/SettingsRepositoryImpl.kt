package com.rizzbot.v2.data.repository

import com.rizzbot.v2.data.local.datastore.SettingsDataStore
import com.rizzbot.v2.domain.model.LlmModel
import com.rizzbot.v2.domain.model.LlmProvider
import com.rizzbot.v2.domain.repository.SettingsRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SettingsRepositoryImpl @Inject constructor(
    private val dataStore: SettingsDataStore
) : SettingsRepository {

    override val provider: Flow<LlmProvider?> = dataStore.provider.map { name ->
        name?.let { LlmProvider.valueOf(it) }
    }

    override val model: Flow<LlmModel?> = dataStore.modelId.map { modelId ->
        modelId?.let { id ->
            LlmProvider.entries.flatMap { it.models }.find { it.id == id }
        }
    }

    override val apiKey: Flow<String?> = dataStore.apiKey
    override val serviceEnabled: Flow<Boolean> = dataStore.serviceEnabled
    override val onboardingCompleted: Flow<Boolean> = dataStore.onboardingCompleted
    override val totalRepliesGenerated: Flow<Int> = dataStore.totalRepliesGenerated
    override val totalRepliesCopied: Flow<Int> = dataStore.totalRepliesCopied
    override val firstCaptureDone: Flow<Boolean> = dataStore.firstCaptureDone

    override suspend fun setProvider(provider: LlmProvider) { dataStore.setProvider(provider.name) }
    override suspend fun setModel(model: LlmModel) { dataStore.setModelId(model.id) }
    override suspend fun setApiKey(key: String) { dataStore.setApiKey(key) }
    override suspend fun setServiceEnabled(enabled: Boolean) { dataStore.setServiceEnabled(enabled) }
    override suspend fun setOnboardingCompleted(completed: Boolean) { dataStore.setOnboardingCompleted(completed) }
    override suspend fun incrementRepliesGenerated() { dataStore.incrementRepliesGenerated() }
    override suspend fun incrementRepliesCopied() { dataStore.incrementRepliesCopied() }
    override suspend fun setFirstCaptureDone() { dataStore.setFirstCaptureDone() }
}
