package com.rizzbot.v2.overlay.manager

import android.graphics.Bitmap
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.SuggestionResult

sealed class BubbleState {
    data object Hidden : BubbleState()
    data object RizzButton : BubbleState()
    data object DirectionPicker : BubbleState()
    data object Capturing : BubbleState()
    data class ScreenshotPreview(val bitmaps: List<Bitmap>, val direction: DirectionWithHint) : BubbleState()
    data object Loading : BubbleState()
    data class Expanded(val result: SuggestionResult.Success) : BubbleState()
    data class Error(val message: String, val errorType: SuggestionResult.ErrorType, val direction: DirectionWithHint? = null) : BubbleState()
}
