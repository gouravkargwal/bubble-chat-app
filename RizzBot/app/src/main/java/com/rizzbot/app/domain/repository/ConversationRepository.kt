package com.rizzbot.app.domain.repository

import com.rizzbot.app.domain.model.ChatMessage
import com.rizzbot.app.domain.model.Conversation
import kotlinx.coroutines.flow.Flow

interface ConversationRepository {
    fun observeAllConversations(): Flow<List<Conversation>>
    fun observeMessages(personName: String): Flow<List<ChatMessage>>
    suspend fun getRecentMessages(personName: String, limit: Int): List<ChatMessage>
    suspend fun saveMessages(personName: String, messages: List<ChatMessage>)
    suspend fun replaceAllMessages(personName: String, messages: List<ChatMessage>)
    suspend fun deleteConversation(personName: String)
    suspend fun deleteAll()
}
