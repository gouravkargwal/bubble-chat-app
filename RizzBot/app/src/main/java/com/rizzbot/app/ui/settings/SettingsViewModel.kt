package com.rizzbot.app.ui.settings

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.app.accessibility.ProfileCacheManager
import com.rizzbot.app.domain.model.TonePreference
import com.rizzbot.app.domain.repository.ConversationRepository
import com.rizzbot.app.domain.repository.SettingsRepository
import com.rizzbot.app.overlay.OverlayService
import com.rizzbot.app.util.PermissionHelper
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
    val selectedTone: TonePreference = TonePreference.FLIRTY,
    val showApiKey: Boolean = false
)

data class RizzStats(
    val profilesSynced: Int = 0,
    val totalConversations: Int = 0,
    val totalMessages: Int = 0
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val settingsRepository: SettingsRepository,
    private val conversationRepository: ConversationRepository,
    private val permissionHelper: PermissionHelper,
    profileCacheManager: ProfileCacheManager,
    @ApplicationContext private val context: Context
) : ViewModel() {

    private val _state = MutableStateFlow(SettingsState())
    val state: StateFlow<SettingsState> = _state.asStateFlow()

    val stats: StateFlow<RizzStats> = combine(
        profileCacheManager.observeAllSyncedNames(),
        conversationRepository.observeAllConversations()
    ) { names, convos ->
        RizzStats(
            profilesSynced = names.size,
            totalConversations = convos.size,
            totalMessages = convos.sumOf { it.messageCount }
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), RizzStats())

    init {
        loadSettings()
    }

    private fun loadSettings() {
        viewModelScope.launch {
            val apiKey = settingsRepository.apiKey.first()
            val isEnabled = settingsRepository.isServiceEnabled.first()
            val toneName = settingsRepository.tonePreference.first()
            val tone = try { TonePreference.valueOf(toneName) } catch (_: Exception) { TonePreference.FLIRTY }

            _state.value = _state.value.copy(
                isServiceEnabled = isEnabled,
                apiKey = apiKey,
                selectedTone = tone
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

    fun toggleService(enabled: Boolean) {
        viewModelScope.launch {
            settingsRepository.setServiceEnabled(enabled)
            _state.value = _state.value.copy(isServiceEnabled = enabled)

            if (enabled) {
                context.startForegroundService(Intent(context, OverlayService::class.java))
            } else {
                context.stopService(Intent(context, OverlayService::class.java))
            }
        }
    }

    fun updateApiKey(key: String) {
        viewModelScope.launch {
            settingsRepository.setApiKey(key)
            _state.value = _state.value.copy(apiKey = key)
        }
    }

    fun selectTone(tone: TonePreference) {
        viewModelScope.launch {
            settingsRepository.setTonePreference(tone)
            _state.value = _state.value.copy(selectedTone = tone)
        }
    }

    fun toggleShowApiKey() {
        _state.value = _state.value.copy(showApiKey = !_state.value.showApiKey)
    }

    fun clearAllData() {
        viewModelScope.launch {
            conversationRepository.deleteAll()
        }
    }
}
