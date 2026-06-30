package com.rizzbot.v2.ui.theme

import androidx.compose.ui.unit.dp

/**
 * Shared spacing and shape tokens for the Nothing OS / Teenage Engineering-inspired UI.
 *
 * - No rounded corners above 12dp (sharp, hard lines).
 * - 1dp borders replace all shadows.
 * - Pill buttons use 999.dp corner radius.
 * - Tight, precise spacing.
 */
object NothingDimens {
    /** Standard screen horizontal padding. */
    val screenPadding = 24.dp
    /** Spacing between major sections. */
    val sectionSpacing = 28.dp
    /** Standard padding inside cards. */
    val cardPadding = 16.dp
    /** Default card corner radius — crisp but slightly softened. */
    val cardRadius = 12.dp
    /** Pill shape radius for buttons. */
    val pillRadius = 999.dp
    /** Minimum touch target. */
    val minTouchTarget = 48.dp
    /** Spacing between stacked text lines. */
    val textGap = 4.dp
    /** Gap between elements in a row. */
    val elementGap = 12.dp
    /** Default border thickness. */
    val borderThickness = 1.dp
}
