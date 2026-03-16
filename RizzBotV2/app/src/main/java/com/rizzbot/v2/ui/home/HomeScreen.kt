package com.rizzbot.v2.ui.home

import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.provider.Settings
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.ExperimentalAnimationApi
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
import androidx.compose.ui.graphics.Brush
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
import com.rizzbot.v2.ui.premium.VoiceDNACalibrationModal

private val Pink = Color(0xFFE91E63)
private val DarkBg = Color(0xFF0F0F1A)
private val CardBg = Color(0xFF1A1A2E)
private val DividerColor = Color(0xFF252542)
private val GodModeGold = Color(0xFFFFD700)
private val GodModeGlow = Color(0xFFFFD700).copy(alpha = 0.15f)

@OptIn(ExperimentalMaterial3Api::class, ExperimentalAnimationApi::class)
@Composable
fun HomeScreen(
    onNavigateToSettings: () -> Unit,
    onNavigateToHistory: () -> Unit,
    onNavigateToStats: () -> Unit,
    onNavigateToProfileAuditor: () -> Unit,
    onNavigateToProfileHistory: () -> Unit,
    onNavigateToProfileOptimizer: () -> Unit,
    onNavigateToProfileStrategy: () -> Unit = {},
    onShowPaywall: () -> Unit = {},
    viewModel: HomeViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    // Treat both "premium" and "god_mode" tiers as God Mode for UI purposes
    val isGodMode = state.usage.tier == "premium" || state.usage.tier == "god_mode"
    // Pro and above can access voice DNA and auto profile builder (profile_blueprints_per_week > 0)
    val isProOrAbove = state.usage.tier == "pro" || isGodMode
    val primaryAccent = if (isGodMode) GodModeGold else Pink
    val heroGlow = if (isGodMode) GodModeGlow else Pink.copy(alpha = 0.05f)

    LifecycleResumeEffect(Unit) {
        viewModel.refreshPermissionStatus()
        onPauseOrDispose {}
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = if (isGodMode) "Cookd ✦" else "Cookd",
                        fontWeight = FontWeight.Bold
                    )
                },
                actions = {
                    IconButton(onClick = onNavigateToSettings) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = DarkBg,
                    titleContentColor = if (isGodMode) GodModeGold else Color.White
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
            // ── PRIMARY ACTIONS ──
            SectionHeader(title = "Primary Actions", icon = "🎯")
            HeroCard(
                isEnabled = state.isServiceEnabled,
                hasPermission = state.hasOverlayPermission,
                onToggle = { viewModel.toggleService(it) },
                onGrantPermission = {
                    context.startActivity(
                        Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:${context.packageName}"))
                    )
                },
                primaryAccent = primaryAccent,
                heroGlow = heroGlow
            )

            // ── PROFILE TOOLS ──
            SectionDivider()
            SectionHeader(title = "Profile Tools", icon = "📸")
            BrutalProfileAuditorCard(
                primaryAccent = primaryAccent,
                isGodMode = isGodMode,
                maxPhotosPerAudit = state.usage.maxPhotosPerAudit,
                onClick = onNavigateToProfileAuditor,
                onViewHistory = onNavigateToProfileHistory
            )
            AutoProfileBuilderCard(
                primaryAccent = primaryAccent,
                isGodMode = isGodMode,
                isProOrAbove = isProOrAbove,
                latestBlueprintTheme = state.latestBlueprintTheme,
                latestBlueprintSlotCount = state.latestBlueprintSlotCount,
                latestBlueprintDate = state.latestBlueprintDate,
                onClick = {
                    if (isProOrAbove) {
                        onNavigateToProfileOptimizer()
                    } else {
                        onShowPaywall()
                    }
                },
                onViewLastBlueprint = {
                    if (isProOrAbove) onNavigateToProfileStrategy() else onShowPaywall()
                }
            )

            // Core data-driven content: skeleton while usage/history still loading
            AnimatedContent(
                targetState = !(state.isLoadingUsage || state.isLoadingHistory),
                label = "homeContent"
            ) { isLoaded ->
                if (!isLoaded) {
                    HomeSkeleton()
                } else {
                    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                        // ── YOUR STATS ──
                        SectionDivider()
                        SectionHeader(title = "Your Stats", icon = "📊")
                        RizzProfileCard(
                            preferences = state.rizzProfile,
                            onSeeFullStats = onNavigateToStats,
                            isGodMode = isGodMode,
                            isProOrAbove = isProOrAbove,
                            onTrainVoiceDNA = {
                                if (isProOrAbove) {
                                    viewModel.showCalibration()
                                } else {
                                    onShowPaywall()
                                }
                            },
                            primaryAccent = primaryAccent
                        )

                        // 5. HOW IT WORKS (dismissible)
                        if (state.showHowItWorks) {
                            HowItWorksCard(onDismiss = { viewModel.dismissHowItWorks() })
                        }

                        // ── RECENT ACTIVITY ──
                        if (state.recentReplies.isNotEmpty()) {
                            SectionDivider()
                            SectionHeader(title = "Recent Activity", icon = "📝")
                        }
                        RecentRepliesSection(
                            replies = state.recentReplies,
                            onSeeAll = onNavigateToHistory,
                            primaryAccent = primaryAccent
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
        }

        if (state.showCalibrationModal) {
            VoiceDNACalibrationModal(
                onDismiss = { viewModel.hideCalibration() },
                onImagesSelected = { uris ->
                    val bitmaps = uris.mapNotNull { uri ->
                        try {
                            context.contentResolver.openInputStream(uri)?.use {
                                BitmapFactory.decodeStream(it)
                            }
                        } catch (_: Exception) {
                            null
                        }
                    }
                    viewModel.calibrateVoiceDNA(uris)
                }
            )
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
    onGrantPermission: () -> Unit,
    primaryAccent: Color,
    heroGlow: Color
) {
    val activeBackground = heroGlow

    Card(
        colors = CardDefaults.cardColors(
            containerColor = if (isEnabled) activeBackground else CardBg
        ),
        shape = RoundedCornerShape(20.dp),
        border = if (isEnabled) BorderStroke(1.dp, primaryAccent.copy(alpha = 0.5f)) else null
    ) {
        Column(modifier = Modifier.padding(20.dp).animateContentSize()) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        if (isEnabled) "Floating Wingman Active ✨" else "Cookd is Inactive",
                        color = if (isEnabled) primaryAccent else Color.Gray,
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp
                    )
                    Text(
                        if (isEnabled) "Ready to use! Open Tinder, Hinge, or Bumble and tap the bubble to generate replies instantly."
                        else "Turn on the overlay to get AI replies without ever leaving your dating apps.",
                        color = Color.Gray,
                        fontSize = 13.sp
                    )
                }
                Switch(
                    checked = isEnabled,
                    onCheckedChange = onToggle,
                    enabled = hasPermission,
                    colors = SwitchDefaults.colors(checkedTrackColor = primaryAccent)
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
private fun SectionHeader(title: String, icon: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text(
            text = icon,
            fontSize = 18.sp
        )
        Text(
            text = title,
            color = Color.White,
            fontSize = 16.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.5.sp
        )
    }
}

@Composable
private fun SectionDivider() {
    HorizontalDivider(
        color = DividerColor.copy(alpha = 0.5f),
        thickness = 1.dp,
        modifier = Modifier.padding(vertical = 8.dp)
    )
}

@Composable
private fun BrutalProfileAuditorCard(
    primaryAccent: Color,
    isGodMode: Boolean,
    maxPhotosPerAudit: Int,
    onClick: () -> Unit,
    onViewHistory: () -> Unit
) {
    val borderColor = if (isGodMode) GodModeGold else primaryAccent
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(0.5.dp, primaryAccent.copy(alpha = 0.3f))
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    Brush.linearGradient(
                        listOf(
                            Color(0xFF1A1A2E),
                            primaryAccent.copy(alpha = 0.05f)
                        )
                    )
                )
        ) {
            Row(
                modifier = Modifier
                    .padding(16.dp)
                    .fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
            // Left: Icon
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(borderColor.copy(alpha = 0.18f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.PhotoCamera,
                    contentDescription = null,
                    tint = borderColor,
                    modifier = Modifier.size(22.dp)
                )
            }

            // Middle: Title and Subtitle
            Column(
                modifier = Modifier.weight(1f)
            ) {
                Text(
                    text = "Stop Getting Ghosted. Run a Zero-BS Photo Audit.",
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = "Upload up to $maxPhotosPerAudit photos. We'll tell you which ones are killing your match rate.",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
            }

            // Right: History button and Chevron
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                IconButton(
                    onClick = onViewHistory,
                    modifier = Modifier.size(40.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.History,
                        contentDescription = "View Past Roasts",
                        tint = Color.Gray,
                        modifier = Modifier.size(20.dp)
                    )
                }
                Icon(
                    imageVector = Icons.Default.ChevronRight,
                    contentDescription = null,
                    tint = primaryAccent,
                    modifier = Modifier.size(20.dp)
                )
            }
        }
        }
    }
}

