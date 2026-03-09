package com.rizzbot.v2.overlay

import com.rizzbot.v2.domain.model.DirectionWithHint

sealed class OverlayEvent {
    data object ShowBubble : OverlayEvent()
    data object HideBubble : OverlayEvent()
    data class CaptureRequested(val direction: DirectionWithHint) : OverlayEvent()
    data class ConfirmScreenshot(val direction: DirectionWithHint) : OverlayEvent()
    data object DismissSuggestions : OverlayEvent()
    data class CopyReply(val reply: String, val vibeIndex: Int, val interactionId: String = "") : OverlayEvent()
    data class RateReply(val vibeIndex: Int, val isPositive: Boolean, val replyText: String, val interactionId: String = "") : OverlayEvent()
    data class Regenerate(val direction: DirectionWithHint) : OverlayEvent()
    data class AddMoreScreenshots(val direction: DirectionWithHint) : OverlayEvent()
    data class BubbleDragged(val deltaX: Int, val deltaY: Int) : OverlayEvent()
    data object UpgradeTapped : OverlayEvent()
}
