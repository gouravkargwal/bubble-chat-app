package com.rizzbot.app.data.repository

import com.rizzbot.app.data.local.db.dao.ConversationDao
import com.rizzbot.app.data.local.db.dao.MessageDao
import com.rizzbot.app.data.local.db.entity.ConversationEntity
import com.rizzbot.app.data.local.db.entity.MessageEntity
import com.rizzbot.app.domain.model.ChatMessage
import com.rizzbot.app.domain.model.Conversation
import com.rizzbot.app.domain.repository.ConversationRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ConversationRepositoryImpl @Inject constructor(
    private val conversationDao: ConversationDao,
    private val messageDao: MessageDao
) : ConversationRepository {

    override fun observeAllConversations(): Flow<List<Conversation>> {
        return conversationDao.observeAllConversations().map { entities ->
            entities.map { entity ->
                Conversation(
                    personName = entity.personName,
                    messages = emptyList(),
                    lastMessageTimestamp = entity.lastMessageTimestamp,
                    messageCount = entity.messageCount,
                    platform = entity.platform
                )
            }
        }
    }

    override fun observeMessages(personName: String): Flow<List<ChatMessage>> {
        return messageDao.observeMessages(personName).map { entities ->
            entities.map { it.toDomain() }
        }
    }

    override suspend fun getRecentMessages(personName: String, limit: Int): List<ChatMessage> {
        return messageDao.getRecentMessages(personName, limit)
            .map { it.toDomain() }
            .reversed() // Oldest first for context building
    }

    override suspend fun saveMessages(personName: String, messages: List<ChatMessage>) {
        if (messages.isEmpty()) return

        val now = System.currentTimeMillis()

        // Upsert conversation FIRST to satisfy foreign key constraint
        val existing = conversationDao.getConversation(personName)
        conversationDao.upsertConversation(
            ConversationEntity(
                personName = personName,
                firstSeenTimestamp = existing?.firstSeenTimestamp ?: now,
                lastMessageTimestamp = now,
                messageCount = existing?.messageCount ?: 0
            )
        )

        val entities = messages.map { msg ->
            MessageEntity(
                personName = personName,
                text = msg.text,
                isIncoming = msg.isIncoming,
                timestamp = msg.timestamp
            )
        }
        messageDao.insertMessages(entities)

        // Update message count after insert
        val messageCount = messageDao.getMessageCount(personName)
        conversationDao.upsertConversation(
            ConversationEntity(
                personName = personName,
                firstSeenTimestamp = existing?.firstSeenTimestamp ?: now,
                lastMessageTimestamp = now,
                messageCount = messageCount
            )
        )
    }

    override suspend fun deleteConversation(personName: String) {
        val conversation = conversationDao.getConversation(personName) ?: return
        conversationDao.deleteConversation(conversation)
    }

    override suspend fun deleteAll() {
        conversationDao.deleteAll()
    }

    private fun MessageEntity.toDomain() = ChatMessage(
        text = text,
        isIncoming = isIncoming,
        timestamp = timestamp
    )
}
