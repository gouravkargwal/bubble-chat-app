package com.rizzbot.v2.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.domain.model.LlmModel
import com.rizzbot.v2.domain.model.LlmProvider
import com.rizzbot.v2.domain.repository.SettingsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsState(
    val provider: LlmProvider? = null,
    val model: LlmModel? = null,
    val apiKey: String = ""
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val settingsRepository: SettingsRepository
) : ViewModel() {

    private val _state = MutableStateFlow(SettingsState())
    val state: StateFlow<SettingsState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            combine(
                settingsRepository.provider,
                settingsRepository.model,
                settingsRepository.apiKey
            ) { provider, model, apiKey ->
                SettingsState(
                    provider = provider,
                    model = model,
                    apiKey = apiKey ?: ""
                )
            }.collect { _state.value = it }
        }
    }

    fun updateProvider(provider: LlmProvider) {
        viewModelScope.launch {
            settingsRepository.setProvider(provider)
            settingsRepository.setModel(provider.defaultModel)
        }
    }

    fun updateModel(model: LlmModel) {
        viewModelScope.launch { settingsRepository.setModel(model) }
    }

    fun updateApiKey(key: String) {
        viewModelScope.launch { settingsRepository.setApiKey(key) }
    }
}
