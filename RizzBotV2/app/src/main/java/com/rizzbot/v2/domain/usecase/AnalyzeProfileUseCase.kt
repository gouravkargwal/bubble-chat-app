package com.rizzbot.v2.domain.usecase

import android.graphics.Bitmap
import com.rizzbot.v2.capture.ImageCompressor
import com.rizzbot.v2.domain.model.DatingApp
import com.rizzbot.v2.domain.model.ProfileAnalysisResult
import com.rizzbot.v2.domain.repository.HostedRepository
import javax.inject.Inject

class AnalyzeProfileUseCase @Inject constructor(
    private val repository: HostedRepository,
    private val imageCompressor: ImageCompressor
) {
    suspend operator fun invoke(
        bitmaps: List<Bitmap>,
        datingApp: DatingApp
    ): ProfileAnalysisResult {
        android.util.Log.d("AnalyzeProfileUC", "invoke called with ${bitmaps.size} bitmaps for ${datingApp.name}")
        
        return try {
            val byteArrays = bitmaps.map { imageCompressor.bitmapToJpegByteArray(it) }
            val result = repository.uploadPhotosForAudit(byteArrays)
            
            result.fold(
                onSuccess = { auditResponse ->
                    android.util.Log.d("AnalyzeProfileUC", "Audit success: ${auditResponse.totalAnalyzed} photos")
                    
                    // Map AuditResponse to ProfileAnalysisResult.Success
                    val photoFeedbacks = auditResponse.photos.map { photo ->
                        "Photo ${photo.photoId.replace("photo_", "")}: [${photo.tier}] Score: ${photo.score}/10\n${photo.brutalFeedback}\nTip: ${photo.improvementTip}"
                    }
                    
                    val avgScore = if (auditResponse.photos.isNotEmpty()) {
                        auditResponse.photos.map { it.score }.average().toFloat()
                    } else 0f

                    ProfileAnalysisResult.Success(
                        overallScore = avgScore,
                        photoFeedback = photoFeedbacks,
                        bioSuggestions = listOf("Update your bio to match your high-value photos."),
                        promptSuggestions = listOf("Use prompts that spark conversation about your hobbies."),
                        redFlags = if (auditResponse.isHardReset) listOf("HARD RESET RECOMMENDED: Your current photos are not performing.") else listOf("None detected"),
                        fullAnalysis = "Your profile was analyzed. You have ${auditResponse.passedCount} photos that passed the audit out of ${auditResponse.totalAnalyzed}."
                    )
                },
                onFailure = { error ->
                    android.util.Log.e("AnalyzeProfileUC", "Audit failed", error)
                    ProfileAnalysisResult.Error(error.message ?: "Failed to analyze profile")
                }
            )
        } catch (e: Exception) {
            android.util.Log.e("AnalyzeProfileUC", "Unexpected error", e)
            ProfileAnalysisResult.Error("An unexpected error occurred: ${e.message}")
        }
    }
}
