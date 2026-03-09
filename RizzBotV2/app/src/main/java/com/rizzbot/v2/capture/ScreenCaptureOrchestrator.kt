package com.rizzbot.v2.capture

import android.graphics.Bitmap
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.usecase.GenerateVisionReplyUseCase
import com.rizzbot.v2.util.AnalyticsHelper
import com.rizzbot.v2.util.Constants
import com.rizzbot.v2.util.HapticHelper
import com.rizzbot.v2.util.NetworkHelper
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ScreenCaptureOrchestrator @Inject constructor(
    private val screenCaptureManager: ScreenCaptureManager,
    private val imageCompressor: ImageCompressor,
    private val generateVisionReplyUseCase: GenerateVisionReplyUseCase,
    private val hostedRepository: HostedRepository,
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

    suspend fun getMaxScreenshots(): Int = hostedRepository.usageState.first().maxScreenshots

    fun canAddMore(maxScreenshots: Int): Boolean = previewBitmaps.size < maxScreenshots

    suspend fun captureScreenshot() {
        if (isOnCooldown) return

        val maxScreenshots = getMaxScreenshots()
        if (!canAddMore(maxScreenshots)) {
            _result.value = SuggestionResult.Error(
                "Max $maxScreenshots screenshots per request. Upgrade for more.",
                SuggestionResult.ErrorType.UNKNOWN
            )
            return
        }

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
                    analyticsHelper.replyGenerated("hosted", latencyMs)
                }
                is SuggestionResult.Error -> {
                    analyticsHelper.replyFailed("hosted", result.message)
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

    fun getPreviewBitmaps(): List<Bitmap> = synchronized(previewBitmaps) {
        previewBitmaps.toList()
    }

    fun getLatestPreviewBitmap(): Bitmap? = synchronized(previewBitmaps) {
        previewBitmaps.lastOrNull()
    }

    fun clearScreenshot() {
        base64Screenshots.clear()
        // Don't recycle bitmaps here — Compose may still be rendering them.
        // Let the GC collect them once all references are released.
        synchronized(previewBitmaps) {
            previewBitmaps.clear()
        }
    }

    fun resetResult() {
        _result.value = SuggestionResult.Loading
    }
}
