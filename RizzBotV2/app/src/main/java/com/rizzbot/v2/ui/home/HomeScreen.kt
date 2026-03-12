package com.rizzbot.v2.ui.home

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.LifecycleResumeEffect
import com.rizzbot.v2.domain.model.UsageState
import com.rizzbot.v2.domain.model.UserPreferences
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private val Pink = Color(0xFFE91E63)
private val DarkBg = Color(0xFF0F0F1A)
private val CardBg = Color(0xFF1A1A2E)
private val DividerColor = Color(0xFF252542)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    onNavigateToSettings: () -> Unit,
    onNavigateToHistory: () -> Unit,
    onNavigateToStats: () -> Unit,
    viewModel: HomeViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    LifecycleResumeEffect(Unit) {
        viewModel.refreshPermissionStatus()
        onPauseOrDispose {}
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Cookd", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = onNavigateToSettings) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings", tint = Color.White)
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
            // 0. TRIAL EXPIRY BANNER
            if (state.usage.tier != "free" && state.usage.trialDaysRemaining in 0..3) {
                TrialBanner(daysRemaining = state.usage.trialDaysRemaining)
            }

            // 1. HERO CARD — Service Toggle
            HeroCard(
                isEnabled = state.isServiceEnabled,
                hasPermission = state.hasOverlayPermission,
                onToggle = { viewModel.toggleService(it) },
                onGrantPermission = {
                    context.startActivity(
                        Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:${context.packageName}"))
                    )
                }
            )

            // 1.5 USAGE QUOTA
            UsageQuotaCard(usage = state.usage)

            // 2. FEATURES ROW
            Text("Features", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                FeatureCard(
                    modifier = Modifier.weight(1f),
                    icon = Icons.Default.QuestionAnswer,
                    title = "Replies",
                    subtitle = "View history",
                    accentColor = Pink,
                    onClick = onNavigateToHistory
                )
                FeatureCard(
                    modifier = Modifier.weight(1f),
                    icon = Icons.Default.BarChart,
                    title = "Stats",
                    subtitle = "Your style",
                    accentColor = Color(0xFF9C27B0),
                    onClick = onNavigateToStats
                )
            }

            // 3. STATS ROW
            StatsRow(
                generated = state.totalRepliesGenerated,
                copied = state.totalRepliesCopied
            )

            // 4. HOW IT WORKS (dismissible)
            if (state.showHowItWorks) {
                HowItWorksCard(onDismiss = { viewModel.dismissHowItWorks() })
            }

            // 5. RECENT REPLIES
            RecentRepliesSection(
                replies = state.recentReplies,
                onSeeAll = onNavigateToHistory
            )

            // 6. RIZZ PROFILE
            val profile = state.rizzProfile
            if (profile != null && profile.hasEnoughData) {
                RizzProfileCard(
                    preferences = profile,
                    onSeeFullStats = onNavigateToStats,
                    isGodMode = state.usage.tier == "god_mode"
                )
            }

            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}

@Composable
private fun FeatureCard(
    modifier: Modifier = Modifier,
    icon: ImageVector,
    title: String,
    subtitle: String,
    accentColor: Color,
    onClick: () -> Unit
) {
    Card(
        modifier = modifier.clickable { onClick() },
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier.padding(14.dp).fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(accentColor.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(icon, contentDescription = null, tint = accentColor, modifier = Modifier.size(22.dp))
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(title, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
            Text(subtitle, color = Color.Gray, fontSize = 11.sp)
        }
    }
}

@Composable
private fun HeroCard(
    isEnabled: Boolean,
    hasPermission: Boolean,
    onToggle: (Boolean) -> Unit,
    onGrantPermission: () -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(20.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp).animateContentSize()) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        if (isEnabled) "Cookd is ACTIVE" else "Cookd is Inactive",
                        color = if (isEnabled) Pink else Color.Gray,
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp
                    )
                    Text(
                        if (isEnabled) "Bubble is floating on screen" else "Tap to start the magic",
                        color = Color.Gray,
                        fontSize = 13.sp
                    )
                }
                Switch(
                    checked = isEnabled,
                    onCheckedChange = onToggle,
                    enabled = hasPermission,
                    colors = SwitchDefaults.colors(checkedTrackColor = Pink)
                )
            }

            if (!hasPermission) {
                Spacer(modifier = Modifier.height(12.dp))
                Card(
                    colors = CardDefaults.cardColors(containerColor = Pink.copy(alpha = 0.15f)),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.clickable { onGrantPermission() }
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Warning, contentDescription = null, tint = Pink, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Overlay permission required. Tap to grant.", color = Color.White, fontSize = 13.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun StatsRow(generated: Int, copied: Int) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        StatCard(modifier = Modifier.weight(1f), value = "$generated", label = "Generated")
        StatCard(modifier = Modifier.weight(1f), value = "$copied", label = "Copied")
    }
}

