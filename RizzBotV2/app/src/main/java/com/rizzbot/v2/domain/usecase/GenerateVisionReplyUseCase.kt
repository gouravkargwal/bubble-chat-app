package com.rizzbot.v2.domain.usecase

import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.repository.HostedRepository
import javax.inject.Inject

class GenerateVisionReplyUseCase @Inject constructor(
    private val hostedRepository: HostedRepository
) {
    suspend operator fun invoke(
        base64Images: List<String>,
        direction: DirectionWithHint
    ): SuggestionResult {
        // Backend tracks generated count in interactions table
        return hostedRepository.generateReply(base64Images, direction)
    }
}
