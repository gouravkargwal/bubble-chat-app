package com.rizzbot.v2.ui.profile

import android.graphics.Bitmap
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.capture.ImageCompressor
import com.rizzbot.v2.domain.model.DatingApp
import com.rizzbot.v2.domain.model.ProfileAnalysisResult
import com.rizzbot.v2.domain.usecase.AnalyzeProfileUseCase
import com.rizzbot.v2.util.AnalyticsHelper
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ProfileOptimizationState(
    val selectedApp: DatingApp = DatingApp.TINDER,
    val selectedImages: List<Uri> = emptyList(),
    val result: ProfileAnalysisResult? = null,
    val isAnalyzing: Boolean = false,
    val freeAnalysesRemaining: Int = 1
)

@HiltViewModel
class ProfileOptimizationViewModel @Inject constructor(
    private val analyzeProfileUseCase: AnalyzeProfileUseCase,
    private val imageCompressor: ImageCompressor,
    private val analyticsHelper: AnalyticsHelper
) : ViewModel() {

    private val _state = MutableStateFlow(ProfileOptimizationState())
    val state: StateFlow<ProfileOptimizationState> = _state.asStateFlow()

    fun selectApp(app: DatingApp) {
        _state.value = _state.value.copy(selectedApp = app)
    }

    fun addImage(uri: Uri) {
        android.util.Log.d("ProfileOptim", "Adding image: $uri")
        val current = _state.value.selectedImages.toMutableList()
        if (current.size < 5) {
            current.add(uri)
            _state.value = _state.value.copy(selectedImages = current)
        } else {
            android.util.Log.w("ProfileOptim", "Max images reached (5)")
        }
    }

    fun removeImage(uri: Uri) {
        val current = _state.value.selectedImages.toMutableList()
        current.remove(uri)
        _state.value = _state.value.copy(selectedImages = current)
    }

    fun analyzeProfile(bitmaps: List<Bitmap>) {
        android.util.Log.d("ProfileOptim", "analyzeProfile called with ${bitmaps.size} bitmaps")
        if (bitmaps.isEmpty()) {
            android.util.Log.w("ProfileOptim", "No bitmaps provided for analysis")
            return
        }

        viewModelScope.launch {
            _state.value = _state.value.copy(isAnalyzing = true, result = ProfileAnalysisResult.Loading)
            analyticsHelper.logEvent("profile_analysis_started", mapOf("app" to _state.value.selectedApp.name, "image_count" to bitmaps.size))

            android.util.Log.d("ProfileOptim", "Calling analyzeProfileUseCase")
            val result = analyzeProfileUseCase(bitmaps, _state.value.selectedApp)
            
            android.util.Log.d("ProfileOptim", "Received result: ${result.javaClass.simpleName}")
            _state.value = _state.value.copy(result = result, isAnalyzing = false)

            when (result) {
                is ProfileAnalysisResult.Success -> {
                    analyticsHelper.logEvent("profile_analysis_completed", mapOf("score" to result.overallScore.toDouble()))
                }
                is ProfileAnalysisResult.Error -> {
                    android.util.Log.e("ProfileOptim", "Analysis error: ${result.message}")
                    analyticsHelper.logEvent("profile_analysis_failed", mapOf("error" to result.message))
                }
                else -> {}
            }
        }
    }

    fun clearResult() {
        _state.value = _state.value.copy(result = null)
    }
}
