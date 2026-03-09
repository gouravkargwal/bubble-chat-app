package com.rizzbot.v2.overlay.ui

import androidx.compose.animation.core.*
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
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
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
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
            // Scrim behind panels
            if (isFullScreen) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Black.copy(alpha = 0.3f))
                        .clickable(
                            interactionSource = remember { MutableInteractionSource() },
                            indication = null
                        ) { onEvent(OverlayEvent.DismissSuggestions) }
                )
            }

            when (val s = currentState) {
                is BubbleState.Hidden -> {}
                is BubbleState.RizzButton -> RizzButton(
                    onTap = { onEvent(OverlayEvent.ShowBubble) },
                    onDrag = { dx, dy -> onEvent(OverlayEvent.BubbleDragged(dx.toInt(), dy.toInt())) },
                )
                is BubbleState.DirectionPicker -> DirectionPicker(
                    allowedDirections = usage.allowedDirections,
                    customHintsEnabled = usage.customHintsEnabled,
                    onDirectionSelected = { direction ->
                        onEvent(OverlayEvent.CaptureRequested(direction))
                    },
                    onUpgrade = { onEvent(OverlayEvent.UpgradeTapped) },
                    onDismiss = { onEvent(OverlayEvent.DismissSuggestions) },
                    modifier = Modifier.align(Alignment.BottomCenter)
                )
                is BubbleState.Capturing -> {}
                is BubbleState.ScreenshotPreview -> ScreenshotPreviewPanel(
                    bitmaps = s.bitmaps,
                    maxScreenshots = usage.maxScreenshots,
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
                    onCopy = { reply, index -> onEvent(OverlayEvent.CopyReply(reply, index, s.result.interactionId)) },
                    onRate = { index, positive, text -> onEvent(OverlayEvent.RateReply(index, positive, text, s.result.interactionId)) },
                    onRegenerate = { onEvent(OverlayEvent.Regenerate(DirectionWithHint())) },
                    onDismiss = { onEvent(OverlayEvent.DismissSuggestions) },
                    modifier = Modifier.align(Alignment.BottomCenter)
                )
                is BubbleState.Error -> ErrorPanel(
                    message = s.message,
                    errorType = s.errorType,
                    onRetry = {
                        val dir = s.direction ?: DirectionWithHint()
                        onEvent(OverlayEvent.Regenerate(dir))
                    },
                    onUpgrade = { onEvent(OverlayEvent.UpgradeTapped) },
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
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
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
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
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
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val screenHeight = LocalConfiguration.current.screenHeightDp.dp

    Card(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(max = screenHeight * 0.75f)
            .padding(16.dp)
            .border(1.dp, PanelBorderColor, PanelShape),
        shape = PanelShape,
        colors = CardDefaults.cardColors(containerColor = PanelColor),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
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
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
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

    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp)
            .border(1.dp, PanelBorderColor, PanelShape),
        shape = PanelShape,
        colors = CardDefaults.cardColors(containerColor = PanelColor),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(if (isQuotaExceeded) "\uD83D\uDCA8" else "\uD83D\uDE15", fontSize = 32.sp)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                if (isQuotaExceeded) "Daily free limit reached" else message,
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
