package com.rizzbot.v2.ui.profile

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import androidx.hilt.navigation.compose.hiltViewModel
import com.rizzbot.v2.domain.model.TierQuota
import kotlinx.coroutines.delay

enum class PhotoTier {
    GOD_TIER,
    FILLER,
    GRAVEYARD
}

data class PhotoFeedbackUi(
    val photoId: String,
    val score: Int,
    val tier: PhotoTier,
    val brutalFeedback: String,
    val improvementTip: String
)

data class AuditResponseUi(
    val totalAnalyzed: Int,
    val passedCount: Int,
    val isHardReset: Boolean,
    val roastSummary: String,
    val overallScore: Int,
    val photos: List<PhotoFeedbackUi>
)

private val DarkBg = Color(0xFF0F0F1A)
private val CardBg = Color(0xFF1A1A2E)
@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun ProfileAuditorScreen(
    onBack: () -> Unit,
    onShowPaywall: () -> Unit = {},
    onOpenPastPhotoAudits: () -> Unit = {},
    viewModel: ProfileAuditorViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val maxPhotos = state.maxPhotosPerAudit

    LaunchedEffect(state.showPaywall) {
        if (state.showPaywall) {
            onShowPaywall()
            viewModel.dismissPaywall()
        }
    }

    val weeklyAuditLimit = state.profileAuditsPerWeek
    val weeklyAuditsUsed = state.weeklyAuditsUsed.coerceAtLeast(0)
    val showIntro =
        state.result == null && !state.isLoading && !state.auditSessionStarted

    val flowStep = when {
        state.result != null -> 3
        state.isLoading -> 2
        state.selectedUris.isNotEmpty() -> 2
        else -> 1
    }

    val photoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickMultipleVisualMedia(maxPhotos)
    ) { uris ->
        viewModel.onPhotosSelected(uris)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Photo Audit",
                        fontSize = 18.sp
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.White
                        )
                    }
                },
                actions = {
                    TextButton(onClick = onOpenPastPhotoAudits) {
                        Text(
                            text = "Past audits",
                            color = MaterialTheme.colorScheme.primary,
                            fontSize = 14.sp,
                            maxLines = 1,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = DarkBg,
                    titleContentColor = Color.White
                )
            )
        },
        bottomBar = {
            Surface(
                color = DarkBg,
                shadowElevation = 12.dp
            ) {
                Column(
                    modifier = Modifier
                        .navigationBarsPadding()
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    when {
                        state.result != null -> {
                            Text(
                                text = "Start over to run another audit. Limits are checked when you tap Run audit.",
                                color = Color.Gray,
                                fontSize = 12.sp,
                                modifier = Modifier.padding(bottom = 2.dp)
                            )
                            OutlinedButton(
                                onClick = { viewModel.startNewAudit() },
                                enabled = !state.isLoading,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(52.dp),
                                shape = RoundedCornerShape(14.dp),
                                border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary),
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.primary)
                            ) {
                                Text(text = "Start a new audit", fontSize = 15.sp)
                            }
                        }
                        showIntro -> {
                            if (TierQuota.isFinite(weeklyAuditLimit) &&
                                state.weeklyAuditsUsed >= weeklyAuditLimit
                            ) {
                                Text(
                                    text = "You’ve used your weekly audits. Tap Run audit to see upgrade options.",
                                    color = Color.Gray,
                                    fontSize = 12.sp,
                                )
                            }
                            Button(
                                onClick = {
                                    viewModel.tryBeginAuditSession { onShowPaywall() }
                                },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(52.dp),
                                shape = RoundedCornerShape(14.dp),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = MaterialTheme.colorScheme.primary
                                )
                            ) {
                                Text(
                                    text = "Run audit",
                                    color = Color.Black,
                                    fontSize = 16.sp,
                                )
                            }
                        }
                        else -> {
                            Button(
                                onClick = { viewModel.analyzePhotos() },
                                enabled = !state.isLoading && state.selectedUris.isNotEmpty(),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(52.dp),
                                shape = RoundedCornerShape(14.dp),
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = MaterialTheme.colorScheme.primary
                                )
                            ) {
                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.Center
                                ) {
                                    if (state.isLoading) {
                                        CircularProgressIndicator(
                                            modifier = Modifier.size(16.dp),
                                            color = Color.Black,
                                            strokeWidth = 2.dp
                                        )
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text(
                                            text = state.auditProgress?.displayText ?: "Working…",
                                            color = Color.Black,
                                            fontSize = 15.sp
                                        )
                                    } else {
                                        Text(
                                            text = if (state.selectedUris.isEmpty()) {
                                                "Choose photos above"
                                            } else {
                                                "Submit for scoring (${state.selectedUris.size})"
                                            },
                                            color = Color.Black,
                                            fontSize = 15.sp
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        containerColor = DarkBg
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier
                    .padding(padding)
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                if (showIntro) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(
                            text = "Photo audit",
                            color = Color.White,
                            fontSize = 22.sp,
                            style = MaterialTheme.typography.headlineSmall,
                        )
                        Text(
                            text = "Walk through the steps below, then tap Run audit to continue. Plan limits apply at that tap only.",
                            color = Color.Gray,
                            fontSize = 14.sp,
                            lineHeight = 20.sp,
                        )
                    }
                    AuditIntroSteps(maxPhotos = maxPhotos)
                }

                Card(
                    colors = CardDefaults.cardColors(containerColor = CardBg),
                    shape = RoundedCornerShape(14.dp)
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Text(
                            text = when {
                                TierQuota.isUnlimited(weeklyAuditLimit) ->
                                    "Unlimited photo audits on your plan."
                                TierQuota.isNotOnPlan(weeklyAuditLimit) ->
                                    "Photo audits aren't included on your current plan."
                                else -> {
                                    val limit = weeklyAuditLimit
                                    val used = weeklyAuditsUsed.coerceAtMost(limit)
                                    val noun = if (limit == 1) "audit" else "audits"
                                    "You've used $used of $limit $noun this week."
                                }
                            },
                            color = Color.White,
                            fontSize = 14.sp,
                            style = MaterialTheme.typography.titleSmall
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "One audit = one run with up to $maxPhotos photos. Open Past audits (top) for earlier results.",
                            color = Color.Gray,
                            fontSize = 12.sp
                        )
                    }
                }

                if (!showIntro) {
                AuditFlowStepRow(
                    currentStep = flowStep,
                    isAnalyzing = state.isLoading,
                )

                state.error?.let { err ->
                    Card(
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF3A1F24)),
                        shape = RoundedCornerShape(16.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = "Something went wrong",
                                    color = Color(0xFFFF8A80),
                                    fontSize = 14.sp,
                                    style = MaterialTheme.typography.titleSmall
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = err,
                                    color = Color.White.copy(alpha = 0.9f),
                                    fontSize = 13.sp
                                )
                            }
                            Text(
                                text = "Dismiss",
                                color = MaterialTheme.colorScheme.primary,
                                fontSize = 13.sp,
                                modifier = Modifier
                                    .clip(RoundedCornerShape(8.dp))
                                    .clickable { viewModel.clearError() }
                                    .padding(8.dp)
                            )
                        }
                    }
                }

                val photoIdToUri = if (state.result != null && state.resultPhotoIdToUri.isNotEmpty()) {
                    state.resultPhotoIdToUri
                } else {
                    remember(state.selectedUris) {
                        state.selectedUris.mapIndexed { index, uri ->
                            "photo_${index + 1}" to uri
                        }.toMap()
                    }
                }

                when {
                    state.isLoading -> {
                        AuditProgressView(progress = state.auditProgress ?: AuditProgress())
                    }
                    state.result != null -> {
                        val result = state.result
                        if (result != null) {
                            Text(
                                text = "Your audit",
                                color = Color.White,
                                fontSize = 20.sp,
                                style = MaterialTheme.typography.titleLarge
                            )
                            Text(
                                text = "Best shots for your profile, okay backups, and photos to replace. Tips are under each image.",
                                color = Color.Gray,
                                fontSize = 13.sp
                            )
                            ProfileAuditResultContent(
                                result = result,
                                photoIdToUri = photoIdToUri
                            )
                        }
                    }
                    else -> {
                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(
                                text = "Step 1 — Choose photos",
                                color = Color.White,
                                fontSize = 18.sp,
                                style = MaterialTheme.typography.titleMedium
                            )
                            Text(
                                text = "Pick up to $maxPhotos photos from your gallery. You can change them until you submit for scoring.",
                                color = Color.Gray,
                                fontSize = 13.sp
                            )
                        }

                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text(
                                text = "Feedback style",
                                color = Color.White,
                                fontSize = 14.sp,
                                style = MaterialTheme.typography.titleSmall
                            )
                            Text(
                                text = "Affects how the feedback is written, not the scores.",
                                color = Color.Gray,
                                fontSize = 12.sp
                            )
                            Row(
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                val options = listOf("English", "Hinglish", "Gen-Z Slang")
                                options.forEach { option ->
                                    val isSelected = option == state.selectedLanguage
                                    AssistChip(
                                        onClick = {
                                            if (!state.isLoading) {
                                                viewModel.setLanguage(option)
                                            }
                                        },
                                        enabled = !state.isLoading,
                                        label = {
                                            Text(
                                                text = option,
                                                color = if (isSelected) Color.Black else Color.White,
                                                fontSize = 12.sp
                                            )
                                        },
                                        colors = AssistChipDefaults.assistChipColors(
                                            containerColor = if (isSelected) MaterialTheme.colorScheme.primary else CardBg
                                        )
                                    )
                                }
                            }
                        }

                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable(
                                    enabled = !state.isLoading,
                                    onClick = {
                                        photoPickerLauncher.launch(
                                            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                                        )
                                    }
                                ),
                            colors = CardDefaults.cardColors(
                                containerColor = if (state.isLoading) CardBg.copy(alpha = 0.5f) else CardBg
                            ),
                            shape = RoundedCornerShape(18.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 20.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    Text(
                                        text = if (state.selectedUris.isEmpty()) {
                                            "Tap to choose from gallery"
                                        } else {
                                            "Tap to add or replace photos"
                                        },
                                        color = Color.White,
                                        fontSize = 15.sp,
                                        style = MaterialTheme.typography.titleSmall
                                    )
                                    Spacer(modifier = Modifier.height(6.dp))
                                    Text(
                                        text = "${state.selectedUris.size} of $maxPhotos selected",
                                        color = Color.Gray,
                                        fontSize = 12.sp
                                    )
                                }
                            }
                        }

                        if (state.selectedUris.isNotEmpty()) {
                            Text(
                                text = "Step 2 — Review & submit",
                                color = Color.White,
                                fontSize = 15.sp,
                                style = MaterialTheme.typography.titleSmall
                            )
                            Text(
                                text = "Use Submit for scoring below when you’re ready.",
                                color = Color.Gray,
                                fontSize = 12.sp
                            )

                            LazyVerticalGrid(
                                columns = GridCells.Fixed(3),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .heightIn(min = 120.dp, max = 420.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                userScrollEnabled = !state.isLoading
                            ) {
                                items(state.selectedUris, key = { it.toString() }) { uri ->
                                    AsyncImage(
                                        model = uri,
                                        contentDescription = "Selected profile photo",
                                        modifier = Modifier
                                            .aspectRatio(1f)
                                            .clip(RoundedCornerShape(12.dp))
                                            .background(Color.Black),
                                        contentScale = ContentScale.Crop
                                    )
                                }
                            }
                        }
                    }
                }
                }

                Spacer(modifier = Modifier.height(80.dp))
            }
        }
    }
    
}

