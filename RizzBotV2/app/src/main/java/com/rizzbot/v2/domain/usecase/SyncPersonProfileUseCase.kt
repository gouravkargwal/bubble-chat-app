package com.rizzbot.v2.domain.usecase

import com.rizzbot.v2.data.local.db.dao.PersonProfileDao
import com.rizzbot.v2.data.local.db.entity.PersonProfileEntity
import com.rizzbot.v2.domain.model.PersonProfileResult
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.repository.LlmRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import kotlinx.coroutines.flow.first
import javax.inject.Inject

class SyncPersonProfileUseCase @Inject constructor(
    private val llmRepository: LlmRepository,
    private val settingsRepository: SettingsRepository,
    private val personProfileDao: PersonProfileDao
) {
    suspend operator fun invoke(base64Images: List<String>): PersonProfileResult {
        val provider = settingsRepository.provider.first()
            ?: return PersonProfileResult.Error("No provider selected")
        val model = settingsRepository.model.first()
            ?: return PersonProfileResult.Error("No model selected")
        val apiKey = settingsRepository.apiKey.first()
            ?: return PersonProfileResult.Error("No API key configured")

        val systemPrompt = buildSystemPrompt()
        val userPrompt = "Extract all profile information from this dating app profile screenshot."

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
                val parsed = parseProfile(result.summary)
                personProfileDao.insert(
                    PersonProfileEntity(
                        name = parsed.name,
                        age = parsed.age,
                        bio = parsed.bio,
                        interests = parsed.interests.joinToString(", "),
                        personalityTraits = parsed.personalityTraits.joinToString(", "),
                        fullExtraction = parsed.fullExtraction
                    )
                )
                parsed
            }
            is SuggestionResult.Error -> PersonProfileResult.Error(result.message)
            is SuggestionResult.Loading -> PersonProfileResult.Loading
        }
    }

    private fun buildSystemPrompt(): String = buildString {
        appendLine("You are an expert at analyzing dating app profiles. Extract all useful information from the profile screenshot.")
        appendLine()
        appendLine("## Output Format (STRICT — follow exactly):")
        appendLine("NAME: [person's name]")
        appendLine("---")
        appendLine("AGE: [age if visible, or UNKNOWN]")
        appendLine("---")
        appendLine("BIO: [their bio/about me text, or NONE if not visible]")
        appendLine("---")
        appendLine("INTERESTS:")
        appendLine("- [interest 1]")
        appendLine("- [interest 2]")
        appendLine("---")
        appendLine("PERSONALITY:")
        appendLine("- [trait 1 observed from profile]")
        appendLine("- [trait 2 observed from profile]")
        appendLine("---")
        appendLine("SUMMARY: [2-3 sentence summary of who this person is, what they seem to value, and good conversation angles to use]")
        appendLine()
        appendLine("## Rules:")
        appendLine("- Extract ONLY what you can actually see in the screenshot")
        appendLine("- For interests, include both listed interests and inferred ones from photos/bio")
        appendLine("- For personality, infer from writing style, emoji usage, photo choices")
        appendLine("- If the screenshot is unreadable, respond with: UNREADABLE")
    }

    private fun parseProfile(rawText: String): PersonProfileResult.Success {
        val sections = rawText.split("---").map { it.trim() }

        var name = "Unknown"
        var age: String? = null
        var bio: String? = null
        val interests = mutableListOf<String>()
        val personalityTraits = mutableListOf<String>()
        var summary = ""

        sections.forEach { section ->
            when {
                section.startsWith("NAME:", ignoreCase = true) -> {
                    name = section.removePrefix("NAME:").trim().ifBlank { "Unknown" }
                }
                section.startsWith("AGE:", ignoreCase = true) -> {
                    val ageStr = section.removePrefix("AGE:").trim()
                    age = if (ageStr.equals("UNKNOWN", ignoreCase = true)) null else ageStr
                }
                section.startsWith("BIO:", ignoreCase = true) -> {
                    val bioStr = section.removePrefix("BIO:").trim()
                    bio = if (bioStr.equals("NONE", ignoreCase = true)) null else bioStr
                }
                section.startsWith("INTERESTS:", ignoreCase = true) -> {
                    section.lines().drop(1).filter { it.trim().startsWith("-") }
                        .forEach { interests.add(it.trim().removePrefix("-").trim()) }
                }
                section.startsWith("PERSONALITY:", ignoreCase = true) -> {
                    section.lines().drop(1).filter { it.trim().startsWith("-") }
                        .forEach { personalityTraits.add(it.trim().removePrefix("-").trim()) }
                }
                section.startsWith("SUMMARY:", ignoreCase = true) -> {
                    summary = section.removePrefix("SUMMARY:").trim()
                }
            }
        }

        return PersonProfileResult.Success(
            name = name,
            age = age,
            bio = bio,
            interests = interests.ifEmpty { listOf("Not specified") },
            personalityTraits = personalityTraits.ifEmpty { listOf("Not enough info") },
            fullExtraction = summary.ifBlank { rawText }
        )
    }
}
