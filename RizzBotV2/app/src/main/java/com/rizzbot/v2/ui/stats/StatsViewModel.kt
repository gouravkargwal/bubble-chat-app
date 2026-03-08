package com.rizzbot.v2.ui.stats

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.domain.model.UserPreferences
import com.rizzbot.v2.domain.repository.SettingsRepository
import com.rizzbot.v2.domain.usecase.AnalyzeUserPreferencesUseCase
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
    private val analyzePreferences: AnalyzeUserPreferencesUseCase
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
            val prefs = analyzePreferences()
            _state.value = _state.value.copy(preferences = prefs)
        }
    }
}
