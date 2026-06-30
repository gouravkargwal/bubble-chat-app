package com.rizzbot.v2.overlay.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingError
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTypography
import com.rizzbot.v2.ui.theme.NothingWhite

private val OverlayColorScheme = darkColorScheme(
    primary = NothingWhite,
    onPrimary = NothingBlack,
    secondary = NothingWhite,
    tertiary = NothingTextSecondary,
    surface = NothingSurface,
    onSurface = NothingWhite,
    surfaceVariant = NothingSurface,
    onSurfaceVariant = NothingTextSecondary,
    background = NothingBlack,
    onBackground = NothingWhite,
    error = NothingError,
    onError = NothingWhite,
    outline = NothingBorder,
    outlineVariant = NothingBorder.copy(alpha = 0.5f),
)

@Composable
fun OverlayTheme(
    isPaidPlan: Boolean = false,
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = OverlayColorScheme,
        typography = NothingTypography,
        content = content
    )
}
