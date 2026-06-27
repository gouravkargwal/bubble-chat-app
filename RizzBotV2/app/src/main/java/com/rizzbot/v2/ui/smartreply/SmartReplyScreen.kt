package com.rizzbot.v2.ui.smartreply

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width

import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Image
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.rizzbot.v2.domain.model.ConversationDirection
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.overlay.ui.components.panels.ErrorPanel
import com.rizzbot.v2.overlay.ui.components.panels.SuggestionPanel
import com.rizzbot.v2.ui.theme.NeonRed
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SmartReplyScreen(
    onBack: () -> Unit,
    onShowPaywall: () -> Unit,
    viewModel: SmartReplyViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val maxScreenshots = state.maxScreenshots

    val galleryLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickMultipleVisualMedia(maxItems = maxScreenshots)
    ) { uris: List<Uri> ->
        if (uris.isNotEmpty()) viewModel.onImagesPicked(uris)
    }

    val galleryFallbackLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri: Uri? ->
        if (uri != null) viewModel.onImagesPicked(listOf(uri))
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Smart Reply", fontWeight = FontWeight.Bold, color = NothingWhite) },
                navigationIcon = {
                    IconButton(onClick = {
                        when (state.step) {
                            SmartReplyStep.SCREENSHOTS -> viewModel.onBackToDirection()
                            else -> onBack()
                        }
                    }) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = NothingWhite) }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = NothingBlack, titleContentColor = NothingWhite)
            )
        },
        containerColor = NothingBlack
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize()) {
            if (state.step != SmartReplyStep.GENERATING && state.step != SmartReplyStep.RESULT) {
                StepIndicator(currentStep = state.step)
            }

            Box(modifier = Modifier.fillMaxSize()) {
                AnimatedContent(targetState = state.step, label = "smartReplyStep") { step ->
                    when (step) {
                        SmartReplyStep.DIRECTION -> DirectionPickerStep(
                            state = state,
                            customHintText = state.customHintText,
                            onDirectionChosen = { viewModel.onDirectionChosen(it) },
                            onCustomHintChanged = { viewModel.onCustomHintChanged(it) },
                            onContinue = { viewModel.onContinueToScreenshots() },
                            onUpgrade = onShowPaywall,
                        )
                        SmartReplyStep.SCREENSHOTS -> ScreenshotsStep(
                            state = state,
                            maxScreenshots = maxScreenshots,
                            onOpenGallery = {
                                if (maxScreenshots > 1) galleryLauncher.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                                else galleryFallbackLauncher.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                            },
                            onRemoveImage = { index ->
                                val uris = state.imageUris.toMutableList()
                                if (index in uris.indices) { uris.removeAt(index); viewModel.onImagesPicked(uris) }
                            },
                            onGenerate = { viewModel.onGenerate() },
                        )
                        SmartReplyStep.GENERATING -> GeneratingStep()
                        SmartReplyStep.RESULT -> {
                            when (val result = state.result) {
                                is SuggestionResult.Success -> {
                                    val directionName = state.direction?.direction?.displayName ?: "Reply"
                                    val screenshotCount = state.imageUris.size
                                    val hintText = state.direction?.customHint
                                    SuggestionPanel(
                                        result = result,
                                        directionName = directionName,
                                        screenshotCount = screenshotCount,
                                        hintText = hintText,
                                        onCopy = { reply, index -> viewModel.onCopyReply(reply, index, result.interactionId) },
                                        onRate = { index, positive, text -> viewModel.onRateReply(index, positive, text, result.interactionId) },
                                        onRegenerate = { viewModel.onRegenerate() },
                                        onClear = { viewModel.onStartOver() },
                                        onDismiss = { viewModel.onBackToDirection() }
                                    )
                                }
                                is SuggestionResult.Error -> ErrorPanel(
                                    message = result.message,
                                    errorType = result.errorType,
                                    onRetry = { viewModel.onRegenerate() },
                                    onUpgrade = onShowPaywall,
                                    onDismiss = { viewModel.onStartOver() }
                                )
                                else -> {
                                    // Should not happen — RESULT step only reached with Success or Error.
                                    // Render nothing to avoid side-effects in composition.
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StepIndicator(currentStep: SmartReplyStep) {
    val steps = listOf(SmartReplyStep.DIRECTION, SmartReplyStep.SCREENSHOTS)
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = NothingDimens.screenPadding, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(0.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        steps.forEachIndexed { index, step ->
            val isActive = step == currentStep
            val isPast = step.ordinal < currentStep.ordinal
            Column(modifier = Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                Box(
                    modifier = Modifier.size(if (isActive) 12.dp else 10.dp)
                        .clip(CircleShape)
                        .background(if (isPast || isActive) NothingWhite else NothingBorder)
                )
                Spacer(modifier = Modifier.height(NothingDimens.textGap))
                Text(step.displayName, color = if (isActive || isPast) NothingWhite else NothingTextTertiary, style = MaterialTheme.typography.labelSmall)
            }
            if (index < steps.lastIndex) {
                Box(modifier = Modifier.height(2.dp).weight(0.6f).background(if (isPast) NothingTextSecondary else NothingBorder, RoundedCornerShape(1.dp)))
            }
        }
    }
    Spacer(modifier = Modifier.height(NothingDimens.elementGap))
}

@Composable
private fun DirectionPickerStep(
    state: SmartReplyState,
    customHintText: String,
    onDirectionChosen: (ConversationDirection) -> Unit,
    onCustomHintChanged: (String) -> Unit,
    onContinue: () -> Unit,
    onUpgrade: () -> Unit,
) {
    val scrollState = rememberScrollState()
    val hasSelection = state.direction != null
    val hintEnabled = state.usage.customHintsEnabled
    var showHintField by remember { mutableStateOf(customHintText.isNotEmpty()) }
    val focusRequester = remember { FocusRequester() }
    val focusManager = LocalFocusManager.current

    LaunchedEffect(showHintField) {
        if (showHintField) focusRequester.requestFocus()
    }

    Column(modifier = Modifier.fillMaxSize().padding(horizontal = NothingDimens.screenPadding)) {
        Column(modifier = Modifier.weight(1f).verticalScroll(scrollState)) {
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
            Text("What kind of reply?", color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleLarge)
            Spacer(modifier = Modifier.height(NothingDimens.textGap))
            Text("Choose the vibe you want to send", color = NothingTextSecondary, style = MaterialTheme.typography.bodyMedium)
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))

            ConversationDirection.entries.forEach { direction ->
                val dirKey = direction.name.lowercase()
                val isLocked = state.usage.allowedDirections.isNotEmpty() && dirKey !in state.usage.allowedDirections
                val isSelected = state.direction?.direction == direction

                Card(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp).clickable { if (isLocked) onUpgrade() else onDirectionChosen(direction) },
                    colors = CardDefaults.cardColors(containerColor = NothingSurface),
                    shape = RoundedCornerShape(NothingDimens.cardRadius),
                    border = BorderStroke(
                        if (isSelected) 2.dp else NothingDimens.borderThickness,
                        if (isSelected) NothingWhite else NothingBorder
                    )
                ) {
                    Row(modifier = Modifier.padding(NothingDimens.cardPadding), verticalAlignment = Alignment.CenterVertically) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(direction.displayName, color = if (isLocked) NothingTextSecondary else NothingWhite, style = MaterialTheme.typography.titleSmall, fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium)
                            if (isLocked) Text("[LOCKED]", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                        }
                        if (isSelected) {
                            Box(modifier = Modifier.size(24.dp).clip(CircleShape).background(NothingWhite), contentAlignment = Alignment.Center) {
                                Icon(Icons.Default.Check, contentDescription = "Selected", tint = NothingBlack, modifier = Modifier.size(14.dp))
                            }
                        }
                    }
                }
            }

            // ── Custom hint section (tier-gated) ──
            if (hintEnabled) {
                Spacer(modifier = Modifier.height(8.dp))
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(NothingDimens.cardRadius))
                        .background(
                            if (showHintField) NothingTextSecondary.copy(alpha = 0.08f) else NothingBorder
                        )
                        .clickable { showHintField = !showHintField }
                        .padding(NothingDimens.cardPadding),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        Icons.Default.Edit,
                        contentDescription = null,
                        tint = if (showHintField) NothingWhite else NothingTextSecondary,
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(NothingDimens.elementGap))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = if (customHintText.isNotEmpty()) "Hint: $customHintText" else "Add a custom hint",
                            color = if (customHintText.isNotEmpty()) NothingWhite else NothingTextSecondary,
                            style = MaterialTheme.typography.titleSmall,
                        )
                        if (customHintText.isEmpty()) {
                            Text(
                                "Tell Cookd something specific to include",
                                color = NothingTextTertiary,
                                style = MaterialTheme.typography.labelSmall,
                            )
                        }
                    }
                    Icon(
                        if (showHintField) Icons.Default.Close else Icons.Default.Edit,
                        contentDescription = if (showHintField) "Close" else "Edit",
                        tint = NothingTextSecondary,
                        modifier = Modifier.size(18.dp)
                    )
                }

                AnimatedVisibility(
                    visible = showHintField,
                    enter = expandVertically() + fadeIn(),
                    exit = shrinkVertically() + fadeOut(),
                ) {
                    Column {
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedTextField(
                            value = customHintText,
                            onValueChange = onCustomHintChanged,
                            placeholder = {
                                Text(
                                    "e.g. Mention her love for dogs, reference our inside joke...",
                                    color = NothingTextTertiary,
                                    style = MaterialTheme.typography.labelSmall,
                                )
                            },
                            modifier = Modifier.fillMaxWidth().focusRequester(focusRequester),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedTextColor = NothingWhite,
                                unfocusedTextColor = NothingWhite,
                                focusedBorderColor = NothingWhite,
                                unfocusedBorderColor = NothingBorder,
                                cursorColor = NothingWhite,
                            ),
                            shape = RoundedCornerShape(NothingDimens.cardRadius),
                            textStyle = MaterialTheme.typography.bodyMedium,
                            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                            keyboardActions = KeyboardActions(onDone = { focusManager.clearFocus() }),
                            singleLine = false,
                            maxLines = 3,
                            supportingText = {
                                Text(
                                    text = "${customHintText.length}/${SmartReplyViewModel.CUSTOM_HINT_MAX_LENGTH}",
                                    color = NothingTextTertiary,
                                    style = MaterialTheme.typography.labelSmall,
                                )
                            },
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            OutlinedButton(
                                onClick = {
                                    onCustomHintChanged("")
                                    showHintField = false
                                },
                                shape = RoundedCornerShape(NothingDimens.pillRadius),
                                modifier = Modifier.weight(1f),
                                border = BorderStroke(NothingDimens.borderThickness, NothingBorder),
                            ) { Text("Clear", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall) }
                            Button(
                                onClick = {
                                    focusManager.clearFocus()
                                    showHintField = false
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
                                shape = RoundedCornerShape(NothingDimens.pillRadius),
                                modifier = Modifier.weight(1f),
                            ) { Text("Done", color = NothingBlack, fontWeight = FontWeight.SemiBold) }
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(NothingDimens.elementGap))

        Button(
            onClick = onContinue,
            enabled = hasSelection,
            colors = ButtonDefaults.buttonColors(containerColor = NeonRed),
            modifier = Modifier.fillMaxWidth().height(NothingDimens.minTouchTarget),
            shape = RoundedCornerShape(NothingDimens.pillRadius)
        ) {
            Icon(Icons.Default.AutoAwesome, contentDescription = null, modifier = Modifier.size(20.dp))
            Spacer(modifier = Modifier.width(NothingDimens.elementGap))
            Text("Continue", color = NothingWhite, fontWeight = FontWeight.Bold)
        }
        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
private fun ScreenshotsStep(
    state: SmartReplyState,
    maxScreenshots: Int,
    onOpenGallery: () -> Unit,
    onRemoveImage: (Int) -> Unit,
    onGenerate: () -> Unit,
) {
    val scrollState = rememberScrollState()
    val hasImages = state.previewBitmaps.isNotEmpty()
    Column(modifier = Modifier.fillMaxSize().padding(horizontal = NothingDimens.screenPadding)) {
        Column(modifier = Modifier.weight(1f).verticalScroll(scrollState)) {
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
            Text("Add screenshots", color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleLarge)
            Spacer(modifier = Modifier.height(NothingDimens.textGap))
            Text("Pick up to $maxScreenshots screenshots from your chat", color = NothingTextSecondary, style = MaterialTheme.typography.bodyMedium)
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))

            if (hasImages) {
                ScreenshotGrid(previewBitmaps = state.previewBitmaps, maxScreenshots = maxScreenshots, onAddMore = onOpenGallery, onRemove = onRemoveImage)
            } else {
                EmptyGalleryCta(onClick = onOpenGallery, maxScreenshots = maxScreenshots)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        Button(
            onClick = if (hasImages) onGenerate else onOpenGallery,
            colors = ButtonDefaults.buttonColors(containerColor = if (hasImages) NeonRed else NothingWhite),
            modifier = Modifier.fillMaxWidth().height(NothingDimens.minTouchTarget),
            shape = RoundedCornerShape(NothingDimens.pillRadius)
        ) {
            Icon(if (hasImages) Icons.Default.AutoAwesome else Icons.Default.Image, contentDescription = null, modifier = Modifier.size(20.dp))
            Spacer(modifier = Modifier.width(NothingDimens.elementGap))
            Text(
                if (hasImages) "Generate Reply" else "Pick Screenshots",
                color = if (hasImages) NothingWhite else NothingBlack,
                fontWeight = FontWeight.Bold
            )
        }
        Spacer(modifier = Modifier.height(32.dp))
    }
}

@Composable
private fun ScreenshotGrid(previewBitmaps: List<android.graphics.Bitmap>, maxScreenshots: Int, onAddMore: () -> Unit, onRemove: (Int) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        var idx = 0
        while (idx < previewBitmaps.size) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // First cell in the row
                ScreenshotCell(
                    bitmap = previewBitmaps[idx],
                    label = "Screenshot ${idx + 1}",
                    onRemove = { onRemove(idx) },
                    modifier = Modifier.weight(1f)
                )
                // Second cell: either another screenshot, add-more button, or empty
                if (idx + 1 < previewBitmaps.size) {
                    ScreenshotCell(
                        bitmap = previewBitmaps[idx + 1],
                        label = "Screenshot ${idx + 1 + 1}",
                        onRemove = { onRemove(idx + 1) },
                        modifier = Modifier.weight(1f)
                    )
                    idx += 2
                } else if (previewBitmaps.size < maxScreenshots) {
                    AddMoreCell(
                        currentCount = previewBitmaps.size,
                        maxScreenshots = maxScreenshots,
                        onAddMore = onAddMore,
                        modifier = Modifier.weight(1f)
                    )
                    idx += 1
                } else {
                    // Odd count but at max — leave second slot empty
                    Spacer(modifier = Modifier.weight(1f))
                    idx += 1
                }
            }
        }
        // If even-numbered images and room for more, add a full-width add-more row
        if (previewBitmaps.size % 2 == 0 && previewBitmaps.size < maxScreenshots) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                AddMoreCell(
                    currentCount = previewBitmaps.size,
                    maxScreenshots = maxScreenshots,
                    onAddMore = onAddMore,
                    modifier = Modifier.weight(1f)
                )
                Spacer(modifier = Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun ScreenshotCell(
    bitmap: android.graphics.Bitmap,
    label: String,
    onRemove: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .height(170.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(NothingSurface)
            .border(NothingDimens.borderThickness, NothingBorder.copy(alpha = 0.3f), RoundedCornerShape(12.dp))
    ) {
        Image(
            bitmap = bitmap.asImageBitmap(),
            contentDescription = label,
            modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(12.dp)),
            contentScale = ContentScale.Crop,
        )
        // Semi-transparent label at bottom
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(32.dp)
                .align(Alignment.BottomCenter)
                .background(NothingBlack.copy(alpha = 0.6f), RoundedCornerShape(bottomStart = 12.dp, bottomEnd = 12.dp)),
            contentAlignment = Alignment.Center
        ) {
            Text(label, color = NothingWhite, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Medium)
        }
        // Remove button
        IconButton(
            onClick = onRemove,
            modifier = Modifier
                .align(Alignment.TopEnd)
                .size(26.dp)
                .padding(2.dp)
                .background(NeonRed.copy(alpha = 0.85f), CircleShape)
        ) {
            Icon(Icons.Default.Close, "Remove", tint = NothingWhite, modifier = Modifier.size(14.dp))
        }
    }
}

@Composable
private fun AddMoreCell(
    currentCount: Int,
    maxScreenshots: Int,
    onAddMore: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .height(170.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(NothingSurface.copy(alpha = 0.5f))
            .border(NothingDimens.borderThickness, NothingBorder.copy(alpha = 0.5f), RoundedCornerShape(12.dp))
            .clickable { onAddMore() },
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier.size(44.dp).clip(CircleShape).background(NothingWhite.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Default.Add, "Add", tint = NothingWhite, modifier = Modifier.size(24.dp))
            }
            Spacer(modifier = Modifier.height(6.dp))
            Text("Add more", color = NothingWhite, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold)
            Text("$currentCount of $maxScreenshots", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
private fun EmptyGalleryCta(onClick: () -> Unit, maxScreenshots: Int) {
    Box(modifier = Modifier.fillMaxWidth().height(160.dp).clip(RoundedCornerShape(NothingDimens.cardRadius)).background(NothingSurface).border(NothingDimens.borderThickness, NothingBorder, RoundedCornerShape(NothingDimens.cardRadius)).clickable { onClick() }, contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(Icons.Default.Image, contentDescription = null, tint = NothingTextSecondary, modifier = Modifier.size(40.dp))
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
            Text("Tap to pick screenshots", color = NothingWhite, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Text("Up to $maxScreenshots images", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
private fun GeneratingStep() {
    val infiniteTransition = rememberInfiniteTransition(label = "loading")

    // Nothing OS dot-matrix loading — 3 pulsing dots
    val dotAlphas = List(3) { index ->
        infiniteTransition.animateFloat(
            initialValue = 0.2f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(
                animation = tween(600, delayMillis = index * 200),
                repeatMode = RepeatMode.Reverse
            ),
            label = "dot$index"
        )
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(NothingDimens.cardPadding),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        // Nothing OS dot-matrix loading — 3 pulsing dots
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            dotAlphas.forEach { anim ->
                Box(
                    modifier = Modifier
                        .size(10.dp)
                        .clip(CircleShape)
                        .background(NothingWhite.copy(alpha = anim.value))
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        Text(
            "Cooking up your reply",
            color = NothingWhite,
            fontWeight = FontWeight.Bold,
            style = MaterialTheme.typography.titleMedium
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            "Analyzing screenshots and crafting the perfect response",
            color = NothingTextSecondary,
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center
        )
    }
}
