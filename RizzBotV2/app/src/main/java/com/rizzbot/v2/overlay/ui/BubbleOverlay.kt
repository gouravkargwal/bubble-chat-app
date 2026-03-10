package com.rizzbot.v2.overlay.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import com.rizzbot.v2.domain.model.ConversationDirection
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.model.UsageState
import com.rizzbot.v2.overlay.OverlayEvent
import com.rizzbot.v2.overlay.manager.BubbleState
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.StateFlow

private val PanelShape = RoundedCornerShape(24.dp)
private val PanelColor = Color(0xFF1A1A2E)
private val PanelBorderColor = Color.White.copy(alpha = 0.08f)
private val AccentPink = Color(0xFFE91E63)

@Composable
fun BubbleOverlay(
    state: StateFlow<BubbleState>,
    usageState: StateFlow<UsageState>,
    onEvent: (OverlayEvent) -> Unit
) {
    val currentState by state.collectAsState()
    val usage by usageState.collectAsState()

    val isFullScreen = currentState is BubbleState.DirectionPicker ||
        currentState is BubbleState.ScreenshotPreview ||
        currentState is BubbleState.Loading ||
        currentState is BubbleState.Expanded ||
        currentState is BubbleState.Error

    OverlayTheme {
        Box(
            modifier = if (isFullScreen) Modifier.fillMaxSize()
            else Modifier.background(Color.Transparent)
        ) {
            // 1. Scrim behind panels with smooth fade
            androidx.compose.animation.AnimatedVisibility(
                visible = isFullScreen,
                enter = androidx.compose.animation.fadeIn(
                    animationSpec = androidx.compose.animation.core.tween(250)
                ),
                exit = androidx.compose.animation.fadeOut(
                    animationSpec = androidx.compose.animation.core.tween(200)
                )
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Black.copy(alpha = 0.6f))
                        .clickable(
                            interactionSource = remember { MutableInteractionSource() },
                            indication = null
                        ) { onEvent(OverlayEvent.DismissSuggestions) }
                )
            }

            // 2. Render RizzButton ONLY when not in full screen
            if (currentState is BubbleState.RizzButton) {
                RizzButton(
                    onTap = { onEvent(OverlayEvent.ShowBubble) }
                )
            }

            // 3. The Panels (Animated scale-in popup centered on screen)
            androidx.compose.animation.AnimatedVisibility(
                visible = isFullScreen,
                enter = androidx.compose.animation.scaleIn(
                    initialScale = 0.85f,
                    animationSpec = androidx.compose.animation.core.tween(
                        durationMillis = 250,
                        easing = androidx.compose.animation.core.LinearOutSlowInEasing
                    )
                ) + androidx.compose.animation.fadeIn(
                    animationSpec = androidx.compose.animation.core.tween(250)
                ),
                exit = androidx.compose.animation.scaleOut(
                    targetScale = 0.85f,
                    animationSpec = androidx.compose.animation.core.tween(
                        durationMillis = 200,
                        easing = androidx.compose.animation.core.FastOutLinearInEasing
                    )
                ) + androidx.compose.animation.fadeOut(
                    animationSpec = androidx.compose.animation.core.tween(200)
                ),
                modifier = Modifier.align(Alignment.Center) // Centers the popup!
            ) {
                Box(modifier = Modifier.padding(horizontal = 16.dp)) {
                    when (val s = currentState) {
                        is BubbleState.DirectionPicker -> DirectionPicker(
                            allowedDirections = usage.allowedDirections,
                            customHintsEnabled = usage.customHintsEnabled,
                            onDirectionSelected = { direction ->
                                onEvent(OverlayEvent.CaptureRequested(direction))
                            },
                            onUpgrade = { onEvent(OverlayEvent.UpgradeTapped) },
                            onDismiss = { onEvent(OverlayEvent.DismissSuggestions) }
                        )
                        is BubbleState.ScreenshotPreview -> ScreenshotPreviewPanel(
                            bitmaps = s.bitmaps,
                            maxScreenshots = usage.maxScreenshots,
                            onConfirm = { onEvent(OverlayEvent.ConfirmScreenshot(s.direction)) },
                            onAddMore = { onEvent(OverlayEvent.AddMoreScreenshots(s.direction)) },
                            onRetake = { onEvent(OverlayEvent.RetakeLastScreenshot(s.direction)) },
                            onRemoveScreenshot = { index ->
                                onEvent(OverlayEvent.RemoveScreenshot(index, s.direction))
                            },
                            onDismiss = { onEvent(OverlayEvent.DismissSuggestions) }
                        )
                        is BubbleState.Loading -> LoadingOverlay()
                        is BubbleState.Expanded -> SuggestionPanel(
                            result = s.result,
                            onCopy = { reply, index ->
                                onEvent(
                                    OverlayEvent.CopyReply(
                                        reply,
                                        index,
                                        s.result.interactionId
                                    )
                                )
                            },
                            onRate = { index, positive, text ->
                                onEvent(
                                    OverlayEvent.RateReply(
                                        index,
                                        positive,
                                        text,
                                        s.result.interactionId
                                    )
                                )
                            },
                            onRegenerate = { onEvent(OverlayEvent.Regenerate(DirectionWithHint())) },
                            onClear = { onEvent(OverlayEvent.ClearAndStartOver) },
                            onDismiss = { onEvent(OverlayEvent.DismissSuggestions) }
                        )
                        is BubbleState.Error -> ErrorPanel(
                            message = s.message,
                            errorType = s.errorType,
                            onRetry = {
                                val dir = s.direction ?: DirectionWithHint()
                                onEvent(OverlayEvent.Regenerate(dir))
                            },
                            onUpgrade = { onEvent(OverlayEvent.UpgradeTapped) },
                            onDismiss = { onEvent(OverlayEvent.DismissSuggestions) }
                        )
                        else -> {}
                    }
                }
            }
        }
    }
}

