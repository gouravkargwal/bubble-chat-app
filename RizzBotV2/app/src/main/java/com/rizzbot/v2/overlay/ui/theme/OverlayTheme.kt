package com.rizzbot.v2.overlay.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.rizzbot.v2.ui.theme.CardBg
import com.rizzbot.v2.ui.theme.PaidPlanPrimary
import com.rizzbot.v2.ui.theme.PaidPlanPrimaryDark
import com.rizzbot.v2.ui.theme.PaidPlanPrimaryLight
import com.rizzbot.v2.ui.theme.Pink
import com.rizzbot.v2.ui.theme.PinkDark

/**
 * Design tokens for the bubble overlay — aligned with in-app [com.rizzbot.v2.ui.theme] colors.
 * Accent and gradients follow [MaterialTheme.colorScheme] / [overlayBubbleGradient] when on a paid plan.
 */
object OverlayColors {
    val PanelColor = CardBg
    val PanelBorderColor = Color.White.copy(alpha = 0.08f)
    val ScrimColor = Color.Black.copy(alpha = 0.6f)
}

@Composable
fun overlayBubbleGradient(): List<Color> {
    val isPaidPlan = com.rizzbot.v2.ui.theme.LocalAppIsPaidPlan.current
    return if (isPaidPlan) {
        listOf(PaidPlanPrimaryLight, PaidPlanPrimary, PaidPlanPrimaryDark)
    } else {
        listOf(
            Color(0xFFFF4081),
            Pink,
            PinkDark
        )
    }
}

object OverlayShapes {
    val PanelShape = RoundedCornerShape(24.dp)
    val CardShape = RoundedCornerShape(12.dp)
    val BubbleShape = RoundedCornerShape(16.dp)
}
