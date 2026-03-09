package com.rizzbot.v2.domain.usecase

import com.rizzbot.v2.domain.model.PersonProfileResult
import javax.inject.Inject

class SyncPersonProfileUseCase @Inject constructor() {
    suspend operator fun invoke(base64Images: List<String>): PersonProfileResult {
        // TODO: Implement via backend API endpoint when available
        return PersonProfileResult.Error("Profile sync coming soon! This feature is being upgraded.")
    }
}
