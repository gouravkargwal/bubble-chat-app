package com.rizzbot.v2.ui.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.data.remote.api.HostedApi
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

@HiltViewModel
class ProfileOptimizerViewModel @Inject constructor(
    private val api: HostedApi
) : ViewModel() {

    private val _state = MutableStateFlow<OptimizerState>(OptimizerState.Idle)
    val state: StateFlow<OptimizerState> = _state.asStateFlow()

    fun generateBlueprint() {
        // Avoid spamming calls if one is already in progress
        if (_state.value is OptimizerState.Loading) return

        _state.value = OptimizerState.Loading

        viewModelScope.launch {
            try {
                val response = api.optimizeProfile()
                if (response.isSuccessful) {
                    val body = response.body()
                    if (body != null) {
                        _state.value = OptimizerState.Success(body.toUi())
                    } else {
                        _state.value = OptimizerState.Error("Empty response from server")
                    }
                } else {
                    val code = response.code()
                    val message = when (code) {
                        400 -> "We need at least one good audit first. Run a Brutal Profile Audit, then try again."
                        401 -> "Session expired. Please log in again."
                        else -> "Server error ($code). Please try again in a moment."
                    }
                    _state.value = OptimizerState.Error(message)
                }
            } catch (e: Exception) {
                _state.value = OptimizerState.Error(
                    e.message ?: "Network error. Please check your connection."
                )
            }
        }
    }

    fun reset() {
        _state.value = OptimizerState.Idle
    }
}