@Composable
private fun AuditIntroSteps(maxPhotos: Int) {
    Card(
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(16.dp),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(
                text = "How it works",
                color = Color.White,
                fontSize = 16.sp,
                style = MaterialTheme.typography.titleMedium,
            )
            AuditIntroStepRow(
                step = 1,
                title = "Choose photos",
                body = "Select up to $maxPhotos dating-style pictures from your gallery. Swap them anytime before you submit.",
            )
            AuditIntroStepRow(
                step = 2,
                title = "Pick feedback style",
                body = "English, Hinglish, or Gen-Z — only changes how the written notes sound.",
            )
            AuditIntroStepRow(
                step = 3,
                title = "Submit & see results",
                body = "We label best picks, backups, and photos to replace. Past runs stay in Past audits (top right).",
            )
        }
    }
}

@Composable
private fun AuditIntroStepRow(
    step: Int,
    title: String,
    body: String,
) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalAlignment = Alignment.Top,
    ) {
        Box(
            modifier = Modifier
                .size(32.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.22f))
                .border(1.5.dp, MaterialTheme.colorScheme.primary, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = "$step",
                color = Color.White,
                fontSize = 14.sp,
                style = MaterialTheme.typography.titleSmall,
            )
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                color = Color.White,
                fontSize = 14.sp,
                style = MaterialTheme.typography.titleSmall,
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = body,
                color = Color.Gray,
                fontSize = 12.sp,
                lineHeight = 16.sp,
            )
        }
    }
}

