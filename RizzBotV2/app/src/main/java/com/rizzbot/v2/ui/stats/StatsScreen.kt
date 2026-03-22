package com.rizzbot.v2.ui.stats

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.PullToRefreshDefaults
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.TileMode
import androidx.compose.ui.graphics.Shadow
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import com.rizzbot.v2.domain.model.UserPreferences
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StatsScreen(
    onBack: () -> Unit,
    viewModel: StatsViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val isRefreshing by viewModel.isRefreshing.collectAsState()
    val pullRefreshState = rememberPullToRefreshState()

    val DarkBg = Color(0xFF0F0F1A)
    val CardBg = Color(0xFF1A1A2E)
    val BrandPink = Color(0xFFE91E63)
    val brandAccent = BrandPink
    val isPremiumTier = state.tier == "premium" || state.tier == "god_mode"
    
    // Auto-refresh when screen becomes visible
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        viewModel.refresh()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = if (isPremiumTier) "Voice DNA Dashboard ✦" else "Voice DNA Dashboard",
                        fontWeight = FontWeight.Bold,
                        color = BrandPink
                    )
                },
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
        PullToRefreshBox(
            isRefreshing = isRefreshing,
            onRefresh = { viewModel.refresh() },
            state = pullRefreshState,
            indicator = {
                PullToRefreshDefaults.Indicator(
                    modifier = Modifier.align(Alignment.TopCenter),
                    isRefreshing = isRefreshing,
                    state = pullRefreshState,
                    containerColor = CardBg,
                    color = BrandPink,
                )
            },
            modifier = Modifier
                .padding(padding)
                .fillMaxSize(),
        ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp)
        ) {
            val hasEnoughData = state.preferences.hasEnoughData

            // Global calibrating banner if data is low
            if (!hasEnoughData) {
                CalibratingBanner(
                    current = state.preferences.totalRatings,
                    target = 20,
                    brandAccent = brandAccent,
                    cardBg = CardBg
                )
                Spacer(modifier = Modifier.height(20.dp))
            }

            // Section 0: High-level usage + success summary
            SuccessSummaryRow(
                totalGenerated = state.totalGenerated,
                totalCopied = state.totalCopied,
                totalConversations = state.totalConversationsInfluenced,
                brandAccent = brandAccent,
                cardBg = CardBg
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Section 1: Personality Breakdown
            SectionCard(
                title = "Personality Breakdown",
                subtitle = if (hasEnoughData) "Based on ${state.preferences.totalRatings} rated conversations" else "We’re still calibrating your personality profile",
                brandAccent = brandAccent,
                cardBg = CardBg
            ) {
                if (hasEnoughData) {
                    PersonalityBreakdownContent(
                        preferences = state.preferences,
                        accent = brandAccent
                    )
                } else {
                    Text(
                        text = "Profile Calibrating...",
                        color = Color.White,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 14.sp
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    ScanningProgressBar(
                        progress = state.preferences.totalRatings / 20f,
                        accent = brandAccent
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        "${state.preferences.totalRatings}/20 ratings — keep using Cookd to unlock deeper insights.",
                        color = Color.Gray,
                        fontSize = 12.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            // Section 2: Linguistic Fingerprint
            SectionCard(
                title = "Linguistic Fingerprint",
                subtitle = "Your most iconic slang and phrases",
                brandAccent = brandAccent,
                cardBg = CardBg
            ) {
                if (hasEnoughData && state.preferences.topSlang.isNotEmpty()) {
                    LinguisticFingerprintContent(
                        slang = state.preferences.topSlang,
                        accent = brandAccent
                    )
                } else {
                    Text(
                        text = "Profile Calibrating...",
                        color = Color.White,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 14.sp
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "We’ll surface your most-used slang and phrases once we’ve seen a few more chats.",
                        color = Color.Gray,
                        fontSize = 12.sp
                    )
                }
            }

        }
        }
    }
}

@Composable
private fun CalibratingBanner(
    current: Int,
    target: Int,
    brandAccent: Color,
    cardBg: Color
) {
    val progress = (current.toFloat() / target).coerceIn(0f, 1f)
    Card(
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        shape = RoundedCornerShape(18.dp),
        border = CardDefaults.outlinedCardBorder().copy(
            width = 1.dp,
            brush = Brush.horizontalGradient(listOf(brandAccent, brandAccent.copy(alpha = 0.3f)))
        )
    ) {
        Box(
            modifier = Modifier
                .background(
                    Brush.verticalGradient(
                        colors = listOf(
                            cardBg.copy(alpha = 0.96f),
                            cardBg.copy(alpha = 0.85f)
                        )
                    )
                )
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                horizontalAlignment = Alignment.Start
            ) {
                Text(
                    text = "Profile Calibrating…",
                    color = brandAccent,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 14.sp
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Keep chatting and rating replies so your Voice DNA Dashboard can fully unlock.",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
                Spacer(modifier = Modifier.height(10.dp))
                ScanningProgressBar(
                    progress = progress,
                    accent = brandAccent
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "$current/$target signals collected",
                    color = Color.Gray,
                    fontSize = 11.sp
                )
            }
        }
    }
}

@Composable
private fun SectionCard(
    title: String,
    subtitle: String,
    brandAccent: Color,
    cardBg: Color,
    content: @Composable ColumnScope.() -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        shape = RoundedCornerShape(24.dp),
        border = CardDefaults.outlinedCardBorder().copy(
            width = 1.dp,
            brush = Brush.horizontalGradient(
                listOf(
                    brandAccent.copy(alpha = 0.7f),
                    brandAccent.copy(alpha = 0.2f)
                )
            )
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            cardBg.copy(alpha = 0.96f),
                            cardBg.copy(alpha = 0.82f)
                        )
                    )
                )
                .padding(18.dp)
        ) {
            Text(
                text = title,
                color = brandAccent,
                fontWeight = FontWeight.SemiBold,
                fontSize = 15.sp
            )
            if (subtitle.isNotEmpty()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = subtitle,
                    color = Color.Gray,
                    fontSize = 12.sp
                )
            }
            Spacer(modifier = Modifier.height(14.dp))
            content()
        }
    }
}

