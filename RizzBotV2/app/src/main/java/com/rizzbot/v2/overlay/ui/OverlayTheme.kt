package com.rizzbot.v2.overlay.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import com.rizzbot.v2.ui.theme.PaidPlanPrimary
import com.rizzbot.v2.ui.theme.PaidPlanPrimaryDark
import com.rizzbot.v2.ui.theme.PaidPlanSecondary
import com.rizzbot.v2.ui.theme.Pink
import com.rizzbot.v2.ui.theme.PinkDark
import com.rizzbot.v2.ui.theme.Purple

private val DarkOnGoldPrimary = Color(0xFF1C1508)

private val OverlayPinkScheme = darkColorScheme(
    primary = Pink,
    onPrimary = Color.White,
    secondary = Purple,
    tertiary = PinkDark,
    surface = Color.Transparent,
    onSurface = Color.White,
    background = Color.Transparent,
    onBackground = Color.White,
    error = Color(0xFFEF5350)
)

private val OverlayPaidPlanScheme = darkColorScheme(
    primary = PaidPlanPrimary,
    onPrimary = DarkOnGoldPrimary,
    secondary = PaidPlanSecondary,
    tertiary = PaidPlanPrimaryDark,
    surface = Color.Transparent,
    onSurface = Color.White,
    background = Color.Transparent,
    onBackground = Color.White,
    error = Color(0xFFEF5350)
)

@Composable
fun OverlayTheme(
    isPaidPlan: Boolean = false,
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = if (isPaidPlan) OverlayPaidPlanScheme else OverlayPinkScheme,
        content = content
    )
}
