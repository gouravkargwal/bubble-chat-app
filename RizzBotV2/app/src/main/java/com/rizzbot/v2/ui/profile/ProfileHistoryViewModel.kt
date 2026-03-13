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

    private val _items = MutableStateFlow<List<HistoryItem>>(emptyList())
    val items: StateFlow<List<HistoryItem>> = _items.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                val dtoItems = repository.getProfileAuditHistory()
                _items.value = dtoItems
                    .map {
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
                    .sortedByDescending { it.score }
            } finally {
                _isLoading.value = false
            }
        }
    }
}

