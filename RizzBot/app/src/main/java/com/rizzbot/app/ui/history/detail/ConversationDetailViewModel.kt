package com.rizzbot.app.ui.history.detail

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import com.rizzbot.app.accessibility.ProfileCacheManager
import com.rizzbot.app.accessibility.model.ParsedProfile
import com.rizzbot.app.domain.model.ChatMessage
import com.rizzbot.app.domain.repository.ConversationRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import androidx.lifecycle.viewModelScope
import javax.inject.Inject

@HiltViewModel
class ConversationDetailViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    conversationRepository: ConversationRepository,
    profileCacheManager: ProfileCacheManager
) : ViewModel() {

    val personName: String = savedStateHandle.get<String>("personName") ?: ""

    val messages: StateFlow<List<ChatMessage>> = conversationRepository
        .observeMessages(personName)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val profile: StateFlow<ParsedProfile?> = profileCacheManager
        .observeProfile(personName)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)
}
