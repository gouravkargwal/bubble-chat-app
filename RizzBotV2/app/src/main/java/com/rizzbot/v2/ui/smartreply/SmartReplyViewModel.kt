package com.rizzbot.v2.ui.smartreply

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.capture.ImageCompressor
import com.rizzbot.v2.domain.model.ConversationDirection
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.model.UsageState
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.util.AnalyticsHelper
import com.rizzbot.v2.util.ClipboardHelper
import com.rizzbot.v2.util.HapticHelper
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import javax.inject.Inject

/**
 * Represents the current step in the Smart Reply flow.
 */
enum class SmartReplyStep(val displayName: String) {
    DIRECTION("Direction"),
    SCREENSHOTS("Screenshots"),
    GENERATING("Generating"),
    RESULT("Done"),
}

data class SmartReplyState(
    /** Current step in the flow. */
    val step: SmartReplyStep = SmartReplyStep.DIRECTION,
    /** The direction+ hint the user chose. */
    val direction: DirectionWithHint? = null,
    /** Gallery URIs the user picked. */
    val imageUris: List<Uri> = emptyList(),
    /** Decoded preview bitmaps for thumbnails. */
    val previewBitmaps: List<Bitmap> = emptyList(),
    /** Max images the user can pick (tier-based). */
    val maxScreenshots: Int = 2,
    /** Generation result (Idle = not started, Loading = in-flight, Success/Error = done). */
    val result: SuggestionResult = SuggestionResult.Idle,
    /** Latest usage snapshot. */
    val usage: UsageState = UsageState(),
    /** Custom hint text typed by the user (tier-gated). */
    val customHintText: String = "",
)

