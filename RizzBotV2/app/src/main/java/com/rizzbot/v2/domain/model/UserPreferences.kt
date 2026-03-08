package com.rizzbot.v2.domain.model

data class UserPreferences(
    val totalRatings: Int = 0,
    val vibeBreakdown: Map<String, Float> = emptyMap(),
    val preferredLength: PreferredLength = PreferredLength.MEDIUM,
    val promptSummary: String? = null
) {
    enum class PreferredLength { SHORT, MEDIUM, LONG }

    val hasEnoughData: Boolean
        get() = totalRatings >= 20
}
