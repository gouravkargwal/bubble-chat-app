package com.rizzbot.v2.ui.profile

import android.graphics.BitmapFactory
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.rizzbot.v2.domain.model.DatingApp
import com.rizzbot.v2.domain.model.ProfileAnalysisResult

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileOptimizationScreen(
    onBack: () -> Unit,
    viewModel: ProfileOptimizationViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    val imagePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetMultipleContents()
    ) { uris ->
        uris.forEach { uri -> viewModel.addImage(uri) }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Optimize My Profile", fontWeight = FontWeight.Bold) },
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
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp)
        ) {
            when (val result = state.result) {
                is ProfileAnalysisResult.Success -> ProfileResultView(
                    result = result,
                    onDone = { viewModel.clearResult() }
                )
                is ProfileAnalysisResult.Loading -> {
                    Box(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 64.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            CircularProgressIndicator(color = Color(0xFFE91E63))
                            Spacer(modifier = Modifier.height(16.dp))
                            Text("Analyzing your profile...", color = Color.White)
                            Text("This may take 10-15 seconds", color = Color.Gray, fontSize = 12.sp)
                        }
                    }
                }
                is ProfileAnalysisResult.Error -> {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
                        shape = RoundedCornerShape(16.dp)
                    ) {
                        Column(modifier = Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                            Text("Something went wrong", color = Color.White, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(result.message, color = Color.Gray, fontSize = 13.sp)
                            Spacer(modifier = Modifier.height(12.dp))
                            Button(
                                onClick = { viewModel.clearResult() },
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63))
                            ) { Text("Try Again") }
                        }
                    }
                }
                null -> ProfileSetupView(
                    state = state,
                    onSelectApp = { viewModel.selectApp(it) },
                    onPickImages = { imagePickerLauncher.launch("image/*") },
                    onRemoveImage = { viewModel.removeImage(it) },
                    onAnalyze = {
                        val bitmaps = state.selectedImages.mapNotNull { uri ->
                            try {
                                context.contentResolver.openInputStream(uri)?.use {
                                    BitmapFactory.decodeStream(it)
                                }
                            } catch (e: Exception) { null }
                        }
                        viewModel.analyzeProfile(bitmaps)
                    },
                    onDeleteAnalysis = { /* Will be handled by backend */ }
                )
            }
        }
    }
}

@Composable
private fun ProfileSetupView(
    state: ProfileOptimizationState,
    onSelectApp: (DatingApp) -> Unit,
    onPickImages: () -> Unit,
    onRemoveImage: (Uri) -> Unit,
    onAnalyze: () -> Unit,
    onDeleteAnalysis: (Long) -> Unit
) {
    // Header
    Text("Get AI-powered feedback on your dating profile", color = Color.Gray, fontSize = 14.sp)
    Spacer(modifier = Modifier.height(20.dp))

    // Free tier notice
    Card(
        colors = CardDefaults.cardColors(
            containerColor = if (state.freeAnalysesRemaining > 0) Color(0xFF1B5E20).copy(alpha = 0.3f) else Color(0xFFE91E63).copy(alpha = 0.2f)
        ),
        shape = RoundedCornerShape(12.dp)
    ) {
        Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(if (state.freeAnalysesRemaining > 0) "\uD83C\uDF81" else "\uD83D\uDD12", fontSize = 20.sp)
            Spacer(modifier = Modifier.width(8.dp))
            Column {
                Text(
                    if (state.freeAnalysesRemaining > 0) "${state.freeAnalysesRemaining} free analysis this month"
                    else "Free analysis used this month",
                    color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.SemiBold
                )
                Text("Premium: unlimited analyses", color = Color.Gray, fontSize = 11.sp)
            }
        }
    }

    Spacer(modifier = Modifier.height(20.dp))

    // Dating app selector
    Text("Which app?", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
    Spacer(modifier = Modifier.height(8.dp))
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        DatingApp.entries.forEach { app ->
            FilterChip(
                selected = state.selectedApp == app,
                onClick = { onSelectApp(app) },
                label = { Text(app.displayName) },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = Color(0xFFE91E63),
                    selectedLabelColor = Color.White
                )
            )
        }
    }

    Spacer(modifier = Modifier.height(20.dp))

    // Image picker
    Text("Profile Screenshots", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
    Text("Add 1-5 screenshots of your profile", color = Color.Gray, fontSize = 12.sp)
    Spacer(modifier = Modifier.height(8.dp))

    if (state.selectedImages.isEmpty()) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .height(120.dp)
                .clickable { onPickImages() },
            colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
            shape = RoundedCornerShape(16.dp)
        ) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(Icons.Default.AddPhotoAlternate, contentDescription = null, tint = Color(0xFFE91E63), modifier = Modifier.size(40.dp))
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Tap to add screenshots", color = Color.Gray)
                }
            }
        }
    } else {
        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(state.selectedImages) { uri ->
                Card(
                    modifier = Modifier.size(100.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF252542)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Box(modifier = Modifier.fillMaxSize()) {
                        Box(
                            modifier = Modifier.fillMaxSize(),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(Icons.Default.Image, contentDescription = null, tint = Color.Gray, modifier = Modifier.size(40.dp))
                        }
                        IconButton(
                            onClick = { onRemoveImage(uri) },
                            modifier = Modifier.align(Alignment.TopEnd).size(24.dp)
                        ) {
                            Icon(Icons.Default.Close, "Remove", tint = Color.White, modifier = Modifier.size(16.dp))
                        }
                    }
                }
            }
            if (state.selectedImages.size < 5) {
                item {
                    Card(
                        modifier = Modifier
                            .size(100.dp)
                            .clickable { onPickImages() },
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            Icon(Icons.Default.Add, contentDescription = null, tint = Color(0xFFE91E63))
                        }
                    }
                }
            }
        }
    }

    Spacer(modifier = Modifier.height(24.dp))

    // Analyze button
    Button(
        onClick = onAnalyze,
        enabled = state.selectedImages.isNotEmpty() && !state.isAnalyzing && state.freeAnalysesRemaining > 0,
        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63)),
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp)
    ) {
        Text(
            if (state.freeAnalysesRemaining > 0) "Analyze My Profile" else "Upgrade to Premium",
            modifier = Modifier.padding(8.dp),
            fontWeight = FontWeight.Bold
        )
    }

    // Previous analyses will be loaded from backend when feature is ready
}