@Composable
private fun StatCard(modifier: Modifier = Modifier, value: String, label: String) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp).fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(value, color = Pink, fontWeight = FontWeight.Bold, fontSize = 24.sp)
            Text(label, color = Color.Gray, fontSize = 12.sp)
        }
    }
}

@Composable
private fun HowItWorksCard(onDismiss: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("How It Works", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                IconButton(onClick = onDismiss, modifier = Modifier.size(24.dp)) {
                    Icon(Icons.Default.Close, contentDescription = "Dismiss", tint = Color.Gray, modifier = Modifier.size(18.dp))
                }
            }
            Spacer(modifier = Modifier.height(12.dp))
            StepItem(number = "1", text = "Open any dating app (Tinder, Bumble, Hinge...)")
            StepItem(number = "2", text = "Tap the floating bubble when you see a chat")
            StepItem(number = "3", text = "Pick a vibe direction (Flirty, Witty, etc.)")
            StepItem(number = "4", text = "Copy the AI reply and send it!")
        }
    }
}

@Composable
private fun StepItem(number: String, text: String) {
    Row(
        modifier = Modifier.padding(vertical = 4.dp),
        verticalAlignment = Alignment.Top
    ) {
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
private fun RecentRepliesSection(
    replies: List<com.rizzbot.v2.data.remote.dto.HistoryItemResponse>,
    onSeeAll: () -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Recent Replies", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                TextButton(onClick = onSeeAll) {
                    Text("See all", color = Pink, fontSize = 13.sp)
                }
            }

            if (replies.isEmpty()) {
                Text(
                    "No replies yet. Open a dating app and tap the bubble!",
                    color = Color.Gray,
                    fontSize = 13.sp,
                    modifier = Modifier.padding(vertical = 12.dp)
                )
            } else {
                replies.forEachIndexed { index, entry ->
                    if (index > 0) HorizontalDivider(color = DividerColor, modifier = Modifier.padding(vertical = 8.dp))
                    ReplyItem(entry)
                }
            }
        }
    }
}

@Composable
private fun ReplyItem(entry: com.rizzbot.v2.data.remote.dto.HistoryItemResponse) {
    val dateFormat = remember { SimpleDateFormat("MMM d, h:mm a", Locale.getDefault()) }
    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                entry.personName?.take(30) ?: "Unknown",
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f)
            )
            Text(
                dateFormat.format(Date(entry.createdAt * 1000)),
                color = Color.Gray,
                fontSize = 11.sp
            )
        }
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            entry.replies.firstOrNull() ?: "",
            color = Color.Gray,
            fontSize = 13.sp,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
    }
}

