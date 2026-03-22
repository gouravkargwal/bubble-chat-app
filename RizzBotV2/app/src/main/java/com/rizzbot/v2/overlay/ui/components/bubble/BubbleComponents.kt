package com.rizzbot.v2.overlay.ui.components.bubble

import android.view.MotionEvent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.wrapContentSize
import androidx.compose.foundation.layout.wrapContentWidth
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Whatshot
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInteropFilter
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.overlay.manager.BubbleState
import com.rizzbot.v2.overlay.ui.theme.overlayBubbleGradient
import kotlinx.coroutines.delay

/**
 * The main floating bubble button with pulsing animation
 * Shows a circular loading indicator around the border when loading
 */
@Composable
fun RizzButton(
    isLoading: Boolean = false,
    modifier: Modifier = Modifier
) {
    val accent = MaterialTheme.colorScheme.primary
    val bubbleGradient = overlayBubbleGradient()
    val pulse = rememberInfiniteTransition(label = "rizz_pulse")
    
    // Normal gentle pulse
    val scale by pulse.animateFloat(
        initialValue = 1f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1400),
            repeatMode = RepeatMode.Reverse
        ),
        label = "rizz_pulse_scale"
    )
    
    // Rotation animation for loading indicator
    val rotation by pulse.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "loading_rotation"
    )

    Box(
        modifier = modifier
            .size(56.dp)
            .shadow(
                elevation = 8.dp,
                shape = CircleShape,
                spotColor = accent
            )
            .scale(scale),
        contentAlignment = Alignment.Center
    ) {
        // Background circle (clipped)
        Box(
            modifier = Modifier
                .size(56.dp)
                .clip(CircleShape)
                .background(
                    if (isLoading) {
                        // Black background when loading to make white indicator visible
                        Brush.radialGradient(
                            colors = listOf(
                                Color(0xFF1A1A1A),
                                Color(0xFF000000)
                            )
                        )
                    } else {
                        // Normal pink gradient when not loading
                        Brush.radialGradient(colors = bubbleGradient)
                    }
                )
                .border(1.dp, Color.White.copy(alpha = 0.15f), CircleShape)
        )
        
        // Circular loading indicator (drawn on top, NOT clipped)
        if (isLoading) {
            Canvas(modifier = Modifier.size(56.dp)) {
                val strokeWidth = 4.dp.toPx()
                // Draw inside the bubble, accounting for stroke width and border
                val padding = strokeWidth / 2 + 2.dp.toPx()
                val diameter = size.minDimension - (padding * 2)
                
                drawArc(
                    color = Color.White,
                    startAngle = rotation,
                    // Use a partial arc so the \"head\" of the loader is clearly visible
                    sweepAngle = 110f,
                    useCenter = false,
                    topLeft = androidx.compose.ui.geometry.Offset(padding, padding),
                    size = androidx.compose.ui.geometry.Size(diameter, diameter),
                    style = Stroke(
                        width = strokeWidth,
                        cap = StrokeCap.Round
                    )
                )
            }
        }
        
        // Rizz icon on top (vector, consistent across devices)
        Icon(
            imageVector = Icons.Filled.Whatshot,
            contentDescription = "Rizz",
            tint = Color.White,
            modifier = Modifier.size(24.dp)
        )
    }
}

/**
 * Bubble with contextual hints that appear based on state
 */
@OptIn(ExperimentalComposeUiApi::class)
@Composable
fun BubbleWithHints(
    state: BubbleState,
    dockOnLeft: Boolean,
    onCollapsedOverlayMotionEvent: (MotionEvent) -> Boolean,
    modifier: Modifier = Modifier
) {
    val showAddMoreHint = state is BubbleState.RizzButtonAddMore
    val showLoadingHint = state is BubbleState.Loading
    
    // Auto-hide the "add more" hint after 4 seconds
    var showAddMoreHintWithTimeout by remember(showAddMoreHint) { 
        mutableStateOf(showAddMoreHint) 
    }
    
    LaunchedEffect(showAddMoreHint) {
        if (showAddMoreHint) {
            showAddMoreHintWithTimeout = true
            delay(4000)
            showAddMoreHintWithTimeout = false
        }
    }

    Box(
        modifier = modifier
            .wrapContentSize()
            .pointerInteropFilter { onCollapsedOverlayMotionEvent(it) }
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (dockOnLeft) {
                RizzButton(isLoading = showLoadingHint)
                Box(modifier = Modifier.width(8.dp)) // Fixed spacer
                // Hint bubble to the right (only show for "add more" hint, not loading)
                Box(modifier = Modifier.wrapContentWidth()) {
                    androidx.compose.animation.AnimatedVisibility(
                        visible = showAddMoreHintWithTimeout,
                        enter = fadeIn(animationSpec = tween(300)) +
                                slideInHorizontally(initialOffsetX = { -it }, animationSpec = tween(300)),
                        exit = fadeOut(animationSpec = tween(300)) +
                               slideOutHorizontally(targetOffsetX = { -it }, animationSpec = tween(300))
                    ) {
                        TalkingBubble(text = "Tap for next screenshot")
                    }
                }
            } else {
                // Hint bubble to the left (only show for "add more" hint, not loading)
                Box(modifier = Modifier.wrapContentWidth()) {
                    androidx.compose.animation.AnimatedVisibility(
                        visible = showAddMoreHintWithTimeout,
                        enter = fadeIn(animationSpec = tween(300)) +
                                slideInHorizontally(initialOffsetX = { it }, animationSpec = tween(300)),
                        exit = fadeOut(animationSpec = tween(300)) +
                               slideOutHorizontally(targetOffsetX = { it }, animationSpec = tween(300))
                    ) {
                        TalkingBubble(text = "Tap for next screenshot")
                    }
                }
                Box(modifier = Modifier.width(8.dp)) // Fixed spacer
                RizzButton(isLoading = showLoadingHint)
            }
        }
    }
}

/**
 * A speech bubble that displays hint text (no tail)
 */
@Composable
fun TalkingBubble(
    text: String,
    modifier: Modifier = Modifier
) {
    Surface(
        color = Color(0xFF111111),
        contentColor = Color.White,
        shape = RoundedCornerShape(16.dp),
        tonalElevation = 0.dp,
        shadowElevation = 6.dp,
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.12f)),
        modifier = modifier
    ) {
        Text(
            text = text,
            fontSize = 13.sp,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp)
        )
    }
}

/**
 * An animated loading speech bubble with pulsing dots
 */
@Composable
fun LoadingSpeechBubble() {
    var dotCount by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(500)
            dotCount = (dotCount + 1) % 4
        }
    }
    val dots = ".".repeat(dotCount)
    TalkingBubble(text = "Cooking up replies$dots")
}
