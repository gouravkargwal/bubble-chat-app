package com.rizzbot.v2.domain.repository

import com.rizzbot.v2.domain.model.SuggestionResult

interface LlmRepository {
    suspend fun generateVisionReply(
        systemPrompt: String,
        userPrompt: String,
        base64Images: List<String>,
        provider: String,
        model: String,
        apiKey: String
    ): SuggestionResult
}
