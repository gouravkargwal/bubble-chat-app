package com.rizzbot.app.domain.model

data class ChatMessage(
    val text: String,
    val isIncoming: Boolean,
    val timestamp: Long
)
