package com.rizzbot.app.accessibility.model

data class ParsedMessage(
    val text: String,
    val isIncoming: Boolean,
    val timestamp: Long = System.currentTimeMillis()
)