@Composable
private fun SuccessSummaryRow(
    totalGenerated: Int,
    totalCopied: Int,
    totalConversations: Int,
    brandAccent: Color,
    cardBg: Color
) {
    val copyRate = if (totalGenerated > 0) {
        ((totalCopied.toFloat() / totalGenerated) * 100).toInt()
    } else 0

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        SummaryStatCard(
            label = "Rizz Score",
            value = "$copyRate%",
            helper = "Based on how often your replies are copied",
            brandAccent = brandAccent,
            cardBg = cardBg,
            modifier = Modifier.weight(1f)
        )
        SummaryStatCard(
            label = "Conversations Influenced",
            value = "$totalConversations",
            helper = "Unique chats Cookd has touched",
            brandAccent = brandAccent,
            cardBg = cardBg,
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun SummaryStatCard(
    label: String,
    value: String,
    helper: String,
    brandAccent: Color,
    cardBg: Color,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(containerColor = Color.Transparent),
        shape = RoundedCornerShape(18.dp),
        border = CardDefaults.outlinedCardBorder().copy(
            width = 1.dp,
            brush = Brush.sweepGradient(
                colors = listOf(
                    brandAccent.copy(alpha = 0.9f),
                    brandAccent.copy(alpha = 0.2f),
                    brandAccent.copy(alpha = 0.6f),
                    brandAccent.copy(alpha = 0.2f),
                    brandAccent.copy(alpha = 0.9f)
                )
            )
        )
    ) {
        Box(
            modifier = Modifier
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            cardBg.copy(alpha = 0.96f),
                            cardBg.copy(alpha = 0.82f)
                        )
                    )
                )
        ) {
            // Radial glow background layer, subtly pulled toward the value text
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .drawBehind {
                        val centerOffset = Offset(
                            x = size.width * 0.7f,
                            y = size.height * 0.35f
                        )
                        val radius = size.maxDimension * 0.9f

                        drawCircle(
                            brush = Brush.radialGradient(
                                colors = listOf(
                                    brandAccent.copy(alpha = 0.15f),
                                    Color.Transparent
                                ),
                                center = centerOffset,
                                radius = radius
                            ),
                            center = centerOffset,
                            radius = radius
                        )
                    }
            )

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                Text(
                    text = label,
                    color = Color.Gray,
                    fontSize = 11.sp
                )
                Spacer(modifier = Modifier.height(6.dp))
                Box(
                    contentAlignment = Alignment.CenterStart,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 2.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .height(40.dp)
                            .fillMaxWidth(0.7f)
                    )
                    Text(
                        text = value,
                        color = brandAccent,
                        fontWeight = FontWeight.ExtraBold,
                        fontSize = 34.sp,
                        style = TextStyle(
                            shadow = Shadow(
                                color = brandAccent.copy(alpha = 0.5f),
                                blurRadius = 8f
                            )
                        )
                    )
                }
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = helper,
                    color = Color.Gray,
                    fontSize = 11.sp
                )
            }
        }
    }
}

