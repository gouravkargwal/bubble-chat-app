package com.rizzbot.v2.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/**
 * Nothing OS-inspired type scale.
 *
 * - **Titles:** Bold, condensed geometric sans-serif (system default, heavy weight).
 * - **Labels / metadata:** Monospaced for a tactical, engineering feel.
 * - **Body:** Clean, light sans-serif for readability.
 */
val NothingTypography: Typography
    get() {
        val base = Typography()
        return base.copy(
            // ── Display / Hero (rarely used) ──
            displayLarge = base.displayLarge.copy(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.ExtraBold,
                letterSpacing = (-1).sp,
                lineHeight = 64.sp,
            ),
            displayMedium = base.displayMedium.copy(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.ExtraBold,
                letterSpacing = (-0.75).sp,
            ),
            displaySmall = base.displaySmall.copy(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.Bold,
            ),

            // ── Headlines ──
            headlineLarge = base.headlineLarge.copy(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.Bold,
            ),
            headlineMedium = base.headlineMedium.copy(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.Bold,
            ),
            headlineSmall = base.headlineSmall.copy(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.Bold,
            ),

            // ── Titles ──
            titleLarge = base.titleLarge.copy(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.Bold,
                letterSpacing = 0.5.sp,
            ),
            titleMedium = base.titleMedium.copy(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.Bold,
            ),
            titleSmall = base.titleSmall.copy(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.SemiBold,
            ),

            // ── Body ──
            bodyLarge = base.bodyLarge.copy(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.Normal,
                lineHeight = 22.sp,
                letterSpacing = 0.15.sp,
            ),
            bodyMedium = base.bodyMedium.copy(
                fontFamily = FontFamily.SansSerif,
                lineHeight = 20.sp,
            ),
            bodySmall = base.bodySmall.copy(
                fontFamily = FontFamily.SansSerif,
                lineHeight = 16.sp,
            ),

            // ── Labels (monospaced for tactical/engineering feel) ──
            labelLarge = base.labelLarge.copy(
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Medium,
                letterSpacing = 0.8.sp,
            ),
            labelMedium = base.labelMedium.copy(
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Medium,
                letterSpacing = 0.6.sp,
            ),
            labelSmall = base.labelSmall.copy(
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Medium,
                letterSpacing = 0.5.sp,
            ),
        )
    }
