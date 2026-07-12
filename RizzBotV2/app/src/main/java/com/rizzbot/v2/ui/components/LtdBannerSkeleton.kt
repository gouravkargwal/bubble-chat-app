package com.rizzbot.v2.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface

/**
 * Pixel-perfect skeleton placeholder for the LTD banner card on Settings.
 *
 * Uses the exact same Card wrapper (dimensions, padding, border) as [LtdBannerCard]
 * so there is ZERO layout shift when the real content loads.
 * Contents are replaced with gentle opacity-pulse shimmer blocks.
 */
@Composable
fun LtdBannerSkeleton() {
    val transition = rememberInfiniteTransition(label = "ltdSkel")
    val alpha = transition.animateFloat(
        initialValue = 0.3f,
        targetValue = 0.9f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "ltdSkelAlpha"
    )

    // Exact same Card as LtdBannerCard but with neutral colors
    Card(
        colors = CardDefaults.cardColors(containerColor = NothingSurface),
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(NothingDimens.cardPadding),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Badge area
            ShimmerBlock(alpha.value, Modifier.width(120.dp).height(22.dp), RoundedCornerShape(4.dp))
            Spacer(Modifier.height(12.dp))

            // Title
            ShimmerBlock(alpha.value, Modifier.width(180.dp).height(28.dp), RoundedCornerShape(6.dp))
            Spacer(Modifier.height(4.dp))

            // Price row — big number + small strikethrough
            Row(verticalAlignment = Alignment.Bottom) {
                ShimmerBlock(alpha.value, Modifier.width(80.dp).height(36.dp), RoundedCornerShape(6.dp))
                Spacer(Modifier.width(8.dp))
                ShimmerBlock(alpha.value, Modifier.width(60.dp).height(16.dp), RoundedCornerShape(4.dp))
            }
            Spacer(Modifier.height(4.dp))
            ShimmerBlock(alpha.value, Modifier.width(200.dp).height(14.dp), RoundedCornerShape(4.dp))

            Spacer(Modifier.height(16.dp))

            // Scarcity bar
            ShimmerBlock(alpha.value, Modifier.fillMaxWidth().height(32.dp), RoundedCornerShape(4.dp))

            Spacer(Modifier.height(16.dp))

            // Benefits row (3 columns)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                repeat(3) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        ShimmerBlock(alpha.value, Modifier.width(40.dp).height(22.dp), RoundedCornerShape(4.dp))
                        Spacer(Modifier.height(4.dp))
                        ShimmerBlock(alpha.value, Modifier.width(60.dp).height(14.dp), RoundedCornerShape(4.dp))
                    }
                }
            }

            Spacer(Modifier.height(16.dp))

            // CTA button
            ShimmerBlock(alpha.value, Modifier.fillMaxWidth().height(46.dp), RoundedCornerShape(NothingDimens.pillRadius))

            // Redeem section — only shown on Settings (showRedeem=true)
            Spacer(Modifier.height(12.dp))
            Box(Modifier.fillMaxWidth().height(1.dp).background(Color.White.copy(alpha = alpha.value * 0.08f)))
            Spacer(Modifier.height(12.dp))
            ShimmerBlock(alpha.value, Modifier.width(140.dp).height(14.dp), RoundedCornerShape(4.dp))
            Spacer(Modifier.height(NothingDimens.textGap))
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                ShimmerBlock(alpha.value, Modifier.weight(1f).height(56.dp), RoundedCornerShape(NothingDimens.cardRadius))
                Spacer(Modifier.width(NothingDimens.elementGap))
                ShimmerBlock(alpha.value, Modifier.width(80.dp).height(40.dp), RoundedCornerShape(NothingDimens.pillRadius))
            }
        }
    }
}

/**
 * Reusable shimmer placeholder block with opacity-pulse animation.
 * Light gray rounded rectangle that gently fades in and out.
 */
@Composable
private fun ShimmerBlock(alpha: Float, modifier: Modifier = Modifier, shape: RoundedCornerShape = RoundedCornerShape(6.dp)) {
    Box(
        modifier = modifier
            .clip(shape)
            .background(Color.White.copy(alpha = alpha * 0.12f))
    )
}
