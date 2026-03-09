package com.rizzbot.v2.ui.stats

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.domain.model.UserPreferences
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class StatsState(
    val totalGenerated: Int = 0,
    val totalCopied: Int = 0,
    val preferences: UserPreferences = UserPreferences()
)

@HiltViewModel
class StatsViewModel @Inject constructor(
    private val settingsRepository: SettingsRepository,
    private val hostedRepository: HostedRepository
) : ViewModel() {

    private val _state = MutableStateFlow(StatsState())
    val state: StateFlow<StatsState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            combine(
                settingsRepository.totalRepliesGenerated,
                settingsRepository.totalRepliesCopied
            ) { generated, copied ->
                Pair(generated, copied)
            }.collect { (generated, copied) ->
                _state.value = _state.value.copy(
                    totalGenerated = generated,
                    totalCopied = copied
                )
            }
        }

        viewModelScope.launch {
            val prefs = hostedRepository.getUserPreferences()
            if (prefs != null && prefs.hasEnoughData) {
                val vibeBreakdown = prefs.vibeBreakdown.associate { it.name to it.percentage }
                val preferredLength = when (prefs.preferredLength) {
                    "short" -> UserPreferences.PreferredLength.SHORT
                    "long" -> UserPreferences.PreferredLength.LONG
                    else -> UserPreferences.PreferredLength.MEDIUM
                }
                _state.value = _state.value.copy(
                    preferences = UserPreferences(
                        totalRatings = prefs.totalRatings,
                        vibeBreakdown = vibeBreakdown,
                        preferredLength = preferredLength
                    )
                )
            }
        }
    }
}
