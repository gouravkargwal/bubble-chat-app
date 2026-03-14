package com.rizzbot.v2.ui.profile

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
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
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
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
import com.rizzbot.v2.ui.paywall.PaywallDialog
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
    val photos: List<PhotoFeedbackUi>
)

private val DarkBg = Color(0xFF0F0F1A)
private val CardBg = Color(0xFF1A1A2E)
private val WarningBg = Color(0xFFFFA726).copy(alpha = 0.18f)

@OptIn(ExperimentalMaterial3Api::class, ExperimentalFoundationApi::class)
@Composable
fun ProfileAuditorScreen(
    onBack: () -> Unit,
    onShowPaywall: () -> Unit = {},
    viewModel: ProfileAuditorViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val maxPhotos = state.maxPhotosPerAudit
    
    // Calculate if user can audit
    val isGodMode = state.tier == "premium" || state.tier == "god_mode"
    val hasAuditsLeft = state.weeklyAuditsUsed < state.profileAuditsPerWeek
    val canAudit = isGodMode || hasAuditsLeft

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
                        text = "Brutal Profile Auditor",
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
                Box(
                    modifier = Modifier
                        .navigationBarsPadding()
                        .padding(16.dp)
                ) {
                    Button(
                        onClick = {
                            if (!canAudit) {
                                onShowPaywall()
                            } else {
                                viewModel.analyzePhotos()
                            }
                        },
                        enabled = if (state.isLoading) {
                            false
                        } else if (!canAudit) {
                            true
                        } else {
                            state.selectedUris.isNotEmpty()
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(52.dp),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFFFFD700)
                        )
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.Center
                        ) {
                            if (state.isLoading) {
                                Text(
                                    text = "Analyzing...",
                                    color = Color.Black,
                                    fontSize = 15.sp
                                )
                            } else if (!canAudit) {
                                Icon(
                                    imageVector = Icons.Filled.Lock,
                                    contentDescription = null,
                                    tint = Color.Black,
                                    modifier = Modifier.size(16.dp)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    text = "Unlock Unlimited Audits",
                                    color = Color.Black,
                                    fontSize = 15.sp
                                )
                            } else {
                                Text(
                                    text = "Analyze Photos",
                                    color = Color.Black,
                                    fontSize = 15.sp
                                )
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
            // Warning banner
            Card(
                colors = CardDefaults.cardColors(containerColor = WarningBg),
                shape = RoundedCornerShape(16.dp)
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Filled.WarningAmber,
                        contentDescription = null,
                        tint = Color(0xFFFFA726),
                        modifier = Modifier.size(22.dp)
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(
                        text = "Warning: This AI is brutal. It will reject bad lighting, bathroom selfies, and cringe poses. Bring your thick skin.",
                        color = Color.White,
                        fontSize = 13.sp
                    )
                }
            }

            // Header copy
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(
                    text = "Upload Your Photos",
                    color = Color.White,
                    fontSize = 18.sp,
                    style = MaterialTheme.typography.titleMedium
                )
                Text(
                    text = "Pick up to ${maxPhotos} photos from your camera roll. We'll tell you which ones are GOD_TIER, FILLER, or belong in the graveyard.",
                    color = Color.Gray,
                    fontSize = 13.sp
                )
            }

            // Language selector chips
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
                            containerColor = if (isSelected) Color(0xFFFFD700) else CardBg
                        )
                    )
                }
            }

            // Picker card
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
                        .padding(vertical = 18.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = if (state.selectedUris.isEmpty()) "Tap to add photos" else "Add / Replace Photos",
                            color = Color.White,
                            fontSize = 14.sp
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "${state.selectedUris.size} of ${maxPhotos} selected",
                            color = Color.Gray,
                            fontSize = 12.sp
                        )
                    }
                }
            }

            // Use preserved URIs from result if available, otherwise map from selectedUris
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
                    ProfileAuditorSkeleton()
                }
                state.result != null -> {
                    val result = state.result
                    if (result != null) {
                        ProfileAuditResultContent(
                            result = result,
                            photoIdToUri = photoIdToUri
                        )
                    }
                }
                state.selectedUris.isNotEmpty() -> {
                    Text(
                        text = "Selected Photos",
                        color = Color.White,
                        fontSize = 14.sp
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
                                contentDescription = null,
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

            Spacer(modifier = Modifier.height(80.dp))
            }
        }
    }
    
    // Paywall Dialog
    if (state.showPaywall) {
        PaywallDialog(
            onDismiss = { viewModel.dismissPaywall() }
        )
    }
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
    if (result.isHardReset) {
        HardResetResultView()
        return
    }

    val godTier = result.photos.filter { it.tier == PhotoTier.GOD_TIER }
    val filler = result.photos.filter { it.tier == PhotoTier.FILLER }
    val graveyard = result.photos.filter { it.tier == PhotoTier.GRAVEYARD }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 8.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        if (godTier.isNotEmpty()) {
            Text(
                text = "🟢 GOD TIER (Use as Main)",
                color = Color(0xFF81C784),
                fontSize = 15.sp
            )
            godTier.forEach { photo ->
                PhotoResultRow(photo = photo, uri = photoIdToUri[photo.photoId])
            }
        }

        if (filler.isNotEmpty()) {
            Text(
                text = "🟡 THE FILLER (Use as Backups)",
                color = Color(0xFFFFF176),
                fontSize = 15.sp
            )
            filler.forEach { photo ->
                PhotoResultRow(photo = photo, uri = photoIdToUri[photo.photoId])
            }
        }

        if (graveyard.isNotEmpty()) {
            Text(
                text = "🔴 THE GRAVEYARD (Delete immediately)",
                color = Color(0xFFEF5350),
                fontSize = 15.sp
            )
            graveyard.forEach { photo ->
                PhotoResultRow(photo = photo, uri = photoIdToUri[photo.photoId])
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

