package com.rizzbot.v2.ui.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.domain.repository.HostedRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ProfileHistoryViewModel @Inject constructor(
    private val repository: HostedRepository,
) : ViewModel() {

    private val _audits = MutableStateFlow<List<HistoryItem>>(emptyList())
    val audits: StateFlow<List<HistoryItem>> = _audits.asStateFlow()

    private var currentOffset = 0
    private var isLastPage = false
    private var isLoading = false

    private val _isLoadingState = MutableStateFlow(false)
    val isLoadingState: StateFlow<Boolean> = _isLoadingState.asStateFlow()

    private val pageSize = 20

    init {
        fetchNextPage()
    }

    fun fetchNextPage() {
        if (isLoading || isLastPage) return

        viewModelScope.launch {
            isLoading = true
            _isLoadingState.value = true
            try {
                val dtoItems = repository.getProfileAuditHistory(limit = pageSize, offset = currentOffset)
                val mapped = dtoItems.map {
                    HistoryItem(
                        id = it.id,
                        imageUrl = it.imageUrl,
                        score = it.score,
                        tier = it.tier,
                        brutalFeedback = it.brutalFeedback,
                        improvementTip = it.improvementTip,
                        createdAt = it.createdAt,
                    )
                }
                _audits.value = _audits.value + mapped.sortedByDescending { it.score }
                currentOffset += pageSize
                if (dtoItems.size < pageSize) {
                    isLastPage = true
                }
            } catch (e: Exception) {
                android.util.Log.e("ProfileHistoryVM", "fetchNextPage failed: ${e.message}")
                currentOffset = (_audits.value.size / pageSize) * pageSize
            } finally {
                isLoading = false
                _isLoadingState.value = false
            }
        }
    }

    fun refresh() {
        viewModelScope.launch {
            isLoading = true
            _isLoadingState.value = true
            currentOffset = 0
            isLastPage = false
            _audits.value = emptyList()
            try {
                val dtoItems = repository.getProfileAuditHistory(limit = pageSize, offset = 0)
                val mapped = dtoItems.map {
                    HistoryItem(
                        id = it.id,
                        imageUrl = it.imageUrl,
                        score = it.score,
                        tier = it.tier,
                        brutalFeedback = it.brutalFeedback,
                        improvementTip = it.improvementTip,
                        createdAt = it.createdAt,
                    )
                }
                _audits.value = mapped.sortedByDescending { it.score }
                currentOffset = pageSize
                if (dtoItems.size < pageSize) {
                    isLastPage = true
                }
            } catch (e: Exception) {
                android.util.Log.e("ProfileHistoryVM", "refresh failed: ${e.message}")
            } finally {
                isLoading = false
                _isLoadingState.value = false
            }
        }
    }

    fun deletePhoto(photoId: String) {
        viewModelScope.launch {
            val result = repository.deleteProfileAuditPhoto(photoId)
            result.fold(
                onSuccess = {
                    _audits.value = _audits.value.filter { it.id != photoId }
                },
                onFailure = {
                    android.util.Log.e("ProfileHistoryVM", "Failed to delete photo: ${it.message}")
                }
            )
        }
    }
}
