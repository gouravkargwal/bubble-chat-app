package com.rizzbot.v2.overlay.ui

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.*
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.domain.model.ConversationDirection
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.overlay.OverlayEvent
import com.rizzbot.v2.overlay.manager.BubbleState
import kotlinx.coroutines.flow.StateFlow

@Composable
fun BubbleOverlay(
    state: StateFlow<BubbleState>,
    onEvent: (OverlayEvent) -> Unit
) {
    val currentState by state.collectAsState()

    val isFullScreen = currentState is BubbleState.DirectionPicker ||
        currentState is BubbleState.ScreenshotPreview ||
        currentState is BubbleState.Loading ||
        currentState is BubbleState.Expanded ||
        currentState is BubbleState.Error

    OverlayTheme {
        Box(modifier = if (isFullScreen) Modifier.fillMaxSize() else Modifier) {
            when (val s = currentState) {
                is BubbleState.Hidden -> {}
                is BubbleState.RizzButton -> RizzButton(
                    onTap = { onEvent(OverlayEvent.ShowBubble) },
                    onDrag = { dx, dy -> onEvent(OverlayEvent.BubbleDragged(dx.toInt(), dy.toInt())) },
                )
                is BubbleState.DirectionPicker -> DirectionPicker(
                    onDirectionSelected = { direction ->
                        onEvent(OverlayEvent.CaptureRequested(direction))
                    },
                    onDismiss = { onEvent(OverlayEvent.DismissSuggestions) },
                    modifier = Modifier.align(Alignment.BottomCenter)
                )
                is BubbleState.Capturing -> {}
                is BubbleState.ScreenshotPreview -> ScreenshotPreviewPanel(
                    bitmaps = s.bitmaps,
                    onConfirm = { onEvent(OverlayEvent.ConfirmScreenshot(s.direction)) },
                    onAddMore = { onEvent(OverlayEvent.AddMoreScreenshots(s.direction)) },
                    onRetake = { onEvent(OverlayEvent.CaptureRequested(s.direction)) },
                    onDismiss = { onEvent(OverlayEvent.DismissSuggestions) },
                    modifier = Modifier.align(Alignment.BottomCenter)
                )
                is BubbleState.Loading -> LoadingOverlay(
                    modifier = Modifier.align(Alignment.BottomCenter)
                )
                is BubbleState.Expanded -> SuggestionPanel(
                    result = s.result,
                    onCopy = { reply, index -> onEvent(OverlayEvent.CopyReply(reply, index)) },
                    onRate = { index, positive, text -> onEvent(OverlayEvent.RateReply(index, positive, text)) },
                    onRegenerate = { onEvent(OverlayEvent.Regenerate(DirectionWithHint())) },
                    onDismiss = { onEvent(OverlayEvent.DismissSuggestions) },
                    modifier = Modifier.align(Alignment.BottomCenter)
                )
                is BubbleState.Error -> ErrorPanel(
                    message = s.message,
                    onRetry = { onEvent(OverlayEvent.CaptureRequested(DirectionWithHint())) },
                    onDismiss = { onEvent(OverlayEvent.DismissSuggestions) },
                    modifier = Modifier.align(Alignment.BottomCenter)
                )
            }
        }
    }
}

@Composable
private fun RizzButton(
    onTap: () -> Unit,
    onDrag: (Float, Float) -> Unit,
    modifier: Modifier = Modifier
) {
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val scale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 1.08f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = EaseInOutCubic),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse_scale"
    )

    var totalDragDistance by remember { mutableFloatStateOf(0f) }

    Box(
        modifier = modifier
            .scale(scale)
            .size(56.dp)
            .clip(CircleShape)
            .background(Color(0xFFE91E63))
            .pointerInput(Unit) {
                detectTapGestures { onTap() }
            }
            .pointerInput(Unit) {
                detectDragGestures(
                    onDragStart = { totalDragDistance = 0f },
                    onDrag = { change, dragAmount ->
                        change.consume()
                        totalDragDistance += kotlin.math.abs(dragAmount.x) + kotlin.math.abs(dragAmount.y)
                        onDrag(dragAmount.x, dragAmount.y)
                    }
                )
            },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = "\uD83D\uDD25",
            fontSize = 24.sp,
            textAlign = TextAlign.Center
        )
    }
}

