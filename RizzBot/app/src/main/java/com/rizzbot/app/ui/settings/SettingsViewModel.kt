package com.rizzbot.app.ui.settings

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.app.accessibility.ProfileCacheManager
import com.rizzbot.app.domain.model.LlmModel
import com.rizzbot.app.domain.model.LlmProvider
import com.rizzbot.app.domain.repository.ConversationRepository
import com.rizzbot.app.domain.repository.LlmRepository
import com.rizzbot.app.domain.repository.SettingsRepository
import com.rizzbot.app.overlay.OverlayService
import com.rizzbot.app.BuildConfig
import com.rizzbot.app.util.AnalyticsHelper
import com.rizzbot.app.util.InAppUpdateHelper
import com.rizzbot.app.util.PermissionHelper
import com.rizzbot.app.util.UpdateInfo
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsState(
    val isServiceEnabled: Boolean = false,
    val isAccessibilityActive: Boolean = false,
    val isOverlayPermitted: Boolean = false,
    val apiKey: String = "",
    val showApiKey: Boolean = false,
    val selectedProvider: LlmProvider = LlmProvider.GROQ,
    val selectedModel: LlmModel = LlmProvider.GROQ.defaultModel,
    val availableModels: List<LlmModel> = LlmProvider.GROQ.models,
    val apiKeyStatus: ApiKeyStatus = ApiKeyStatus.NONE,
    val showGuide: Boolean = false
)

enum class ApiKeyStatus { NONE, VALIDATING, VALID, INVALID }

data class RizzStats(
    val profilesSynced: Int = 0,
    val totalConversations: Int = 0,
    val totalMessages: Int = 0,
    val repliesGenerated: Int = 0
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val settingsRepository: SettingsRepository,
    private val conversationRepository: ConversationRepository,
    private val llmRepository: LlmRepository,
    private val permissionHelper: PermissionHelper,
    private val analyticsHelper: AnalyticsHelper,
    profileCacheManager: ProfileCacheManager,
    @ApplicationContext private val context: Context
) : ViewModel() {

    private val _state = MutableStateFlow(SettingsState())
    val state: StateFlow<SettingsState> = _state.asStateFlow()

    private val _updateInfo = MutableStateFlow<UpdateInfo?>(null)
    val updateInfo: StateFlow<UpdateInfo?> = _updateInfo.asStateFlow()

    val stats: StateFlow<RizzStats> = combine(
        profileCacheManager.observeAllSyncedNames(),
        conversationRepository.observeAllConversations(),
        settingsRepository.repliesGenerated
    ) { names, convos, replies ->
        RizzStats(
            profilesSynced = names.size,
            totalConversations = convos.size,
            totalMessages = convos.sumOf { it.messageCount },
            repliesGenerated = replies
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), RizzStats())

    init {
        loadSettings()
        checkForUpdate()
    }

    private fun loadSettings() {
        viewModelScope.launch {
            val apiKey = settingsRepository.apiKey.first()
            val isEnabled = settingsRepository.isServiceEnabled.first()
            val providerName = settingsRepository.selectedProvider.first()
            val modelId = settingsRepository.selectedModel.first()

            val provider = try { LlmProvider.valueOf(providerName) } catch (_: Exception) { LlmProvider.GROQ }
            val model = provider.models.find { it.id == modelId } ?: provider.defaultModel

            val hasSeenGuide = settingsRepository.hasSeenGuide.first()

            _state.value = _state.value.copy(
                isServiceEnabled = isEnabled,
                apiKey = apiKey,
                selectedProvider = provider,
                selectedModel = model,
                availableModels = provider.models,
                showGuide = !hasSeenGuide
            )
            refreshPermissionStatus()
        }
    }

    fun refreshPermissionStatus() {
        _state.value = _state.value.copy(
            isAccessibilityActive = permissionHelper.isAccessibilityServiceEnabled(),
            isOverlayPermitted = permissionHelper.canDrawOverlays()
        )
    }

    private val _showAccessibilityPrompt = MutableStateFlow(false)
    val showAccessibilityPrompt: StateFlow<Boolean> = _showAccessibilityPrompt.asStateFlow()

    private var pendingServiceEnabled: Boolean = false

    fun toggleService(enabled: Boolean) {
        viewModelScope.launch {
            settingsRepository.setServiceEnabled(enabled)
            _state.value = _state.value.copy(isServiceEnabled = enabled)

            if (enabled) {
                context.startForegroundService(Intent(context, OverlayService::class.java))
            } else {
                context.stopService(Intent(context, OverlayService::class.java))
            }

            // Prompt user to also toggle accessibility service
            if (!enabled && permissionHelper.isAccessibilityServiceEnabled()) {
                pendingServiceEnabled = false
                _showAccessibilityPrompt.value = true
            } else if (enabled && !permissionHelper.isAccessibilityServiceEnabled()) {
                pendingServiceEnabled = true
                _showAccessibilityPrompt.value = true
            }
        }
    }

    fun dismissAccessibilityPrompt() {
        _showAccessibilityPrompt.value = false
    }

    fun selectProvider(provider: LlmProvider) {
        viewModelScope.launch {
            val defaultModel = provider.defaultModel
            settingsRepository.setSelectedProvider(provider.name)
            settingsRepository.setSelectedModel(defaultModel.id)
            settingsRepository.setApiKey("")
            analyticsHelper.logProviderSelected(provider.name)
            analyticsHelper.setUserProperty("provider", provider.name)
            _state.value = _state.value.copy(
                selectedProvider = provider,
                selectedModel = defaultModel,
                availableModels = provider.models,
                apiKey = "",
                showApiKey = false
            )
        }
    }

    fun selectModel(model: LlmModel) {
        viewModelScope.launch {
            settingsRepository.setSelectedModel(model.id)
            _state.value = _state.value.copy(selectedModel = model)
        }
    }

    fun updateApiKey(key: String) {
        viewModelScope.launch {
            settingsRepository.setApiKey(key)
            _state.value = _state.value.copy(apiKey = key, apiKeyStatus = ApiKeyStatus.NONE)
        }
    }

    fun validateApiKey() {
        val key = _state.value.apiKey
        if (key.isBlank()) {
            _state.value = _state.value.copy(apiKeyStatus = ApiKeyStatus.INVALID)
            return
        }
        _state.value = _state.value.copy(apiKeyStatus = ApiKeyStatus.VALIDATING)
        viewModelScope.launch {
            val isValid = llmRepository.validateApiKey()
            _state.value = _state.value.copy(
                apiKeyStatus = if (isValid) ApiKeyStatus.VALID else ApiKeyStatus.INVALID
            )
        }
    }

    fun toggleShowApiKey() {
        _state.value = _state.value.copy(showApiKey = !_state.value.showApiKey)
    }

    fun dismissGuide() {
        _state.value = _state.value.copy(showGuide = false)
        viewModelScope.launch {
            settingsRepository.setGuideComplete()
        }
    }

    fun showGuideAgain() {
        _state.value = _state.value.copy(showGuide = true)
    }

    fun clearAllData() {
        viewModelScope.launch {
            conversationRepository.deleteAll()
        }
    }

    private fun checkForUpdate() {
        viewModelScope.launch {
            val info = InAppUpdateHelper.checkForUpdate(BuildConfig.VERSION_NAME)
            _updateInfo.value = info
        }
    }
}
