package com.rizzbot.v2.ui.profile

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage
import com.rizzbot.v2.ui.theme.Pink

private val BgColor = Color(0xFF050510)
private val CardColor = Color(0xFF0D0D22)
private val Accent = Pink
private val TextPrimary = Color.White
private val TextSecondary = Color(0xFFB0B0D0)
private val TextMuted = Color(0xFF606080)
private val HingeColor = Color(0xFFFF6B6B)
private val AisleColor = Color(0xFF6BDDFF)

private fun formatBlueprintDateLine(createdAt: String): String {
    val t = createdAt.trim()
    if (t.length >= 10 && t[4] == '-' && t[7] == '-') return t.take(10)
    return try {
        java.time.Instant.parse(t).atZone(java.time.ZoneId.systemDefault()).toLocalDate().toString()
    } catch (_: Exception) {
        t.take(16).ifEmpty { "—" }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileStrategyScreen(
    onBack: () -> Unit,
    viewModel: ProfileOptimizerViewModel = hiltViewModel()
) {
    val historyState by viewModel.historyState.collectAsState()
    val clipboard = LocalClipboardManager.current

    // null = list view; non-null = detail view for that blueprint
    var detailBlueprint by remember { mutableStateOf<ProfileBlueprint?>(null) }

    LaunchedEffect(Unit) {
        viewModel.loadHistory()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = if (detailBlueprint != null) "Blueprint detail" else "Profile blueprints",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = TextPrimary
                        )
                        if (detailBlueprint == null) {
                            Text(
                                text = "From Auto-Build Profile",
                                color = TextMuted,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Normal
                            )
                        }
                    }
                },
                navigationIcon = {
                    IconButton(onClick = {
                        if (detailBlueprint != null) detailBlueprint = null else onBack()
                    }) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = TextPrimary
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = BgColor,
                    titleContentColor = TextPrimary
                )
            )
        },
        containerColor = BgColor
    ) { padding ->
        val currentDetail = detailBlueprint
        if (currentDetail != null) {
            BlueprintDetailView(
                blueprint = currentDetail,
                modifier = Modifier.padding(padding),
                onCopy = { text -> clipboard.setText(AnnotatedString(text)) }
            )
        } else {
            BlueprintHistoryListView(
                historyState = historyState,
                modifier = Modifier.padding(padding),
                onBlueprintClick = { blueprint -> detailBlueprint = blueprint },
                onRetry = { viewModel.loadHistory() }
            )
        }
    }
}

@Composable
private fun BlueprintHistoryListView(
    historyState: BlueprintHistoryState,
    modifier: Modifier = Modifier,
    onBlueprintClick: (ProfileBlueprint) -> Unit,
    onRetry: () -> Unit,
) {
    when (historyState) {
        is BlueprintHistoryState.Idle, is BlueprintHistoryState.Loading -> {
            Box(
                modifier = modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Text("Loading blueprints…", color = TextSecondary, fontSize = 14.sp)
            }
        }

        is BlueprintHistoryState.Success -> {
            if (historyState.blueprints.isEmpty()) {
                Box(
                    modifier = modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        "No blueprints yet.\nOpen Auto-Build Profile from Home to generate one.",
                        color = TextSecondary,
                        fontSize = 13.sp
                    )
                }
            } else {
                LazyColumn(
                    modifier = modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(
                        items = historyState.blueprints.sortedByDescending { it.createdAt },
                        key = { it.id }
                    ) { blueprint ->
                        val index = historyState.blueprints
                            .sortedByDescending { it.createdAt }
                            .indexOf(blueprint)
                        BlueprintListCard(
                            label = "Blueprint ${index + 1}",
                            blueprint = blueprint,
                            onClick = { onBlueprintClick(blueprint) }
                        )
                    }
                }
            }
        }

        is BlueprintHistoryState.Error -> {
            Column(
                modifier = modifier
                    .fillMaxSize()
                    .padding(24.dp),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(historyState.message, color = Color(0xFFFF6B6B), fontSize = 13.sp)
                Spacer(modifier = Modifier.height(16.dp))
                Button(
                    onClick = onRetry,
                    colors = ButtonDefaults.buttonColors(containerColor = Accent, contentColor = Color.Black)
                ) {
                    Text("Try again", fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}

@Composable
private fun BlueprintListCard(
    label: String,
    blueprint: ProfileBlueprint,
    onClick: () -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = CardColor),
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = label,
                color = Accent,
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = blueprint.overallTheme,
                color = TextPrimary,
                fontSize = 13.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "${blueprint.slots.size} photos · ${formatBlueprintDateLine(blueprint.createdAt)}",
                color = TextMuted,
                fontSize = 12.sp
            )
        }
    }
}

