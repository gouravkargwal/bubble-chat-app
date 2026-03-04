package com.rizzbot.app.domain.model

sealed class SuggestionResult {
    data class Success(val replies: List<String>) : SuggestionResult()
    data class Error(val message: String) : SuggestionResult()
    data object Loading : SuggestionResult()
}
