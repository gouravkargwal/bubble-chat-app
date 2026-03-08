package com.rizzbot.v2.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class AnthropicResponse(
    val content: List<AnthropicResponseContent>
)

@Serializable
data class AnthropicResponseContent(
    val text: String? = null
)
