package com.rizzbot.v2.overlay.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.rizzbot.v2.ui.theme.CardBg
import com.rizzbot.v2.ui.theme.Pink

/**
 * Design tokens for the bubble overlay — aligned with in-app [com.rizzbot.v2.ui.theme] colors.
 */
object OverlayColors {
    val PanelColor = CardBg
    val PanelBorderColor = Color.White.copy(alpha = 0.08f)
    val AccentPink = Pink
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