@HiltViewModel
class SmartReplyViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val hostedRepository: HostedRepository,
    private val imageCompressor: ImageCompressor,
    private val hapticHelper: HapticHelper,
    private val clipboardHelper: ClipboardHelper,
    private val analyticsHelper: AnalyticsHelper,
) : ViewModel() {

    private val _state = MutableStateFlow(SmartReplyState())
    val state: StateFlow<SmartReplyState> = _state.asStateFlow()

    private val usageMaxScreenshots: Int
        get() = _state.value.usage.maxScreenshots.coerceIn(1, 10)

    init {
        analyticsHelper.screenViewed("SmartReply")

        viewModelScope.launch {
            hostedRepository.usageState.collect { usage ->
                _state.update { current ->
                    val updated = current.copy(
                        usage = usage,
                        maxScreenshots = usage.maxScreenshots.coerceIn(1, 10),
                    )
                    // Auto-dismiss quota error when credits are restored (e.g. after upgrade)
                    // so the user continues from where they left off instead of seeing a stale error.
                    if (usage.canGenerate &&
                        updated.step == SmartReplyStep.RESULT &&
                        updated.result is SuggestionResult.Error
                    ) {
                        val errorType = (updated.result as SuggestionResult.Error).errorType
                        if (errorType == SuggestionResult.ErrorType.QUOTA_EXCEEDED) {
                            // Preserve direction + images — go back to the screenshots step
                            updated.copy(
                                step = if (updated.imageUris.isNotEmpty() && updated.direction != null)
                                    SmartReplyStep.SCREENSHOTS
                                else
                                    SmartReplyStep.DIRECTION,
                                result = SuggestionResult.Idle,
                            )
                        } else {
                            updated
                        }
                    } else {
                        updated
                    }
                }
            }
        }
    }

    /** Max characters for the custom hint text. */
    companion object {
        const val CUSTOM_HINT_MAX_LENGTH = 200
    }

    /**
     * User typed or cleared a custom hint. Truncated to [CUSTOM_HINT_MAX_LENGTH].
     */
    fun onCustomHintChanged(text: String) {
        val truncated = text.take(CUSTOM_HINT_MAX_LENGTH)
        _state.update { it.copy(customHintText = truncated) }
    }

    /**
     * User chose a direction from the picker.
     * Stay on direction step — user must tap "Continue" to proceed.
     * Includes the current custom hint text in the DirectionWithHint.
     */
    fun onDirectionChosen(direction: ConversationDirection) {
        val hint = _state.value.customHintText.takeIf { it.isNotBlank() }
        _state.update {
            it.copy(direction = DirectionWithHint(direction = direction, customHint = hint))
        }
    }

    /**
     * User tapped "Continue" after picking a direction.
     * Re-builds DirectionWithHint with whatever custom hint is currently typed.
     * Moves to the screenshots step.
     */
    fun onContinueToScreenshots() {
        if (_state.value.direction == null) return
        // Ensure the latest hint text is captured
        val hint = _state.value.customHintText.takeIf { it.isNotBlank() }
        val dir = _state.value.direction?.direction ?: return
        _state.update {
            it.copy(
                direction = DirectionWithHint(direction = dir, customHint = hint),
                step = SmartReplyStep.SCREENSHOTS,
            )
        }
    }

    /**
     * User tapped back from screenshots step — return to direction picker.
     */
    fun onBackToDirection() {
        _state.update { it.copy(step = SmartReplyStep.DIRECTION) }
    }

    /**
     * User picked images from the gallery (or cancelled).
     */
    fun onImagesPicked(uris: List<Uri>) {
        if (uris.isEmpty()) return

        viewModelScope.launch {
            val bitmaps = withContext(Dispatchers.IO) {
                uris.mapNotNull { uri ->
                    runCatching {
                        context.contentResolver.openInputStream(uri)?.use { input ->
                            BitmapFactory.decodeStream(input)
                        }
                    }.getOrNull()
                }
            }

            _state.update {
                it.copy(
                    imageUris = uris,
                    previewBitmaps = bitmaps,
                )
            }
        }
    }

    /**
     * User tapped "Generate" — explicitly starts generation.
     */
    fun onGenerate() {
        val current = _state.value
        val dir = current.direction ?: return
        if (current.imageUris.isEmpty()) return
        if (!current.usage.canGenerate) {
            _state.update {
                it.copy(
                    step = SmartReplyStep.RESULT,
                    result = SuggestionResult.Error("No credits remaining", SuggestionResult.ErrorType.QUOTA_EXCEEDED),
                )
            }
            return
        }
        generateInternal(dir)
    }

    /**
     * Regenerate with the same direction and images.
     */
    fun onRegenerate() {
        val current = _state.value
        val dir = current.direction ?: return
        if (current.imageUris.isEmpty()) return
        if (!current.usage.canGenerate) {
            _state.update {
                it.copy(
                    result = SuggestionResult.Error("No credits remaining", SuggestionResult.ErrorType.QUOTA_EXCEEDED),
                    step = SmartReplyStep.RESULT,
                )
            }
            return
        }
        generateInternal(dir)
    }

    /**
     * Start over: go back to direction picker.
     */
    fun onStartOver() {
        // Release bitmaps to avoid memory leaks
        _state.value.previewBitmaps.forEach { b ->
            if (!b.isRecycled) b.recycle()
        }
        _state.update {
            SmartReplyState(
                step = SmartReplyStep.DIRECTION,
                usage = it.usage,
                maxScreenshots = it.maxScreenshots,
            )
        }
    }

    /**
     * Copy reply to clipboard and track it.
     */
    fun onCopyReply(reply: String, index: Int, interactionId: String) {
        clipboardHelper.copyToClipboard(reply)
        hapticHelper.lightTap()
        analyticsHelper.replyCopied(index)
        viewModelScope.launch {
            if (interactionId.isNotEmpty()) {
                try {
                    hostedRepository.trackCopy(interactionId, index)
                } catch (_: Exception) { }
            }
        }
    }

    /**
     * Rate a reply.
     */
    fun onRateReply(index: Int, positive: Boolean, text: String, interactionId: String) {
        analyticsHelper.replyRated(index, positive)
        viewModelScope.launch {
            if (interactionId.isNotEmpty()) {
                try {
                    hostedRepository.trackRating(interactionId, index, positive)
                } catch (_: Exception) { }
            }
        }
    }

    // ── Internal ──

    private fun generateInternal(direction: DirectionWithHint) {
        viewModelScope.launch {
            _state.update { it.copy(step = SmartReplyStep.GENERATING, result = SuggestionResult.Loading) }

            // Compress URIs to base64 on IO thread
            val base64Images = withContext(Dispatchers.IO) {
                _state.value.imageUris.mapNotNull { uri ->
                    runCatching {
                        context.contentResolver.openInputStream(uri)?.use { input ->
                            val bitmap = BitmapFactory.decodeStream(input)
                            if (bitmap != null) imageCompressor.bitmapToBase64Jpeg(bitmap) else null
                        }
                    }.getOrNull()
                }
            }

            if (base64Images.isEmpty()) {
                _state.update {
                    it.copy(
                        step = SmartReplyStep.RESULT,
                        result = SuggestionResult.Error("Could not read images. Try again.", SuggestionResult.ErrorType.UNKNOWN)
                    )
                }
                return@launch
            }

            val result = hostedRepository.generateReply(base64Images, direction)

            when (result) {
                is SuggestionResult.Success -> hapticHelper.successTap()
                else -> { /* error handled in UI */ }
            }

            _state.update {
                it.copy(step = SmartReplyStep.RESULT, result = result)
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        _state.value.previewBitmaps.forEach { bitmap ->
            if (!bitmap.isRecycled) bitmap.recycle()
        }
    }
}
