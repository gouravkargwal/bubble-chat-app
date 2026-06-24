package com.rizzbot.v2.overlay.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingWhite

private val OverlayColorScheme = darkColorScheme(
    primary = NothingWhite,
    onPrimary = NothingBlack,
    secondary = NothingWhite,
    tertiary = Color(0xFFCCCCCC),
    surface = NothingBlack,
    onSurface = NothingWhite,
    background = Color.Transparent,
    onBackground = NothingWhite,
    error = Color(0xFFFF3355)
)

@Composable
fun OverlayTheme(
    isPaidPlan: Boolean = false,
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = OverlayColorScheme,
        content = content
    )
}
