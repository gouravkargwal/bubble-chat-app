package com.rizzbot.v2.ui.profile

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Article
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Cached
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage
import com.rizzbot.v2.ui.theme.NeonRed
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite
import com.rizzbot.v2.util.HapticHelper
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileOptimizerScreen(
    onBack: () -> Unit,
    onViewStrategy: () -> Unit = {},
    viewModel: ProfileOptimizerViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val selectedLanguage by viewModel.selectedLanguage.collectAsState()
    val clipboardManager = LocalClipboardManager.current
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Auto-Build Profile", fontWeight = FontWeight.SemiBold, color = NothingWhite) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = NothingWhite) } },
                actions = { IconButton(onClick = onViewStrategy) { Icon(Icons.Filled.Article, contentDescription = "Saved blueprints", tint = NothingWhite) } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = NothingBlack, titleContentColor = NothingWhite)
            )
        },
        containerColor = NothingBlack,
        snackbarHost = { SnackbarHost(snackbarHostState) },
    ) { padding ->
        Box(modifier = Modifier.padding(padding).fillMaxSize().background(NothingBlack)) {
            when (val s = state) {
                is OptimizerState.Idle -> IdleOptimizerCard(selectedLanguage = selectedLanguage, onLanguageSelected = { viewModel.setLanguage(it) }, onGenerate = { viewModel.generateBlueprint() })
                is OptimizerState.Loading -> LoadingState()
                is OptimizerState.Success -> SuccessState(blueprint = s.blueprint, selectedLanguage = selectedLanguage, onLanguageSelected = { viewModel.setLanguage(it) }, onCopy = { text -> clipboardManager.setText(AnnotatedString(text)); HapticHelper(context).successTap(); scope.launch { snackbarHostState.showSnackbar("Copied") } }, onRecalibrate = { viewModel.generateBlueprint() }, onViewStrategy = onViewStrategy)
                is OptimizerState.Error -> ErrorState(message = s.message, selectedLanguage = selectedLanguage, onLanguageSelected = { viewModel.setLanguage(it) }, onRetry = { viewModel.generateBlueprint() }, onBackToIdle = { viewModel.reset() })
            }
        }
    }
}

@Composable
private fun IdleOptimizerCard(selectedLanguage: String, onLanguageSelected: (String) -> Unit, onGenerate: () -> Unit) {
    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).navigationBarsPadding().padding(NothingDimens.screenPadding), horizontalAlignment = Alignment.CenterHorizontally) {
        Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(NothingDimens.cardPadding), verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)) {
                Text("Uses your audited photos to produce slot order, captions, and cross-app prompts.", color = NothingTextSecondary, style = MaterialTheme.typography.bodyMedium)
                Text("How it works", color = NothingWhite, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleSmall)
                Text("\u2022 Pulls from photos you've already run through Photo Audit", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                Text("\u2022 Orders slots using scores and feedback", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                Text("\u2022 Writes captions and prompts in your chosen language", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                Button(onClick = onGenerate, modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = NothingWhite), shape = RoundedCornerShape(NothingDimens.pillRadius)) {
                    Text("Generate My Profile Blueprint", color = NothingBlack, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun LoadingState() {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)) {
            CircularProgressIndicator(color = NothingWhite, strokeWidth = 3.dp)
            Text("Analyzing your best angles...", color = NothingTextSecondary, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun SuccessState(blueprint: ProfileBlueprint, selectedLanguage: String, onLanguageSelected: (String) -> Unit, onCopy: (String) -> Unit, onRecalibrate: () -> Unit, onViewStrategy: () -> Unit) {
    LazyColumn(modifier = Modifier.fillMaxSize().navigationBarsPadding().padding(horizontal = NothingDimens.screenPadding), verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap), contentPadding = PaddingValues(top = NothingDimens.elementGap, bottom = 40.dp)) {
        item {
            Text(blueprint.overallTheme, color = NothingWhite, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
            TextButton(onClick = onViewStrategy, modifier = Modifier.fillMaxWidth()) { Text("View Blueprints & History", color = NothingTextSecondary, fontWeight = FontWeight.SemiBold) }
        }
        items(items = blueprint.slots.sortedBy { it.slotNumber }, key = { it.slotNumber }) { slot ->
            SlotCard(slot = slot, onCopy = onCopy)
        }
        item {
            TextButton(onClick = onRecalibrate, modifier = Modifier.fillMaxWidth()) { Text("Recalibrate", color = NothingTextSecondary) }
        }
    }
}

@Composable
private fun SlotCard(slot: OptimizedSlot, onCopy: (String) -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(NothingDimens.cardPadding), verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)) {
            Text("Slot ${slot.slotNumber}: ${slot.role}", color = NothingWhite, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleSmall)
            if (slot.imageUrl.isNotBlank()) {
                AsyncImage(model = slot.imageUrl, contentDescription = null, modifier = Modifier.fillMaxWidth().aspectRatio(0.75f).clip(RoundedCornerShape(NothingDimens.cardRadius)))
            }
            Text(slot.caption, color = NothingWhite, style = MaterialTheme.typography.bodyMedium)
            if (slot.hingePrompt.isNotBlank()) {
                Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder)) {
                    Row(modifier = Modifier.padding(NothingDimens.cardPadding).fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text("Hinge", color = NothingWhite, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.labelSmall)
                        IconButton(onClick = { onCopy(slot.hingePrompt) }, modifier = Modifier.size(28.dp)) { Icon(Icons.Default.ContentCopy, "Copy", tint = NothingTextSecondary, modifier = Modifier.size(16.dp)) }
                    }
                    Text(slot.hingePrompt, color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = NothingDimens.cardPadding, bottom = NothingDimens.cardPadding))
                }
            }
            if (slot.aislePrompt.isNotBlank()) {
                Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder)) {
                    Row(modifier = Modifier.padding(NothingDimens.cardPadding).fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text("Aisle", color = NothingWhite, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.labelSmall)
                        IconButton(onClick = { onCopy(slot.aislePrompt) }, modifier = Modifier.size(28.dp)) { Icon(Icons.Default.ContentCopy, "Copy", tint = NothingTextSecondary, modifier = Modifier.size(16.dp)) }
                    }
                    Text(slot.aislePrompt, color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(start = NothingDimens.cardPadding, bottom = NothingDimens.cardPadding))
                }
            }
        }
    }
}

@Composable
private fun ErrorState(message: String, selectedLanguage: String, onLanguageSelected: (String) -> Unit, onRetry: () -> Unit, onBackToIdle: () -> Unit) {
    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).navigationBarsPadding().padding(NothingDimens.screenPadding), horizontalAlignment = Alignment.CenterHorizontally) {
        Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(NothingDimens.cardPadding), verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)) {
                Text("Couldn't generate a blueprint", color = NothingWhite, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleSmall)
                Text(message, color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall)
                Button(onClick = onRetry, colors = ButtonDefaults.buttonColors(containerColor = NothingWhite), shape = RoundedCornerShape(NothingDimens.pillRadius)) { Text("Try Again", color = NothingBlack, fontWeight = FontWeight.SemiBold) }
            }
        }
    }
}
