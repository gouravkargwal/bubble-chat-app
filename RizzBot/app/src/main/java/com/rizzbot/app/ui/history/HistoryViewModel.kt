package com.rizzbot.app.ui.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.app.accessibility.ProfileCacheManager
import com.rizzbot.app.accessibility.model.ParsedProfile
import com.rizzbot.app.domain.model.Conversation
import com.rizzbot.app.domain.repository.ConversationRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HistoryViewModel @Inject constructor(
    private val conversationRepository: ConversationRepository,
    private val profileCacheManager: ProfileCacheManager
) : ViewModel() {

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    val conversations: StateFlow<List<Conversation>> = combine(
        conversationRepository.observeAllConversations(),
        _searchQuery
    ) { convos, query ->
        if (query.isBlank()) convos
        else convos.filter { it.personName.contains(query, ignoreCase = true) }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val syncedProfileNames: StateFlow<Set<String>> = profileCacheManager
        .observeAllSyncedNames()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptySet())

    val syncedOnlyProfiles: StateFlow<List<ParsedProfile>> = combine(
        profileCacheManager.observeAllProfiles(),
        conversationRepository.observeAllConversations(),
        _searchQuery
    ) { profiles, convos, query ->
        val convoNames = convos.map { it.personName.lowercase() }.toSet()
        val filtered = profiles.filter { it.name.lowercase() !in convoNames }
        if (query.isBlank()) filtered
        else filtered.filter { it.name.contains(query, ignoreCase = true) }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun updateSearchQuery(query: String) {
        _searchQuery.value = query
    }

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
