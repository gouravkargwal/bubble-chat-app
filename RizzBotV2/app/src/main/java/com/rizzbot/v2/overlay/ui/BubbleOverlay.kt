package com.rizzbot.v2.overlay.ui

import android.os.Build
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.UsageState
import com.rizzbot.v2.overlay.OverlayEvent
import com.rizzbot.v2.overlay.manager.BubbleState
import com.rizzbot.v2.overlay.ui.components.bubble.BubbleWithHints
import com.rizzbot.v2.overlay.ui.components.panels.BubbleHeader
import com.rizzbot.v2.overlay.ui.components.panels.DirectionPicker
import com.rizzbot.v2.overlay.ui.components.panels.ErrorPanel
import com.rizzbot.v2.overlay.ui.components.panels.LoadingOverlay
import com.rizzbot.v2.overlay.ui.components.panels.ProcessingOverlay
import com.rizzbot.v2.overlay.ui.components.panels.ScreenshotPreviewPanel
import com.rizzbot.v2.overlay.ui.components.panels.SuggestionPanel
import com.rizzbot.v2.overlay.ui.theme.OverlayColors
import com.rizzbot.v2.overlay.ui.theme.OverlayShapes
import kotlinx.coroutines.flow.StateFlow

/**
 * Main entry point for the Bubble Overlay UI
 * 
 * This composable manages the entire overlay experience including:
 * - Floating bubble with hints
 * - Full-screen panels for direction picking, screenshot preview, and reply suggestions
 * - Smooth scale and fade transitions
 * - Background scrim with blur effect
 */
@Composable
fun BubbleOverlay(
    state: StateFlow<BubbleState>,
    usageState: StateFlow<UsageState>,
    dockOnLeft: StateFlow<Boolean>,
    isGalleryMode: StateFlow<Boolean>,
    onEvent: (OverlayEvent) -> Unit
) {
    val currentState by state.collectAsState()
    val usage by usageState.collectAsState()
    val dockLeft by dockOnLeft.collectAsState()
    val galleryMode by isGalleryMode.collectAsState()

    val isFullScreen = currentState is BubbleState.DirectionPicker ||
        currentState is BubbleState.ScreenshotPreview ||
        currentState is BubbleState.Expanded ||
        currentState is BubbleState.Error

    OverlayTheme {
        Box(
            modifier = if (isFullScreen) Modifier.fillMaxSize() 
            else Modifier.background(Color.Transparent)
        ) {
            // Background scrim with blur effect
            BackgroundScrim(
                visible = isFullScreen,
                onDismiss = { onEvent(OverlayEvent.DismissSuggestions) }
            )

            // Floating bubble with hints (shown when not in full-screen mode)
            AnimatedVisibility(
                visible = !isFullScreen,
                enter = fadeIn() + scaleIn(initialScale = 0.8f),
                exit = fadeOut() + scaleOut(targetScale = 0.8f)
            ) {
                BubbleWithHints(
                    state = currentState,
                    dockOnLeft = dockLeft,
                    onTap = { onEvent(OverlayEvent.ShowBubble) }
                )
            }

            // Full-screen card panels (shown when in full-screen mode)
            AnimatedVisibility(
                visible = isFullScreen,
                enter = scaleIn(
                    initialScale = 0.2f,
                    animationSpec = spring(
                        dampingRatio = 0.75f,
                        stiffness = Spring.StiffnessMediumLow
                    )
                ) + fadeIn(
                    animationSpec = spring(
                        dampingRatio = 0.85f,
                        stiffness = Spring.StiffnessLow
                    )
                ),
                exit = scaleOut(
                    targetScale = 0.2f,
                    animationSpec = spring(
                        dampingRatio = 0.9f,
                        stiffness = Spring.StiffnessMedium
                    )
                ) + fadeOut(
                    animationSpec = spring(
                        dampingRatio = 0.9f,
                        stiffness = Spring.StiffnessMedium
                    )
                ),
                modifier = Modifier.align(Alignment.Center)
            ) {
                FullScreenCard(
                    currentState = currentState,
                    usage = usage,
                    isGalleryMode = galleryMode,
                    onEvent = onEvent
                )
            }
        }
    }
}

/**
 * Background scrim with optional blur effect (Android 12+)
 */
@Composable
private fun BackgroundScrim(
    visible: Boolean,
    onDismiss: () -> Unit
) {
    val scrimBase = Modifier.fillMaxSize()
    val scrimModifier = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        scrimBase.blur(16.dp)
    } else {
        scrimBase
    }

    AnimatedVisibility(
        visible = visible,
        enter = fadeIn(
            animationSpec = spring(dampingRatio = 0.85f, stiffness = Spring.StiffnessLow)
        ),
        exit = fadeOut(
            animationSpec = spring(dampingRatio = 0.9f, stiffness = Spring.StiffnessMedium)
        )
    ) {
        Box(
            modifier = scrimModifier
                .background(OverlayColors.ScrimColor)
                .clickable(
                    interactionSource = remember { MutableInteractionSource() },
                    indication = null
                ) { onDismiss() }
        )
    }
}

/**
 * The main card container with smooth animations
 * Contains all full-screen panels (Direction Picker, Screenshot Preview, Loading, Replies, Error)
 */
@Composable
private fun FullScreenCard(
    currentState: BubbleState,
    usage: UsageState,
    isGalleryMode: Boolean,
    onEvent: (OverlayEvent) -> Unit
) {
    Box(modifier = Modifier.padding(horizontal = 16.dp)) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .animateContentSize(
                    animationSpec = spring(
                        dampingRatio = 0.85f,
                        stiffness = Spring.StiffnessMedium
                    )
                ),
            shape = OverlayShapes.PanelShape,
            colors = CardDefaults.cardColors(containerColor = OverlayColors.PanelColor),
            border = BorderStroke(1.dp, OverlayColors.PanelBorderColor)
        ) {
            Column {
                // Header with navigation
                BubbleHeader(
                    currentState = currentState,
                    onBack = { onEvent(OverlayEvent.Back) },
                    onClose = { onEvent(OverlayEvent.DismissSuggestions) },
                    onStartOver = { onEvent(OverlayEvent.ClearAndStartOver) }
                )

                Divider(color = Color.White.copy(alpha = 0.08f))

                // Route to appropriate panel based on current state
                when (val s = currentState) {
                    is BubbleState.DirectionPicker -> DirectionPicker(
                        allowedDirections = usage.allowedDirections,
                        customHintsEnabled = usage.customHintsEnabled,
                        isGalleryMode = isGalleryMode,
                        onInputModeChanged = { isGallery ->
                            onEvent(OverlayEvent.SetGalleryMode(isGallery))
                        },
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
                    is BubbleState.Loading -> {
                        if (s.isProcessing) {
                            ProcessingOverlay()
                        } else {
                            LoadingOverlay()
                        }
                    }
                    is BubbleState.Expanded -> SuggestionPanel(
                        result = s.result,
                        onCopy = { reply, index ->
                            onEvent(OverlayEvent.CopyReply(reply, index, s.result.interactionId))
                        },
                        onRate = { index, positive, text ->
                            onEvent(OverlayEvent.RateReply(index, positive, text, s.result.interactionId))
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
