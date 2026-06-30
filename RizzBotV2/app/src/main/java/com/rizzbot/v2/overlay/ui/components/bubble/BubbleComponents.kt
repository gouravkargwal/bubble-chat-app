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
import androidx.compose.material3.Surface
import androidx.compose.material3.Text

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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInteropFilter
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.overlay.manager.BubbleState
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingWhite
import com.rizzbot.v2.ui.components.CookdLogo
import kotlinx.coroutines.delay

/**
 * The main floating bubble button.
 * Shows a circular loading indicator around the border when loading.
 * No idle pulsing — Nothing OS is static and precise, not bouncy.
 */
@Composable
fun RizzButton(
    isLoading: Boolean = false,
    modifier: Modifier = Modifier
) {
    // Rotation animation for loading indicator — runs continuously but only visible when loading
    val loadingTransition = rememberInfiniteTransition(label = "loading_rotate")
    val rotation by loadingTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "loading_rotation"
    )

    val bubbleColor = NothingBlack.copy(alpha = 0.75f)
    val borderColor = NothingWhite
    val borderWidth = 2.dp
    val bubbleSize = 56.dp

    Box(
        modifier = modifier.size(bubbleSize),
        contentAlignment = Alignment.Center
    ) {
        // Background circle with white border
        Box(
            modifier = Modifier
                .size(bubbleSize)
                .clip(CircleShape)
                .background(bubbleColor)
                .border(borderWidth, borderColor, CircleShape)
        )

        // ── Dot-matrix ring: Nothing OS signature element ──
        // A circle of evenly-spaced dots around the inner edge of the bubble.
        // Replicates the NDot / Glyph interface aesthetic.
        Canvas(
            modifier = Modifier
                .size(bubbleSize)
                .clip(CircleShape)
        ) {
            val center = Offset(size.width / 2f, size.height / 2f)
            val dotRadius = 1.2.dp.toPx()
            val ringRadius = size.minDimension / 2f - borderWidth.toPx() - 4.dp.toPx()
            val dotCount = 24

            for (i in 0 until dotCount) {
                val angle = (360.0 / dotCount) * i * kotlin.math.PI / 180.0
                val x = center.x + ringRadius * kotlin.math.cos(angle).toFloat()
                val y = center.y + ringRadius * kotlin.math.sin(angle).toFloat()
                drawCircle(
                    color = NothingWhite.copy(alpha = 0.5f),
                    radius = dotRadius,
                    center = Offset(x, y)
                )
            }
        }

        // Circular loading indicator (drawn on top, clipped to circle)
        if (isLoading) {
            Canvas(
                modifier = Modifier
                    .size(bubbleSize)
                    .clip(CircleShape)
            ) {
                val strokeWidth = 3.dp.toPx()
                val padding = borderWidth.toPx() + 4.dp.toPx()
                val diameter = size.minDimension - (padding * 2)
                
                drawArc(
                    color = NothingWhite,
                    startAngle = rotation,
                    sweepAngle = 160f,
                    useCenter = false,
                    topLeft = Offset(padding, padding),
                    size = Size(diameter, diameter),
                    style = Stroke(
                        width = strokeWidth,
                        cap = StrokeCap.Round
                    )
                )
            }
        }
        
        // "C" logo (hidden during loading)
        if (!isLoading) {
            CookdLogo(
                size = 30.dp,
                backgroundColor = Color.Transparent,
                iconTint = NothingWhite,
            )
        }
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
    asyncWorkInFlight: Boolean,
    onCollapsedOverlayMotionEvent: (MotionEvent) -> Boolean,
    modifier: Modifier = Modifier
) {
    val showAddMoreHint = state is BubbleState.RizzButtonAddMore
    val showLoadingHint = state is BubbleState.Loading ||
        ((state is BubbleState.RizzButton || state is BubbleState.RizzButtonAddMore) && asyncWorkInFlight)
    
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
                Box(modifier = Modifier.width(8.dp))
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
                Box(modifier = Modifier.width(8.dp))
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
        color = NothingSurface,
        contentColor = NothingWhite,
        shape = RoundedCornerShape(12.dp),
        tonalElevation = 0.dp,
        border = BorderStroke(1.dp, NothingBorder),
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
