package com.rizzbot.app.domain.usecase

import com.rizzbot.app.domain.model.ChatMessage
import com.rizzbot.app.domain.repository.ConversationRepository
import com.rizzbot.app.util.Constants
import javax.inject.Inject

class GetConversationHistoryUseCase @Inject constructor(
    private val conversationRepository: ConversationRepository
) {
    suspend operator fun invoke(personName: String): List<ChatMessage> {
        return conversationRepository.getRecentMessages(personName, Constants.MAX_CONTEXT_MESSAGES)
    }
}