@Composable
private fun DirectionPicker(
    onDirectionSelected: (DirectionWithHint) -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    var customHint by remember { mutableStateOf("") }
    var showCustomInput by remember { mutableStateOf(false) }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Pick a direction", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                IconButton(onClick = onDismiss) {
                    Icon(Icons.Default.Close, "Close", tint = Color.White)
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Direction chips in a flow layout
            ConversationDirection.entries.forEach { direction ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .clickable {
                            onDirectionSelected(DirectionWithHint(direction))
                        }
                        .padding(vertical = 8.dp, horizontal = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(direction.emoji, fontSize = 20.sp)
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(direction.displayName, color = Color.White, fontSize = 14.sp)
                }
            }

            // Custom hint option
            if (!showCustomInput) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .clickable { showCustomInput = true }
                        .padding(vertical = 8.dp, horizontal = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("\u270D\uFE0F", fontSize = 20.sp)
                    Spacer(modifier = Modifier.width(12.dp))
                    Text("Custom hint", color = Color.White, fontSize = 14.sp)
                }
            } else {
                OutlinedTextField(
                    value = customHint,
                    onValueChange = { customHint = it },
                    placeholder = { Text("e.g., mention that I also love hiking", color = Color.Gray) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                        focusedBorderColor = Color(0xFFE91E63),
                        unfocusedBorderColor = Color.Gray
                    ),
                    singleLine = true
                )
                Spacer(modifier = Modifier.height(8.dp))
                Button(
                    onClick = {
                        onDirectionSelected(DirectionWithHint(customHint = customHint))
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Generate")
                }
            }
        }
    }
}

@Composable
private fun LoadingOverlay(modifier: Modifier = Modifier) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E))
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            CircularProgressIndicator(color = Color(0xFFE91E63))
            Spacer(modifier = Modifier.height(16.dp))
            Text("Analyzing screenshot...", color = Color.White)
        }
    }
}

@Composable
private fun ScreenshotPreviewPanel(
    bitmaps: List<android.graphics.Bitmap>,
    onConfirm: () -> Unit,
    onAddMore: () -> Unit,
    onRetake: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val screenHeight = LocalConfiguration.current.screenHeightDp.dp

    Card(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(max = screenHeight * 0.75f)
            .padding(16.dp),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    "${bitmaps.size} screenshot${if (bitmaps.size > 1) "s" else ""} captured",
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp
                )
                IconButton(onClick = onDismiss) {
                    Icon(Icons.Default.Close, "Close", tint = Color.White)
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Screenshot preview - show latest
            Image(
                bitmap = bitmaps.last().asImageBitmap(),
                contentDescription = "Captured screenshot",
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = screenHeight * 0.35f)
                    .clip(RoundedCornerShape(12.dp)),
                contentScale = ContentScale.Fit
            )

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                if (bitmaps.size == 1) "add more screenshots for better context"
                else "${bitmaps.size} screenshots ready",
                color = Color.Gray,
                fontSize = 13.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Action buttons
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedButton(
                    onClick = onRetake,
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("Retake", color = Color.White)
                }
                if (bitmaps.size < 5) {
                    OutlinedButton(
                        onClick = onAddMore,
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text("+ Add more", color = Color(0xFFE91E63))
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Button(
                onClick = onConfirm,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63)),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("Generate replies")
            }
        }
    }
}

@Composable
private fun SuggestionPanel(
    result: SuggestionResult.Success,
    onCopy: (String, Int) -> Unit,
    onRate: (Int, Boolean, String) -> Unit,
    onRegenerate: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val vibeLabels = listOf("\uD83D\uDD25 Flirty", "\uD83D\uDE0F Witty", "\u2728 Smooth", "\uD83D\uDCAA Bold")
    val screenHeight = LocalConfiguration.current.screenHeightDp.dp

    Card(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(max = screenHeight * 0.7f)
            .padding(16.dp),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E))
    ) {
        Column(
            modifier = Modifier
                .padding(16.dp)
                .verticalScroll(rememberScrollState())
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Suggestions", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                Row {
                    IconButton(onClick = onRegenerate) {
                        Icon(Icons.Default.Refresh, "Regenerate", tint = Color(0xFFE91E63))
                    }
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, "Close", tint = Color.White)
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            result.replies.forEachIndexed { index, reply ->
                SuggestionCard(
                    label = vibeLabels.getOrElse(index) { "\uD83D\uDCAC Reply" },
                    reply = reply,
                    onCopy = { onCopy(reply, index) },
                    onThumbsUp = { onRate(index, true, reply) },
                    onThumbsDown = { onRate(index, false, reply) }
                )
                if (index < result.replies.lastIndex) {
                    Spacer(modifier = Modifier.height(8.dp))
                }
            }
        }
    }
}

@Composable
private fun ErrorPanel(
    message: String,
    onRetry: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E))
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("\uD83D\uDE15", fontSize = 32.sp)
            Spacer(modifier = Modifier.height(8.dp))
            Text(message, color = Color.White, textAlign = TextAlign.Center)
            Spacer(modifier = Modifier.height(16.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onDismiss) {
                    Text("Dismiss")
                }
                Button(
                    onClick = onRetry,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63))
                ) {
                    Text("Retry")
                }
            }
        }
    }
}