@Composable
fun CloseTargetUI(isHovering: Boolean) {
    val scale by animateFloatAsState(
        targetValue = if (isHovering) 1.3f else 1.0f,
        label = "close_target_scale"
    )
    val containerColor by animateColorAsState(
        targetValue = if (isHovering) Color(0xFFD32F2F) else Color(0xFF1A1A2E).copy(alpha = 0.8f),
        label = "close_target_color"
    )
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(bottom = 60.dp),
        contentAlignment = Alignment.BottomCenter
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier
                    .size(70.dp)
                    .scale(scale)
                    .clip(CircleShape)
                    .background(containerColor)
                    .border(2.dp, Color.White.copy(alpha = 0.5f), CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Close,
                    contentDescription = "Close",
                    tint = Color.White,
                    modifier = Modifier.size(36.dp)
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Close",
                color = Color.White,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier
                    .background(Color.Black.copy(alpha = 0.4f), RoundedCornerShape(4.dp))
                    .padding(horizontal = 8.dp)
            )
        }
    }
}

@Composable
private fun RizzButton(
    onTap: () -> Unit,
    modifier: Modifier = Modifier
) {
    var totalDragDistance by remember { mutableFloatStateOf(0f) }

    Box(
        modifier = modifier
            .size(56.dp)
            .clip(CircleShape)
            .background(
                Brush.radialGradient(
                    colors = listOf(
                        Color(0xFFFF4081),
                        AccentPink,
                        Color(0xFFC2185B)
                    )
                )
            )
            .border(1.dp, Color.White.copy(alpha = 0.15f), CircleShape)
            .pointerInput(Unit) {
                detectTapGestures { onTap() }
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
    allowedDirections: List<String>,
    customHintsEnabled: Boolean,
    onDirectionSelected: (DirectionWithHint) -> Unit,
    onUpgrade: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    var customHint by remember { mutableStateOf("") }
    var showCustomInput by remember { mutableStateOf(false) }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp)
            .border(1.dp, PanelBorderColor, PanelShape),
        shape = PanelShape,
        colors = CardDefaults.cardColors(containerColor = PanelColor),
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

            ConversationDirection.entries.forEach { direction ->
                val dirKey = direction.name.lowercase()
                val isLocked = allowedDirections.isNotEmpty() && dirKey !in allowedDirections

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 2.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color.White.copy(alpha = if (isLocked) 0.02f else 0.05f))
                        .clickable {
                            if (isLocked) onUpgrade() else onDirectionSelected(DirectionWithHint(direction))
                        }
                        .padding(vertical = 10.dp, horizontal = 12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(direction.emoji, fontSize = 20.sp)
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        direction.displayName,
                        color = if (isLocked) Color.Gray else Color.White,
                        fontSize = 14.sp
                    )
                    if (isLocked) {
                        Spacer(modifier = Modifier.weight(1f))
                        Text("\uD83D\uDD12", fontSize = 14.sp)
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("PRO", color = AccentPink, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }

            // Custom hint option
            if (!showCustomInput) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 2.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color.White.copy(alpha = if (customHintsEnabled) 0.05f else 0.02f))
                        .clickable {
                            if (customHintsEnabled) showCustomInput = true else onUpgrade()
                        }
                        .padding(vertical = 10.dp, horizontal = 12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("\u270D\uFE0F", fontSize = 20.sp)
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        "Custom hint",
                        color = if (customHintsEnabled) Color.White else Color.Gray,
                        fontSize = 14.sp
                    )
                    if (!customHintsEnabled) {
                        Spacer(modifier = Modifier.weight(1f))
                        Text("\uD83D\uDD12", fontSize = 14.sp)
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("PRO", color = AccentPink, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    }
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
                        focusedBorderColor = AccentPink,
                        unfocusedBorderColor = Color.Gray
                    ),
                    singleLine = true
                )
                Spacer(modifier = Modifier.height(8.dp))
                Button(
                    onClick = {
                        onDirectionSelected(DirectionWithHint(customHint = customHint))
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = AccentPink),
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
    var dotCount by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(500)
            dotCount = (dotCount + 1) % 4
        }
    }
    val dots = ".".repeat(dotCount)

    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp)
            .border(1.dp, PanelBorderColor, PanelShape),
        shape = PanelShape,
        colors = CardDefaults.cardColors(containerColor = PanelColor),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            CircularProgressIndicator(color = AccentPink)
            Spacer(modifier = Modifier.height(16.dp))
            Text("Cooking up replies$dots", color = Color.White)
        }
    }
}

