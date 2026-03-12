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
    val totalConversationsInfluenced: Int = 0,
    val preferences: UserPreferences = UserPreferences()
)

@HiltViewModel
class StatsViewModel @Inject constructor(
    private val hostedRepository: HostedRepository
) : ViewModel() {

    private val _state = MutableStateFlow(StatsState())
    val state: StateFlow<StatsState> = _state.asStateFlow()

    init {
        // Collect stats from backend usage state
        viewModelScope.launch {
            hostedRepository.usageState.collect { usage ->
                _state.update { 
                    it.copy(
                        totalGenerated = usage.totalRepliesGenerated,
                        totalCopied = usage.totalRepliesCopied
                    )
                }
            }
        }
        
        // Refresh both usage and preferences on init
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            hostedRepository.refreshUsage()
        }
        
        viewModelScope.launch {
            refreshPreferences()
        }

        // Pull recent interactions to estimate "conversations influenced"
        viewModelScope.launch {
            val history = hostedRepository.getHistory(limit = 200)
            val conversations = history
                .mapNotNull { it.personName ?: it.id }
                .distinct()
                .size
            _state.update { it.copy(totalConversationsInfluenced = conversations) }
        }
    }

    private suspend fun refreshPreferences() {
        val prefs = hostedRepository.getUserPreferences()
        if (prefs != null) {
            val vibeBreakdown = if (prefs.hasEnoughData) {
                prefs.vibeBreakdown.associate { it.name to it.percentage }
            } else {
                emptyMap()
            }
            val preferredLength = when (prefs.preferredLength) {
                "short" -> UserPreferences.PreferredLength.SHORT
                "long" -> UserPreferences.PreferredLength.LONG
                else -> UserPreferences.PreferredLength.MEDIUM
            }
            _state.update {
                it.copy(
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
