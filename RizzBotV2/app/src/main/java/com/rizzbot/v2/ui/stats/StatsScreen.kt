package com.rizzbot.v2.ui.stats

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.ExperimentalMaterialApi
import androidx.compose.material.pullrefresh.PullRefreshIndicator
import androidx.compose.material.pullrefresh.pullRefresh
import androidx.compose.material.pullrefresh.rememberPullRefreshState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect

@OptIn(ExperimentalMaterial3Api::class, ExperimentalMaterialApi::class)
@Composable
fun StatsScreen(
    onBack: () -> Unit,
    viewModel: StatsViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    var isRefreshing by remember { mutableStateOf(false) }
    
    // Auto-refresh when screen becomes visible
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        viewModel.refresh()
    }
    
    val pullRefreshState = rememberPullRefreshState(
        refreshing = isRefreshing,
        onRefresh = {
            isRefreshing = true
            viewModel.refresh()
            // Reset refreshing after a short delay (the actual data will update via flow)
            kotlinx.coroutines.GlobalScope.launch {
                kotlinx.coroutines.delay(1000)
                isRefreshing = false
            }
        }
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Your Stats", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF0F0F1A),
                    titleContentColor = Color.White
                )
            )
        },
        containerColor = Color(0xFF0F0F1A)
    ) { padding ->
        Box(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .pullRefresh(pullRefreshState)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp)
            ) {
            // Stats cards row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                StatCard(
                    emoji = "\u26A1",
                    value = "${state.totalGenerated}",
                    label = "Replies Generated",
                    modifier = Modifier.weight(1f)
                )
                StatCard(
                    emoji = "\uD83D\uDCCB",
                    value = "${state.totalCopied}",
                    label = "Replies Copied",
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Copy rate
            val copyRate = if (state.totalGenerated > 0) {
                ((state.totalCopied.toFloat() / state.totalGenerated) * 100).toInt()
            } else 0

            StatCard(
                emoji = "\uD83C\uDFAF",
                value = "$copyRate%",
                label = "Copy Rate",
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Rizz Profile section
            Text("Your Rizz Profile", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 20.sp)
            Spacer(modifier = Modifier.height(4.dp))

            if (state.preferences.hasEnoughData) {
                Text("Based on ${state.preferences.totalRatings} ratings", color = Color.Gray, fontSize = 12.sp)
                Spacer(modifier = Modifier.height(16.dp))

                // Vibe breakdown bars
                val vibeColors = mapOf(
                    "Flirty" to Color(0xFFE91E63),
                    "Witty" to Color(0xFF9C27B0),
                    "Smooth" to Color(0xFF2196F3),
                    "Bold" to Color(0xFFFF9800)
                )

                state.preferences.vibeBreakdown.entries
                    .sortedByDescending { it.value }
                    .forEach { (vibe, percentage) ->
                        VibeBar(
                            vibe = vibe,
                            percentage = percentage,
                            color = vibeColors[vibe] ?: Color(0xFFE91E63)
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                    }

                Spacer(modifier = Modifier.height(16.dp))

                // Preferred length
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("\uD83D\uDCCF", fontSize = 24.sp)
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            Text("Preferred Reply Length", color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                            Text(
                                state.preferences.preferredLength.name.lowercase().replaceFirstChar { it.uppercase() },
                                color = Color(0xFFE91E63), fontSize = 13.sp
                            )
                        }
                    }
                }

            } else {
                Spacer(modifier = Modifier.height(16.dp))
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text("\uD83D\uDD2E", fontSize = 40.sp)
                        Spacer(modifier = Modifier.height(12.dp))
                        Text("Not enough data yet", color = Color.White, fontWeight = FontWeight.SemiBold)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            "Rate ${20 - state.preferences.totalRatings} more replies to unlock your Rizz Profile",
                            color = Color.Gray,
                            fontSize = 13.sp,
                            textAlign = TextAlign.Center
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        LinearProgressIndicator(
                            progress = { state.preferences.totalRatings / 20f },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(6.dp)
                                .clip(RoundedCornerShape(3.dp)),
                            color = Color(0xFFE91E63),
                            trackColor = Color(0xFF252542)
                        )
                        Text(
                            "${state.preferences.totalRatings}/20 ratings",
                            color = Color.Gray,
                            fontSize = 11.sp,
                            modifier = Modifier.padding(top = 4.dp)
                        )
                    }
                }
            }
            
            PullRefreshIndicator(
                refreshing = isRefreshing,
                state = pullRefreshState,
                modifier = Modifier.align(Alignment.TopCenter),
                backgroundColor = Color(0xFF1A1A2E),
                contentColor = Color(0xFFE91E63)
            )
        }
    }
}

@Composable
private fun StatCard(
    emoji: String,
    value: String,
    label: String,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(emoji, fontSize = 28.sp)
            Spacer(modifier = Modifier.height(8.dp))
            Text(value, color = Color(0xFFE91E63), fontWeight = FontWeight.Bold, fontSize = 28.sp)
            Text(label, color = Color.Gray, fontSize = 12.sp)
        }
    }
}

@Composable
private fun VibeBar(
    vibe: String,
    percentage: Float,
    color: Color
) {
    val vibeEmojis = mapOf(
        "Flirty" to "\uD83D\uDD25",
        "Witty" to "\uD83D\uDE0F",
        "Smooth" to "\u2728",
        "Bold" to "\uD83D\uDCAA"
    )

    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                "${vibeEmojis[vibe] ?: "\uD83D\uDCAC"} $vibe",
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                "${(percentage * 100).toInt()}%",
                color = color,
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold
            )
        }
        Spacer(modifier = Modifier.height(4.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp)
                .clip(RoundedCornerShape(4.dp))
                .background(Color(0xFF252542))
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(percentage)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(4.dp))
                    .background(color)
            )
        }
    }
}
