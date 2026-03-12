package com.rizzbot.v2.ui.home

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.data.remote.dto.HistoryItemResponse
import com.rizzbot.v2.domain.model.UserPreferences
import com.rizzbot.v2.domain.model.UsageState
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import com.rizzbot.v2.overlay.OverlayService
import com.rizzbot.v2.util.PermissionHelper
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HomeState(
    val isServiceEnabled: Boolean = false,
    val hasOverlayPermission: Boolean = false,
    val totalRepliesGenerated: Int = 0,
    val totalRepliesCopied: Int = 0,
    val showHowItWorks: Boolean = true,
    val recentReplies: List<HistoryItemResponse> = emptyList(),
    val rizzProfile: UserPreferences? = null,
    val usage: UsageState = UsageState(),
    val showCalibrationModal: Boolean = false
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val settingsRepository: SettingsRepository,
    private val hostedRepository: HostedRepository,
    private val permissionHelper: PermissionHelper,
    private val bubbleManager: dagger.Lazy<com.rizzbot.v2.overlay.manager.BubbleManager>
) : ViewModel() {

    private val _state = MutableStateFlow(HomeState())
    val state: StateFlow<HomeState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            combine(
                settingsRepository.serviceEnabled,
                settingsRepository.firstCaptureDone
            ) { serviceEnabled, firstCaptureDone ->
                _state.value.copy(
                    // Use actual bubble visibility, not just the stored pref
                    isServiceEnabled = serviceEnabled && bubbleManager.get().isActuallyShown.value,
                    hasOverlayPermission = permissionHelper.canDrawOverlays(),
                    showHowItWorks = !firstCaptureDone
                )
            }.collect { _state.value = it }
        }

        // Also collect bubble visibility changes to update isServiceEnabled in real-time
        viewModelScope.launch {
            bubbleManager.get().isActuallyShown.collect { isShown ->
                _state.update { currentState ->
                    currentState.copy(isServiceEnabled = isShown)
                }
            }
        }

        // Collect usage state immediately (includes totalRepliesGenerated/Copied from backend)
        viewModelScope.launch {
            hostedRepository.usageState.collect { usage ->
                _state.update { 
                    it.copy(
                        usage = usage,
                        totalRepliesGenerated = usage.totalRepliesGenerated,
                        totalRepliesCopied = usage.totalRepliesCopied
                    ) 
                }
            }
        }
        // Refresh in background to ensure latest data from backend
        viewModelScope.launch {
            hostedRepository.refreshUsage()
        }

        // Fetch recent history from backend
        viewModelScope.launch {
            val history = hostedRepository.getHistory(limit = 3)
            // Filter out items with no valid replies
            val validHistory = history.filter { item ->
                item.replies.any { reply -> reply.isNotBlank() }
            }
            _state.update { it.copy(recentReplies = validHistory) }
        }

        // Fetch user preferences from backend
        viewModelScope.launch {
            val prefs = hostedRepository.getUserPreferences()
            if (prefs != null && prefs.hasEnoughData) {
                val vibeBreakdown = prefs.vibeBreakdown.associate { it.name to it.percentage }
                val preferredLength = when (prefs.preferredLength) {
                    "short" -> UserPreferences.PreferredLength.SHORT
                    "long" -> UserPreferences.PreferredLength.LONG
                    else -> UserPreferences.PreferredLength.MEDIUM
                }
                _state.update {
                    it.copy(
                        rizzProfile = UserPreferences(
                            totalRatings = prefs.totalRatings,
                            vibeBreakdown = vibeBreakdown,
                            preferredLength = preferredLength
                        )
                    )
                }
            }
        }
    }

    fun refreshPermissionStatus() {
        _state.update { it.copy(hasOverlayPermission = permissionHelper.canDrawOverlays()) }
    }

    fun toggleService(enabled: Boolean) {
        viewModelScope.launch {
            settingsRepository.setServiceEnabled(enabled)
            if (enabled) {
                context.startForegroundService(Intent(context, OverlayService::class.java))
            } else {
                context.stopService(Intent(context, OverlayService::class.java))
            }
        }
    }

    fun dismissHowItWorks() {
        viewModelScope.launch {
            settingsRepository.setFirstCaptureDone()
        }
    }

    fun showCalibration() {
        _state.update { it.copy(showCalibrationModal = true) }
    }

    fun hideCalibration() {
        _state.update { it.copy(showCalibrationModal = false) }
    }
}
