package com.rizzbot.v2.ui.profile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.material3.MaterialTheme
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
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingError
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileStrategyScreen(
    onBack: () -> Unit,
    viewModel: ProfileOptimizerViewModel = hiltViewModel()
) {
    val historyState by viewModel.historyState.collectAsState()
    val clipboard = LocalClipboardManager.current
    var detailBlueprint by remember { mutableStateOf<ProfileBlueprint?>(null) }

    LaunchedEffect(Unit) { viewModel.loadHistory() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Column {
                    Text(if (detailBlueprint != null) "Blueprint detail" else "Profile blueprints", fontWeight = FontWeight.SemiBold, color = NothingWhite)
                    if (detailBlueprint == null) Text("From Auto-Build Profile", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall)
                } },
                navigationIcon = { IconButton(onClick = { if (detailBlueprint != null) detailBlueprint = null else onBack() }) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = NothingWhite) } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = NothingBlack, titleContentColor = NothingWhite)
            )
        },
        containerColor = NothingBlack
    ) { padding ->
        val currentDetail = detailBlueprint
        if (currentDetail != null) {
            BlueprintDetailView(blueprint = currentDetail, modifier = Modifier.padding(padding), onCopy = { text -> clipboard.setText(AnnotatedString(text)) })
        } else {
            BlueprintHistoryListView(historyState = historyState, modifier = Modifier.padding(padding), onBlueprintClick = { detailBlueprint = it }, onRetry = { viewModel.loadHistory() })
        }
    }
}

@Composable
private fun BlueprintHistoryListView(historyState: BlueprintHistoryState, modifier: Modifier = Modifier, onBlueprintClick: (ProfileBlueprint) -> Unit, onRetry: () -> Unit) {
    when (historyState) {
        is BlueprintHistoryState.Idle, is BlueprintHistoryState.Loading -> Box(modifier = modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Text("Loading\u2026", color = NothingTextSecondary, style = MaterialTheme.typography.bodyMedium) }
        is BlueprintHistoryState.Success -> {
            if (historyState.blueprints.isEmpty()) {
                Box(modifier = modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Text("No blueprints yet.", color = NothingTextSecondary, style = MaterialTheme.typography.bodyMedium) }
            } else {
                LazyColumn(modifier = modifier.fillMaxSize(), contentPadding = PaddingValues(NothingDimens.screenPadding), verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)) {
                    items(items = historyState.blueprints.sortedByDescending { it.createdAt }, key = { it.id }) { blueprint ->
                        Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.fillMaxWidth().clickable { onBlueprintClick(blueprint) }) {
                            Column(modifier = Modifier.padding(NothingDimens.cardPadding)) {
                                Text(blueprint.overallTheme, color = NothingWhite, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, maxLines = 2, overflow = TextOverflow.Ellipsis)
                                Spacer(modifier = Modifier.height(NothingDimens.textGap))
                                Text("${blueprint.slots.size} photos", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                }
            }
        }
        is BlueprintHistoryState.Error -> {
            Column(modifier = modifier.fillMaxSize().padding(NothingDimens.screenPadding), verticalArrangement = Arrangement.Center, horizontalAlignment = Alignment.CenterHorizontally) {
                Text(historyState.message, color = NothingError, style = MaterialTheme.typography.bodySmall)
                Spacer(modifier = Modifier.height(NothingDimens.elementGap))
                Button(onClick = onRetry, colors = ButtonDefaults.buttonColors(containerColor = NothingWhite), shape = RoundedCornerShape(NothingDimens.pillRadius)) { Text("Try again", color = NothingBlack, fontWeight = FontWeight.SemiBold) }
            }
        }
    }
}

@Composable
private fun BlueprintDetailView(blueprint: ProfileBlueprint, modifier: Modifier = Modifier, onCopy: (String) -> Unit) {
    LazyColumn(modifier = modifier.fillMaxSize(), contentPadding = PaddingValues(NothingDimens.screenPadding), verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)) {
        item { Text(blueprint.overallTheme, color = NothingWhite, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold) }
        items(items = blueprint.slots.sortedBy { it.slotNumber }, key = { it.id }) { slot ->
            Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(NothingDimens.cardPadding)) {
                    Text("Slot ${slot.slotNumber} \u2014 ${slot.role}", color = NothingWhite, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleSmall)
                    if (slot.imageUrl.isNotBlank()) { Spacer(modifier = Modifier.height(NothingDimens.textGap)); AsyncImage(model = slot.imageUrl, contentDescription = null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxWidth().aspectRatio(4f / 5f).clip(RoundedCornerShape(NothingDimens.cardRadius))) }
                    if (slot.caption.isNotBlank()) { Spacer(modifier = Modifier.height(NothingDimens.textGap)); Text(slot.caption, color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall) }
                    if (slot.hingePrompt.isNotBlank()) { Spacer(modifier = Modifier.height(NothingDimens.textGap)); Text("Hinge: ${slot.hingePrompt}", color = NothingWhite, style = MaterialTheme.typography.labelSmall) }
                    if (slot.aislePrompt.isNotBlank()) { Spacer(modifier = Modifier.height(NothingDimens.textGap)); Text("Aisle: ${slot.aislePrompt}", color = NothingWhite, style = MaterialTheme.typography.labelSmall) }
                }
            }
        }
        if (blueprint.bio.isNotBlank()) {
            item {
                Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(NothingDimens.cardPadding)) {
                        Text("Bio", color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall)
                        Spacer(modifier = Modifier.height(NothingDimens.textGap))
                        Text(blueprint.bio, color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
    }
}
