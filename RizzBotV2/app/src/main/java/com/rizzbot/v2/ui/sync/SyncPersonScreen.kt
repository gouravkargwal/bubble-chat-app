package com.rizzbot.v2.ui.sync

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.rizzbot.v2.domain.model.PersonProfileResult
import com.rizzbot.v2.ui.theme.NeonRed
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SyncPersonScreen(onBack: () -> Unit, viewModel: SyncPersonViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current
    val imagePickerLauncher = rememberLauncherForActivityResult(contract = ActivityResultContracts.GetMultipleContents()) { uris -> viewModel.addImages(uris) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Sync Person Profile", fontWeight = FontWeight.Bold, color = NothingWhite) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = NothingWhite) } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = NothingBlack, titleContentColor = NothingWhite)
            )
        },
        containerColor = NothingBlack
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).padding(NothingDimens.screenPadding), verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)) {
            when (val result = state.result) {
                is PersonProfileResult.Loading -> Box(modifier = Modifier.fillMaxWidth().padding(vertical = 64.dp), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) { CircularProgressIndicator(color = NothingWhite); Spacer(modifier = Modifier.height(NothingDimens.elementGap)); Text("Extracting profile info...", color = NothingWhite) }
                }
                is PersonProfileResult.Success -> ProfileResultCard(result = result, onDone = { viewModel.clearResult() })
                is PersonProfileResult.Error -> Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(NothingDimens.cardPadding).fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) { Text("Something went wrong", color = NothingWhite, fontWeight = FontWeight.Bold); Text(result.message, color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall) }
                }
                null -> {
                    Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder)) {
                        Column(modifier = Modifier.padding(NothingDimens.cardPadding), verticalArrangement = Arrangement.spacedBy(NothingDimens.textGap)) {
                            Text("How it works", color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall)
                            Text("1. Take screenshots of their profile", color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall)
                            Text("2. Upload 1-5 screenshots here", color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall)
                            Text("3. AI extracts their interests & personality", color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall)
                            Text("4. Get more personalized reply suggestions", color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                    Text("Profile Screenshots", color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall)
                    Card(
                        modifier = Modifier.fillMaxWidth().height(120.dp).clickable { imagePickerLauncher.launch("image/*") },
                        colors = CardDefaults.cardColors(containerColor = NothingSurface),
                        shape = RoundedCornerShape(NothingDimens.cardRadius),
                        border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
                    ) { Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Column(horizontalAlignment = Alignment.CenterHorizontally) { Icon(Icons.Default.AddPhotoAlternate, null, tint = NothingWhite, modifier = Modifier.size(40.dp)); Text("Tap to add screenshots", color = NothingTextSecondary) } } }
                }
            }
        }
    }
}

@Composable
private fun ProfileResultCard(result: PersonProfileResult.Success, onDone: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(NothingDimens.cardPadding), verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(modifier = Modifier.size(48.dp).clip(RoundedCornerShape(NothingDimens.cardRadius)).background(NothingWhite), contentAlignment = Alignment.Center) { Text(result.name.take(1).uppercase(), color = NothingBlack, fontWeight = FontWeight.Bold) }
                Spacer(modifier = Modifier.width(NothingDimens.elementGap))
                Column { Text(result.name, color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall); result.age?.let { Text("Age: $it", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall) } }
            }
            result.bio?.let { Text("Bio", color = NothingTextSecondary, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelSmall); Text(it, color = NothingWhite, style = MaterialTheme.typography.bodySmall) }
            Text("Interests", color = NothingTextSecondary, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelSmall)
            result.interests.forEach { Text("\u2022 $it", color = NothingWhite, style = MaterialTheme.typography.bodySmall) }
            Text("Personality Traits", color = NothingTextSecondary, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelSmall)
            result.personalityTraits.forEach { Text("\u2022 $it", color = NothingWhite, style = MaterialTheme.typography.bodySmall) }
            Text("Conversation Angles", color = NothingTextSecondary, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelSmall)
            Text(result.fullExtraction, color = NothingWhite, style = MaterialTheme.typography.bodySmall)
            Button(onClick = onDone, colors = ButtonDefaults.buttonColors(containerColor = NothingWhite), shape = RoundedCornerShape(NothingDimens.pillRadius), modifier = Modifier.fillMaxWidth()) { Text("Done", color = NothingBlack) }
        }
    }
}
