package com.rizzbot.v2.ui.history

import android.content.Intent
import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.PullToRefreshDefaults
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.rizzbot.v2.data.remote.dto.HistoryItemResponse
import com.rizzbot.v2.ui.theme.NeonRed
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingError
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryScreen(
    onBack: () -> Unit,
    viewModel: HistoryViewModel = hiltViewModel()
) {
    val history by viewModel.history.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val isPullRefreshing by viewModel.isPullRefreshing.collectAsState()
    val pullRefreshState = rememberPullToRefreshState()
    val isLoadingMore by viewModel.isLoadingMore.collectAsState()
    val hasMore by viewModel.hasMore.collectAsState()
    val context = LocalContext.current
    val listState = rememberLazyListState()

    LaunchedEffect(listState) {
        snapshotFlow { listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index }
            .collect { lastVisibleIndex ->
                if (lastVisibleIndex != null && lastVisibleIndex >= history.size - 3 && hasMore && !isLoadingMore) {
                    viewModel.loadMore()
                }
            }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Reply History", fontWeight = FontWeight.Bold, color = NothingWhite)
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = "From screenshots & overlay",
                            color = NothingTextSecondary,
                            style = MaterialTheme.typography.labelSmall,
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = NothingWhite)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = NothingBlack,
                    titleContentColor = NothingWhite
                )
            )
        },
        containerColor = NothingBlack
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = isPullRefreshing,
            onRefresh = { viewModel.refresh() },
            state = pullRefreshState,
            indicator = {
                PullToRefreshDefaults.Indicator(
                    modifier = Modifier.align(Alignment.TopCenter),
                    isRefreshing = isPullRefreshing,
                    state = pullRefreshState,
                    containerColor = NothingSurface,
                    color = NothingWhite,
                )
            },
            modifier = Modifier.padding(padding).fillMaxSize(),
        ) {
        if (isLoading && history.isEmpty()) {
            HistorySkeleton(modifier = Modifier.fillMaxSize())
        } else if (history.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("\uD83D\uDCDD", fontSize = 56.sp)
                    Spacer(modifier = Modifier.height(NothingDimens.elementGap))
                    Text("No reply history yet", color = NothingWhite, style = MaterialTheme.typography.titleSmall)
                    Spacer(modifier = Modifier.height(NothingDimens.textGap))
                    Text("Your generated replies will appear here", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                    Spacer(modifier = Modifier.height(NothingDimens.sectionSpacing))
                    Button(
                        onClick = onBack,
                        colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
                        shape = RoundedCornerShape(NothingDimens.pillRadius)
                    ) {
                        Text("Back to home", color = NothingBlack, fontWeight = FontWeight.Bold)
                    }
                }
            }
        } else {
            LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = NothingDimens.screenPadding, vertical = NothingDimens.screenPadding),
                verticalArrangement = Arrangement.spacedBy(NothingDimens.sectionSpacing)
            ) {
                items(history, key = { it.id }) { entry ->
                    val dismissState = rememberSwipeToDismissBoxState(
                        confirmValueChange = { value ->
                            if (value == SwipeToDismissBoxValue.EndToStart) {
                                viewModel.deleteEntry(entry.id)
                                true
                            } else false
                        }
                    )

                    SwipeToDismissBox(
                        state = dismissState,
                        backgroundContent = {
                            val color by animateColorAsState(
                                if (dismissState.targetValue == SwipeToDismissBoxValue.EndToStart) NothingError
                                else Color.Transparent, label = "bg"
                            )
                            Box(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .background(color, RoundedCornerShape(NothingDimens.cardRadius))
                                    .padding(end = NothingDimens.screenPadding),
                                contentAlignment = Alignment.CenterEnd
                            ) {
                                Icon(Icons.Default.Delete, "Delete", tint = NothingWhite)
                            }
                        },
                        enableDismissFromStartToEnd = false
                    ) {
                        HistoryCard(entry = entry, onCopyReply = { reply, isHighValue ->
                            viewModel.copyReply(reply)
                            if (isHighValue) {
                                viewModel.incrementHighValueCopyCount { count ->
                                    if (count == 2) launchInAppReview(context)
                                }
                            }
                        })
                    }
                }

                if (isLoadingMore) {
                    item {
                        Box(
                            modifier = Modifier.fillMaxWidth().padding(NothingDimens.cardPadding),
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(24.dp),
                                color = NothingWhite
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
private fun HistoryCard(
    entry: HistoryItemResponse,
    onCopyReply: (String, Boolean) -> Unit
) {
    val context = LocalContext.current
    val dateFormat = remember { SimpleDateFormat("MMM d, h:mm a", Locale.getDefault()) }
    var expanded by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { expanded = !expanded },
        colors = CardDefaults.cardColors(containerColor = NothingSurface),
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
    ) {
        Column(modifier = Modifier.padding(NothingDimens.cardPadding)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    if (!entry.personName.isNullOrBlank()) {
                        Text(entry.personName, color = NothingWhite, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        "${entry.direction}${entry.customHint?.let { " \u2022 $it" } ?: ""}",
                        color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall,
                    )
                }
                Text(dateFormat.format(Date(entry.createdAt * 1000)), color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall)
            }

            Spacer(modifier = Modifier.height(NothingDimens.elementGap))

            if (!entry.userOrganicText.isNullOrBlank()) {
                Box(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    contentAlignment = Alignment.CenterEnd
                ) {
                    Surface(
                        color = NothingBorder,
                        shape = RoundedCornerShape(NothingDimens.cardRadius)
                    ) {
                        Text(
                            text = "You: ${entry.userOrganicText}",
                            color = NothingWhite,
                            style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.padding(horizontal = NothingDimens.elementGap, vertical = 8.dp)
                        )
                    }
                }
                Spacer(modifier = Modifier.height(NothingDimens.textGap))
            }

            val replies = entry.replies
            val displayReplies = if (expanded) replies else replies.take(1)

            displayReplies.forEachIndexed { index, reply ->
                if (reply.text.isNotBlank()) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                        verticalAlignment = Alignment.Top
                    ) {
                        Text(
                            "Vibe ${index + 1}",
                            color = NothingTextTertiary,
                            style = MaterialTheme.typography.labelSmall,
                            modifier = Modifier.width(60.dp)
                        )
                        Text(
                            reply.text,
                            color = NothingWhite,
                            style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.weight(1f),
                            maxLines = if (expanded) Int.MAX_VALUE else 2,
                            overflow = TextOverflow.Ellipsis
                        )
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            IconButton(
                                onClick = { onCopyReply(reply.text, entry.direction in listOf("Opener", "Ask Out", "Tease")) },
                                modifier = Modifier.size(28.dp)
                            ) {
                                Icon(Icons.Default.ContentCopy, "Copy", tint = NothingTextSecondary, modifier = Modifier.size(14.dp))
                            }
                            IconButton(
                                onClick = {
                                    val shareText = "${reply.text}\n\n\u2014 Generated by Cookd"
                                    val sendIntent = Intent(Intent.ACTION_SEND).apply {
                                        type = "text/plain"
                                        putExtra(Intent.EXTRA_TEXT, shareText)
                                    }
                                    context.startActivity(Intent.createChooser(sendIntent, null))
                                },
                                modifier = Modifier.size(28.dp)
                            ) {
                                Icon(Icons.Default.Share, "Share", tint = NothingTextSecondary, modifier = Modifier.size(14.dp))
                            }
                        }
                    }
                }
            }

            if (!expanded && replies.size > 1) {
                Text(
                    "Tap to see all ${replies.size} replies",
                    color = NothingTextTertiary,
                    style = MaterialTheme.typography.labelSmall,
                    modifier = Modifier.padding(top = NothingDimens.textGap)
                )
            }
        }
    }
}
