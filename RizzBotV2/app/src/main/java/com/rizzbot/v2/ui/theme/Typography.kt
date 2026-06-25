package com.rizzbot.v2.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.R

/**
 * Minimalist type scale using Plus Jakarta Sans — a clean, modern, minimalist
 * sans-serif font that matches the Nothing OS design language.
 *
 * Source: Google Fonts (SIL Open Font License)
 * https://fonts.google.com/specimen/Plus+Jakarta+Sans
 */

private val JakartaFontFamily = FontFamily(
    Font(R.font.plus_jakarta_regular, FontWeight.Normal),
    Font(R.font.plus_jakarta_bold, FontWeight.Bold),
)

val NothingTypography: Typography
    get() {
        val base = Typography()
        return base.copy(
            // ── Display / Hero ──
            displayLarge = base.displayLarge.copy(
                fontFamily = JakartaFontFamily,
                fontWeight = FontWeight.ExtraBold,
                letterSpacing = (-1).sp,
                lineHeight = 64.sp,
            ),
            displayMedium = base.displayMedium.copy(
                fontFamily = JakartaFontFamily,
                fontWeight = FontWeight.ExtraBold,
                letterSpacing = (-0.75).sp,
            ),
            displaySmall = base.displaySmall.copy(
                fontFamily = JakartaFontFamily,
                fontWeight = FontWeight.Bold,
            ),

            // ── Headlines ──
            headlineLarge = base.headlineLarge.copy(
                fontFamily = JakartaFontFamily,
                fontWeight = FontWeight.Bold,
            ),
            headlineMedium = base.headlineMedium.copy(
                fontFamily = JakartaFontFamily,
                fontWeight = FontWeight.Bold,
            ),
            headlineSmall = base.headlineSmall.copy(
                fontFamily = JakartaFontFamily,
                fontWeight = FontWeight.Bold,
            ),

            // ── Titles ──
            titleLarge = base.titleLarge.copy(
                fontFamily = JakartaFontFamily,
                fontWeight = FontWeight.Bold,
                letterSpacing = 0.5.sp,
            ),
            titleMedium = base.titleMedium.copy(
                fontFamily = JakartaFontFamily,
                fontWeight = FontWeight.Bold,
            ),
            titleSmall = base.titleSmall.copy(
                fontFamily = JakartaFontFamily,
                fontWeight = FontWeight.SemiBold,
            ),

            // ── Body ──
            bodyLarge = base.bodyLarge.copy(
                fontFamily = JakartaFontFamily,
                fontWeight = FontWeight.Normal,
                lineHeight = 22.sp,
                letterSpacing = 0.15.sp,
            ),
            bodyMedium = base.bodyMedium.copy(
                fontFamily = JakartaFontFamily,
                lineHeight = 20.sp,
            ),
            bodySmall = base.bodySmall.copy(
                fontFamily = JakartaFontFamily,
                lineHeight = 16.sp,
            ),

            // ── Labels ──
            labelLarge = base.labelLarge.copy(
                fontFamily = JakartaFontFamily,
                fontWeight = FontWeight.Medium,
                letterSpacing = 0.8.sp,
            ),
            labelMedium = base.labelMedium.copy(
                fontFamily = JakartaFontFamily,
                fontWeight = FontWeight.Medium,
                letterSpacing = 0.6.sp,
            ),
            labelSmall = base.labelSmall.copy(
                fontFamily = JakartaFontFamily,
                fontWeight = FontWeight.Medium,
                letterSpacing = 0.5.sp,
            ),
        )
    }
