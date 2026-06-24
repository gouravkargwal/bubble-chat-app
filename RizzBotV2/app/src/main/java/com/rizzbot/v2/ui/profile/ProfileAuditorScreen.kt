package com.rizzbot.v2.ui.profile

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
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
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import androidx.hilt.navigation.compose.hiltViewModel
import com.rizzbot.v2.domain.model.TierQuota
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingError
import com.rizzbot.v2.ui.theme.NothingSuccess
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite

// ── Data models (used by ViewModel and screens) ──

enum class PhotoTier { GOD_TIER, FILLER, GRAVEYARD }

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
        if (state.showPaywall) { onShowPaywall(); viewModel.dismissPaywall() }
    }

    val creditsRemaining = state.creditsRemaining
    val showIntro = state.result == null && !state.isLoading && !state.auditSessionStarted
    val flowStep = when { state.result != null -> 3; state.isLoading -> 2; state.selectedUris.isNotEmpty() -> 2; else -> 1 }

    val photoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickMultipleVisualMedia(maxPhotos)
    ) { uris -> viewModel.onPhotosSelected(uris) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Photo Audit", fontWeight = FontWeight.SemiBold, color = NothingWhite) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = NothingWhite) } },
                actions = { TextButton(onClick = onOpenPastPhotoAudits) { Text("Past audits", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall) } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = NothingBlack, titleContentColor = NothingWhite)
            )
        },
        bottomBar = {
            Surface(color = NothingBlack) {
                Column(modifier = Modifier.navigationBarsPadding().padding(horizontal = NothingDimens.screenPadding, vertical = NothingDimens.elementGap), verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)) {
                    when {
                        state.result != null -> OutlinedButton(onClick = { viewModel.startNewAudit() }, enabled = !state.isLoading, modifier = Modifier.fillMaxWidth().height(NothingDimens.minTouchTarget), shape = RoundedCornerShape(NothingDimens.pillRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder)) { Text("Start a new audit", color = NothingTextSecondary) }
                        showIntro -> Button(onClick = { viewModel.tryBeginAuditSession { onShowPaywall() } }, modifier = Modifier.fillMaxWidth().height(NothingDimens.minTouchTarget), colors = ButtonDefaults.buttonColors(containerColor = NothingWhite), shape = RoundedCornerShape(NothingDimens.pillRadius)) { Text("Run audit", color = NothingBlack) }
                        else -> Button(onClick = { viewModel.analyzePhotos() }, enabled = !state.isLoading && state.selectedUris.isNotEmpty(), modifier = Modifier.fillMaxWidth().height(NothingDimens.minTouchTarget), colors = ButtonDefaults.buttonColors(containerColor = NothingWhite), shape = RoundedCornerShape(NothingDimens.pillRadius)) {
                            if (state.isLoading) { CircularProgressIndicator(modifier = Modifier.size(16.dp), color = NothingBlack, strokeWidth = 2.dp); Spacer(modifier = Modifier.width(8.dp)); Text("Working\u2026", color = NothingBlack) }
                            else Text(if (state.selectedUris.isEmpty()) "Choose photos above" else "Submit for scoring (${state.selectedUris.size})", color = NothingBlack)
                        }
                    }
                }
            }
        },
        containerColor = NothingBlack
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize()) {
            Column(modifier = Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = NothingDimens.screenPadding, vertical = NothingDimens.elementGap), verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)) {
                if (showIntro) {
                    Text("Select up to $maxPhotos photos. Your plan limit is checked on tap.", color = NothingTextSecondary, style = MaterialTheme.typography.bodyMedium)
                }

                Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder)) {
                    Column(modifier = Modifier.padding(NothingDimens.cardPadding)) {
                        Text("Costs ${TierQuota.CREDIT_COST_AUDIT} credits per audit. You have $creditsRemaining credits.", color = NothingWhite, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleSmall)
                    }
                }

                if (!showIntro) {
                    state.error?.let { err ->
                        Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder)) {
                            Row(modifier = Modifier.padding(NothingDimens.cardPadding), verticalAlignment = Alignment.CenterVertically) {
                                Column(modifier = Modifier.weight(1f)) { Text("Something went wrong", color = NothingTextSecondary, style = MaterialTheme.typography.titleSmall); Text(err, color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall) }
                                Text("Dismiss", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall, modifier = Modifier.clip(RoundedCornerShape(8.dp)).clickable { viewModel.clearError() }.padding(8.dp))
                            }
                        }
                    }

                    when {
                        state.isLoading -> {
                            Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    CircularProgressIndicator(color = NothingWhite, strokeWidth = 3.dp)
                                    Spacer(modifier = Modifier.height(NothingDimens.elementGap))
                                    Text(state.auditProgress?.displayText ?: "Analyzing\u2026", color = NothingTextSecondary, style = MaterialTheme.typography.bodyMedium)
                                }
                            }
                        }
                        state.result != null -> {
                            val result = state.result
                            if (result != null) ProfileAuditResultContent(result = result, photoIdToUri = state.resultPhotoIdToUri)
                        }
                        else -> {
                            Text("Step 1 \u2014 Choose photos", color = NothingWhite, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                            Card(
                                modifier = Modifier.fillMaxWidth().clickable { if (!state.isLoading) photoPickerLauncher.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) },
                                colors = CardDefaults.cardColors(containerColor = NothingSurface),
                                shape = RoundedCornerShape(NothingDimens.cardRadius),
                                border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
                            ) {
                                Box(modifier = Modifier.fillMaxWidth().padding(vertical = 20.dp), contentAlignment = Alignment.Center) {
                                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                        Text(if (state.selectedUris.isEmpty()) "Tap to choose from gallery" else "Tap to add or replace photos", color = NothingWhite, style = MaterialTheme.typography.titleSmall)
                                        Text("${state.selectedUris.size} of $maxPhotos selected", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                                    }
                                }
                            }

                            if (state.selectedUris.isNotEmpty()) {
                                LazyVerticalGrid(columns = GridCells.Fixed(3), modifier = Modifier.fillMaxWidth().heightIn(min = 120.dp, max = 420.dp), verticalArrangement = Arrangement.spacedBy(8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    items(state.selectedUris, key = { it.toString() }) { uri ->
                                        AsyncImage(model = uri, contentDescription = "Photo", modifier = Modifier.aspectRatio(1f).clip(RoundedCornerShape(NothingDimens.cardRadius)).background(NothingBlack), contentScale = ContentScale.Crop)
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
private fun ProfileAuditResultContent(result: AuditResponseUi, photoIdToUri: Map<String, Uri>) {
    Column(modifier = Modifier.fillMaxWidth().padding(top = 8.dp), verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)) {
        Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder)) {
            Column(modifier = Modifier.padding(NothingDimens.cardPadding)) {
                Text("${result.overallScore}/100 overall", color = NothingWhite, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                Text(result.roastSummary, color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(top = NothingDimens.textGap))
            }
        }

        val grouped = result.photos.groupBy { it.tier }
        listOf(PhotoTier.GOD_TIER to "Best", PhotoTier.FILLER to "Decent", PhotoTier.GRAVEYARD to "Replace").forEach { (tier, label) ->
            grouped[tier]?.let { photos ->
                Text(label, color = NothingWhite, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleSmall)
                photos.forEach { photo -> PhotoResultRow(photo = photo, uri = photoIdToUri[photo.photoId]) }
            }
        }
    }
}

@Composable
private fun PhotoResultRow(photo: PhotoFeedbackUi, uri: Uri?) {
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(modifier = Modifier.size(64.dp).clip(RoundedCornerShape(10.dp)).background(NothingBlack)) {
            if (uri != null) AsyncImage(model = uri, contentDescription = null, modifier = Modifier.matchParentSize(), contentScale = ContentScale.Crop)
        }
        Spacer(modifier = Modifier.width(NothingDimens.elementGap))
        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("Score: ${photo.score}/10", color = NothingWhite, style = MaterialTheme.typography.bodySmall)
            Text(photo.brutalFeedback, color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
            if (photo.improvementTip.isNotBlank()) Text("Tip: ${photo.improvementTip}", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
        }
    }
}
