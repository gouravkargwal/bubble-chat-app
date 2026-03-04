package com.rizzbot.app.domain.model

data class Conversation(
    val personName: String,
    val messages: List<ChatMessage>,
    val lastMessageTimestamp: Long,
    val messageCount: Int,
    val platform: String = "aisle"
)