@Composable
private fun ScreenshotPreviewPanel(
    bitmaps: List<android.graphics.Bitmap>,
    maxScreenshots: Int,
    onConfirm: () -> Unit,
    onAddMore: () -> Unit,
    onRetake: () -> Unit,
    onRemoveScreenshot: (Int) -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val screenHeight = LocalConfiguration.current.screenHeightDp.dp

    var selectedIndex by remember(bitmaps) {
        mutableIntStateOf(bitmaps.lastIndex.coerceAtLeast(0))
    }
    LaunchedEffect(bitmaps.size) {
        if (bitmaps.isEmpty()) return@LaunchedEffect
        if (selectedIndex !in bitmaps.indices) {
            selectedIndex = bitmaps.lastIndex
        }
    }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(max = screenHeight * 0.75f)
            .padding(16.dp)
            .border(1.dp, PanelBorderColor, PanelShape),
        shape = PanelShape,
        colors = CardDefaults.cardColors(containerColor = PanelColor),
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

            if (bitmaps.isNotEmpty()) {
                // Outer box: not clipped, has border. Inner box: clipped image.
                // Close button is anchored to the outer box so it visually
                // overlaps the top-right corner of the image (half in / half out).
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(max = screenHeight * 0.35f)
                        .border(1.dp, Color.White.copy(alpha = 0.15f), RoundedCornerShape(14.dp))
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(top = 4.dp, end = 4.dp)
                            .clip(RoundedCornerShape(12.dp))
                    ) {
                        Image(
                            bitmap = bitmaps[selectedIndex].asImageBitmap(),
                            contentDescription = "Captured screenshot",
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Crop
                        )
                    }

                    IconButton(
                        onClick = { onRemoveScreenshot(selectedIndex) },
                        modifier = Modifier
                            .align(Alignment.TopEnd)
                            .offset(y = 12.dp) // push down a bit so it sits on the edge
                            .size(28.dp)
                            .background(Color.Black.copy(alpha = 0.85f), CircleShape)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Close,
                            contentDescription = "Remove screenshot",
                            tint = Color.White,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            if (bitmaps.size > 1) {
                LazyRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(72.dp)
                ) {
                    itemsIndexed(bitmaps) { index, bitmap ->
                        Box(
                            modifier = Modifier
                                .width(60.dp)
                                .fillMaxHeight()
                                .clip(RoundedCornerShape(10.dp))
                                .background(
                                    if (index == selectedIndex) {
                                        Color.White.copy(alpha = 0.12f)
                                    } else {
                                        Color.White.copy(alpha = 0.04f)
                                    }
                                )
                                .clickable { selectedIndex = index }
                                .padding(2.dp)
                        ) {
                            Image(
                                bitmap = bitmap.asImageBitmap(),
                                contentDescription = "Screenshot thumbnail",
                                modifier = Modifier
                                    .fillMaxSize()
                                    .clip(RoundedCornerShape(8.dp)),
                                contentScale = ContentScale.Crop
                            )
                        }
                    }
                }
            }

            Text(
                when {
                    bitmaps.size == 1 && maxScreenshots > 1 ->
                        "Tip: Add more screenshots for better context (${bitmaps.size}/$maxScreenshots)"
                    bitmaps.size == 1 ->
                        "1 screenshot captured"
                    else ->
                        "${bitmaps.size}/$maxScreenshots screenshots ready"
                },
                color = Color.Gray,
                fontSize = 13.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(12.dp))

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
                if (bitmaps.size < maxScreenshots) {
                    OutlinedButton(
                        onClick = onAddMore,
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text("+ Add more", color = AccentPink)
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Button(
                onClick = onConfirm,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = AccentPink),
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
    onClear: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val vibeLabels = listOf("\uD83D\uDD25 Flirty", "\uD83D\uDE0F Witty", "\u2728 Smooth", "\uD83D\uDCAA Bold")
    val screenHeight = LocalConfiguration.current.screenHeightDp.dp

    Card(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(max = screenHeight * 0.7f)
            .padding(16.dp)
            .border(1.dp, PanelBorderColor, PanelShape),
        shape = PanelShape,
        colors = CardDefaults.cardColors(containerColor = PanelColor),
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
                        Icon(Icons.Default.Refresh, "Regenerate", tint = AccentPink)
                    }
                    IconButton(onClick = onClear) {
                        Icon(Icons.Default.Delete, "Clear", tint = Color.Gray)
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
    errorType: SuggestionResult.ErrorType,
    onRetry: () -> Unit,
    onUpgrade: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val isQuotaExceeded = errorType == SuggestionResult.ErrorType.QUOTA_EXCEEDED
    val isRateLimited = errorType == SuggestionResult.ErrorType.RATE_LIMITED

    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp)
            .border(1.dp, PanelBorderColor, PanelShape),
        shape = PanelShape,
        colors = CardDefaults.cardColors(containerColor = PanelColor),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(if (isQuotaExceeded) "\uD83D\uDCA8" else "\uD83D\uDE15", fontSize = 32.sp)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                when {
                    isQuotaExceeded -> "Daily free limit reached"
                    isRateLimited -> "We're getting a lot of requests. Please try again in a minute."
                    else -> {
                        // Hide low-level error details (e.g. provider quota, timeouts)
                        // behind a friendly, generic server error message.
                        "Something went wrong on our side. We're looking into it."
                    }
                },
                color = Color.White,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )
            if (isQuotaExceeded) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    "Upgrade to Premium for unlimited replies",
                    color = Color.Gray,
                    fontSize = 13.sp,
                    textAlign = TextAlign.Center
                )
                Spacer(modifier = Modifier.height(16.dp))
                Button(
                    onClick = onUpgrade,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = AccentPink),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("Upgrade Now")
                }
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedButton(
                    onClick = onDismiss,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("Dismiss", color = Color.White)
                }
            } else {
                Spacer(modifier = Modifier.height(16.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = onDismiss) {
                        Text("Dismiss", color = Color.White)
                    }
                    Button(
                        onClick = onRetry,
                        colors = ButtonDefaults.buttonColors(containerColor = AccentPink)
                    ) {
                        Text("Retry")
                    }
                }
            }
        }
    }
}
