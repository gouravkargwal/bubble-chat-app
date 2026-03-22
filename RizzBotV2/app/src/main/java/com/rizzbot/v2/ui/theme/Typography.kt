package com.rizzbot.v2.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/**
 * Tuned Material 3 type scale for a darker, slightly editorial in-app feel
 * without bundling custom font files.
 */
val CookdTypography: Typography
    get() {
        val base = Typography()
        return base.copy(
            displayLarge = base.displayLarge.copy(
                fontWeight = FontWeight.Bold,
                letterSpacing = (-0.5).sp,
                lineHeight = 64.sp,
            ),
            displayMedium = base.displayMedium.copy(
                fontWeight = FontWeight.Bold,
                letterSpacing = (-0.25).sp,
            ),
            displaySmall = base.displaySmall.copy(fontWeight = FontWeight.Bold),
            headlineLarge = base.headlineLarge.copy(fontWeight = FontWeight.Bold),
            headlineMedium = base.headlineMedium.copy(fontWeight = FontWeight.SemiBold),
            headlineSmall = base.headlineSmall.copy(fontWeight = FontWeight.SemiBold),
            titleLarge = base.titleLarge.copy(
                fontWeight = FontWeight.Bold,
                letterSpacing = 0.15.sp,
            ),
            titleMedium = base.titleMedium.copy(fontWeight = FontWeight.SemiBold),
            titleSmall = base.titleSmall.copy(fontWeight = FontWeight.Medium),
            bodyLarge = base.bodyLarge.copy(
                lineHeight = 24.sp,
                letterSpacing = 0.2.sp,
            ),
            bodyMedium = base.bodyMedium.copy(lineHeight = 20.sp),
            bodySmall = base.bodySmall.copy(lineHeight = 16.sp),
            labelLarge = base.labelLarge.copy(fontWeight = FontWeight.SemiBold),
            labelMedium = base.labelMedium.copy(fontWeight = FontWeight.Medium),
            labelSmall = base.labelSmall.copy(
                fontWeight = FontWeight.Medium,
                letterSpacing = 0.6.sp,
            ),
        )
    }
