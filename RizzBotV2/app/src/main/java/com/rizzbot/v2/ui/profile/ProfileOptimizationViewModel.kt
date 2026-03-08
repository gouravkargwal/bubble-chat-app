package com.rizzbot.v2.ui.profile

import android.graphics.Bitmap
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.capture.ImageCompressor
import com.rizzbot.v2.data.local.db.dao.ProfileAnalysisDao
import com.rizzbot.v2.data.local.db.entity.ProfileAnalysisEntity
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
    val previousAnalyses: List<ProfileAnalysisEntity> = emptyList(),
    val freeAnalysesRemaining: Int = 1
)

@HiltViewModel
class ProfileOptimizationViewModel @Inject constructor(
    private val analyzeProfileUseCase: AnalyzeProfileUseCase,
    private val imageCompressor: ImageCompressor,
    private val profileAnalysisDao: ProfileAnalysisDao,
    private val analyticsHelper: AnalyticsHelper
) : ViewModel() {

    private val _state = MutableStateFlow(ProfileOptimizationState())
    val state: StateFlow<ProfileOptimizationState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            profileAnalysisDao.getAll().collect { analyses ->
                _state.value = _state.value.copy(previousAnalyses = analyses)
            }
        }
        viewModelScope.launch {
            val thisMonth = System.currentTimeMillis() - (30L * 24 * 60 * 60 * 1000)
            val countThisMonth = profileAnalysisDao.countSince(thisMonth)
            _state.value = _state.value.copy(freeAnalysesRemaining = (1 - countThisMonth).coerceAtLeast(0))
        }
    }

    fun selectApp(app: DatingApp) {
        _state.value = _state.value.copy(selectedApp = app)
    }

    fun addImage(uri: Uri) {
        val current = _state.value.selectedImages.toMutableList()
        if (current.size < 5) {
            current.add(uri)
            _state.value = _state.value.copy(selectedImages = current)
        }
    }

    fun removeImage(uri: Uri) {
        val current = _state.value.selectedImages.toMutableList()
        current.remove(uri)
        _state.value = _state.value.copy(selectedImages = current)
    }

    fun analyzeProfile(bitmaps: List<Bitmap>) {
        if (bitmaps.isEmpty()) return

        viewModelScope.launch {
            _state.value = _state.value.copy(isAnalyzing = true, result = ProfileAnalysisResult.Loading)
            analyticsHelper.logEvent("profile_analysis_started", mapOf("app" to _state.value.selectedApp.name, "image_count" to bitmaps.size))

            val base64Images = bitmaps.map { imageCompressor.bitmapToBase64Jpeg(it) }
            val result = analyzeProfileUseCase(base64Images, _state.value.selectedApp)

            _state.value = _state.value.copy(result = result, isAnalyzing = false)

            when (result) {
                is ProfileAnalysisResult.Success -> {
                    analyticsHelper.logEvent("profile_analysis_completed", mapOf("score" to result.overallScore.toDouble()))
                    // Refresh free count
                    val thisMonth = System.currentTimeMillis() - (30L * 24 * 60 * 60 * 1000)
                    val countThisMonth = profileAnalysisDao.countSince(thisMonth)
                    _state.value = _state.value.copy(freeAnalysesRemaining = (1 - countThisMonth).coerceAtLeast(0))
                }
                is ProfileAnalysisResult.Error -> {
                    analyticsHelper.logEvent("profile_analysis_failed", mapOf("error" to result.message))
                }
                else -> {}
            }
        }
    }

    fun deleteAnalysis(id: Long) {
        viewModelScope.launch { profileAnalysisDao.deleteById(id) }
    }

    fun clearResult() {
        _state.value = _state.value.copy(result = null)
    }
}
