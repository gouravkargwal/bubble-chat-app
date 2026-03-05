package com.rizzbot.app.domain.usecase

import com.rizzbot.app.accessibility.model.ParsedMessage
import com.rizzbot.app.domain.model.ChatMessage
import com.rizzbot.app.domain.repository.ConversationRepository
import javax.inject.Inject

class SaveMessageUseCase @Inject constructor(
    private val conversationRepository: ConversationRepository
) {
    suspend operator fun invoke(personName: String, messages: List<ParsedMessage>) {
        val chatMessages = messages.map { parsed ->
            ChatMessage(
                text = parsed.text,
                isIncoming = parsed.isIncoming,
                timestamp = parsed.timestamp,
                timestampText = parsed.timestampText
            )
        }
        conversationRepository.saveMessages(personName, chatMessages)
    }

    /**
     * Replace all messages for a conversation — used after a full chat read
     * to ensure correct chronological ordering.
     */
    suspend fun replaceAll(personName: String, messages: List<ParsedMessage>) {
        val chatMessages = messages.map { parsed ->
            ChatMessage(
                text = parsed.text,
                isIncoming = parsed.isIncoming,
                timestamp = parsed.timestamp,
                timestampText = parsed.timestampText
            )
        }
        conversationRepository.replaceAllMessages(personName, chatMessages)
    }
}
