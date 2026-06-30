package com.rizzbot.v2.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.compositionLocalOf

val LocalAppIsPaidPlan = compositionLocalOf { false }

private val NothingColorScheme = darkColorScheme(
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
fun RizzBotV2Theme(
    isPaidPlan: Boolean = false,
    content: @Composable () -> Unit
) {
    CompositionLocalProvider(LocalAppIsPaidPlan provides isPaidPlan) {
        MaterialTheme(
            colorScheme = NothingColorScheme,
            typography = NothingTypography,
            content = content
        )
    }
}
