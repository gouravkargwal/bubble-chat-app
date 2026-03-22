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

    private val _isLoading = MutableStateFlow(true)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _isLoadingMore = MutableStateFlow(false)
    val isLoadingMore: StateFlow<Boolean> = _isLoadingMore.asStateFlow()

    private val _hasMore = MutableStateFlow(true)
    val hasMore: StateFlow<Boolean> = _hasMore.asStateFlow()

    private var currentOffset = 0
    private val pageSize = 20

    private val _isPullRefreshing = MutableStateFlow(false)
    val isPullRefreshing: StateFlow<Boolean> = _isPullRefreshing.asStateFlow()

    init {
        viewModelScope.launch {
            reloadFirstPage(showFullScreenLoading = true)
        }
    }

    /** Pull-to-refresh: reload first page without full-screen skeleton. */
    fun refresh() {
        viewModelScope.launch {
            _isPullRefreshing.value = true
            try {
                reloadFirstPage(showFullScreenLoading = false)
            } finally {
                _isPullRefreshing.value = false
            }
        }
    }

    private suspend fun reloadFirstPage(showFullScreenLoading: Boolean) {
        if (showFullScreenLoading) {
            _isLoading.value = true
        }
        currentOffset = 0
        try {
            val history = hostedRepository.getHistory(limit = pageSize, offset = 0)
            val filtered = history.filter { item ->
                item.replies.any { reply -> reply.text.isNotBlank() }
            }
            _history.value = filtered
            _hasMore.value = filtered.size == pageSize
        } catch (e: Exception) {
            android.util.Log.e("HistoryVM", "reloadFirstPage failed: ${e.message}")
        } finally {
            if (showFullScreenLoading) {
                _isLoading.value = false
            }
        }
    }

    fun loadMore() {
        if (_isLoadingMore.value || !_hasMore.value) return

        viewModelScope.launch {
            _isLoadingMore.value = true
            try {
                currentOffset += pageSize
                val newItems = hostedRepository.getHistory(limit = pageSize, offset = currentOffset)
                val filtered = newItems.filter { item ->
                    item.replies.any { reply -> reply.text.isNotBlank() }
                }
                _history.value = _history.value + filtered
                _hasMore.value = filtered.size == pageSize
            } catch (e: Exception) {
                android.util.Log.e("HistoryVM", "loadMore failed: ${e.message}")
                currentOffset -= pageSize // Rollback on error
            } finally {
                _isLoadingMore.value = false
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
