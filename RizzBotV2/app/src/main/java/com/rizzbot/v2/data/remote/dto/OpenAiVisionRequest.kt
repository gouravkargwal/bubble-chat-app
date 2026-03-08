package com.rizzbot.v2.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class OpenAiVisionRequest(
    val model: String,
    val messages: List<OpenAiMessage>,
    @SerialName("max_tokens") val maxTokens: Int = 2000,
    val temperature: Double = 0.9
)

@Serializable
data class OpenAiMessage(
    val role: String,
    val content: List<OpenAiContentPart>
)

@Serializable
sealed class OpenAiContentPart {
    @Serializable
    @SerialName("text")
    data class Text(val text: String) : OpenAiContentPart()

    @Serializable
    @SerialName("image_url")
    data class ImageUrl(
        @SerialName("image_url") val imageUrl: ImageUrlData
    ) : OpenAiContentPart()
}

@Serializable
data class ImageUrlData(
    val url: String
)
