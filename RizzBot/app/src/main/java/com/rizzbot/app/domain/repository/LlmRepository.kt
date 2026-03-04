package com.rizzbot.app.domain.repository

interface LlmRepository {
    suspend fun generateReply(systemPrompt: String, userPrompt: String): String
}
