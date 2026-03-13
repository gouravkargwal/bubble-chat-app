package com.rizzbot.v2.ui.premium

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

@Composable
fun SubscriptionSkeleton() {
    val baseColor = Color(0xFF1A1A2E)
    val highlightColor = Color(0xFF2A2A40)

    val transition = rememberInfiniteTransition(label = "skeleton")
    val progress = transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "skeletonProgress"
    )

    val shimmerBrush = Brush.linearGradient(
        colors = listOf(
            baseColor,
            highlightColor,
            baseColor
        ),
        start = androidx.compose.ui.geometry.Offset(0f, 0f),
        end = androidx.compose.ui.geometry.Offset(400f * progress.value, 400f * progress.value)
    )

    Column(
        modifier = Modifier.fillMaxWidth()
    ) {
        // Fake plan card
        Card(
            colors = CardDefaults.cardColors(containerColor = baseColor),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier
                .fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Box(
                    modifier = Modifier
                        .height(20.dp)
                        .fillMaxWidth(0.4f)
                        .clip(RoundedCornerShape(8.dp))
                        .background(shimmerBrush)
                )
                Spacer(modifier = Modifier.height(12.dp))
                Box(
                    modifier = Modifier
                        .height(32.dp)
                        .fillMaxWidth(0.6f)
                        .clip(RoundedCornerShape(8.dp))
                        .background(shimmerBrush)
                )
                Spacer(modifier = Modifier.height(16.dp))
                repeat(3) {
                    Box(
                        modifier = Modifier
                            .height(14.dp)
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(6.dp))
                            .background(shimmerBrush)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                }
                Spacer(modifier = Modifier.height(12.dp))
                Box(
                    modifier = Modifier
                        .height(44.dp)
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(shimmerBrush)
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Second placeholder card
        Card(
            colors = CardDefaults.cardColors(containerColor = baseColor),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier
                .fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Box(
                    modifier = Modifier
                        .height(18.dp)
                        .fillMaxWidth(0.3f)
                        .clip(RoundedCornerShape(8.dp))
                        .background(shimmerBrush)
                )
                Spacer(modifier = Modifier.height(10.dp))
                repeat(2) {
                    Box(
                        modifier = Modifier
                            .height(14.dp)
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(6.dp))
                            .background(shimmerBrush)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
        }
    }
}