@Composable
private fun AuditFlowStepRow(
    currentStep: Int,
    isAnalyzing: Boolean,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceEvenly,
    ) {
        AuditStepPill(
            index = 1,
            label = "Add",
            currentStep = currentStep,
        )
        AuditStepConnector(done = currentStep >= 2)
        AuditStepPill(
            index = 2,
            label = if (isAnalyzing) "Wait" else "Score",
            currentStep = currentStep,
        )
        AuditStepConnector(done = currentStep >= 3)
        AuditStepPill(
            index = 3,
            label = "Results",
            currentStep = currentStep,
        )
    }
}

@Composable
private fun AuditStepPill(
    index: Int,
    label: String,
    currentStep: Int,
) {
    val done = index < currentStep
    val current = index == currentStep
    val bg = when {
        done -> Color(0xFF1B5E20).copy(alpha = 0.45f)
        current -> MaterialTheme.colorScheme.primary.copy(alpha = 0.22f)
        else -> CardBg
    }
    val ring = when {
        done -> Color(0xFF81C784)
        current -> MaterialTheme.colorScheme.primary
        else -> Color(0xFF252542)
    }
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.widthIn(min = 64.dp, max = 88.dp),
    ) {
        Box(
            modifier = Modifier
                .size(30.dp)
                .clip(CircleShape)
                .background(bg)
                .border(1.5.dp, ring, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            if (done) {
                Text("✓", color = Color.White, fontSize = 14.sp)
            } else {
                Text(
                    text = "$index",
                    color = Color.White,
                    fontSize = 13.sp,
                )
            }
        }
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = label,
            color = if (current || done) Color.White else Color.Gray,
            fontSize = 10.sp,
            maxLines = 1,
        )
    }
}

