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

        // Filter out messages already in DB to avoid duplicates
        val existingIncoming = messageDao.getExistingTexts(personName, isIncoming = true).toSet()
        val existingOutgoing = messageDao.getExistingTexts(personName, isIncoming = false).toSet()

        val newMessages = messages.filter { msg ->
            val existingSet = if (msg.isIncoming) existingIncoming else existingOutgoing
            msg.text !in existingSet
        }

        if (newMessages.isNotEmpty()) {
            val entities = newMessages.map { msg ->
                MessageEntity(
                    personName = personName,
                    text = msg.text,
                    isIncoming = msg.isIncoming,
                    timestamp = msg.timestamp,
                    timestampText = msg.timestampText
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
    }

    override suspend fun replaceAllMessages(personName: String, messages: List<ChatMessage>) {
        if (messages.isEmpty()) return

        val now = System.currentTimeMillis()

        // Upsert conversation FIRST to satisfy foreign key constraint
        val existing = conversationDao.getConversation(personName)
        conversationDao.upsertConversation(
            ConversationEntity(
                personName = personName,
                firstSeenTimestamp = existing?.firstSeenTimestamp ?: now,
                lastMessageTimestamp = now,
                messageCount = messages.size
            )
        )

        // Delete all existing messages and re-insert in correct chronological order
        messageDao.deleteMessagesForPerson(personName)

        val entities = messages.map { msg ->
            MessageEntity(
                personName = personName,
                text = msg.text,
                isIncoming = msg.isIncoming,
                timestamp = msg.timestamp,
                timestampText = msg.timestampText
            )
        }
        messageDao.insertMessages(entities)
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
        timestamp = timestamp,
        timestampText = timestampText
    )
}
