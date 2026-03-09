package com.rizzbot.v2.domain.usecase

import com.rizzbot.v2.domain.model.DatingApp
import com.rizzbot.v2.domain.model.ProfileAnalysisResult
import javax.inject.Inject

class AnalyzeProfileUseCase @Inject constructor() {
    suspend operator fun invoke(
        base64Images: List<String>,
        datingApp: DatingApp
    ): ProfileAnalysisResult {
        // TODO: Implement via backend API endpoint when available
        return ProfileAnalysisResult.Error("Profile analysis coming soon! This feature is being upgraded.")
    }
}
