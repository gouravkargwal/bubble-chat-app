package com.rizzbot.v2.domain.model

data class UserPreferences(
    val totalRatings: Int = 0,
    val hasEnoughData: Boolean = false,
    val vibeBreakdown: Map<String, Float> = emptyMap(),
    val preferredLength: PreferredLength = PreferredLength.MEDIUM,
    val promptSummary: String? = null,
    val emojiFrequency: Float = 0f,
    val lowercaseUsage: Float = 0f,
    val punctuationStyle: String = "Casual",
    val topSlang: List<String> = emptyList()
) {
    enum class PreferredLength { SHORT, MEDIUM, LONG }
}
