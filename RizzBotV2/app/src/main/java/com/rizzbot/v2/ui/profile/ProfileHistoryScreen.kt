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
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.SubcomposeAsyncImage
import coil.compose.SubcomposeAsyncImageContent
import coil.compose.AsyncImagePainter
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingError
import com.rizzbot.v2.ui.theme.NothingSuccess
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.PullToRefreshDefaults
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.hilt.navigation.compose.hiltViewModel

// ── Data model (used by ViewModel) ──
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
    viewModel: ProfileHistoryViewModel = hiltViewModel(),
) {
    val auditsState = viewModel.audits.collectAsState()
    val isLoadingState = viewModel.isLoadingState.collectAsState()
    val listState = rememberLazyListState()
    val pullRefreshState = rememberPullToRefreshState()

    val shouldLoadMore = remember { derivedStateOf { val layoutInfo = listState.layoutInfo; val lastVisibleIndex = layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: -1; lastVisibleIndex >= auditsState.value.size - 3 && !isLoadingState.value } }
    LaunchedEffect(shouldLoadMore) { snapshotFlow { shouldLoadMore.value }.collect { if (it) viewModel.fetchNextPage() } }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Photo Audit History", color = NothingWhite) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = NothingWhite) } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = NothingBlack, titleContentColor = NothingWhite)
            )
        },
        containerColor = NothingBlack
    ) { padding ->
        if (isLoadingState.value && auditsState.value.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Text("Loading\u2026", color = NothingTextSecondary) }
        } else if (auditsState.value.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize().padding(NothingDimens.cardPadding), contentAlignment = Alignment.Center) { Text("No audits yet.", color = NothingTextSecondary, style = MaterialTheme.typography.bodyMedium) }
        } else {
            LazyColumn(
                state = listState,
                modifier = Modifier.padding(padding).fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap),
                contentPadding = PaddingValues(NothingDimens.screenPadding)
            ) {
                items(auditsState.value, key = { it.id }) { audit ->
                    Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.fillMaxWidth()) {
                        Column {
                            if (audit.imageUrl.isBlank()) {
                                Box(modifier = Modifier.fillMaxWidth().aspectRatio(0.75f).background(NothingSurface), contentAlignment = Alignment.Center) { Text("Image unavailable", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall) }
                            } else {
                                SubcomposeAsyncImage(model = audit.imageUrl, contentDescription = "Audited Photo", modifier = Modifier.fillMaxWidth(), contentScale = ContentScale.FillWidth) {
                                    val state = painter.state
                                    if (state is AsyncImagePainter.State.Loading || state is AsyncImagePainter.State.Error) Box(modifier = Modifier.fillMaxWidth().aspectRatio(0.75f).background(NothingBorder))
                                    else SubcomposeAsyncImageContent(modifier = Modifier.wrapContentHeight())
                                }
                            }
                            HorizontalDivider(color = NothingBorder, thickness = NothingDimens.borderThickness)
                            Column(modifier = Modifier.padding(NothingDimens.cardPadding), verticalArrangement = Arrangement.spacedBy(NothingDimens.textGap)) {
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                    Text("Score: ${audit.score}/10", color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall)
                                    val tierColor = when (audit.tier.uppercase()) { "GOD_TIER" -> NothingSuccess; "FILLER" -> NothingTextSecondary; "GRAVEYARD" -> NothingError; else -> NothingTextTertiary }
                                    Box(modifier = Modifier.clip(RoundedCornerShape(6.dp)).background(tierColor.copy(alpha = 0.1f)).padding(horizontal = 8.dp, vertical = 4.dp)) { Text(formatAuditTierLabel(audit.tier), color = tierColor, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.SemiBold) }
                                }
                                Text(audit.brutalFeedback, color = NothingWhite, style = MaterialTheme.typography.bodySmall)
                                Text(audit.improvementTip, color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun formatAuditTierLabel(raw: String): String = when (raw.uppercase()) { "GOD_TIER" -> "Top pick"; "FILLER" -> "Decent"; "GRAVEYARD" -> "Replace"; else -> raw }
