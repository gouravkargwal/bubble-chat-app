package com.rizzbot.app.domain.model

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
            LlmModel("llama-3.3-70b-versatile", "Llama 3.3 70B", isRecommended = true),
            LlmModel("llama-3.1-8b-instant", "Llama 3.1 8B")
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
            LlmModel("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite")
        ),
        keyHelperText = "Get free key at aistudio.google.com/apikey"
    );

    val defaultModel: LlmModel
        get() = models.first { it.isRecommended }
}
