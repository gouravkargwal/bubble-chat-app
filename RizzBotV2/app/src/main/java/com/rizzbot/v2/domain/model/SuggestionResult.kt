package com.rizzbot.v2.domain.model

import com.rizzbot.v2.data.remote.dto.ReplyOption

sealed class SuggestionResult {
    data class Success(
        val replies: List<ReplyOption>,
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

    data class RequiresUserConfirmation(
        val suggestedMatch: SuggestedMatch
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
