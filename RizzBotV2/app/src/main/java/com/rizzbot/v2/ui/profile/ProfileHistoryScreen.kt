package com.rizzbot.v2.ui.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.runtime.Composable
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ElevatedButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.hilt.navigation.compose.hiltViewModel

data class HistoryItem(
    val id: String,
    val imageUrl: String,
    val score: Int,
    val tier: String,
    val brutalFeedback: String,
    val improvementTip: String,
    val createdAt: Long,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileHistoryScreen(
    onBack: () -> Unit,
    onNavigateToOptimizer: () -> Unit = {},
    viewModel: ProfileHistoryViewModel = hiltViewModel(),
) {
    val itemsState = viewModel.items.collectAsState()
    val isLoadingState = viewModel.isLoading.collectAsState()

    val darkBg = Color(0xFF0F0F1A)
    val cardBg = Color(0xFF1A1A2E)

    val selectedPhoto: MutableState<HistoryItem?> = remember { mutableStateOf(null) }
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Profile Audit History",
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
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            ElevatedButton(
                onClick = onNavigateToOptimizer,
                modifier = Modifier
                    .fillMaxWidth()
                    .wrapContentHeight(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF252542),
                    contentColor = Color.White
                )
            ) {
                Icon(
                    imageVector = Icons.Default.AutoAwesome,
                    contentDescription = null,
                    tint = Color(0xFFFFD700),
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "✨ Auto-Build Masterpiece Profile",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }

            Text(
                text = "Tap a photo to see the full roast and improvement tip.",
                style = MaterialTheme.typography.bodyMedium,
                color = Color(0xFFB0B0D0),
                fontSize = 13.sp,
            )

            if (isLoadingState.value) {
                Box(
                    modifier = Modifier
                        .fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = Color.White)
                }
            } else if (itemsState.value.isEmpty()) {
                Spacer(modifier = Modifier.height(24.dp))
                Text(
                    text = "No audits yet. Run a Brutal Profile Audit to see history here.",
                    color = Color(0xFF8080A0),
                    fontSize = 14.sp,
                )
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    modifier = Modifier.fillMaxSize(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(itemsState.value, key = { it.id }) { photo ->
                        HistoryPhotoItem(
                            photo = photo,
                            cardBg = cardBg,
                            onClick = { selectedPhoto.value = photo },
                        )
                    }
                }
            }
        }

        val current = selectedPhoto.value
        if (current != null) {
            ModalBottomSheet(
                onDismissRequest = { selectedPhoto.value = null },
                sheetState = sheetState,
                containerColor = Color(0xFF141428),
            ) {
                HistoryDetailSheet(photo = current)
            }
        }
    }
}

@Composable
private fun HistoryPhotoItem(
    photo: HistoryItem,
    cardBg: Color,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = cardBg),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(110.dp),
        ) {
            AsyncImage(
                model = photo.imageUrl,
                contentDescription = null,
                modifier = Modifier
                    .fillMaxSize()
                    .clip(RoundedCornerShape(12.dp)),
                contentScale = ContentScale.Crop,
            )

            // Tier badge
            val badgeColor = when (photo.tier.uppercase()) {
                "GOD_TIER" -> Color(0xFFFFD700) // gold/green highlight
                "FILLER" -> Color(0xFFFFEB3B) // yellow
                "GRAVEYARD" -> Color(0xFFE57373) // red
                else -> Color(0xFFB0BEC5)
            }

            Box(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(6.dp)
                    .clip(RoundedCornerShape(999.dp))
                    .background(Color(0xCC000000)),
                contentAlignment = Alignment.Center,
            ) {
                RowWithScoreBadge(score = photo.score, badgeColor = badgeColor)
            }
        }
    }
}

@Composable
private fun RowWithScoreBadge(score: Int, badgeColor: Color) {
    androidx.compose.foundation.layout.Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
    ) {
        Box(
            modifier = Modifier
                .size(10.dp)
                .clip(CircleShape)
                .background(badgeColor),
        )
        Text(
            text = "$score/10",
            color = Color.White,
            fontSize = 11.sp,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
private fun HistoryDetailSheet(photo: HistoryItem) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .height(220.dp)
                .clip(RoundedCornerShape(16.dp)),
            color = Color.Black,
        ) {
            AsyncImage(
                model = photo.imageUrl,
                contentDescription = null,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop,
            )
        }

        Text(
            text = "${photo.score}/10",
            color = Color.White,
            fontSize = 28.sp,
            fontWeight = FontWeight.Bold,
        )
        Text(
            text = photo.tier,
            color = Color(0xFFFFD700),
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
        )

        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                text = "Brutal Feedback",
                color = Color(0xFFFFD700),
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = photo.brutalFeedback,
                color = Color(0xFFFFCDD2),
                fontSize = 14.sp,
                lineHeight = 20.sp,
            )
        }

        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                text = "Improvement Tip",
                color = Color(0xFF80CBC4),
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
            )
            Text(
                text = photo.improvementTip,
                color = Color(0xFFE0FFE8),
                fontSize = 14.sp,
                lineHeight = 20.sp,
                maxLines = 6,
                overflow = TextOverflow.Ellipsis,
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
    }
}