@Composable
private fun BlueprintDetailView(
    blueprint: ProfileBlueprint,
    modifier: Modifier = Modifier,
    onCopy: (String) -> Unit
) {
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 40.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Overall theme
        item {
            Text(
                text = blueprint.overallTheme,
                color = Accent,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                lineHeight = 20.sp
            )
        }

        // Photo slots
        items(
            items = blueprint.slots.sortedBy { it.slotNumber },
            key = { it.id }
        ) { slot ->
            SlotDetailCard(slot = slot, onCopy = onCopy)
        }

        // Bio section
        if (blueprint.bio.isNotBlank()) {
            item {
                HorizontalDivider(
                    color = Color.White.copy(alpha = 0.08f),
                    thickness = 0.5.dp
                )
                Spacer(modifier = Modifier.height(4.dp))
                BioCard(bio = blueprint.bio, onCopy = { onCopy(blueprint.bio) })
            }
        }
    }
}

@Composable
private fun SlotDetailCard(slot: OptimizedSlot, onCopy: (String) -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = CardColor),
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            // Slot header
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "Slot ${slot.slotNumber}",
                    color = Accent,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = slot.role,
                    color = TextSecondary,
                    fontSize = 12.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f)
                )
            }

            // Photo + caption
            if (slot.imageUrl.isNotBlank()) {
                Spacer(modifier = Modifier.height(10.dp))
                AsyncImage(
                    model = slot.imageUrl,
                    contentDescription = "Slot ${slot.slotNumber} photo",
                    contentScale = ContentScale.Crop,
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(4f / 5f)
                        .clip(RoundedCornerShape(8.dp))
                )
            }

            if (slot.caption.isNotBlank()) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = slot.caption,
                    color = TextPrimary,
                    fontSize = 13.sp,
                    lineHeight = 19.sp
                )
            }

            // Hinge prompt
            if (slot.hingePrompt.isNotBlank()) {
                Spacer(modifier = Modifier.height(10.dp))
                HorizontalDivider(color = Color.White.copy(alpha = 0.06f), thickness = 0.5.dp)
                Spacer(modifier = Modifier.height(10.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.Top
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Hinge",
                            color = HingeColor,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = slot.hingePrompt,
                            color = TextSecondary,
                            fontSize = 13.sp,
                            lineHeight = 19.sp
                        )
                    }
                    IconButton(
                        onClick = { onCopy(slot.hingePrompt) },
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(
                            Icons.Default.ContentCopy,
                            contentDescription = "Copy Hinge prompt",
                            tint = HingeColor,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }
            }

            // Aisle prompt
            if (slot.aislePrompt.isNotBlank()) {
                Spacer(modifier = Modifier.height(10.dp))
                HorizontalDivider(color = Color.White.copy(alpha = 0.06f), thickness = 0.5.dp)
                Spacer(modifier = Modifier.height(10.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.Top
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Aisle",
                            color = AisleColor,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = slot.aislePrompt,
                            color = TextSecondary,
                            fontSize = 13.sp,
                            lineHeight = 19.sp
                        )
                    }
                    IconButton(
                        onClick = { onCopy(slot.aislePrompt) },
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(
                            Icons.Default.ContentCopy,
                            contentDescription = "Copy Aisle prompt",
                            tint = AisleColor,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun BioCard(bio: String, onCopy: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = CardColor),
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Bio",
                    color = TextPrimary,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold
                )
                TextButton(
                    onClick = onCopy,
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp)
                ) {
                    Text(
                        text = "Copy",
                        color = Accent,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = bio,
                color = TextSecondary,
                fontSize = 14.sp,
                lineHeight = 21.sp
            )
        }
    }
}
