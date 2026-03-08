package com.rizzbot.v2.data.repository

import com.rizzbot.v2.data.remote.LlmClientFactory
import com.rizzbot.v2.data.remote.dto.*
import com.rizzbot.v2.domain.model.LlmProvider
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.repository.LlmRepository
import com.rizzbot.v2.util.Constants
import kotlinx.coroutines.delay
import retrofit2.HttpException
import java.net.SocketTimeoutException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LlmRepositoryImpl @Inject constructor(
    private val clientFactory: LlmClientFactory
) : LlmRepository {

    override suspend fun generateVisionReply(
        systemPrompt: String,
        userPrompt: String,
        base64Images: List<String>,
        provider: String,
        model: String,
        apiKey: String
    ): SuggestionResult {
        var lastException: Exception? = null

        repeat(Constants.MAX_RETRIES + 1) { attempt ->
            try {
                val rawText = when (LlmProvider.valueOf(provider)) {
                    LlmProvider.GROQ, LlmProvider.OPENAI -> callOpenAiCompatible(
                        baseUrl = LlmProvider.valueOf(provider).baseUrl,
                        model = model,
                        apiKey = apiKey,
                        systemPrompt = systemPrompt,
                        userPrompt = userPrompt,
                        base64Images = base64Images
                    )
                    LlmProvider.ANTHROPIC -> callAnthropic(
                        model = model,
                        apiKey = apiKey,
                        systemPrompt = systemPrompt,
                        userPrompt = userPrompt,
                        base64Images = base64Images
                    )
                    LlmProvider.GEMINI -> callGemini(
                        model = model,
                        apiKey = apiKey,
                        systemPrompt = systemPrompt,
                        userPrompt = userPrompt,
                        base64Images = base64Images
                    )
                }

                if (rawText.isNullOrBlank()) {
                    return SuggestionResult.Error(
                        "Empty response from AI",
                        SuggestionResult.ErrorType.UNKNOWN
                    )
                }

                if (rawText.trim().uppercase() == "UNREADABLE") {
                    return SuggestionResult.Error(
                        "Couldn't read the screen. Try scrolling so messages are fully visible.",
                        SuggestionResult.ErrorType.UNREADABLE_SCREENSHOT
                    )
                }

                return parseResponse(rawText)

            } catch (e: HttpException) {
                lastException = e
                val errorBody = try { e.response()?.errorBody()?.string() } catch (_: Exception) { null }
                when (e.code()) {
                    401 -> return SuggestionResult.Error(
                        "Invalid API key. Check your settings.",
                        SuggestionResult.ErrorType.INVALID_API_KEY
                    )
                    429 -> return SuggestionResult.Error(
                        "Too many requests. Please wait a moment.",
                        SuggestionResult.ErrorType.RATE_LIMITED
                    )
                    400 -> return SuggestionResult.Error(
                        "Bad request: ${errorBody?.take(200) ?: "unknown error"}",
                        SuggestionResult.ErrorType.UNKNOWN
                    )
                    else -> {
                        if (attempt < Constants.MAX_RETRIES) {
                            delay(Constants.RETRY_INITIAL_DELAY_MS * (attempt + 1))
                        }
                    }
                }
            } catch (e: SocketTimeoutException) {
                lastException = e
                if (attempt < Constants.MAX_RETRIES) {
                    delay(Constants.RETRY_INITIAL_DELAY_MS * (attempt + 1))
                }
            } catch (e: Exception) {
                lastException = e
                if (attempt < Constants.MAX_RETRIES) {
                    delay(Constants.RETRY_INITIAL_DELAY_MS * (attempt + 1))
                }
            }
        }

        return SuggestionResult.Error(
            lastException?.message ?: "Failed after retries",
            if (lastException is SocketTimeoutException) SuggestionResult.ErrorType.TIMEOUT
            else SuggestionResult.ErrorType.UNKNOWN
        )
    }

    private suspend fun callOpenAiCompatible(
        baseUrl: String,
        model: String,
        apiKey: String,
        systemPrompt: String,
        userPrompt: String,
        base64Images: List<String>
    ): String? {
        val api = clientFactory.openAiCompatible(baseUrl, apiKey)
        val userContent = mutableListOf<OpenAiContentPart>(
            OpenAiContentPart.Text(text = userPrompt)
        )
        base64Images.forEach { img ->
            userContent.add(OpenAiContentPart.ImageUrl(imageUrl = ImageUrlData(url = "data:image/jpeg;base64,$img")))
        }
        val request = OpenAiVisionRequest(
            model = model,
            messages = listOf(
                OpenAiMessage(
                    role = "system",
                    content = listOf(OpenAiContentPart.Text(text = systemPrompt))
                ),
                OpenAiMessage(role = "user", content = userContent)
            )
        )
        val response = api.chatCompletion(request)
        return response.choices.firstOrNull()?.message?.content
    }

    private suspend fun callAnthropic(
        model: String,
        apiKey: String,
        systemPrompt: String,
        userPrompt: String,
        base64Images: List<String>
    ): String? {
        val api = clientFactory.anthropic(apiKey)
        val userContent = mutableListOf<AnthropicContentBlock>()
        base64Images.forEach { img ->
            userContent.add(AnthropicContentBlock.Image(source = AnthropicImageSource(data = img)))
        }
        userContent.add(AnthropicContentBlock.Text(text = userPrompt))
        val request = AnthropicVisionRequest(
            model = model,
            system = systemPrompt,
            messages = listOf(AnthropicMessage(role = "user", content = userContent))
        )
        val response = api.createMessage(request)
        return response.content.firstOrNull()?.text
    }

    private suspend fun callGemini(
        model: String,
        apiKey: String,
        systemPrompt: String,
        userPrompt: String,
        base64Images: List<String>
    ): String? {
        val api = clientFactory.gemini(apiKey)
        val userParts = mutableListOf<GeminiPart>(GeminiPart(text = userPrompt))
        base64Images.forEach { img ->
            userParts.add(GeminiPart(inlineData = GeminiInlineData(data = img)))
        }
        val request = GeminiVisionRequest(
            systemInstruction = GeminiContent(
                parts = listOf(GeminiPart(text = systemPrompt))
            ),
            contents = listOf(GeminiContent(role = "user", parts = userParts)),
            generationConfig = GeminiGenerationConfig()
        )
        val response = api.generateContent(model, apiKey, request)
        return response.candidates?.firstOrNull()?.content?.parts?.firstOrNull()?.text
    }

    private fun parseResponse(rawText: String): SuggestionResult {
        val parts = rawText.split("===", limit = 2)
        val repliesSection = parts[0].trim()
        val contextSection = parts.getOrNull(1)?.trim() ?: ""

        val labelPattern = Regex("^(?:Reply\\s*\\d+[:\\-–]?|(?:Flirty|Witty|Smooth|Bold)[:\\-–]?)\\s*", RegexOption.IGNORE_CASE)
        val replies = repliesSection.split("---")
            .map { it.trim().replace(labelPattern, "").trim() }
            .filter { it.isNotBlank() }

        if (replies.isEmpty()) {
            return SuggestionResult.Error(
                "Couldn't parse AI response. Try again.",
                SuggestionResult.ErrorType.UNKNOWN
            )
        }

        // Extract person name from CONTEXT block
        var personName: String? = null
        val contextMatch = Regex("Person name:\\s*(.+?)\\.", RegexOption.IGNORE_CASE).find(contextSection)
        if (contextMatch != null) {
            personName = contextMatch.groupValues[1].trim()
        }

        // Clean up context — remove "CONTEXT:" prefix
        val summary = contextSection
            .removePrefix("CONTEXT:")
            .removePrefix("context:")
            .trim()
            .ifBlank { "No context extracted" }

        return SuggestionResult.Success(
            replies = replies.take(4),
            summary = summary,
            personName = personName
        )
    }
}
