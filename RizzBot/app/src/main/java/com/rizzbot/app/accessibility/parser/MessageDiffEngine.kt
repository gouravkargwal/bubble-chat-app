package com.rizzbot.app.accessibility.parser

import com.rizzbot.app.accessibility.model.ParsedMessage
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MessageDiffEngine @Inject constructor() {

    private var lastKnownMessages: Map<String, List<String>> = emptyMap() // personName -> texts

    fun computeNewMessages(
        personName: String,
        currentMessages: List<ParsedMessage>
    ): List<ParsedMessage> {
        val previousTexts = lastKnownMessages[personName] ?: emptyList()
        val currentTexts = currentMessages.map { it.text }

        // Update stored state
        lastKnownMessages = lastKnownMessages + (personName to currentTexts)

        if (previousTexts.isEmpty()) {
            // First time seeing this conversation - don't trigger
            return emptyList()
        }

        // Find messages that are new (not in previous set)
        val previousSet = previousTexts.toSet()
        return currentMessages.filter { it.text !in previousSet }
    }

    fun hasNewIncomingMessage(
        personName: String,
        currentMessages: List<ParsedMessage>
    ): Boolean {
        val newMessages = computeNewMessages(personName, currentMessages)
        return newMessages.any { it.isIncoming }
    }

    fun reset() {
        lastKnownMessages = emptyMap()
    }

    fun resetForPerson(personName: String) {
        lastKnownMessages = lastKnownMessages - personName
    }
}