@Composable
private fun AutoProfileBuilderCard(
    primaryAccent: Color,
    isGodMode: Boolean,
    isProOrAbove: Boolean,
    latestBlueprintTheme: String?,
    latestBlueprintSlotCount: Int,
    latestBlueprintDate: String?,
    onClick: () -> Unit,
    onViewLastBlueprint: () -> Unit = {}
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(0.5.dp, primaryAccent.copy(alpha = 0.3f))
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    Brush.linearGradient(
                        listOf(
                            Color(0xFF1A1A2E),
                            primaryAccent.copy(alpha = 0.05f)
                        )
                    )
                )
        ) {
            Column {
                // Main tappable row
                Row(
                    modifier = Modifier
                        .clickable { onClick() }
                        .padding(16.dp)
                        .fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(
                        modifier = Modifier.weight(1f),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(36.dp)
                                .clip(RoundedCornerShape(10.dp))
                                .background(primaryAccent.copy(alpha = 0.15f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.AutoAwesome,
                                contentDescription = null,
                                tint = primaryAccent,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Auto-Build Profile",
                                color = Color.White,
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = "AI-powered profile builder",
                                color = Color.Gray,
                                fontSize = 11.sp
                            )
                        }
                    }
                    if (!isProOrAbove) {
                        Icon(
                            imageVector = Icons.Default.Lock,
                            contentDescription = "Pro Feature",
                            tint = GodModeGold,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                    }
                    Icon(
                        imageVector = Icons.Default.ChevronRight,
                        contentDescription = "Open",
                        tint = primaryAccent.copy(alpha = 0.7f),
                        modifier = Modifier.size(20.dp)
                    )
                }

                // Latest blueprint preview
                if (latestBlueprintTheme != null) {
                    HorizontalDivider(
                        color = primaryAccent.copy(alpha = 0.1f),
                        thickness = 0.5.dp
                    )
                    Row(
                        modifier = Modifier
                            .clickable { onViewLastBlueprint() }
                            .padding(horizontal = 16.dp, vertical = 10.dp)
                            .fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "Last blueprint",
                                color = Color.Gray,
                                fontSize = 10.sp
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = latestBlueprintTheme,
                                color = primaryAccent,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Medium,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                            if (latestBlueprintDate != null) {
                                Text(
                                    text = "$latestBlueprintSlotCount photos • $latestBlueprintDate",
                                    color = Color.Gray,
                                    fontSize = 10.sp
                                )
                            }
                        }
                        Text(
                            text = "View →",
                            color = primaryAccent.copy(alpha = 0.8f),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun StatsRow(generated: Int, copied: Int, primaryAccent: Color) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        StatCard(modifier = Modifier.weight(1f), value = "$generated", label = "Generated", primaryAccent = primaryAccent)
        StatCard(modifier = Modifier.weight(1f), value = "$copied", label = "Copied", primaryAccent = primaryAccent)
    }
}

@Composable
private fun StatCard(modifier: Modifier = Modifier, value: String, label: String, primaryAccent: Color) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp).fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(value, color = primaryAccent, fontWeight = FontWeight.Bold, fontSize = 24.sp)
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
    onSeeAll: () -> Unit,
    primaryAccent: Color
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
                    Text("See all", color = primaryAccent, fontSize = 13.sp)
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
            entry.replies.firstOrNull()?.text ?: "",
            color = Color.Gray,
            fontSize = 13.sp,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis
        )
    }
}