@Composable
private fun AuditStepConnector(done: Boolean) {
    Box(
        modifier = Modifier
            .width(20.dp)
            .height(3.dp)
            .clip(RoundedCornerShape(2.dp))
            .background(if (done) Color(0xFF81C784) else Color(0xFF252542)),
    )
}

@Composable
private fun Modifier.shimmerEffect(): Modifier {
    val infiniteTransition = rememberInfiniteTransition(label = "shimmer")
    val alpha by infiniteTransition.animateFloat(
        initialValue = 0.2f,
        targetValue = 0.6f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "shimmer_alpha"
    )
    return this.background(Color(0xFF252542).copy(alpha = alpha))
}

@Composable
private fun SkeletonTextLines(modifier: Modifier = Modifier, lines: Int = 3) {
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        repeat(lines) { index ->
            val widthFraction = when (index) {
                0 -> 1f // First line full width
                lines - 1 -> 0.6f // Last line shortest
                else -> 0.85f // Middle lines slightly shorter
            }
            Box(
                modifier = Modifier
                    .fillMaxWidth(widthFraction)
                    .height(14.dp)
                    .clip(RoundedCornerShape(4.dp))
                    .shimmerEffect()
            )
        }
    }
}

@Composable
private fun AuditProgressView(progress: AuditProgress) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(20.dp)
    ) {
        Spacer(modifier = Modifier.height(24.dp))

        // Animated progress ring
        Box(contentAlignment = Alignment.Center) {
            CircularProgressIndicator(
                progress = { if (progress.progress > 0f) progress.progress else 0f },
                modifier = Modifier.size(100.dp),
                color = MaterialTheme.colorScheme.primary,
                trackColor = Color(0xFF252542),
                strokeWidth = 6.dp,
            )
            // Indeterminate spinner overlay when progress is 0
            if (progress.progress <= 0f) {
                CircularProgressIndicator(
                    modifier = Modifier.size(100.dp),
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.5f),
                    strokeWidth = 4.dp,
                )
            }
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                if (progress.total > 0 && progress.current > 0) {
                    Text(
                        text = "${progress.current}/${progress.total}",
                        color = Color.White,
                        fontSize = 22.sp,
                        style = MaterialTheme.typography.headlineSmall
                    )
                }
            }
        }

        // Step description
        Text(
            text = progress.displayText,
            color = Color.White,
            fontSize = 16.sp,
            style = MaterialTheme.typography.titleMedium
        )

        // Fun roasting messages that rotate
        val roastingMessages = listOf(
            "Judging your selfie game...",
            "Checking for bathroom mirrors...",
            "Analyzing cringe levels...",
            "Rating your main character energy...",
            "Scanning for red flags..."
        )
        var messageIndex by remember { mutableIntStateOf(0) }
        LaunchedEffect(Unit) {
            while (true) {
                delay(2500)
                messageIndex = (messageIndex + 1) % roastingMessages.size
            }
        }
        Text(
            text = roastingMessages[messageIndex],
            color = Color.Gray,
            fontSize = 13.sp
        )

        Spacer(modifier = Modifier.height(12.dp))

        // Skeleton cards underneath
        repeat(2) {
            SkeletonAuditCard()
        }
    }
}

