package com.rizzbot.v2.domain.model

sealed class ProfileAnalysisResult {
    data class Success(
        val overallScore: Float,
        val photoFeedback: List<String>,
        val bioSuggestions: List<String>,
        val promptSuggestions: List<String>,
        val redFlags: List<String>,
        val fullAnalysis: String
    ) : ProfileAnalysisResult()

    data class Error(val message: String) : ProfileAnalysisResult()
    data object Loading : ProfileAnalysisResult()
}

enum class DatingApp(val displayName: String) {
    TINDER("Tinder"),
    BUMBLE("Bumble"),
    HINGE("Hinge"),
    OTHER("Other")
}