@Composable
private fun ProfileResultView(
    result: ProfileAnalysisResult.Success,
    onDone: () -> Unit
) {
    // Score header
    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier
                    .size(80.dp)
                    .clip(CircleShape)
                    .background(scoreColor(result.overallScore)),
                contentAlignment = Alignment.Center
            ) {
                Text("${result.overallScore}", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 24.sp)
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text("out of 10", color = Color.Gray, fontSize = 13.sp)
            Text(scoreLabel(result.overallScore), color = scoreColor(result.overallScore), fontWeight = FontWeight.Bold, fontSize = 16.sp)
        }
    }

    Spacer(modifier = Modifier.height(24.dp))

    // Photo Feedback
    FeedbackSection(
        title = "\uD83D\uDCF8 Photo Feedback",
        items = result.photoFeedback,
        color = Color(0xFF2196F3)
    )

    Spacer(modifier = Modifier.height(16.dp))

    // Bio Suggestions
    FeedbackSection(
        title = "\u270D\uFE0F Bio Suggestions",
        items = result.bioSuggestions,
        color = Color(0xFF9C27B0)
    )

    Spacer(modifier = Modifier.height(16.dp))

    // Prompt Suggestions
    FeedbackSection(
        title = "\uD83D\uDCAC Prompt Improvements",
        items = result.promptSuggestions,
        color = Color(0xFF4CAF50)
    )

    Spacer(modifier = Modifier.height(16.dp))

    // Red Flags
    if (result.redFlags.any { it != "None detected" }) {
        FeedbackSection(
            title = "\uD83D\uDEA9 Red Flags",
            items = result.redFlags,
            color = Color(0xFFEF5350)
        )
        Spacer(modifier = Modifier.height(16.dp))
    }

    // Summary
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Overall", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
            Spacer(modifier = Modifier.height(8.dp))
            Text(result.fullAnalysis, color = Color.White, fontSize = 14.sp)
        }
    }

    Spacer(modifier = Modifier.height(24.dp))

    Button(
        onClick = onDone,
        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63)),
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp)
    ) {
        Text("Done", modifier = Modifier.padding(8.dp))
    }

    Spacer(modifier = Modifier.height(16.dp))
}

@Composable
private fun FeedbackSection(
    title: String,
    items: List<String>,
    color: Color
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(title, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 15.sp)
            Spacer(modifier = Modifier.height(8.dp))
            items.forEach { item ->
                Row(modifier = Modifier.padding(vertical = 3.dp), verticalAlignment = Alignment.Top) {
                    Box(
                        modifier = Modifier
                            .padding(top = 6.dp)
                            .size(6.dp)
                            .clip(CircleShape)
                            .background(color)
                    )
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(item, color = Color.White, fontSize = 13.sp)
                }
            }
        }
    }
}

private fun scoreColor(score: Float): Color = when {
    score >= 8f -> Color(0xFF4CAF50)
    score >= 6f -> Color(0xFFFF9800)
    score >= 4f -> Color(0xFFFF5722)
    else -> Color(0xFFEF5350)
}

private fun scoreLabel(score: Float): String = when {
    score >= 9f -> "Outstanding!"
    score >= 8f -> "Great Profile"
    score >= 7f -> "Good, room to improve"
    score >= 5f -> "Average \u2014 let\u2019s fix that"
    else -> "Needs work"
}
