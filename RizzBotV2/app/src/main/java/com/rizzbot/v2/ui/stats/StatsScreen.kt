package com.rizzbot.v2.ui.stats

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.rizzbot.v2.domain.model.UserPreferences
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
fun StatsScreen(onBack: () -> Unit, viewModel: StatsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Your Stats", fontWeight = FontWeight.Bold, color = NothingWhite) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = NothingWhite) } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = NothingBlack, titleContentColor = NothingWhite)
            )
        },
        containerColor = NothingBlack
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).padding(NothingDimens.screenPadding)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)) {
                Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.weight(1f)) {
                    Column(modifier = Modifier.padding(NothingDimens.cardPadding), horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("Rizz Score", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                        val copyRate = if (state.totalGenerated > 0) ((state.totalCopied.toFloat() / state.totalGenerated) * 100).toInt() else 0
                        Text("$copyRate%", color = NothingWhite, fontWeight = FontWeight.ExtraBold, style = MaterialTheme.typography.displayMedium)
                    }
                }
                Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.weight(1f)) {
                    Column(modifier = Modifier.padding(NothingDimens.cardPadding), horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("Conversations", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                        Text("${state.totalConversationsInfluenced}", color = NothingWhite, fontWeight = FontWeight.ExtraBold, style = MaterialTheme.typography.displayMedium)
                    }
                }
            }

            Spacer(modifier = Modifier.height(NothingDimens.elementGap))

            Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(NothingDimens.cardPadding)) {
                    Text("Personality Breakdown", color = NothingWhite, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleSmall)
                    if (state.preferences.hasEnoughData && state.preferences.vibeBreakdown.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(NothingDimens.elementGap))
                        state.preferences.vibeBreakdown.entries.sortedByDescending { it.value }.forEach { (vibe, percentage) ->
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(vibe, color = NothingWhite, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
                                Text("${(percentage * 100).toInt()}%", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                            }
                            Spacer(modifier = Modifier.height(NothingDimens.textGap))
                            LinearProgressIndicator(progress = { percentage.coerceIn(0f, 1f) }, modifier = Modifier.fillMaxWidth().height(4.dp).clip(RoundedCornerShape(2.dp)), color = NothingWhite, trackColor = NothingBorder)
                            Spacer(modifier = Modifier.height(NothingDimens.textGap))
                        }
                    } else {
                        Spacer(modifier = Modifier.height(NothingDimens.textGap))
                        Text("Not enough data yet", color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }

            Spacer(modifier = Modifier.height(NothingDimens.elementGap))

            Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(NothingDimens.cardPadding)) {
                    Text("Linguistic Fingerprint", color = NothingWhite, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.titleSmall)
                    if (state.preferences.hasEnoughData && state.preferences.topSlang.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(NothingDimens.textGap))
                        state.preferences.topSlang.forEach { word ->
                            Box(modifier = Modifier.clip(RoundedCornerShape(NothingDimens.pillRadius)).background(NothingBorder).padding(horizontal = NothingDimens.elementGap, vertical = 6.dp)) {
                                Text(word, color = NothingWhite, style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    } else {
                        Spacer(modifier = Modifier.height(NothingDimens.textGap))
                        Text("Not enough data yet", color = NothingTextSecondary, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
    }
}
