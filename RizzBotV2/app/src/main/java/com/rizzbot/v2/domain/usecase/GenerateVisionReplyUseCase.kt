package com.rizzbot.v2.domain.usecase

import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import javax.inject.Inject

class GenerateVisionReplyUseCase @Inject constructor(
    private val hostedRepository: HostedRepository,
    private val settingsRepository: SettingsRepository
) {
    suspend operator fun invoke(
        base64Images: List<String>,
        direction: DirectionWithHint
    ): SuggestionResult {
        val result = hostedRepository.generateReply(base64Images, direction)

        if (result is SuggestionResult.Success) {
            settingsRepository.incrementRepliesGenerated()
        }

        return result
    }
}
