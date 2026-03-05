package com.rizzbot.app.ui.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.app.domain.model.LlmModel
import com.rizzbot.app.domain.model.LlmProvider
import com.rizzbot.app.domain.repository.SettingsRepository
import com.rizzbot.app.util.AnalyticsHelper
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
    val selectedProvider: LlmProvider = LlmProvider.GROQ,
    val selectedModel: LlmModel = LlmProvider.GROQ.defaultModel,
    val availableModels: List<LlmModel> = LlmProvider.GROQ.models,
    val apiKey: String = ""
)

@HiltViewModel
class OnboardingViewModel @Inject constructor(
    private val settingsRepository: SettingsRepository,
    private val permissionHelper: PermissionHelper,
    private val analyticsHelper: AnalyticsHelper
) : ViewModel() {

    companion object {
        const val TOTAL_STEPS = 2
    }

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

    fun selectProvider(provider: LlmProvider) {
        _state.value = _state.value.copy(
            selectedProvider = provider,
            selectedModel = provider.defaultModel,
            availableModels = provider.models,
            apiKey = ""
        )
    }

    fun selectModel(model: LlmModel) {
        _state.value = _state.value.copy(selectedModel = model)
    }

    fun updateApiKey(key: String) {
        _state.value = _state.value.copy(apiKey = key)
    }

    fun completeOnboarding(onComplete: () -> Unit) {
        viewModelScope.launch {
            settingsRepository.setSelectedProvider(_state.value.selectedProvider.name)
            settingsRepository.setSelectedModel(_state.value.selectedModel.id)
            settingsRepository.setApiKey(_state.value.apiKey)
            settingsRepository.setServiceEnabled(true)
            settingsRepository.setOnboardingComplete()
            analyticsHelper.logOnboardingCompleted()
            analyticsHelper.logProviderSelected(_state.value.selectedProvider.name)
            analyticsHelper.setUserProperty("provider", _state.value.selectedProvider.name)
            onComplete()
        }
    }
}