@Composable
private fun PersonalityBreakdownContent(
    preferences: UserPreferences,
    accent: Color
) {
    val vibeEntries = preferences.vibeBreakdown
        .entries
        .sortedByDescending { it.value }

    if (vibeEntries.isNotEmpty()) {
        vibeEntries.forEach { (vibe, percentage) ->
            VibeBarDashboard(
                label = vibe,
                progress = percentage.coerceIn(0f, 1f),
                accent = accent
            )
            Spacer(modifier = Modifier.height(10.dp))
        }
        Spacer(modifier = Modifier.height(12.dp))
    }

    // Derived personality metrics from existing signals
    val topVibe = vibeEntries.firstOrNull()?.key.orEmpty()
    val sarcasmLevel = when (topVibe) {
        "Witty" -> 0.85f
        "Bold" -> 0.7f
        else -> 0.5f
    }
    val responseSpeed = when (preferences.preferredLength) {
        UserPreferences.PreferredLength.SHORT -> 0.9f
        UserPreferences.PreferredLength.MEDIUM -> 0.65f
        UserPreferences.PreferredLength.LONG -> 0.4f
    }

    SegmentedMetricBarDashboard(
        label = "Sarcasm Levels",
        value = sarcasmLevel,
        accent = accent
    )
    Spacer(modifier = Modifier.height(8.dp))
    SegmentedMetricBarDashboard(
        label = "Response Speed",
        value = responseSpeed,
        accent = accent
    )
}

@Composable
private fun VibeBarDashboard(
    label: String,
    progress: Float,
    accent: Color
) {
    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(label, color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            Text("${(progress * 100).toInt()}%", color = accent, fontSize = 12.sp)
        }
        Spacer(modifier = Modifier.height(4.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(6.dp)
                .clip(RoundedCornerShape(3.dp))
                .background(Color(0xFF252542))
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(progress)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(3.dp))
                    .background(accent)
            )
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun LinguisticFingerprintContent(
    slang: List<String>,
    accent: Color
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = "Most used slang",
            color = Color.White,
            fontWeight = FontWeight.SemiBold,
            fontSize = 13.sp
        )
        Spacer(modifier = Modifier.height(4.dp))
        FlowRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            slang.forEach { word ->
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(999.dp))
                        .background(accent.copy(alpha = 0.1f))
                        .border(
                            width = 1.dp,
                            color = accent.copy(alpha = 0.3f),
                            shape = RoundedCornerShape(999.dp)
                        )
                        .padding(horizontal = 10.dp, vertical = 6.dp)
                ) {
                    Text(
                        text = word,
                        color = Color.White,
                        fontSize = 12.sp
                    )
                }
            }
        }
    }
}

@Composable
private fun SegmentedMetricBarDashboard(
    label: String,
    value: Float,
    accent: Color,
    segments: Int = 10
) {
    val clamped = value.coerceIn(0f, 1f)
    val activeSegments = (clamped * segments).roundToInt()

    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(label, color = Color.White, fontSize = 13.sp)
            Text("${(clamped * 100).toInt()}%", color = Color.Gray, fontSize = 12.sp)
        }
        Spacer(modifier = Modifier.height(4.dp))
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(10.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            repeat(segments) { index ->
                val isActive = index < activeSegments
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxHeight()
                        .clip(RoundedCornerShape(3.dp))
                        .background(
                            if (isActive) {
                                Brush.verticalGradient(
                                    colors = listOf(
                                        accent.copy(alpha = 0.95f),
                                        accent.copy(alpha = 0.4f)
                                    )
                                )
                            } else {
                                Brush.verticalGradient(
                                    colors = listOf(
                                        Color(0xFF252542),
                                        Color(0xFF181830)
                                    )
                                )
                            }
                        )
                )
            }
        }
    }
}

@Composable
private fun ScanningProgressBar(
    progress: Float,
    accent: Color,
    trackColor: Color = Color(0xFF252542)
) {
    val clampedProgress = progress.coerceIn(0f, 1f)
    val infiniteTransition = rememberInfiniteTransition(label = "scan_transition")
    val scanOffset by infiniteTransition.animateFloat(
        initialValue = -0.5f,
        targetValue = 1.5f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1400, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "scan_offset"
    )

    androidx.compose.foundation.Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(6.dp)
            .clip(RoundedCornerShape(3.dp))
    ) {
        val width = size.width
        val height = size.height
        val progressWidth = width * clampedProgress

        // Track
        drawRoundRect(
            color = trackColor,
            size = Size(width, height),
            cornerRadius = CornerRadius(3.dp.toPx(), 3.dp.toPx())
        )

        if (progressWidth > 0f) {
            // Filled portion
            drawRoundRect(
                color = accent,
                size = Size(progressWidth, height),
                cornerRadius = CornerRadius(3.dp.toPx(), 3.dp.toPx())
            )

            // Scanning highlight across the filled portion
            val highlightWidth = progressWidth / 3f
            val startX = (scanOffset * progressWidth) - highlightWidth
            val endX = startX + highlightWidth

            drawRoundRect(
                brush = Brush.linearGradient(
                    colors = listOf(
                        Color.Transparent,
                        accent.copy(alpha = 0.85f),
                        Color.Transparent
                    ),
                    start = Offset(startX, 0f),
                    end = Offset(endX, 0f),
                    tileMode = TileMode.Clamp
                ),
                size = Size(progressWidth, height),
                cornerRadius = CornerRadius(3.dp.toPx(), 3.dp.toPx())
            )
        }
    }
}
