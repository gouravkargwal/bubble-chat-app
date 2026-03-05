package com.rizzbot.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class AnthropicRequest(
    val model: String,
    val system: String,
    val messages: List<AnthropicMessage>,
    @SerialName("max_tokens") val maxTokens: Int = 150,
    val temperature: Double = 0.9
)

@Serializable
data class AnthropicMessage(
    val role: String,
    val content: String
)
