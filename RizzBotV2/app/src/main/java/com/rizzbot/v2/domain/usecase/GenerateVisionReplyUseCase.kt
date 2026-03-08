package com.rizzbot.v2.domain.usecase

import com.rizzbot.v2.data.local.db.dao.PersonProfileDao
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.repository.LlmRepository
import com.rizzbot.v2.domain.repository.MemoryRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import kotlinx.coroutines.flow.first
import javax.inject.Inject

class GenerateVisionReplyUseCase @Inject constructor(
    private val llmRepository: LlmRepository,
    private val memoryRepository: MemoryRepository,
    private val settingsRepository: SettingsRepository,
    private val buildSystemPromptUseCase: BuildSystemPromptUseCase,
    private val personProfileDao: PersonProfileDao
) {
    var currentProvider: String = ""
        private set

    suspend operator fun invoke(
        base64Images: List<String>,
        direction: DirectionWithHint
    ): SuggestionResult {
        val provider = settingsRepository.provider.first()
            ?: return SuggestionResult.Error("No provider selected", SuggestionResult.ErrorType.UNKNOWN)
        val model = settingsRepository.model.first()
            ?: return SuggestionResult.Error("No model selected", SuggestionResult.ErrorType.UNKNOWN)
        val apiKey = settingsRepository.apiKey.first()
            ?: return SuggestionResult.Error("No API key configured", SuggestionResult.ErrorType.INVALID_API_KEY)

        currentProvider = provider.name

        val previousSummary = memoryRepository.getActiveMemory()
        val latestPersonProfile = personProfileDao.getLatest()
        val personContext = latestPersonProfile?.let { profile ->
            buildString {
                appendLine("Name: ${profile.name}")
                if (profile.age != null) appendLine("Age: ${profile.age}")
                if (profile.bio != null) appendLine("Bio: ${profile.bio}")
                if (!profile.interests.isNullOrBlank()) appendLine("Interests: ${profile.interests}")
                if (!profile.personalityTraits.isNullOrBlank()) appendLine("Personality: ${profile.personalityTraits}")
            }
        }
        val (systemPrompt, userPrompt) = buildSystemPromptUseCase.forScreenshotAnalysis(
            previousSummary = previousSummary,
            direction = direction,
            personProfileContext = personContext
        )

        val result = llmRepository.generateVisionReply(
            systemPrompt = systemPrompt,
            userPrompt = userPrompt,
            base64Images = base64Images,
            provider = provider.name,
            model = model.id,
            apiKey = apiKey
        )

        // Save memory on success
        if (result is SuggestionResult.Success) {
            memoryRepository.saveMemory(result.personName, result.summary)
            settingsRepository.incrementRepliesGenerated()
        }

        return result
    }
}
