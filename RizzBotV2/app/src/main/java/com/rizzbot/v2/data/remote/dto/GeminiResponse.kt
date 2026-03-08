package com.rizzbot.v2.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class GeminiResponse(
    val candidates: List<GeminiCandidate>? = null
)

@Serializable
data class GeminiCandidate(
    val content: GeminiResponseContent? = null
)

@Serializable
data class GeminiResponseContent(
    val parts: List<GeminiResponsePart>? = null
)

@Serializable
data class GeminiResponsePart(
    val text: String? = null
)
