package com.rizzbot.app.ui.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.app.accessibility.ProfileCacheManager
import com.rizzbot.app.accessibility.model.ParsedProfile
import com.rizzbot.app.domain.model.Conversation
import com.rizzbot.app.domain.repository.ConversationRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HistoryViewModel @Inject constructor(
    private val conversationRepository: ConversationRepository,
    private val profileCacheManager: ProfileCacheManager
) : ViewModel() {

    val conversations: StateFlow<List<Conversation>> = conversationRepository
        .observeAllConversations()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val syncedProfileNames: StateFlow<Set<String>> = profileCacheManager
        .observeAllSyncedNames()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptySet())

    /** Profiles synced from the like/dislike page that don't have a conversation yet */
    val syncedOnlyProfiles: StateFlow<List<ParsedProfile>> = combine(
        profileCacheManager.observeAllProfiles(),
        conversationRepository.observeAllConversations()
    ) { profiles, convos ->
        val convoNames = convos.map { it.personName.lowercase() }.toSet()
        profiles.filter { it.name.lowercase() !in convoNames }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun deleteConversation(personName: String) {
        viewModelScope.launch {
            conversationRepository.deleteConversation(personName)
        }
    }

    fun deleteProfile(personName: String) {
        viewModelScope.launch {
            profileCacheManager.deleteProfile(personName)
        }
    }
}
