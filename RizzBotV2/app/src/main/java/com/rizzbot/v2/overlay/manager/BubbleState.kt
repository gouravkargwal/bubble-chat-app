package com.rizzbot.v2.overlay.manager

import android.graphics.Bitmap
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.SuggestedMatch
import com.rizzbot.v2.domain.model.SuggestionResult

sealed class BubbleState(open val isProcessing: Boolean = false) {
    data object Hidden : BubbleState()
    data object RizzButton : BubbleState()
    data object RizzButtonAddMore : BubbleState()
    data object DirectionPicker : BubbleState()
    data object Capturing : BubbleState()
    data class ScreenshotPreview(
        val bitmaps: List<Bitmap>,
        val direction: DirectionWithHint
    ) : BubbleState()
    data class Loading(
        override val isProcessing: Boolean = false
    ) : BubbleState(isProcessing)
    data class Expanded(
        val result: SuggestionResult.Success
    ) : BubbleState()

    data class RequiresUserConfirmation(
        val payload: SuggestedMatch
    ) : BubbleState()
    data class Error(
        val message: String,
        val errorType: SuggestionResult.ErrorType,
        val direction: DirectionWithHint? = null
    ) : BubbleState()
    
    // Helper to check if this state should show expanded content
    fun isExpandedState(): Boolean = when (this) {
        is DirectionPicker,
        is ScreenshotPreview,
        is Loading,
        is Expanded,
        is RequiresUserConfirmation,
        is Error -> true
        else -> false
    }
}
