package com.rizzbot.v2.domain.usecase

import com.rizzbot.v2.data.local.db.dao.ReplyRatingDao
import com.rizzbot.v2.domain.model.UserPreferences
import javax.inject.Inject

class AnalyzeUserPreferencesUseCase @Inject constructor(
    private val ratingDao: ReplyRatingDao
) {
    private val vibeNames = listOf("Flirty", "Witty", "Smooth", "Bold")

    suspend operator fun invoke(): UserPreferences {
        val totalRatings = ratingDao.totalCount()
        if (totalRatings < 20) return UserPreferences(totalRatings = totalRatings)

        val positiveByVibe = ratingDao.getPositiveCountsByVibe()
        val totalPositive = positiveByVibe.sumOf { it.cnt }.coerceAtLeast(1)

        val vibeBreakdown = mutableMapOf<String, Float>()
        positiveByVibe.forEach { stat ->
            val name = vibeNames.getOrElse(stat.vibeIndex) { "Unknown" }
            vibeBreakdown[name] = stat.cnt.toFloat() / totalPositive
        }

        val shortCount = ratingDao.shortPositiveCount()
        val mediumCount = ratingDao.mediumPositiveCount()
        val longCount = ratingDao.longPositiveCount()
        val preferredLength = when {
            shortCount >= mediumCount && shortCount >= longCount -> UserPreferences.PreferredLength.SHORT
            longCount >= mediumCount && longCount >= shortCount -> UserPreferences.PreferredLength.LONG
            else -> UserPreferences.PreferredLength.MEDIUM
        }

        val topVibe = vibeBreakdown.maxByOrNull { it.value }?.key ?: "Witty"
        val lengthPref = when (preferredLength) {
            UserPreferences.PreferredLength.SHORT -> "concise, short"
            UserPreferences.PreferredLength.MEDIUM -> "moderate length"
            UserPreferences.PreferredLength.LONG -> "detailed, longer"
        }

        val promptSummary = "User prefers $topVibe style with $lengthPref replies. " +
            "Style breakdown: ${vibeBreakdown.entries.joinToString(", ") { "${it.key}: ${(it.value * 100).toInt()}%" }}."

        return UserPreferences(
            totalRatings = totalRatings,
            vibeBreakdown = vibeBreakdown,
            preferredLength = preferredLength,
            promptSummary = promptSummary
        )
    }
}
