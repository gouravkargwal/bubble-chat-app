package com.rizzbot.v2.ui.profile

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.data.remote.api.HostedApi
import com.rizzbot.v2.domain.repository.SettingsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class OptimizerState {
    data object Idle : OptimizerState()
    data object Loading : OptimizerState()
    data class Success(val blueprint: ProfileBlueprint) : OptimizerState()
    data class Error(val message: String) : OptimizerState()
}

sealed class BlueprintHistoryState {
    data object Idle : BlueprintHistoryState()
    data object Loading : BlueprintHistoryState()
    data class Success(val blueprints: List<ProfileBlueprint>) : BlueprintHistoryState()
    data class Error(val message: String) : BlueprintHistoryState()
}

@HiltViewModel
class ProfileOptimizerViewModel @Inject constructor(
    private val api: HostedApi,
    private val settingsRepository: SettingsRepository
) : ViewModel() {

    private val _state = MutableStateFlow<OptimizerState>(OptimizerState.Idle)
    val state: StateFlow<OptimizerState> = _state.asStateFlow()

    private val _historyState = MutableStateFlow<BlueprintHistoryState>(BlueprintHistoryState.Idle)
    val historyState: StateFlow<BlueprintHistoryState> = _historyState.asStateFlow()

    private val selectedLanguage = MutableStateFlow("English")

    init {
        viewModelScope.launch {
            settingsRepository.roastLanguage.collect { lang ->
                selectedLanguage.value = lang
            }
        }
    }

    fun generateBlueprint() {
        // Avoid spamming calls if one is already in progress
        if (_state.value is OptimizerState.Loading) return

        _state.value = OptimizerState.Loading

        viewModelScope.launch {
            try {
                val lang = selectedLanguage.value
                Log.d("ProfileOptimizerVM", "optimizeProfile: requesting blueprint, lang=$lang")
                val response = api.optimizeProfile(lang = lang)
                Log.d(
                    "ProfileOptimizerVM",
                    "optimizeProfile: httpCode=${response.code()} isSuccessful=${response.isSuccessful}"
                )
                if (response.isSuccessful) {
                    val body = response.body()
                    if (body != null) {
                        Log.d(
                            "ProfileOptimizerVM",
                            "optimizeProfile: slots=${body.slots.size}, overallTheme=${body.overallTheme.take(80)}"
                        )
                        _state.value = OptimizerState.Success(body.toUi())
                    } else {
                        Log.w("ProfileOptimizerVM", "optimizeProfile: empty body from server")
                        _state.value = OptimizerState.Error("Empty response from server")
                    }
                } else {
                    val code = response.code()
                    val message = when (code) {
                        400 -> "We need at least one good audit first. Run a Brutal Profile Audit, then try again."
                        401 -> "Session expired. Please log in again."
                        else -> "Server error ($code). Please try again in a moment."
                    }
                    Log.w(
                        "ProfileOptimizerVM",
                        "optimizeProfile: server error code=$code, message=$message"
                    )
                    _state.value = OptimizerState.Error(message)
                }
            } catch (e: Exception) {
                Log.e("ProfileOptimizerVM", "optimizeProfile: network or parsing error", e)
                _state.value = OptimizerState.Error(
                    e.message ?: "Network error. Please check your connection."
                )
            }
        }
    }

    fun reset() {
        _state.value = OptimizerState.Idle
    }

    fun loadHistory() {
        if (_historyState.value is BlueprintHistoryState.Loading) return

        _historyState.value = BlueprintHistoryState.Loading

        viewModelScope.launch {
            try {
                val response = api.getProfileBlueprints()
                if (response.isSuccessful) {
                    val body = response.body()
                    if (body != null) {
                        val blueprints = body.items.map { it.toUi() }
                        _historyState.value = BlueprintHistoryState.Success(blueprints)
                    } else {
                        _historyState.value = BlueprintHistoryState.Error("Empty response from server")
                    }
                } else {
                    _historyState.value = BlueprintHistoryState.Error("Server error: ${response.code()}")
                }
            } catch (e: Exception) {
                Log.e("ProfileOptimizerVM", "loadHistory: error", e)
                _historyState.value = BlueprintHistoryState.Error(
                    e.message ?: "Network error. Please check your connection."
                )
            }
        }
    }
}

