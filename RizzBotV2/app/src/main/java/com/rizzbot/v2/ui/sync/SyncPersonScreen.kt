package com.rizzbot.v2.ui.sync

import android.graphics.BitmapFactory
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.rizzbot.v2.data.local.db.entity.PersonProfileEntity
import com.rizzbot.v2.domain.model.PersonProfileResult
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private val Pink = Color(0xFFE91E63)
private val DarkBg = Color(0xFF0F0F1A)
private val CardBg = Color(0xFF1A1A2E)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SyncPersonScreen(
    onBack: () -> Unit,
    viewModel: SyncPersonViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    val imagePickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetMultipleContents()
    ) { uris ->
        viewModel.addImages(uris)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Sync Person Profile", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = DarkBg,
                    titleContentColor = Color.White
                )
            )
        },
        containerColor = DarkBg
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            when (val result = state.result) {
                is PersonProfileResult.Loading -> {
                    Box(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 64.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            CircularProgressIndicator(color = Pink)
                            Spacer(modifier = Modifier.height(16.dp))
                            Text("Extracting profile info...", color = Color.White)
                            Text("This may take a few seconds", color = Color.Gray, fontSize = 12.sp)
                        }
                    }
                }
                is PersonProfileResult.Success -> {
                    ProfileResultCard(result = result, onDone = { viewModel.clearResult() })
                }
                is PersonProfileResult.Error -> {
                    Card(colors = CardDefaults.cardColors(containerColor = CardBg), shape = RoundedCornerShape(16.dp)) {
                        Column(
                            modifier = Modifier.padding(16.dp).fillMaxWidth(),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Text("Something went wrong", color = Color.White, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(result.message, color = Color.Gray, fontSize = 13.sp)
                            Spacer(modifier = Modifier.height(12.dp))
                            Button(
                                onClick = { viewModel.clearResult() },
                                colors = ButtonDefaults.buttonColors(containerColor = Pink)
                            ) { Text("Try Again") }
                        }
                    }
                }
                null -> {
                    // Instructions
                    Card(colors = CardDefaults.cardColors(containerColor = CardBg), shape = RoundedCornerShape(16.dp)) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("How it works", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                            Spacer(modifier = Modifier.height(8.dp))
                            StepRow("1", "Take screenshots of their dating profile")
                            StepRow("2", "Upload 1-5 screenshots here")
                            StepRow("3", "AI extracts their interests, bio & personality")
                            StepRow("4", "Get more personalized reply suggestions")
                        }
                    }

                    // Image picker
                    Text("Profile Screenshots", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    Text("Add 1-5 screenshots of their profile", color = Color.Gray, fontSize = 12.sp)

                    if (state.selectedImages.isEmpty()) {
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(120.dp)
                                .clickable { imagePickerLauncher.launch("image/*") },
                            colors = CardDefaults.cardColors(containerColor = CardBg),
                            shape = RoundedCornerShape(16.dp)
                        ) {
                            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    Icon(Icons.Default.AddPhotoAlternate, null, tint = Pink, modifier = Modifier.size(40.dp))
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
                                            Icon(Icons.Default.Image, null, tint = Color.Gray, modifier = Modifier.size(40.dp))
                                        }
                                        IconButton(
                                            onClick = { viewModel.removeImage(uri) },
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
                                            .clickable { imagePickerLauncher.launch("image/*") },
                                        colors = CardDefaults.cardColors(containerColor = CardBg),
                                        shape = RoundedCornerShape(12.dp)
                                    ) {
                                        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                            Icon(Icons.Default.Add, null, tint = Pink)
                                        }
                                    }
                                }
                            }
                        }

                        Button(
                            onClick = {
                                val bitmaps = state.selectedImages.mapNotNull { uri ->
                                    try {
                                        context.contentResolver.openInputStream(uri)?.use {
                                            BitmapFactory.decodeStream(it)
                                        }
                                    } catch (_: Exception) { null }
                                }
                                viewModel.syncProfile(bitmaps)
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = Pink),
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text("Sync Profile", modifier = Modifier.padding(8.dp), fontWeight = FontWeight.Bold)
                        }
                    }

                    // Saved profiles
                    if (state.savedProfiles.isNotEmpty()) {
                        Text("Saved Profiles", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                        state.savedProfiles.forEach { profile ->
                            SavedProfileCard(profile = profile, onDelete = { viewModel.deleteProfile(profile.id) })
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StepRow(number: String, text: String) {
    Row(modifier = Modifier.padding(vertical = 4.dp), verticalAlignment = Alignment.Top) {
        Box(
            modifier = Modifier
                .size(24.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(Pink.copy(alpha = 0.2f)),
            contentAlignment = Alignment.Center
        ) {
            Text(number, color = Pink, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(modifier = Modifier.width(12.dp))
        Text(text, color = Color.Gray, fontSize = 13.sp, modifier = Modifier.padding(top = 2.dp))
    }
}

@Composable
private fun ProfileResultCard(result: PersonProfileResult.Success, onDone: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = CardBg), shape = RoundedCornerShape(16.dp)) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier.size(48.dp).clip(CircleShape).background(Pink),
                    contentAlignment = Alignment.Center
                ) {
                    Text(result.name.take(1).uppercase(), color = Color.White, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(result.name, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                    if (result.age != null) {
                        Text("Age: ${result.age}", color = Color.Gray, fontSize = 13.sp)
                    }
                }
            }

            if (result.bio != null) {
                Spacer(modifier = Modifier.height(16.dp))
                Text("Bio", color = Pink, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                Spacer(modifier = Modifier.height(4.dp))
                Text(result.bio, color = Color.White, fontSize = 13.sp)
            }

            Spacer(modifier = Modifier.height(16.dp))
            Text("Interests", color = Pink, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            Spacer(modifier = Modifier.height(4.dp))
            result.interests.forEach { interest ->
                Row(modifier = Modifier.padding(vertical = 2.dp)) {
                    Text("  \u2022  ", color = Pink, fontSize = 13.sp)
                    Text(interest, color = Color.White, fontSize = 13.sp)
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
            Text("Personality Traits", color = Pink, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            Spacer(modifier = Modifier.height(4.dp))
            result.personalityTraits.forEach { trait ->
                Row(modifier = Modifier.padding(vertical = 2.dp)) {
                    Text("  \u2022  ", color = Pink, fontSize = 13.sp)
                    Text(trait, color = Color.White, fontSize = 13.sp)
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
            Text("Conversation Angles", color = Pink, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            Spacer(modifier = Modifier.height(4.dp))
            Text(result.fullExtraction, color = Color.White, fontSize = 13.sp)

            Spacer(modifier = Modifier.height(20.dp))
            Button(
                onClick = onDone,
                colors = ButtonDefaults.buttonColors(containerColor = Pink),
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("Done", modifier = Modifier.padding(4.dp))
            }
        }
    }
}

@Composable
private fun SavedProfileCard(profile: PersonProfileEntity, onDelete: () -> Unit) {
    val dateFormat = remember { SimpleDateFormat("MMM d, h:mm a", Locale.getDefault()) }
    Card(
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(12.dp)
    ) {
        Row(
            modifier = Modifier.padding(12.dp).fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier.size(40.dp).clip(CircleShape).background(Pink.copy(alpha = 0.3f)),
                contentAlignment = Alignment.Center
            ) {
                Text(profile.name.take(1).uppercase(), color = Pink, fontWeight = FontWeight.Bold, fontSize = 16.sp)
            }
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(profile.name, color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                Text(
                    profile.interests?.take(50) ?: "No interests",
                    color = Color.Gray,
                    fontSize = 11.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(dateFormat.format(Date(profile.createdAt)), color = Color.Gray, fontSize = 10.sp)
            }
            IconButton(onClick = onDelete, modifier = Modifier.size(32.dp)) {
                Icon(Icons.Default.Delete, "Delete", tint = Color.Gray, modifier = Modifier.size(18.dp))
            }
        }
    }
}
