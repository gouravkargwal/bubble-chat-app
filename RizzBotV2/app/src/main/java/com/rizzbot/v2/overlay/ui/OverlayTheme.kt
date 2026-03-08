package com.rizzbot.v2.overlay.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val OverlayColorScheme = darkColorScheme(
    primary = Color(0xFFE91E63),
    onPrimary = Color.White,
    secondary = Color(0xFF9C27B0),
    surface = Color(0xFF1A1A2E),
    onSurface = Color.White,
    background = Color(0xFF0F0F1A),
    onBackground = Color.White,
    error = Color(0xFFEF5350)
)

@Composable
fun OverlayTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = OverlayColorScheme,
        content = content
    )
}