@Composable
private fun ProfileAuditorSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Header skeleton
        Box(
            modifier = Modifier
                .width(120.dp)
                .height(24.dp)
                .shimmerEffect()
        )

        // Skeleton audit cards
        repeat(3) {
            SkeletonAuditCard()
        }
    }
}

@Composable
private fun SkeletonAuditCard() {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(0.5.dp, Color(0xFF252542)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Left: Photo skeleton
            Box(
                modifier = Modifier
                    .width(100.dp)
                    .height(130.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .shimmerEffect()
            )
            
            // Right: Content skeleton
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Score badge skeleton (circle)
                Box(
                    modifier = Modifier
                        .size(32.dp)
                        .clip(RoundedCornerShape(16.dp))
                        .shimmerEffect()
                )
                
                Spacer(modifier = Modifier.height(4.dp))
                
                // Text line skeletons
                SkeletonTextLines(lines = 4)
            }
        }
    }
}

@Composable
private fun ProfileAuditResultContent(
    result: AuditResponseUi,
    photoIdToUri: Map<String, Uri>
) {
    val godTier = result.photos.filter { it.tier == PhotoTier.GOD_TIER }
    val filler = result.photos.filter { it.tier == PhotoTier.FILLER }
    val graveyard = result.photos.filter { it.tier == PhotoTier.GRAVEYARD }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 8.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        RoastSummaryBanner(result = result)

        if (godTier.isNotEmpty()) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = "Best — lead with these",
                    color = Color(0xFF81C784),
                    fontSize = 15.sp,
                    style = MaterialTheme.typography.titleSmall,
                )
                Text(
                    text = "Strongest shots; good light, clear face, dating-app ready.",
                    color = Color.Gray,
                    fontSize = 12.sp,
                )
            }
            godTier.forEach { photo ->
                PhotoResultRow(photo = photo, uri = photoIdToUri[photo.photoId])
            }
        }

        if (filler.isNotEmpty()) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = "Okay — backup slots",
                    color = Color(0xFFFFF176),
                    fontSize = 15.sp,
                    style = MaterialTheme.typography.titleSmall,
                )
                Text(
                    text = "Usable later or mixed in, but not your first impression.",
                    color = Color.Gray,
                    fontSize = 12.sp,
                )
            }
            filler.forEach { photo ->
                PhotoResultRow(photo = photo, uri = photoIdToUri[photo.photoId])
            }
        }

        if (graveyard.isNotEmpty()) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = "Skip — replace these",
                    color = Color(0xFFEF5350),
                    fontSize = 15.sp,
                    style = MaterialTheme.typography.titleSmall,
                )
                Text(
                    text = "Likely hurting matches; swap for new photos when you can.",
                    color = Color.Gray,
                    fontSize = 12.sp,
                )
            }
            graveyard.forEach { photo ->
                PhotoResultRow(photo = photo, uri = photoIdToUri[photo.photoId])
            }
        }
    }
}

