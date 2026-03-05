package com.rizzbot.app.accessibility.model

data class ParsedMessage(
    val text: String,
    val isIncoming: Boolean,
    val timestamp: Long = 0L,
    val timestampText: String? = null
)
