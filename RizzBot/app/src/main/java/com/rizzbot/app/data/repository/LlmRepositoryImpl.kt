package com.rizzbot.app.data.repository

import com.rizzbot.app.data.remote.api.GroqApi
import com.rizzbot.app.data.remote.dto.GroqMessage
import com.rizzbot.app.data.remote.dto.GroqRequest
import com.rizzbot.app.domain.repository.LlmRepository
import com.rizzbot.app.util.Constants
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LlmRepositoryImpl @Inject constructor(
    private val groqApi: GroqApi
) : LlmRepository {

    override suspend fun generateReply(systemPrompt: String, userPrompt: String): String {
        val request = GroqRequest(
            model = Constants.GROQ_MODEL,
            messages = listOf(
                GroqMessage(role = "system", content = systemPrompt),
                GroqMessage(role = "user", content = userPrompt)
            ),
            maxTokens = Constants.LLM_MAX_TOKENS,
            temperature = Constants.LLM_TEMPERATURE
        )
        val response = groqApi.createChatCompletion(request)
        return response.choices.firstOrNull()?.message?.content?.trim()
            ?: throw IllegalStateException("Empty response from LLM")
    }
}
