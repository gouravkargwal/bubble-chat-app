package com.rizzbot.app.ui.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.app.domain.model.TonePreference
import com.rizzbot.app.domain.repository.SettingsRepository
import com.rizzbot.app.util.PermissionHelper
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class OnboardingState(
    val currentStep: Int = 0,
    val isAccessibilityEnabled: Boolean = false,
    val isOverlayEnabled: Boolean = false,
    val selectedTone: TonePreference = TonePreference.FLIRTY
)

@HiltViewModel
class OnboardingViewModel @Inject constructor(
    private val settingsRepository: SettingsRepository,
    private val permissionHelper: PermissionHelper
) : ViewModel() {

    private val _state = MutableStateFlow(OnboardingState())
    val state: StateFlow<OnboardingState> = _state.asStateFlow()

    fun refreshPermissions() {
        _state.value = _state.value.copy(
            isAccessibilityEnabled = permissionHelper.isAccessibilityServiceEnabled(),
            isOverlayEnabled = permissionHelper.canDrawOverlays()
        )
    }

    fun nextStep() {
        _state.value = _state.value.copy(currentStep = _state.value.currentStep + 1)
    }

    fun previousStep() {
        if (_state.value.currentStep > 0) {
            _state.value = _state.value.copy(currentStep = _state.value.currentStep - 1)
        }
    }

    fun selectTone(tone: TonePreference) {
        _state.value = _state.value.copy(selectedTone = tone)
    }

    fun completeOnboarding(onComplete: () -> Unit) {
        viewModelScope.launch {
            settingsRepository.setTonePreference(_state.value.selectedTone)
            settingsRepository.setServiceEnabled(true)
            settingsRepository.setOnboardingComplete()
            onComplete()
        }
    }
}
