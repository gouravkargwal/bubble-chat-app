package com.rizzbot.v2.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.ui.graphics.Color

val LocalAppIsPaidPlan = compositionLocalOf { false }

private val DarkOnGoldPrimary = Color(0xFF1C1508)

private val DarkColorScheme = darkColorScheme(
    primary = Pink,
    onPrimary = TextWhite,
    secondary = Purple,
    tertiary = PinkDark,
    surface = CardBg,
    onSurface = TextWhite,
    background = DarkBg,
    onBackground = TextWhite,
    error = ErrorRed,
    onError = TextWhite
)

private val PaidPlanColorScheme = darkColorScheme(
    primary = PaidPlanPrimary,
    onPrimary = DarkOnGoldPrimary,
    secondary = PaidPlanSecondary,
    tertiary = PaidPlanPrimaryDark,
    surface = CardBg,
    onSurface = TextWhite,
    background = DarkBg,
    onBackground = TextWhite,
    error = ErrorRed,
    onError = TextWhite
)

@Composable
fun RizzBotV2Theme(
    isPaidPlan: Boolean = false,
    content: @Composable () -> Unit
) {
    CompositionLocalProvider(LocalAppIsPaidPlan provides isPaidPlan) {
        MaterialTheme(
            colorScheme = if (isPaidPlan) PaidPlanColorScheme else DarkColorScheme,
            typography = CookdTypography,
            content = content
        )
    }
}
