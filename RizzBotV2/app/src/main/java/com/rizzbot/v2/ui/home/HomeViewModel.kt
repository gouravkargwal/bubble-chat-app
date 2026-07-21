package com.rizzbot.v2.ui.home

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.data.remote.api.HostedApi
import com.rizzbot.v2.domain.model.UserPreferences
import com.rizzbot.v2.domain.model.UsageState
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import com.rizzbot.v2.overlay.OverlayService
import com.rizzbot.v2.util.AnalyticsHelper
import com.rizzbot.v2.util.HapticHelper
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
    val showOverlayPermissionPrompt: Boolean = false,
    val showHowItWorks: Boolean = true,
    val rizzProfile: UserPreferences? = null,
    val usage: UsageState = UsageState(),
    val isLoadingUsage: Boolean = true,
    val roastLanguage: String = "English",
    val latestBlueprintTheme: String? = null,
    val latestBlueprintSlotCount: Int = 0,
    val latestBlueprintDate: String? = null,
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val settingsRepository: SettingsRepository,
    private val hostedRepository: HostedRepository,
    private val permissionHelper: PermissionHelper,
    private val bubbleManager: dagger.Lazy<com.rizzbot.v2.overlay.manager.BubbleManager>,
    private val hostedApi: HostedApi,
    private val hapticHelper: HapticHelper,
    private val analyticsHelper: AnalyticsHelper,
) : ViewModel() {

    private val _state = MutableStateFlow(HomeState())
    val state: StateFlow<HomeState> = _state.asStateFlow()

    private val _isPullRefreshing = MutableStateFlow(false)
    val isPullRefreshing: StateFlow<Boolean> = _isPullRefreshing.asStateFlow()

    init {
        analyticsHelper.screenViewed("Home")

        // Fire overlay_permission_granted once when permission is first detected after signup
        viewModelScope.launch {
            permissionHelper.canDrawOverlays().let { granted ->
                if (granted) analyticsHelper.overlayPermissionGranted()
            }
        }

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

        // Roast language preference
        viewModelScope.launch {
            settingsRepository.roastLanguage.collect { lang ->
                _state.update { it.copy(roastLanguage = lang) }
            }
        }

        // Collect usage state from backend
        viewModelScope.launch {
            hostedRepository.usageState.collect { usage ->
                _state.update {
                    it.copy(
                        usage = usage,
                        isLoadingUsage = false
                    )
                }
            }
        }
        // Refresh in background to ensure latest data from backend (use cache if available)
        viewModelScope.launch {
            hostedRepository.refreshUsage(force = false)
        }

        // Fetch user preferences from backend
        viewModelScope.launch {
            try {
                val prefs = hostedRepository.getUserPreferences()
                if (prefs != null) {
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
                                hasEnoughData = prefs.hasEnoughData,
                                vibeBreakdown = vibeBreakdown,
                                preferredLength = preferredLength
                            )
                        )
                    }
                } else {
                    // Backend returned null — set empty defaults so UI can show 0-progress
                    _state.update { it.copy(rizzProfile = UserPreferences()) }
                }
            } catch (e: Exception) {
                // Network/parse error — leave rizzProfile as null so UI shows loading skeleton
            }
        }

        // Fetch latest profile blueprint for home card preview
        viewModelScope.launch {
            try {
                val response = hostedApi.getProfileBlueprints(limit = 1)
                if (response.isSuccessful) {
                    val blueprint = response.body()?.items?.firstOrNull()
                    if (blueprint != null) {
                        _state.update {
                            it.copy(
                                latestBlueprintTheme = blueprint.overallTheme,
                                latestBlueprintSlotCount = blueprint.slots.size,
                                latestBlueprintDate = blueprint.createdAt.take(10)
                            )
                        }
                    }
                }
            } catch (_: Exception) { }
        }
    }

    fun refreshPermissionStatus() {
        val hadPermission = _state.value.hasOverlayPermission
        val nowHasPermission = permissionHelper.canDrawOverlays()
        if (!hadPermission && nowHasPermission) {
            analyticsHelper.overlayPermissionGranted()
        }
        _state.update { it.copy(hasOverlayPermission = nowHasPermission) }
    }

    /**
     * User pull-to-refresh: permissions, usage, voice profile, latest blueprint.
     */
    fun refresh() {
        viewModelScope.launch {
            _isPullRefreshing.value = true
            try {
                refreshPermissionStatus()
                hostedRepository.refreshUsage(force = true)

                try {
                    val prefs = hostedRepository.getUserPreferences()
                    if (prefs != null) {
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
                                    hasEnoughData = prefs.hasEnoughData,
                                    vibeBreakdown = vibeBreakdown,
                                    preferredLength = preferredLength
                                )
                            )
                        }
                    } else {
                        _state.update { it.copy(rizzProfile = UserPreferences()) }
                    }
                } catch (_: Exception) { }

                try {
                    val response = hostedApi.getProfileBlueprints(limit = 1)
                    if (response.isSuccessful) {
                        val blueprint = response.body()?.items?.firstOrNull()
                        if (blueprint != null) {
                            _state.update {
                                it.copy(
                                    latestBlueprintTheme = blueprint.overallTheme,
                                    latestBlueprintSlotCount = blueprint.slots.size,
                                    latestBlueprintDate = blueprint.createdAt.take(10)
                                )
                            }
                        }
                    }
                } catch (_: Exception) { }
            } finally {
                _isPullRefreshing.value = false
            }
        }
    }

    fun toggleService(enabled: Boolean) {
        if (enabled && !permissionHelper.canDrawOverlays()) {
            // Permission not granted — show the prompt instead of toggling
            _state.update { it.copy(showOverlayPermissionPrompt = true) }
            return
        }
        performToggle(enabled)
    }

    fun dismissOverlayPermissionPrompt() {
        _state.update { it.copy(showOverlayPermissionPrompt = false) }
    }

    private fun performToggle(enabled: Boolean) {
        viewModelScope.launch {
            settingsRepository.setServiceEnabled(enabled)
            if (enabled) {
                context.startForegroundService(Intent(context, OverlayService::class.java))
            } else {
                context.stopService(Intent(context, OverlayService::class.java))
            }
            hapticHelper.mediumTap()
        }
    }

    fun dismissHowItWorks() {
        viewModelScope.launch {
            settingsRepository.setFirstCaptureDone()
        }
    }

}
