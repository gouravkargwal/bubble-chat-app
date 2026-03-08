package com.rizzbot.v2.ui.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.data.local.db.dao.ReplyHistoryDao
import com.rizzbot.v2.data.local.db.entity.ReplyHistoryEntity
import com.rizzbot.v2.util.ClipboardHelper
import com.rizzbot.v2.util.Constants
import com.rizzbot.v2.util.HapticHelper
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HistoryViewModel @Inject constructor(
    private val replyHistoryDao: ReplyHistoryDao,
    private val clipboardHelper: ClipboardHelper,
    private val hapticHelper: HapticHelper
) : ViewModel() {

    val history: StateFlow<List<ReplyHistoryEntity>> = replyHistoryDao.getAll()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    init {
        viewModelScope.launch {
            val cutoff = System.currentTimeMillis() - (Constants.REPLY_HISTORY_EXPIRY_DAYS * 24 * 60 * 60 * 1000)
            replyHistoryDao.deleteExpired(cutoff)
        }
    }

    fun copyReply(text: String) {
        clipboardHelper.copyToClipboard(text)
        hapticHelper.lightTap()
    }

    fun deleteEntry(id: Long) {
        viewModelScope.launch {
            replyHistoryDao.deleteById(id)
        }
    }
}
