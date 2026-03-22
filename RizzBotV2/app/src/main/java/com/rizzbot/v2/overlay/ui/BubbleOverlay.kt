package com.rizzbot.v2.overlay.ui

import android.os.Build
import android.view.MotionEvent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.zIndex
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.TierQuota
import com.rizzbot.v2.domain.model.UsageState
import com.rizzbot.v2.overlay.OverlayEvent
import com.rizzbot.v2.overlay.manager.BubbleState
import com.rizzbot.v2.overlay.ui.components.bubble.BubbleWithHints
import com.rizzbot.v2.overlay.ui.components.panels.BubbleHeader
import com.rizzbot.v2.overlay.ui.components.panels.DirectionPicker
import com.rizzbot.v2.overlay.ui.components.panels.ErrorPanel
import com.rizzbot.v2.overlay.ui.components.panels.LoadingOverlay
import com.rizzbot.v2.overlay.ui.components.panels.MergeConfirmationPanel
import com.rizzbot.v2.overlay.ui.components.panels.ScreenshotPreviewPanel
import com.rizzbot.v2.overlay.ui.components.panels.SuggestionPanel
import com.rizzbot.v2.overlay.ui.theme.OverlayColors
import com.rizzbot.v2.overlay.ui.theme.OverlayShapes
import com.rizzbot.v2.ui.theme.LocalAppGodMode
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
    asyncWorkInFlight: StateFlow<Boolean>,
    onEvent: (OverlayEvent) -> Unit,
    onCollapsedOverlayMotionEvent: (MotionEvent) -> Boolean,
) {
    val currentState by state.collectAsState()
    val usage by usageState.collectAsState()
    val dockLeft by dockOnLeft.collectAsState()
    val galleryMode by isGalleryMode.collectAsState()
    val workInFlight by asyncWorkInFlight.collectAsState()

    val isFullScreen = currentState is BubbleState.DirectionPicker ||
        currentState is BubbleState.ScreenshotPreview ||
        currentState is BubbleState.Loading ||
        currentState is BubbleState.Expanded ||
        currentState is BubbleState.RequiresUserConfirmation ||
        currentState is BubbleState.Error

    val isGodMode = usage.isGodModeActive
    CompositionLocalProvider(LocalAppGodMode provides isGodMode) {
        OverlayTheme(isGodMode = isGodMode) {
            Box(
                modifier = if (isFullScreen) Modifier.fillMaxSize()
                else Modifier.background(Color.Transparent)
            ) {
            // Background scrim with blur effect
            BackgroundScrim(
                visible = isFullScreen,
                onDismiss = { onEvent(OverlayEvent.DismissSuggestions) }
            )

            // Floating bubble: dock-aware slide + soft spring scale + eased fade (premium entrance)
            val bubbleEnter = remember(dockLeft) {
                fadeIn(animationSpec = tween(340, easing = FastOutSlowInEasing)) +
                    scaleIn(
                        initialScale = 0.88f,
                        animationSpec = spring(
                            dampingRatio = Spring.DampingRatioNoBouncy,
                            stiffness = Spring.StiffnessLow
                        )
                    ) +
                    if (dockLeft) {
                        slideInHorizontally(
                            initialOffsetX = { -it / 4 },
                            animationSpec = tween(400, easing = FastOutSlowInEasing)
                        )
                    } else {
                        slideInHorizontally(
                            initialOffsetX = { it / 4 },
                            animationSpec = tween(400, easing = FastOutSlowInEasing)
                        )
                    }
            }
            val bubbleExit = remember(dockLeft) {
                fadeOut(animationSpec = tween(200, easing = FastOutSlowInEasing)) +
                    scaleOut(
                        targetScale = 0.92f,
                        animationSpec = tween(220, easing = FastOutSlowInEasing)
                    ) +
                    if (dockLeft) {
                        slideOutHorizontally(
                            targetOffsetX = { -it / 5 },
                            animationSpec = tween(220, easing = FastOutSlowInEasing)
                        )
                    } else {
                        slideOutHorizontally(
                            targetOffsetX = { it / 5 },
                            animationSpec = tween(220, easing = FastOutSlowInEasing)
                        )
                    }
            }
            val showFloatingBubble =
                !isFullScreen || (currentState is BubbleState.Loading && workInFlight)
            val bubbleModifier = if (isFullScreen) {
                Modifier
                    .zIndex(2f)
                    .align(if (dockLeft) Alignment.TopStart else Alignment.TopEnd)
                    .statusBarsPadding()
                    .padding(horizontal = 8.dp, vertical = 12.dp)
            } else {
                Modifier
            }
            AnimatedVisibility(
                visible = showFloatingBubble,
                modifier = bubbleModifier,
                enter = bubbleEnter,
                exit = bubbleExit
            ) {
                BubbleWithHints(
                    state = currentState,
                    dockOnLeft = dockLeft,
                    asyncWorkInFlight = workInFlight,
                    onCollapsedOverlayMotionEvent = onCollapsedOverlayMotionEvent
                )
            }

            // Full-screen card panels (shown when in full-screen mode)
            AnimatedVisibility(
                visible = isFullScreen,
                enter = fadeIn(
                    animationSpec = tween(240, easing = FastOutSlowInEasing)
                ) + scaleIn(
                    initialScale = 0.96f,
                    animationSpec = tween(280, easing = FastOutSlowInEasing)
                ),
                exit = fadeOut(
                    animationSpec = tween(180, easing = FastOutSlowInEasing)
                ) + scaleOut(
                    targetScale = 0.96f,
                    animationSpec = tween(200, easing = FastOutSlowInEasing)
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
        enter = fadeIn(tween(220, easing = FastOutSlowInEasing)),
        exit = fadeOut(tween(180, easing = FastOutSlowInEasing))
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
    val isLoading = currentState is BubbleState.Loading
    
    Box(modifier = Modifier.padding(horizontal = 16.dp)) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .fillMaxHeight(0.7f),
            shape = OverlayShapes.PanelShape,
            colors = CardDefaults.cardColors(containerColor = OverlayColors.PanelColor),
            border = BorderStroke(1.dp, OverlayColors.PanelBorderColor)
        ) {
            Column(modifier = Modifier.fillMaxSize()) {
                BubbleHeader(
                    currentState = currentState,
                    onBack = { onEvent(OverlayEvent.Back) },
                    onClose = { onEvent(OverlayEvent.DismissSuggestions) },
                    onStartOver = { onEvent(OverlayEvent.ClearAndStartOver) }
                )

                Divider(color = Color.White.copy(alpha = 0.08f))

                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                ) {
                    when (val s = currentState) {
                        is BubbleState.DirectionPicker -> DirectionPicker(
                            allowedDirections = usage.allowedDirections,
                            customHintsEnabled = usage.customHintsEnabled,
                            isGalleryMode = isGalleryMode,
                            isLoading = isLoading,
                            onInputModeChanged = { isGallery ->
                                if (!isLoading) {
                                    onEvent(OverlayEvent.SetGalleryMode(isGallery))
                                }
                            },
                            onDirectionSelected = { direction ->
                                if (!isLoading) {
                                    onEvent(OverlayEvent.CaptureRequested(direction))
                                }
                            },
                            onUpgrade = { onEvent(OverlayEvent.UpgradeTapped) },
                            onDismiss = { onEvent(OverlayEvent.DismissSuggestions) },
                            onKeyboardFocus = { enabled -> onEvent(OverlayEvent.SetKeyboardFocus(enabled)) },
                            modifier = Modifier.fillMaxSize()
                        )
                        is BubbleState.ScreenshotPreview -> {
                            val hasRepliesLeft =
                                TierQuota.isUnlimited(usage.dailyLimit) ||
                                    usage.dailyUsed < usage.dailyLimit
                            val canGenerate = usage.isGodModeActive || hasRepliesLeft

                            ScreenshotPreviewPanel(
                                bitmaps = s.bitmaps,
                                maxScreenshots = usage.maxScreenshots,
                                canGenerate = canGenerate && !isLoading,
                                isLoading = isLoading,
                                onConfirm = {
                                    if (!isLoading) {
                                        onEvent(OverlayEvent.ConfirmScreenshot(s.direction))
                                    }
                                },
                                onAddMore = {
                                    if (!isLoading) {
                                        onEvent(OverlayEvent.AddMoreScreenshots(s.direction))
                                    }
                                },
                                onRetake = {
                                    if (!isLoading) {
                                        onEvent(OverlayEvent.RetakeLastScreenshot(s.direction))
                                    }
                                },
                                onRemoveScreenshot = { index ->
                                    if (!isLoading) {
                                        onEvent(OverlayEvent.RemoveScreenshot(index, s.direction))
                                    }
                                },
                                onDismiss = { onEvent(OverlayEvent.DismissSuggestions) },
                                modifier = Modifier.fillMaxSize()
                            )
                        }
                        is BubbleState.Loading -> {
                            Box(
                                modifier = Modifier.fillMaxSize(),
                                contentAlignment = Alignment.Center
                            ) {
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
                            onDismiss = { onEvent(OverlayEvent.DismissSuggestions) },
                            modifier = Modifier.fillMaxSize()
                        )
                        is BubbleState.RequiresUserConfirmation -> MergeConfirmationPanel(
                            payload = s.payload,
                            onYes = { onEvent(OverlayEvent.ConfirmMerge(isMatch = true)) },
                            onNo = { onEvent(OverlayEvent.ConfirmMerge(isMatch = false)) },
                            modifier = Modifier.fillMaxSize()
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
                            modifier = Modifier.fillMaxSize()
                        )
                        else -> {}
                    }
                }
            }
        }
    }
}
