package com.rizzbot.v2.domain.model

data class LlmModel(
    val id: String,
    val displayName: String,
    val isRecommended: Boolean = false
)

enum class LlmProvider(
    val displayName: String,
    val baseUrl: String,
    val models: List<LlmModel>,
    val keyHelperText: String
) {
    GROQ(
        displayName = "Groq",
        baseUrl = "https://api.groq.com/openai/",
        models = listOf(
            LlmModel("meta-llama/llama-4-scout-17b-16e-instruct", "Llama 4 Scout", isRecommended = true),
            LlmModel("meta-llama/llama-4-maverick-17b-128e-instruct", "Llama 4 Maverick")
        ),
        keyHelperText = "Get free key at console.groq.com/keys"
    ),
    OPENAI(
        displayName = "OpenAI",
        baseUrl = "https://api.openai.com/",
        models = listOf(
            LlmModel("gpt-4o-mini", "GPT-4o Mini", isRecommended = true),
            LlmModel("gpt-4o", "GPT-4o")
        ),
        keyHelperText = "Get key at platform.openai.com/api-keys"
    ),
    ANTHROPIC(
        displayName = "Claude",
        baseUrl = "https://api.anthropic.com/",
        models = listOf(
            LlmModel("claude-sonnet-4-20250514", "Claude Sonnet 4", isRecommended = true),
            LlmModel("claude-haiku-3-5-20241022", "Claude 3.5 Haiku")
        ),
        keyHelperText = "Get key at console.anthropic.com/keys"
    ),
    GEMINI(
        displayName = "Gemini",
        baseUrl = "https://generativelanguage.googleapis.com/",
        models = listOf(
            LlmModel("gemini-2.5-flash", "Gemini 2.5 Flash", isRecommended = true),
            LlmModel("gemini-2.0-flash-lite", "Gemini 2.0 Flash Lite")
        ),
        keyHelperText = "Get free key at aistudio.google.com/apikey"
    );

    val defaultModel: LlmModel
        get() = models.first { it.isRecommended }
}