@Composable
private fun RoastSummaryBanner(result: AuditResponseUi) {
    val gradientBrush = Brush.verticalGradient(
        colors = listOf(
            MaterialTheme.colorScheme.primary.copy(alpha = 0.45f),
            MaterialTheme.colorScheme.primary.copy(alpha = 0.12f),
            DarkBg
        )
    )

    AnimatedVisibility(
        visible = true,
        enter = fadeIn(animationSpec = tween(450)) + expandVertically(animationSpec = tween(450))
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(gradientBrush, RoundedCornerShape(24.dp))
                .padding(18.dp)
        ) {
            Column(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                horizontalAlignment = Alignment.Start
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .background(
                                color = Color.Black.copy(alpha = 0.45f),
                                shape = RoundedCornerShape(999.dp)
                            )
                            .padding(horizontal = 10.dp, vertical = 4.dp)
                    ) {
                        Text(
                            text = "${result.overallScore}/100 overall",
                            color = Color.White,
                            fontSize = 12.sp
                        )
                    }
                    Text(
                        text = "${result.passedCount} / ${result.totalAnalyzed} photos passed",
                        color = Color.White.copy(alpha = 0.75f),
                        fontSize = 11.sp
                    )
                }

                Text(
                    text = "Overall take",
                    color = Color.White.copy(alpha = 0.78f),
                    fontSize = 12.sp
                )

                Row(
                    verticalAlignment = Alignment.Top,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = "“",
                        color = Color.White.copy(alpha = 0.85f),
                        fontSize = 26.sp
                    )
                    Text(
                        text = result.roastSummary.ifBlank {
                            "You know you look good, and you're making sure nobody forgets it."
                        },
                        color = Color.White,
                        fontSize = 13.sp,
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }
    }
}

@Composable
private fun PhotoResultRow(
    photo: PhotoFeedbackUi,
    uri: Uri?
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(64.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(Color.Black)
        ) {
            if (uri != null) {
                AsyncImage(
                    model = uri,
                    contentDescription = null,
                    modifier = Modifier.matchParentSize(),
                    contentScale = ContentScale.Crop
                )
            }
        }
        Spacer(modifier = Modifier.width(12.dp))
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Text(
                text = "Score: ${photo.score}/10",
                color = Color.White,
                fontSize = 13.sp
            )
            Text(
                text = photo.brutalFeedback,
                color = Color.Gray,
                fontSize = 12.sp
            )
            if (photo.improvementTip.isNotBlank()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Tip: ${photo.improvementTip}",
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.92f),
                    fontSize = 12.sp,
                )
            }
        }
    }
}

@Composable
private fun HardResetResultView() {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 8.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Card(
            colors = CardDefaults.cardColors(containerColor = Color(0xFF2B1A1A)),
            shape = RoundedCornerShape(18.dp)
        ) {
            Column(
                modifier = Modifier.padding(18.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(
                    text = "0/12 Photos Passed. Your profile is flatlining.",
                    color = Color(0xFFFF8A80),
                    fontSize = 16.sp
                )
                Text(
                    text = "You aren't ugly, but your photography is. Do not use these photos.",
                    color = Color.White,
                    fontSize = 13.sp
                )
            }
        }

        Card(
            colors = CardDefaults.cardColors(containerColor = CardBg),
            shape = RoundedCornerShape(18.dp)
        ) {
            Column(
                modifier = Modifier.padding(18.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text(
                    text = "Blueprint Checklist",
                    color = Color.White,
                    fontSize = 15.sp
                )
                Text(
                    text = "1. Golden Hour Portrait.",
                    color = Color.Gray,
                    fontSize = 13.sp
                )
                Text(
                    text = "2. Candid Activity Shot.",
                    color = Color.Gray,
                    fontSize = 13.sp
                )
                Text(
                    text = "3. High-status Social Photo.",
                    color = Color.Gray,
                    fontSize = 13.sp
                )
            }
        }
    }
}

