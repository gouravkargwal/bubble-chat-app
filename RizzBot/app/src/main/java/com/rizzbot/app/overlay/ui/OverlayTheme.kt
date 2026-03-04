package com.rizzbot.app.overlay.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val OverlayColorScheme = darkColorScheme(
    primary = Color(0xFFFF6B6B),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFFF8E8E),
    surface = Color(0xFF1E1E2E),
    onSurface = Color.White,
    surfaceVariant = Color(0xFF2A2A3E),
    onSurfaceVariant = Color(0xFFB0B0C0)
)

@Composable
fun OverlayTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = OverlayColorScheme,
        content = content
    )
}
