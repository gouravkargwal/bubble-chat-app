package com.rizzbot.v2.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class OpenAiResponse(
    val choices: List<OpenAiChoice>
)

@Serializable
data class OpenAiChoice(
    val message: OpenAiResponseMessage
)

@Serializable
data class OpenAiResponseMessage(
    val content: String
)
