package com.rizzbot.v2.ui.profile

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.snapshotFlow
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.SubcomposeAsyncImage
import coil.compose.SubcomposeAsyncImageContent
import coil.compose.AsyncImagePainter
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.hilt.navigation.compose.hiltViewModel

data class HistoryItem(
    val id: String,
    val imageUrl: String,
    val score: Int,
    val tier: String,
    val brutalFeedback: String,
    val improvementTip: String,
    val createdAt: Long,
    val archetypeTitle: String,
    val roastSummary: String,
    val shareCardColor: String,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileHistoryScreen(
    onBack: () -> Unit,
    onNavigateToOptimizer: () -> Unit = {},
    viewModel: ProfileHistoryViewModel = hiltViewModel(),
) {
    val auditsState = viewModel.audits.collectAsState()
    val isLoadingState = viewModel.isLoadingState.collectAsState()
    val isSharingState = viewModel.isSharingState.collectAsState()
    val listState = rememberLazyListState()

    // Detect scroll near bottom and load more
    val shouldLoadMore = remember {
        derivedStateOf {
            val layoutInfo = listState.layoutInfo
            val lastVisibleIndex = layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: -1
            val totalItems = auditsState.value.size
            lastVisibleIndex >= totalItems - 3 && !isLoadingState.value
        }
    }

    LaunchedEffect(shouldLoadMore) {
        snapshotFlow { shouldLoadMore.value }
            .collect { shouldLoad ->
                if (shouldLoad) {
                    viewModel.fetchNextPage()
                }
            }
    }


    val darkBg = Color(0xFF0F0F1A)
    val cardBg = Color(0xFF1A1A2E)

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Photo Audit History",
                        fontSize = 18.sp,
                        color = Color.White,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.White,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = darkBg,
                    titleContentColor = Color.White,
                ),
            )
        },
        containerColor = darkBg,
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = isLoadingState.value && auditsState.value.isNotEmpty(),
            onRefresh = { viewModel.refresh() },
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
        ) {
            if (isLoadingState.value && auditsState.value.isEmpty()) {
                AuditHistorySkeletonFeed()
            } else if (auditsState.value.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "No audits yet. Run a Photo Audit to see history here.",
                        color = Color(0xFF8080A0),
                        fontSize = 14.sp,
                    )
                }
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(24.dp),
                    contentPadding = PaddingValues(16.dp)
                ) {
                    items(auditsState.value, key = { it.id }) { audit ->
                        AuditHistoryCard(
                            audit = audit,
                            isSharing = isSharingState.value,
                            onShare = { viewModel.shareLatestRoast() },
                            onDelete = { viewModel.deletePhoto(audit.id) }
                        )
                    }

                    // Loading indicator at bottom when loading more
                    if (isLoadingState.value) {
                        item {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(16.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(24.dp),
                                    color = Color.White
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun AuditHistoryCard(
    audit: HistoryItem,
    isSharing: Boolean,
    onShare: () -> Unit,
    onDelete: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, Color(0xFF252542))
    ) {
        Column {
            // Photo with FillWidth to prevent cropping
            SubcomposeAsyncImage(
                model = audit.imageUrl,
                contentDescription = "Audited Photo",
                modifier = Modifier.fillMaxWidth(),
                contentScale = ContentScale.FillWidth
            ) {
                val state = painter.state
                if (state is AsyncImagePainter.State.Loading || state is AsyncImagePainter.State.Error) {
                    // Show the skeleton box while downloading from the network
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .aspectRatio(0.75f) // Standard 3:4 portrait ratio to reserve space
                            .shimmerEffect()
                    )
                } else {
                    // The image is ready, show it with its natural height
                    SubcomposeAsyncImageContent(
                        modifier = Modifier.wrapContentHeight()
                    )
                }
            }
            
            // Premium accent divider
            HorizontalDivider(
                color = Color(0xFFE91E63),
                thickness = 2.dp
            )
            
            // Roasted Data
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Header Row: Score and Tier Badge
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Score: ${audit.score}/10",
                        color = Color.White,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold
                    )
                    
                    // Tier Badge
                    val tierColor = when (audit.tier.uppercase()) {
                        "GOD_TIER" -> Color(0xFFFFD700)
                        "FILLER" -> Color(0xFFFFEB3B)
                        "GRAVEYARD" -> Color(0xFFE57373)
                        else -> Color(0xFFB0BEC5)
                    }
                    
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(tierColor.copy(alpha = 0.2f))
                            .padding(horizontal = 10.dp, vertical = 4.dp)
                    ) {
                        Text(
                            text = audit.tier.replace("_", "-"),
                            color = tierColor,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }
                
                // Brutal Feedback
                Text(
                    text = audit.brutalFeedback,
                    color = Color.White,
                    fontSize = 14.sp
                )
                
                Spacer(modifier = Modifier.height(12.dp))
                
                // Improvement Tip
                Text(
                    text = audit.improvementTip,
                    color = Color.Gray,
                    fontSize = 13.sp
                )
                
                Spacer(modifier = Modifier.height(16.dp))

                // Action row: Delete only (share temporarily disabled)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = onDelete,
                        modifier = Modifier.weight(1f),
                        colors = androidx.compose.material3.ButtonDefaults.outlinedButtonColors(
                            contentColor = Color(0xFFFF5252)
                        ),
                        border = BorderStroke(1.dp, Color(0xFFFF5252))
                    ) {
                        Text(
                            text = "Delete",
                            fontSize = 14.sp
                        )
                    }
                }
            }
        }
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
private fun AuditHistorySkeletonFeed() {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(24.dp),
        contentPadding = PaddingValues(16.dp),
        userScrollEnabled = false
    ) {
        items(3) {
            AuditHistorySkeletonCard()
        }
    }
}

@Composable
private fun AuditHistorySkeletonCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, Color(0xFF252542))
    ) {
        Column {
            // Image Placeholder
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(0.75f)
                    .shimmerEffect()
            )
            
            // Divider
            HorizontalDivider(
                color = Color(0xFF252542),
                thickness = 2.dp
            )
            
            // Content Area
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Header (Score and Tier Badge)
                Box(
                    modifier = Modifier
                        .width(140.dp)
                        .height(20.dp)
                        .shimmerEffect()
                )
                
                Spacer(modifier = Modifier.height(16.dp))
                
                // Feedback Text Lines
                SkeletonTextLines(lines = 3)
                
                Spacer(modifier = Modifier.height(24.dp))
                
                // Button Placeholder
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .shimmerEffect()
                )
            }
        }
    }
}
