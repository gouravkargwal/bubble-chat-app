package com.rizzbot.v2.ui.onboarding

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.domain.model.LlmProvider
import com.rizzbot.v2.domain.repository.SettingsRepository
import com.rizzbot.v2.util.AnalyticsHelper
import com.rizzbot.v2.util.PermissionHelper
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class OnboardingState(
    val currentStep: Int = 0,
    val hasOverlayPermission: Boolean = false,
    val selectedProvider: LlmProvider? = null,
    val selectedModelId: String? = null,
    val apiKey: String = "",
    val isApiKeyValid: Boolean = false
)

@HiltViewModel
class OnboardingViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val settingsRepository: SettingsRepository,
    private val permissionHelper: PermissionHelper,
    private val analyticsHelper: AnalyticsHelper
) : ViewModel() {

    private val _state = MutableStateFlow(OnboardingState())
    val state: StateFlow<OnboardingState> = _state.asStateFlow()

    init {
        analyticsHelper.onboardingStarted()
        refreshPermissions()
    }

    fun refreshPermissions() {
        _state.value = _state.value.copy(
            hasOverlayPermission = permissionHelper.canDrawOverlays()
        )
    }

    fun nextStep() {
        val next = _state.value.currentStep + 1
        _state.value = _state.value.copy(currentStep = next)
        analyticsHelper.onboardingStepCompleted(next)
    }

    fun selectProvider(provider: LlmProvider) {
        _state.value = _state.value.copy(
            selectedProvider = provider,
            selectedModelId = provider.defaultModel.id,
            apiKey = ""
        )
        analyticsHelper.providerSelected(provider.name)
    }

    fun selectModel(modelId: String) {
        _state.value = _state.value.copy(selectedModelId = modelId)
        analyticsHelper.modelSelected(modelId)
    }

    fun updateApiKey(key: String) {
        _state.value = _state.value.copy(
            apiKey = key,
            isApiKeyValid = key.length >= 10
        )
    }

    fun completeOnboarding() {
        viewModelScope.launch {
            val s = _state.value
            s.selectedProvider?.let { settingsRepository.setProvider(it) }
            s.selectedModelId?.let { modelId ->
                val model = s.selectedProvider?.models?.find { it.id == modelId }
                model?.let { settingsRepository.setModel(it) }
            }
            if (s.apiKey.isNotBlank()) settingsRepository.setApiKey(s.apiKey)
            settingsRepository.setOnboardingCompleted(true)
            analyticsHelper.onboardingCompleted()
        }
    }
}
