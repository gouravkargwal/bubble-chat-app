package com.rizzbot.v2.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val DarkColorScheme = darkColorScheme(
    primary = Pink,
    onPrimary = TextWhite,
    secondary = Purple,
    surface = CardBg,
    onSurface = TextWhite,
    background = DarkBg,
    onBackground = TextWhite,
    error = ErrorRed,
    onError = TextWhite
)

@Composable
fun RizzBotV2Theme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        content = content
    )
}
