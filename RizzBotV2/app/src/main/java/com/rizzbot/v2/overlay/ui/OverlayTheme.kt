package com.rizzbot.v2.overlay.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import com.rizzbot.v2.ui.theme.GodModePrimary
import com.rizzbot.v2.ui.theme.GodModePrimaryDark
import com.rizzbot.v2.ui.theme.GodModeSecondary
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

private val OverlayGodModeScheme = darkColorScheme(
    primary = GodModePrimary,
    onPrimary = DarkOnGoldPrimary,
    secondary = GodModeSecondary,
    tertiary = GodModePrimaryDark,
    surface = Color.Transparent,
    onSurface = Color.White,
    background = Color.Transparent,
    onBackground = Color.White,
    error = Color(0xFFEF5350)
)

@Composable
fun OverlayTheme(
    isGodMode: Boolean = false,
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = if (isGodMode) OverlayGodModeScheme else OverlayPinkScheme,
        content = content
    )
}
