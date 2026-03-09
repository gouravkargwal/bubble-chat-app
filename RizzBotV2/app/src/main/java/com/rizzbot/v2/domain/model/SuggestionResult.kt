package com.rizzbot.v2.domain.model

sealed class SuggestionResult {
    data class Success(
        val replies: List<String>,
        val summary: String,
        val personName: String?,
        val interactionId: String = "",
        val stage: String? = null,
        val usageRemaining: Int = -1
    ) : SuggestionResult()

    data class Error(
        val message: String,
        val errorType: ErrorType
    ) : SuggestionResult()

    data object Loading : SuggestionResult()

    enum class ErrorType {
        NO_INTERNET,
        INVALID_API_KEY,
        RATE_LIMITED,
        QUOTA_EXCEEDED,
        UNREADABLE_SCREENSHOT,
        TIMEOUT,
        UNKNOWN
    }
}
