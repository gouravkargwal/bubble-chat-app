package com.rizzbot.app.accessibility.model

data class ParsedChatScreen(
    val personName: String,
    val messages: List<ParsedMessage>,
    val profileInfo: String? = null // Bio, age, interests extracted from chat header
)
