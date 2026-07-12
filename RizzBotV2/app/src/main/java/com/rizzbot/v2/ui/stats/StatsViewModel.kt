package com.rizzbot.v2.ui.stats

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.domain.model.UserPreferences
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.util.AnalyticsHelper
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class StatsState(
    val totalGenerated: Int = 0,
    val totalCopied: Int = 0,
    val totalConversationsInfluenced: Int = 0,
    val preferences: UserPreferences = UserPreferences(),
    val tier: String = "free",
)
// Note: totalGenerated/totalCopied are now derived from local history (getHistory), not from
// usage.totalRepliesGenerated / usage.totalRepliesCopied which no longer exist in UsageState.

@HiltViewModel
class StatsViewModel @Inject constructor(
    private val hostedRepository: HostedRepository,
    private val analyticsHelper: AnalyticsHelper
) : ViewModel() {

    private val _state = MutableStateFlow(StatsState())
    val state: StateFlow<StatsState> = _state.asStateFlow()

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    init {
        analyticsHelper.screenViewed("Stats")

        // Collect tier from backend usage state
        viewModelScope.launch {
            hostedRepository.usageState.collect { usage ->
                _state.update {
                    it.copy(tier = usage.tier)
                }
            }
        }

        // Refresh both usage and preferences on init (use cache if available)
        viewModelScope.launch {
            hostedRepository.refreshUsage(force = false)
        }

        viewModelScope.launch {
            refreshPreferences()
        }

        // Pull recent interactions to derive totalGenerated, totalCopied, and conversationsInfluenced
        viewModelScope.launch {
            val history = hostedRepository.getHistory(limit = 200, offset = 0)
            val conversations = history
                .mapNotNull { it.personName ?: it.id }
                .distinct()
                .size
            val copied = history.count { it.copiedIndex != null }
            _state.update {
                it.copy(
                    totalGenerated = history.size,
                    totalCopied = copied,
                    totalConversationsInfluenced = conversations
                )
            }
        }
    }

    fun refresh() {
        analyticsHelper.statsRefreshed()
        viewModelScope.launch {
            _isRefreshing.value = true
            try {
                hostedRepository.refreshUsage(force = true)
                refreshPreferences()
                val history = hostedRepository.getHistory(limit = 200, offset = 0)
                val conversations = history
                    .mapNotNull { it.personName ?: it.id }
                    .distinct()
                    .size
                val copied = history.count { it.copiedIndex != null }
                _state.update {
                    it.copy(
                        totalGenerated = history.size,
                        totalCopied = copied,
                        totalConversationsInfluenced = conversations
                    )
                }
            } finally {
                _isRefreshing.value = false
            }
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
