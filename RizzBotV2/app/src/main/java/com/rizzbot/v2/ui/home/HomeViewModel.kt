package com.rizzbot.v2.ui.home

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.data.local.db.dao.ReplyHistoryDao
import com.rizzbot.v2.data.local.db.entity.ReplyHistoryEntity
import com.rizzbot.v2.domain.model.UserPreferences
import com.rizzbot.v2.domain.repository.SettingsRepository
import com.rizzbot.v2.domain.usecase.AnalyzeUserPreferencesUseCase
import com.rizzbot.v2.overlay.OverlayService
import com.rizzbot.v2.util.PermissionHelper
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class HomeState(
    val isServiceEnabled: Boolean = false,
    val hasOverlayPermission: Boolean = false,
    val totalRepliesGenerated: Int = 0,
    val totalRepliesCopied: Int = 0,
    val showHowItWorks: Boolean = true,
    val recentReplies: List<ReplyHistoryEntity> = emptyList(),
    val rizzProfile: UserPreferences? = null
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val settingsRepository: SettingsRepository,
    private val permissionHelper: PermissionHelper,
    private val replyHistoryDao: ReplyHistoryDao,
    private val analyzeUserPreferencesUseCase: AnalyzeUserPreferencesUseCase
) : ViewModel() {

    private val _state = MutableStateFlow(HomeState())
    val state: StateFlow<HomeState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            combine(
                settingsRepository.serviceEnabled,
                settingsRepository.totalRepliesGenerated,
                settingsRepository.totalRepliesCopied,
                settingsRepository.firstCaptureDone,
                replyHistoryDao.getAll()
            ) { serviceEnabled, generated, copied, firstCaptureDone, history ->
                _state.value.copy(
                    isServiceEnabled = serviceEnabled,
                    hasOverlayPermission = permissionHelper.canDrawOverlays(),
                    totalRepliesGenerated = generated,
                    totalRepliesCopied = copied,
                    showHowItWorks = !firstCaptureDone,
                    recentReplies = history.take(3)
                )
            }.collect { _state.value = it }
        }

        viewModelScope.launch {
            val prefs = analyzeUserPreferencesUseCase()
            if (prefs.hasEnoughData) {
                _state.update { it.copy(rizzProfile = prefs) }
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
}
