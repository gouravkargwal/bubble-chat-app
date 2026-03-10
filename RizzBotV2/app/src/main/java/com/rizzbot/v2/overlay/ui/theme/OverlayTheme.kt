package com.rizzbot.v2.overlay.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

/**
 * Design tokens and theme constants for the Bubble Overlay UI
 */
object OverlayColors {
    val PanelColor = Color(0xFF1A1A2E)
    val PanelBorderColor = Color.White.copy(alpha = 0.08f)
    val AccentPink = Color(0xFFE91E63)
    val ScrimColor = Color.Black.copy(alpha = 0.6f)
    
    val BubbleGradientColors = listOf(
        Color(0xFFFF4081),
        Color(0xFFE91E63),
        Color(0xFFC2185B)
    )
}

object OverlayShapes {
    val PanelShape = RoundedCornerShape(24.dp)
    val CardShape = RoundedCornerShape(12.dp)
    val BubbleShape = RoundedCornerShape(16.dp)
}
