package com.rizzbot.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ChatCompletionRequest(
    val model: String,
    val messages: List<ChatMessage>,
    @SerialName("max_tokens") val maxTokens: Int = 150,
    val temperature: Double = 0.9
)

@Serializable
data class ChatMessage(
    val role: String,
    val content: String
)