@Composable
private fun RizzProfileCard(
    preferences: UserPreferences?,
    onSeeFullStats: () -> Unit,
    isGodMode: Boolean,
    isProOrAbove: Boolean,
    onTrainVoiceDNA: () -> Unit,
    primaryAccent: Color
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
                    "Your AI Clone Status",
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp
                )
                if (preferences?.hasEnoughData == true) {
                    TextButton(onClick = onSeeFullStats) {
                        Text("Full stats", color = Pink, fontSize = 13.sp)
                    }
                }
            }
            Spacer(modifier = Modifier.height(8.dp))

            when {
                // ── STATE 1: Still loading from backend ──
                preferences == null -> {
                    // Skeleton shimmer placeholders
                    repeat(3) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth(if (it == 2) 0.6f else 1f)
                                .height(14.dp)
                                .clip(RoundedCornerShape(4.dp))
                                .background(DividerColor)
                        )
                        Spacer(modifier = Modifier.height(10.dp))
                    }
                }

                // ── STATE 2: Loaded, has enough data → show vibe breakdown from API ──
                preferences.hasEnoughData -> {
                    // Vibe breakdown bars from backend data
                    if (preferences.vibeBreakdown.isNotEmpty()) {
                        Text(
                            "Your Vibe Profile",
                            color = Color.White,
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 14.sp
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            preferences.vibeBreakdown.entries
                                .sortedByDescending { it.value }
                                .forEach { (vibeName, percentage) ->
                                    VibeBar(
                                        label = vibeName,
                                        progress = percentage.coerceIn(0f, 1f),
                                        primaryAccent = primaryAccent
                                    )
                                }
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Preferred length indicator
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Preferred Reply Length", color = Color.White, fontSize = 13.sp)
                        Text(
                            when (preferences.preferredLength) {
                                UserPreferences.PreferredLength.SHORT -> "Short & punchy"
                                UserPreferences.PreferredLength.LONG -> "Detailed"
                                else -> "Medium"
                            },
                            color = Color.Gray,
                            fontSize = 12.sp
                        )
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Interactions count
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Total Interactions", color = Color.White, fontSize = 13.sp)
                        Text(
                            "${preferences.totalRatings}",
                            color = primaryAccent,
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    // Pro / God Mode messaging
                    if (!isProOrAbove) {
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
                                    "AI Voice Cloning: \uD83D\uDD12",
                                    color = Color.White,
                                    fontWeight = FontWeight.SemiBold,
                                    fontSize = 13.sp
                                )
                                Text(
                                    "Upgrade to Pro so the AI learns your exact humor, slang, and texting style.",
                                    color = Color.Gray,
                                    fontSize = 12.sp
                                )
                            }
                        }
                    } else {
                        TextButton(onClick = onTrainVoiceDNA) {
                            Text(
                                text = "\uD83E\uDDEC Add Sample Styles to refine your AI Twin",
                                color = Color(0xFFA5D6A7),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Medium
                            )
                        }
                    }
                }

                // ── STATE 3: Zero data → onboarding CTA (no fake metrics) ──
                preferences.totalRatings == 0 -> {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "\uD83E\uDDEC",
                            fontSize = 36.sp
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "Your AI Twin isn't trained yet",
                            color = Color.White,
                            fontWeight = FontWeight.Bold,
                            fontSize = 15.sp
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "Use Cookd in your chats or upload screenshots so it can learn your humor, slang, and vibe.",
                            color = Color.Gray,
                            fontSize = 13.sp,
                            modifier = Modifier.padding(horizontal = 8.dp),
                            lineHeight = 18.sp
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        Button(
                            onClick = onTrainVoiceDNA,
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(containerColor = primaryAccent)
                        ) {
                            Text(
                                text = if (isProOrAbove) "Upload Chat Screenshots" else "🔒 Unlock AI Voice DNA",
                                color = Color.White,
                                fontSize = 14.sp,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }
                }

                // ── STATE 4: Has some data, learning in progress → real progress ──
                else -> {
                    val currentRatings = preferences.totalRatings
                    val targetRatings = 20
                    val progressFraction = (currentRatings / targetRatings.toFloat()).coerceIn(0f, 1f)

                    Text(
                        text = "Calibrating Your AI Twin \uD83E\uDDEC",
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Cookd is analyzing your texts to learn your style. Keep chatting!",
                        color = Color.Gray,
                        fontSize = 13.sp
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "Progress",
                            color = Color.White,
                            fontSize = 13.sp
                        )
                        Text(
                            text = "$currentRatings / $targetRatings interactions",
                            color = Color.Gray,
                            fontSize = 12.sp
                        )
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    LinearProgressIndicator(
                        progress = { progressFraction },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(6.dp)
                            .clip(RoundedCornerShape(3.dp)),
                        color = primaryAccent,
                        trackColor = DividerColor
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Button(
                        onClick = onTrainVoiceDNA,
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = primaryAccent)
                    ) {
                        Text(
                            text = if (isProOrAbove) "Upload Screenshots to Speed Up" else "🔒 Unlock AI Voice DNA",
                            color = Color.White,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun MetricBar(label: String, value: Float, primaryAccent: Color) {
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
            color = primaryAccent,
            trackColor = DividerColor
        )
    }
}

@Composable
private fun VibeBar(label: String, progress: Float, primaryAccent: Color) {
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
            color = primaryAccent,
            trackColor = DividerColor
        )
    }
}
