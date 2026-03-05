package com.rizzbot.app.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class AnthropicResponse(
    val content: List<AnthropicContent>
)

@Serializable
data class AnthropicContent(
    val type: String,
    val text: String = ""
)
