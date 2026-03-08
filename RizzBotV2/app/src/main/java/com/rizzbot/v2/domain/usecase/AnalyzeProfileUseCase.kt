package com.rizzbot.v2.domain.usecase

import com.rizzbot.v2.data.local.db.dao.ProfileAnalysisDao
import com.rizzbot.v2.data.local.db.entity.ProfileAnalysisEntity
import com.rizzbot.v2.domain.model.DatingApp
import com.rizzbot.v2.domain.model.ProfileAnalysisResult
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.repository.LlmRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import kotlinx.coroutines.flow.first
import javax.inject.Inject

class AnalyzeProfileUseCase @Inject constructor(
    private val llmRepository: LlmRepository,
    private val settingsRepository: SettingsRepository,
    private val profileAnalysisDao: ProfileAnalysisDao
) {
    suspend operator fun invoke(
        base64Images: List<String>,
        datingApp: DatingApp
    ): ProfileAnalysisResult {
        val provider = settingsRepository.provider.first()
            ?: return ProfileAnalysisResult.Error("No provider selected")
        val model = settingsRepository.model.first()
            ?: return ProfileAnalysisResult.Error("No model selected")
        val apiKey = settingsRepository.apiKey.first()
            ?: return ProfileAnalysisResult.Error("No API key configured")

        val systemPrompt = buildSystemPrompt(datingApp)
        val userPrompt = buildUserPrompt(datingApp, base64Images.size)

        val result = llmRepository.generateVisionReply(
            systemPrompt = systemPrompt,
            userPrompt = userPrompt,
            base64Images = base64Images,
            provider = provider.name,
            model = model.id,
            apiKey = apiKey
        )

        return when (result) {
            is SuggestionResult.Success -> {
                val parsed = parseProfileAnalysis(result.summary)
                // Save to DB
                profileAnalysisDao.insert(
                    ProfileAnalysisEntity(
                        datingApp = datingApp.name,
                        overallScore = parsed.overallScore,
                        photoFeedback = parsed.photoFeedback.joinToString("\n"),
                        bioSuggestions = parsed.bioSuggestions.joinToString("\n"),
                        promptSuggestions = parsed.promptSuggestions.joinToString("\n"),
                        redFlags = parsed.redFlags.joinToString("\n"),
                        fullAnalysis = parsed.fullAnalysis
                    )
                )
                parsed
            }
            is SuggestionResult.Error -> ProfileAnalysisResult.Error(result.message)
            is SuggestionResult.Loading -> ProfileAnalysisResult.Loading
        }
    }

    private fun buildSystemPrompt(datingApp: DatingApp): String = buildString {
        appendLine("You are an expert dating profile optimizer with deep knowledge of what makes profiles successful on ${datingApp.displayName}.")
        appendLine()
        appendLine("## Your Task:")
        appendLine("Analyze the user's dating profile screenshot and provide detailed, actionable feedback.")
        appendLine()
        appendLine("## Output Format (STRICT):")
        appendLine("SCORE: [X.X/10]")
        appendLine("---")
        appendLine("PHOTOS:")
        appendLine("- [feedback point 1]")
        appendLine("- [feedback point 2]")
        appendLine("---")
        appendLine("BIO:")
        appendLine("- [suggestion 1]")
        appendLine("- [suggestion 2]")
        appendLine("- [Alternative bio option]")
        appendLine("---")
        appendLine("PROMPTS:")
        appendLine("- [prompt improvement 1]")
        appendLine("- [prompt improvement 2]")
        appendLine("---")
        appendLine("RED FLAGS:")
        appendLine("- [red flag 1]")
        appendLine("- [red flag 2]")
        appendLine("---")
        appendLine("SUMMARY: [2-3 sentence overall assessment with the most impactful change to make]")
        appendLine()
        appendLine("## Rules:")
        appendLine("- Be specific and actionable (not vague like 'use better photos')")
        appendLine("- Reference what you actually see in the screenshot")
        appendLine("- Tailor advice to ${datingApp.displayName}'s format and culture")
        appendLine("- If the screenshot is unreadable, respond with: UNREADABLE")
        appendLine("- Score honestly — most profiles are 5-7, only exceptional ones are 8+")
    }

    private fun buildUserPrompt(datingApp: DatingApp, imageCount: Int): String = buildString {
        appendLine("Analyze this ${datingApp.displayName} dating profile screenshot.")
        appendLine("Provide a score out of 10, photo feedback, bio suggestions, prompt improvements, and any red flags.")
        if (imageCount > 1) {
            appendLine("Note: This is the main profile view. The user has $imageCount screenshots total.")
        }
    }

    private fun parseProfileAnalysis(rawText: String): ProfileAnalysisResult.Success {
        val sections = rawText.split("---").map { it.trim() }

        var score = 5.0f
        val photoFeedback = mutableListOf<String>()
        val bioSuggestions = mutableListOf<String>()
        val promptSuggestions = mutableListOf<String>()
        val redFlags = mutableListOf<String>()
        var summary = ""

        sections.forEach { section ->
            when {
                section.startsWith("SCORE:", ignoreCase = true) -> {
                    val scoreStr = section.removePrefix("SCORE:").trim()
                    val match = Regex("(\\d+\\.?\\d*)").find(scoreStr)
                    score = match?.groupValues?.get(1)?.toFloatOrNull() ?: 5.0f
                }
                section.startsWith("PHOTOS:", ignoreCase = true) -> {
                    section.lines().drop(1).filter { it.trim().startsWith("-") }
                        .forEach { photoFeedback.add(it.trim().removePrefix("-").trim()) }
                }
                section.startsWith("BIO:", ignoreCase = true) -> {
                    section.lines().drop(1).filter { it.trim().startsWith("-") }
                        .forEach { bioSuggestions.add(it.trim().removePrefix("-").trim()) }
                }
                section.startsWith("PROMPTS:", ignoreCase = true) -> {
                    section.lines().drop(1).filter { it.trim().startsWith("-") }
                        .forEach { promptSuggestions.add(it.trim().removePrefix("-").trim()) }
                }
                section.startsWith("RED FLAGS:", ignoreCase = true) -> {
                    section.lines().drop(1).filter { it.trim().startsWith("-") }
                        .forEach { redFlags.add(it.trim().removePrefix("-").trim()) }
                }
                section.startsWith("SUMMARY:", ignoreCase = true) -> {
                    summary = section.removePrefix("SUMMARY:").trim()
                }
            }
        }

        return ProfileAnalysisResult.Success(
            overallScore = score.coerceIn(0f, 10f),
            photoFeedback = photoFeedback.ifEmpty { listOf("No specific photo feedback") },
            bioSuggestions = bioSuggestions.ifEmpty { listOf("No specific bio suggestions") },
            promptSuggestions = promptSuggestions.ifEmpty { listOf("No specific prompt suggestions") },
            redFlags = redFlags.ifEmpty { listOf("None detected") },
            fullAnalysis = summary.ifBlank { rawText }
        )
    }
}
