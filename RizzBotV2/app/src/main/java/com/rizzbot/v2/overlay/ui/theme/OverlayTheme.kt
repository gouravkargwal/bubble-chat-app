package com.rizzbot.v2.overlay.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.dp
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingSurface

/**
 * Design tokens for the bubble overlay — aligned with in-app [com.rizzbot.v2.ui.theme] colors.
 */
object OverlayColors {
    val PanelColor = NothingSurface
    val PanelBorderColor = NothingBorder
    val ScrimColor = NothingBlack.copy(alpha = 0.7f)
}

object OverlayShapes {
    val PanelShape = RoundedCornerShape(12.dp)
    val CardShape = RoundedCornerShape(10.dp)
    val BubbleShape = RoundedCornerShape(12.dp)
}