@Composable
private fun RizzProfileCard(
    preferences: UserPreferences,
    onSeeFullStats: () -> Unit,
    isGodMode: Boolean
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    "Your Digital Twin Status",
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp
                )
                TextButton(onClick = onSeeFullStats) {
                    Text("Full stats", color = Pink, fontSize = 13.sp)
                }
            }
            Spacer(modifier = Modifier.height(8.dp))

            // Voice DNA metrics
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                MetricBar(
                    label = "Emoji Frequency",
                    value = preferences.emojiFrequency.coerceIn(0f, 1f)
                )
                MetricBar(
                    label = "Lowercase Usage",
                    value = preferences.lowercaseUsage.coerceIn(0f, 1f)
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Punctuation Style", color = Color.White, fontSize = 13.sp)
                    Text(
                        preferences.punctuationStyle,
                        color = Color.Gray,
                        fontSize = 12.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Top slang chips
            if (preferences.topSlang.isNotEmpty()) {
                Text(
                    "Top Slang",
                    color = Color.White,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 14.sp
                )
                Spacer(modifier = Modifier.height(6.dp))
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    preferences.topSlang.forEach { slang ->
                        Surface(
                            color = Color.White.copy(alpha = 0.06f),
                            shape = RoundedCornerShape(999.dp),
                            border = BorderStroke(1.dp, Color.White.copy(alpha = 0.18f))
                        ) {
                            Text(
                                text = slang,
                                color = Color.White,
                                fontSize = 12.sp,
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Premium / God Mode messaging
            if (!isGodMode) {
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.06f)),
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Text(
                            "Deep Persona Sync: 🔒",
                            color = Color.White,
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 13.sp
                        )
                        Text(
                            "Upgrade to God Mode to see your exact psychological texting profile.",
                            color = Color.Gray,
                            fontSize = 12.sp
                        )
                    }
                }
            } else {
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1B5E20).copy(alpha = 0.25f)),
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Text(
                            "Semantic Profile",
                            color = Color(0xFFA5D6A7),
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 13.sp
                        )
                        Text(
                            "You have a dry, deadpan humor style and prefer short, witty comebacks.",
                            color = Color.White,
                            fontSize = 12.sp
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MetricBar(label: String, value: Float) {
    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(label, color = Color.White, fontSize = 13.sp)
            Text("${(value * 100).toInt()}%", color = Color.Gray, fontSize = 12.sp)
        }
        Spacer(modifier = Modifier.height(4.dp))
        LinearProgressIndicator(
            progress = { value },
            modifier = Modifier
                .fillMaxWidth()
                .height(6.dp)
                .clip(RoundedCornerShape(3.dp)),
            color = Pink,
            trackColor = DividerColor
        )
    }
}

@Composable
private fun VibeBar(label: String, progress: Float) {
    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(label, color = Color.White, fontSize = 13.sp)
            Text("${(progress * 100).toInt()}%", color = Color.Gray, fontSize = 12.sp)
        }
        Spacer(modifier = Modifier.height(4.dp))
        LinearProgressIndicator(
            progress = { progress },
            modifier = Modifier
                .fillMaxWidth()
                .height(6.dp)
                .clip(RoundedCornerShape(3.dp)),
            color = Pink,
            trackColor = DividerColor
        )
    }
}

@Composable
private fun TrialBanner(daysRemaining: Int) {
    Card(
        colors = CardDefaults.cardColors(
            containerColor = Color(0xFFFF8F00).copy(alpha = 0.15f)
        ),
        shape = RoundedCornerShape(14.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                Icons.Default.Timer,
                contentDescription = null,
                tint = Color(0xFFFF8F00),
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    when (daysRemaining) {
                        0 -> "Your Pro trial expires today!"
                        1 -> "Your Pro trial expires tomorrow"
                        else -> "Pro trial: $daysRemaining days remaining"
                    },
                    color = Color.White,
                    fontWeight = FontWeight.Medium,
                    fontSize = 13.sp
                )
                Text(
                    "Upgrade to keep unlimited replies",
                    color = Color(0xFFFF8F00),
                    fontSize = 11.sp
                )
            }
        }
    }
}

@Composable
private fun UsageQuotaCard(usage: UsageState) {
    Card(
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Daily Usage", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                if (usage.isPremium) {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF4CAF50)),
                        shape = RoundedCornerShape(4.dp)
                    ) {
                        Text(
                            "UNLIMITED",
                            color = Color.White,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                        )
                    }
                } else {
                    Text(
                        "${usage.dailyUsed} of ${usage.dailyLimit} used",
                        color = Color.Gray,
                        fontSize = 12.sp
                    )
                }
            }
            if (!usage.isPremium) {
                Spacer(modifier = Modifier.height(8.dp))
                val progress = if (usage.dailyLimit > 0) usage.dailyUsed.toFloat() / usage.dailyLimit else 0f
                LinearProgressIndicator(
                    progress = { progress.coerceIn(0f, 1f) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(8.dp)
                        .clip(RoundedCornerShape(4.dp)),
                    color = if (progress >= 0.8f) Color(0xFFEF5350) else Pink,
                    trackColor = DividerColor
                )
                if (usage.dailyRemaining <= 1 && usage.dailyRemaining >= 0) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        if (usage.dailyRemaining == 0) "Limit reached! Upgrade for unlimited replies."
                        else "1 reply left today",
                        color = Color(0xFFEF5350),
                        fontSize = 12.sp
                    )
                }
            }
        }
    }
}
