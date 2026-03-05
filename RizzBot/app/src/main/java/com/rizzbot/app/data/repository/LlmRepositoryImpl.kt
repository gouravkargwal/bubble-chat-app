package com.rizzbot.app.data.repository

import com.rizzbot.app.data.local.datastore.SettingsDataStore
import com.rizzbot.app.data.remote.LlmClientFactory
import com.rizzbot.app.data.remote.dto.AnthropicMessage
import com.rizzbot.app.data.remote.dto.AnthropicRequest
import com.rizzbot.app.data.remote.dto.ChatCompletionRequest
import com.rizzbot.app.data.remote.dto.ChatMessage
import com.rizzbot.app.data.remote.dto.GeminiContent
import com.rizzbot.app.data.remote.dto.GeminiGenerationConfig
import com.rizzbot.app.data.remote.dto.GeminiPart
import com.rizzbot.app.data.remote.dto.GeminiRequest
import com.rizzbot.app.domain.model.LlmProvider
import com.rizzbot.app.domain.repository.LlmRepository
import com.rizzbot.app.util.Constants
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withTimeout
import android.util.Log
import retrofit2.HttpException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import com.rizzbot.app.util.AnalyticsHelper
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LlmRepositoryImpl @Inject constructor(
    private val clientFactory: LlmClientFactory,
    private val settingsDataStore: SettingsDataStore,
    private val analyticsHelper: AnalyticsHelper
) : LlmRepository {

    override suspend fun generateReply(systemPrompt: String, userPrompt: String): String {
        val providerName = settingsDataStore.selectedProvider.first()
        val model = settingsDataStore.selectedModel.first()
        val apiKey = settingsDataStore.apiKey.first()

        if (apiKey.isBlank()) {
            throw IllegalStateException("No API key configured. Open RizzBot app → Settings → enter your API key.")
        }

        val provider = try {
            LlmProvider.valueOf(providerName)
        } catch (_: Exception) {
            LlmProvider.GROQ
        }

        // Increment usage counter
        settingsDataStore.incrementRepliesGenerated()

        val tone = settingsDataStore.tonePreference.first()

        return try {
            val result = withRetry {
                withTimeout(TIMEOUT_MS) {
                    when (provider) {
                        LlmProvider.GROQ, LlmProvider.OPENAI -> callOpenAiCompatible(provider, apiKey, model, systemPrompt, userPrompt)
                        LlmProvider.ANTHROPIC -> callAnthropic(apiKey, model, systemPrompt, userPrompt)
                        LlmProvider.GEMINI -> callGemini(apiKey, model, systemPrompt, userPrompt)
                    }
                }
            }
            analyticsHelper.logReplyGenerated(provider.name, tone)
            result
        } catch (e: Exception) {
            analyticsHelper.logError("Reply generation failed: ${provider.name}/$model", e)
            throw e
        }
    }

    override suspend fun validateApiKey(): Boolean {
        val providerName = settingsDataStore.selectedProvider.first()
        val model = settingsDataStore.selectedModel.first()
        val apiKey = settingsDataStore.apiKey.first()

        if (apiKey.isBlank()) return false

        val provider = try {
            LlmProvider.valueOf(providerName)
        } catch (_: Exception) {
            LlmProvider.GROQ
        }

        return try {
            withTimeout(15_000) {
                when (provider) {
                    LlmProvider.GROQ, LlmProvider.OPENAI -> callOpenAiCompatible(provider, apiKey, model, "Reply with OK", "test")
                    LlmProvider.ANTHROPIC -> callAnthropic(apiKey, model, "Reply with OK", "test")
                    LlmProvider.GEMINI -> callGemini(apiKey, model, "Reply with OK", "test")
                }
            }
            Log.d(TAG, "API key validation SUCCESS for $providerName/$model")
            true
        } catch (e: HttpException) {
            val body = try { e.response()?.errorBody()?.string() } catch (_: Exception) { null }
            Log.e(TAG, "API key validation FAILED for $providerName/$model: HTTP ${e.code()} - $body", e)
            false
        } catch (e: Exception) {
            Log.e(TAG, "API key validation FAILED for $providerName/$model: ${e.javaClass.simpleName} - ${e.message}", e)
            false
        }
    }

    private suspend fun <T> withRetry(block: suspend () -> T): T {
        var lastException: Exception? = null
        repeat(MAX_RETRIES) { attempt ->
            try {
                return block()
            } catch (e: Exception) {
                lastException = e
                if (!isRetryable(e) || attempt == MAX_RETRIES - 1) {
                    throw mapException(e)
                }
                delay(RETRY_DELAY_MS * (attempt + 1))
            }
        }
        throw mapException(lastException!!)
    }

    private fun isRetryable(e: Exception): Boolean = when (e) {
        is SocketTimeoutException -> true
        is HttpException -> e.code() in listOf(429, 500, 502, 503, 504)
        else -> false
    }

    private fun mapException(e: Exception): Exception = when (e) {
        is HttpException -> when (e.code()) {
            401 -> IllegalStateException("Invalid API key. Please check your key in Settings.")
            429 -> IllegalStateException("Rate limited. Wait a moment and try again, or switch to a different provider.")
            402 -> IllegalStateException("Insufficient credits/quota. Check your API provider account.")
            403 -> IllegalStateException("Access denied. Your API key may not have the required permissions.")
            in 500..599 -> IllegalStateException("Provider is having issues. Try again or switch provider.")
            else -> IllegalStateException("API error (${e.code()}). Try again.")
        }
        is SocketTimeoutException -> IllegalStateException("Request timed out. Try a faster model like Groq Llama 3.3.")
        is UnknownHostException -> IllegalStateException("No internet connection. Check your network and try again.")
        is kotlinx.coroutines.TimeoutCancellationException -> IllegalStateException("Taking too long. Try Groq for faster responses.")
        else -> e
    }

    private suspend fun callOpenAiCompatible(
        provider: LlmProvider,
        apiKey: String,
        model: String,
        systemPrompt: String,
        userPrompt: String
    ): String {
        val api = clientFactory.createOpenAiCompatibleApi(provider.baseUrl, apiKey)
        val request = ChatCompletionRequest(
            model = model,
            messages = listOf(
                ChatMessage(role = "system", content = systemPrompt),
                ChatMessage(role = "user", content = userPrompt)
            ),
            maxTokens = Constants.LLM_MAX_TOKENS,
            temperature = Constants.LLM_TEMPERATURE
        )
        val response = api.createChatCompletion(request)
        return response.choices.firstOrNull()?.message?.content?.trim()
            ?: throw IllegalStateException("Empty response from LLM")
    }

    private suspend fun callAnthropic(
        apiKey: String,
        model: String,
        systemPrompt: String,
        userPrompt: String
    ): String {
        val api = clientFactory.createAnthropicApi(apiKey)
        val request = AnthropicRequest(
            model = model,
            system = systemPrompt,
            messages = listOf(
                AnthropicMessage(role = "user", content = userPrompt)
            ),
            maxTokens = Constants.LLM_MAX_TOKENS,
            temperature = Constants.LLM_TEMPERATURE
        )
        val response = api.createMessage(request)
        return response.content.firstOrNull { it.type == "text" }?.text?.trim()
            ?: throw IllegalStateException("Empty response from LLM")
    }

    private suspend fun callGemini(
        apiKey: String,
        model: String,
        systemPrompt: String,
        userPrompt: String
    ): String {
        val api = clientFactory.createGeminiApi()
        val request = GeminiRequest(
            contents = listOf(
                GeminiContent(
                    role = "user",
                    parts = listOf(GeminiPart(text = userPrompt))
                )
            ),
            systemInstruction = GeminiContent(
                parts = listOf(GeminiPart(text = systemPrompt))
            ),
            generationConfig = GeminiGenerationConfig(
                temperature = Constants.LLM_TEMPERATURE,
                maxOutputTokens = Constants.LLM_MAX_TOKENS
            )
        )
        val response = api.generateContent(model = model, apiKey = apiKey, request = request)
        return response.candidates.firstOrNull()?.content?.parts?.firstOrNull()?.text?.trim()
            ?: throw IllegalStateException("Empty response from LLM")
    }

    companion object {
        private const val TAG = "RizzBot"
        private const val MAX_RETRIES = 2
        private const val RETRY_DELAY_MS = 1000L
        private const val TIMEOUT_MS = 30_000L
    }
}
