package com.rizzbot.v2.ui.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.data.remote.dto.HistoryItemResponse
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import com.rizzbot.v2.util.ClipboardHelper
import com.rizzbot.v2.util.HapticHelper
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HistoryViewModel @Inject constructor(
    private val hostedRepository: HostedRepository,
    private val clipboardHelper: ClipboardHelper,
    private val hapticHelper: HapticHelper,
    private val settingsRepository: SettingsRepository
) : ViewModel() {

    private val _history = MutableStateFlow<List<HistoryItemResponse>>(emptyList())
    val history: StateFlow<List<HistoryItemResponse>> = _history.asStateFlow()

    init {
        viewModelScope.launch {
            val history = hostedRepository.getHistory(limit = 50)
            // Filter out items with no valid replies (by text)
            _history.value = history.filter { item ->
                item.replies.any { reply -> reply.text.isNotBlank() }
            }
        }
    }

    fun copyReply(text: String) {
        clipboardHelper.copyToClipboard(text)
        hapticHelper.lightTap()
    }

    fun incrementHighValueCopyCount(onResult: (Int) -> Unit) {
        viewModelScope.launch {
            val value = settingsRepository.incrementHighValueCopyCount()
            onResult(value)
        }
    }

    fun deleteEntry(id: String) {
        viewModelScope.launch {
            hostedRepository.deleteHistoryItem(id)
            _history.value = _history.value.filter { it.id != id }
        }
    }
}
