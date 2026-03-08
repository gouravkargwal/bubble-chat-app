package com.rizzbot.v2.capture

import android.graphics.Bitmap
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.usecase.GenerateVisionReplyUseCase
import com.rizzbot.v2.util.AnalyticsHelper
import com.rizzbot.v2.util.Constants
import com.rizzbot.v2.util.HapticHelper
import com.rizzbot.v2.util.NetworkHelper
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ScreenCaptureOrchestrator @Inject constructor(
    private val screenCaptureManager: ScreenCaptureManager,
    private val imageCompressor: ImageCompressor,
    private val generateVisionReplyUseCase: GenerateVisionReplyUseCase,
    private val networkHelper: NetworkHelper,
    private val hapticHelper: HapticHelper,
    private val analyticsHelper: AnalyticsHelper
) {
    private val _result = MutableStateFlow<SuggestionResult>(SuggestionResult.Loading)
    val result: StateFlow<SuggestionResult> = _result.asStateFlow()

    private var lastCaptureTime = 0L
    private val base64Screenshots = mutableListOf<String>()
    private val previewBitmaps = mutableListOf<Bitmap>()

    val screenshotCount: Int get() = previewBitmaps.size

    val isOnCooldown: Boolean
        get() = System.currentTimeMillis() - lastCaptureTime < Constants.CAPTURE_COOLDOWN_MS

    suspend fun captureScreenshot() {
        if (isOnCooldown) return

        if (!networkHelper.isConnected()) {
            _result.value = SuggestionResult.Error(
                "No internet connection",
                SuggestionResult.ErrorType.NO_INTERNET
            )
            return
        }

        _result.value = SuggestionResult.Loading
        analyticsHelper.bubbleTapped()

        try {
            val (resultCode, data) = screenCaptureManager.requestConsent()
            hapticHelper.mediumTap()
            val bitmap = screenCaptureManager.captureScreenshot(resultCode, data)
            analyticsHelper.screenshotCaptured()
            lastCaptureTime = System.currentTimeMillis()

            base64Screenshots.add(imageCompressor.bitmapToBase64Jpeg(bitmap))
            previewBitmaps.add(bitmap)
        } catch (e: CaptureException) {
            analyticsHelper.screenshotFailed(e.message ?: "unknown")
            _result.value = SuggestionResult.Error(
                e.message ?: "Screenshot capture failed",
                SuggestionResult.ErrorType.UNKNOWN
            )
        } catch (e: Exception) {
            analyticsHelper.screenshotFailed(e.message ?: "unknown")
            _result.value = SuggestionResult.Error(
                "Something went wrong: ${e.message}",
                SuggestionResult.ErrorType.UNKNOWN
            )
        }
    }

    suspend fun generateFromScreenshots(direction: DirectionWithHint) {
        if (base64Screenshots.isEmpty()) {
            _result.value = SuggestionResult.Error(
                "No screenshot available. Try again.",
                SuggestionResult.ErrorType.UNKNOWN
            )
            return
        }

        _result.value = SuggestionResult.Loading
        analyticsHelper.directionSelected(
            direction.customHint?.let { "custom" } ?: direction.direction.name
        )

        try {
            val startTime = System.currentTimeMillis()
            val result = generateVisionReplyUseCase(base64Screenshots.toList(), direction)
            val latencyMs = System.currentTimeMillis() - startTime

            when (result) {
                is SuggestionResult.Success -> {
                    hapticHelper.successTap()
                    analyticsHelper.replyGenerated(
                        generateVisionReplyUseCase.currentProvider,
                        latencyMs
                    )
                }
                is SuggestionResult.Error -> {
                    analyticsHelper.replyFailed(
                        generateVisionReplyUseCase.currentProvider,
                        result.message
                    )
                }
                else -> {}
            }

            _result.value = result
        } catch (e: Exception) {
            _result.value = SuggestionResult.Error(
                "Something went wrong: ${e.message}",
                SuggestionResult.ErrorType.UNKNOWN
            )
        }
    }

    fun getPreviewBitmaps(): List<Bitmap> = previewBitmaps.toList()

    fun getLatestPreviewBitmap(): Bitmap? = previewBitmaps.lastOrNull()

    fun clearScreenshot() {
        base64Screenshots.clear()
        previewBitmaps.forEach { it.recycle() }
        previewBitmaps.clear()
    }

    fun resetResult() {
        _result.value = SuggestionResult.Loading
    }
}
