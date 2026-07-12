package com.rizzbot.v2.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
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
 * Reusable shimmer block — a rounded rectangle that pulses in opacity.
 */
@Composable
private fun ShimmerBlock(alpha: Float, modifier: Modifier = Modifier, shape: RoundedCornerShape = RoundedCornerShape(6.dp)) {
    Box(
        modifier = modifier
            .clip(shape)
            .background(Color.White.copy(alpha = alpha * 0.12f))
    )
}

/**
 * Pixel-perfect skeleton for the Settings account + plan card section.
 *
 * Matches the real layout exactly — same Card wrappers, same padding, same nested structure.
 * Zero layout shift when real content replaces this skeleton.
 */
@Composable
fun PlanCardSkeleton() {
    val transition = rememberInfiniteTransition(label = "planSkel")
    val alpha = transition.animateFloat(
        initialValue = 0.3f,
        targetValue = 0.9f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "planSkelAlpha"
    )

    Column(Modifier.fillMaxWidth()) {
        // "ACCOUNT" section header
        ShimmerBlock(alpha.value, Modifier.width(80.dp).height(14.dp))
        Spacer(Modifier.height(NothingDimens.elementGap))

        // Outer account card — exact same as real
        Card(
            colors = CardDefaults.cardColors(containerColor = NothingSurface),
            shape = RoundedCornerShape(NothingDimens.cardRadius),
            border = BorderStroke(NothingDimens.borderThickness, NothingBorder),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(Modifier.padding(NothingDimens.cardPadding)) {
                // User avatar row
                Row(verticalAlignment = Alignment.CenterVertically) {
                    ShimmerBlock(alpha.value, Modifier.size(36.dp), RoundedCornerShape(18.dp))
                    Spacer(Modifier.width(NothingDimens.elementGap))
                    Column(Modifier.weight(1f)) {
                        ShimmerBlock(alpha.value, Modifier.width(120.dp).height(16.dp))
                        Spacer(Modifier.height(4.dp))
                        ShimmerBlock(alpha.value, Modifier.width(160.dp).height(12.dp))
                    }
                }

                Spacer(Modifier.height(NothingDimens.elementGap))
                ShimmerBlock(alpha.value, Modifier.fillMaxWidth().height(1.dp), RoundedCornerShape(0.dp))
                Spacer(Modifier.height(NothingDimens.elementGap))

                // Nested CompactPlanCard skeleton
                Card(
                    colors = CardDefaults.cardColors(containerColor = NothingSurface),
                    shape = RoundedCornerShape(NothingDimens.cardRadius),
                    border = BorderStroke(NothingDimens.borderThickness, NothingBorder),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(Modifier.padding(NothingDimens.cardPadding)) {
                        // Plan row: icon + name + credits
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            ShimmerBlock(alpha.value, Modifier.size(24.dp))
                            Spacer(Modifier.width(NothingDimens.elementGap))
                            ShimmerBlock(alpha.value, Modifier.weight(1f).height(18.dp))
                            Spacer(Modifier.width(NothingDimens.elementGap))
                            ShimmerBlock(alpha.value, Modifier.width(40.dp).height(22.dp))
                        }

                        Spacer(Modifier.height(6.dp))
                        ShimmerBlock(alpha.value, Modifier.width(140.dp).height(12.dp))

                        Spacer(Modifier.height(8.dp))
                        ShimmerBlock(alpha.value, Modifier.fillMaxWidth().height(4.dp), RoundedCornerShape(2.dp))
                        Spacer(Modifier.height(4.dp))
                        ShimmerBlock(alpha.value, Modifier.width(180.dp).height(12.dp))

                        Spacer(Modifier.height(NothingDimens.elementGap))
                        ShimmerBlock(alpha.value, Modifier.fillMaxWidth().height(46.dp), RoundedCornerShape(NothingDimens.pillRadius))
                    }
                }
            }
        }
    }
}
