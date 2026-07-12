package com.rizzbot.v2.ui.home

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.animation.ExperimentalAnimationApi
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.PullToRefreshDefaults
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
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
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.LifecycleResumeEffect
import com.rizzbot.v2.domain.model.TierQuota
import com.rizzbot.v2.ui.theme.NeonRed
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite

@OptIn(ExperimentalMaterial3Api::class, ExperimentalAnimationApi::class)
@Composable
fun HomeScreen(
    onNavigateToSettings: () -> Unit,
    onNavigateToHistory: () -> Unit,
    onNavigateToStats: () -> Unit,
    onNavigateToProfileAuditor: () -> Unit,
    onNavigateToProfileOptimizer: () -> Unit,
    onNavigateToProfileStrategy: () -> Unit = {},
    onNavigateToSmartReply: () -> Unit = {},
    onShowPaywall: () -> Unit = {},
    viewModel: HomeViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val isPullRefreshing by viewModel.isPullRefreshing.collectAsState()
    val pullRefreshState = rememberPullToRefreshState()
    val context = LocalContext.current

    val isPaidPlan = state.usage.isPaidPlan

    LifecycleResumeEffect(Unit) {
        viewModel.refreshPermissionStatus()
        onPauseOrDispose {}
    }

    // Overlay permission dialog
    if (state.showOverlayPermissionPrompt) {
        OverlayPermissionDialog(
            onGrantPermission = {
                viewModel.dismissOverlayPermissionPrompt()
                context.startActivity(
                    Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:${context.packageName}"))
                )
            },
            onDismiss = { viewModel.dismissOverlayPermissionPrompt() }
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = if (isPaidPlan) "Cookd \u2726" else "Cookd",
                        style = MaterialTheme.typography.titleLarge,
                        color = NothingWhite,
                    )
                },
                actions = {
                    IconButton(onClick = onNavigateToSettings) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings", tint = NothingWhite)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = NothingBlack,
                    titleContentColor = NothingWhite
                )
            )
        },
        containerColor = NothingBlack
    ) { padding ->
        Box(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
        ) {
            PullToRefreshBox(
                isRefreshing = isPullRefreshing,
                onRefresh = { viewModel.refresh() },
                state = pullRefreshState,
                indicator = {
                    PullToRefreshDefaults.Indicator(
                        modifier = Modifier.align(Alignment.TopCenter),
                        isRefreshing = isPullRefreshing,
                        state = pullRefreshState,
                        containerColor = NothingSurface,
                        color = NothingWhite,
                    )
                },
                modifier = Modifier.fillMaxSize(),
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                        .padding(NothingDimens.screenPadding),
                    verticalArrangement = Arrangement.spacedBy(NothingDimens.sectionSpacing)
                ) {
                    SectionHeader(title = "Primary Actions")
                    SmartReplyEntryCard(
                        onClick = onNavigateToSmartReply,
                        tier = state.usage.tier,
                        creditsRemaining = state.usage.creditsRemaining,
                        creditsPeriodLimit = state.usage.creditsPeriodLimit,
                        billingPeriod = state.usage.billingPeriod,
                    )
                    HeroCard(
                        isEnabled = state.isServiceEnabled,
                        hasPermission = state.hasOverlayPermission,
                        onToggle = { viewModel.toggleService(it) },
                    )
                    ReplyHistoryQuickLink(onClick = onNavigateToHistory)

                    SectionDivider()
                    SectionHeader(title = "Profile Tools")

                    PhotoAuditCard(
                        maxPhotosPerAudit = state.usage.maxPhotosPerAudit,
                        onRunAudit = onNavigateToProfileAuditor
                    )
                    AutoProfileBuilderCard(
                        isPaidPlan = isPaidPlan,
                        isProOrAbove = isPaidPlan,
                        latestBlueprintTheme = state.latestBlueprintTheme,
                        latestBlueprintSlotCount = state.latestBlueprintSlotCount,
                        latestBlueprintDate = state.latestBlueprintDate,
                        onClick = {
                            if (isPaidPlan) onNavigateToProfileOptimizer()
                            else onShowPaywall()
                        },
                        onViewLastBlueprint = {
                            if (isPaidPlan) onNavigateToProfileStrategy() else onShowPaywall()
                        }
                    )

                    Spacer(modifier = Modifier.height(32.dp))
                }
            }
        }
    }
}

// ─────────────────────────────────────────────
// Smart Reply Entry Card
// ─────────────────────────────────────────────

@Composable
private fun SmartReplyEntryCard(
    onClick: () -> Unit,
    tier: String,
    creditsRemaining: Int,
    creditsPeriodLimit: Int,
    billingPeriod: String = "daily",
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() },
        colors = CardDefaults.cardColors(containerColor = NothingSurface),
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(NothingDimens.cardPadding),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .background(NothingBorder),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.AutoAwesome,
                    contentDescription = null,
                    tint = NothingWhite,
                    modifier = Modifier.size(24.dp)
                )
            }
            Spacer(modifier = Modifier.width(NothingDimens.elementGap))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "Smart Reply",
                    color = NothingWhite,
                    fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(
                    text = "Pick screenshots and get AI replies",
                    color = NothingTextSecondary,
                    style = MaterialTheme.typography.labelMedium,
                )
            }
            Spacer(modifier = Modifier.width(NothingDimens.elementGap))
            // Credit badge — shows fraction for paid, total for free
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = if (tier == TierQuota.PLAN_FREE)
                        "$creditsRemaining cr"
                    else
                        "$creditsRemaining / $creditsPeriodLimit",
                    color = if (creditsRemaining <= 0) NothingError else NothingTextSecondary,
                    style = MaterialTheme.typography.labelSmall,
                )
                if (tier != TierQuota.PLAN_FREE && creditsPeriodLimit > 0) {
                    Text(
                        text = TierQuota.billingPeriodNoun(billingPeriod),
                        color = NothingTextTertiary,
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
            }
            Spacer(modifier = Modifier.width(8.dp))
            Icon(
                imageVector = Icons.Default.ChevronRight,
                contentDescription = "Open",
                tint = NothingTextSecondary,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}

// ─────────────────────────────────────────────
// Hero Card (Overlay Toggle)
// ─────────────────────────────────────────────

@Composable
private fun HeroCard(
    isEnabled: Boolean,
    hasPermission: Boolean,
    onToggle: (Boolean) -> Unit,
) {
    Card(
        colors = CardDefaults.cardColors(
            containerColor = if (isEnabled) NothingBorder else NothingSurface
        ),
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
    ) {
        Column(
            modifier = Modifier
                .padding(NothingDimens.cardPadding)
                .animateContentSize(
                    animationSpec = spring(
                        dampingRatio = Spring.DampingRatioNoBouncy,
                        stiffness = Spring.StiffnessMediumLow
                    )
                )
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        if (isEnabled) "Active" else "Inactive",
                        color = if (isEnabled) NothingWhite else NothingTextSecondary,
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.titleMedium,
                    )
                    Spacer(modifier = Modifier.height(NothingDimens.textGap))
                    Text(
                        if (isEnabled) "Open a dating app and tap the bubble."
                        else "Turn on to get AI replies in your dating apps.",
                        color = NothingTextSecondary,
                        style = MaterialTheme.typography.labelMedium,
                    )
                }
                Switch(
                    checked = isEnabled,
                    onCheckedChange = onToggle,
                    colors = SwitchDefaults.colors(checkedTrackColor = NothingWhite)
                )
            }

            if (!hasPermission && !isEnabled) {
                Spacer(modifier = Modifier.height(NothingDimens.elementGap))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(NothingDimens.cardRadius))
                        .background(NothingBorder)
                        .padding(horizontal = 12.dp, vertical = 10.dp)
                ) {
                    Text(
                        "Tap the switch to grant overlay permission",
                        color = NothingTextSecondary,
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
            }
        }
    }
}

// ─────────────────────────────────────────────
// Section Header
// ─────────────────────────────────────────────

@Composable
private fun SectionHeader(title: String) {
    Text(
        text = title,
        color = NothingTextSecondary,
        style = MaterialTheme.typography.labelMedium,
        fontWeight = FontWeight.Bold,
    )
}

// ─────────────────────────────────────────────
// Section Divider
// ─────────────────────────────────────────────

@Composable
private fun SectionDivider() {
    HorizontalDivider(
        color = NothingBorder,
        thickness = NothingDimens.borderThickness,
        modifier = Modifier.padding(vertical = 8.dp)
    )
}

// ─────────────────────────────────────────────
// Reply History Quick Link
// ─────────────────────────────────────────────

@Composable
private fun ReplyHistoryQuickLink(onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(NothingDimens.cardRadius))
            .background(NothingSurface)
            .clickable(onClick = onClick)
            .padding(NothingDimens.cardPadding),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(NothingDimens.elementGap),
            modifier = Modifier.weight(1f)
        ) {
            Icon(
                imageVector = Icons.Default.Chat,
                contentDescription = null,
                tint = NothingWhite,
                modifier = Modifier.size(22.dp)
            )
            Column {
                Text(
                    text = "Reply history",
                    color = NothingWhite,
                    fontWeight = FontWeight.SemiBold,
                    style = MaterialTheme.typography.titleSmall,
                )
                Spacer(modifier = Modifier.height(NothingDimens.textGap))
                Text(
                    text = "AI replies from your screenshots",
                    color = NothingTextSecondary,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
        Icon(
            imageVector = Icons.Default.ChevronRight,
            contentDescription = null,
            tint = NothingTextSecondary,
            modifier = Modifier.size(20.dp)
        )
    }
}

// ─────────────────────────────────────────────
// Photo Audit Card
// ─────────────────────────────────────────────

@Composable
private fun PhotoAuditCard(
    maxPhotosPerAudit: Int,
    onRunAudit: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = NothingSurface),
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clickable(onClick = onRunAudit)
                .padding(NothingDimens.cardPadding),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)
        ) {
            Icon(
                imageVector = Icons.Default.PhotoCamera,
                contentDescription = null,
                tint = NothingWhite,
                modifier = Modifier.size(24.dp)
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "Photo audit",
                    color = NothingWhite,
                    fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.titleSmall,
                )
                Spacer(modifier = Modifier.height(NothingDimens.textGap))
                Text(
                    text = "Score your dating photos",
                    color = NothingTextSecondary,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
            Icon(
                imageVector = Icons.Default.ChevronRight,
                contentDescription = "Open photo audit",
                tint = NothingTextSecondary,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}

// ─────────────────────────────────────────────
// Auto Profile Builder Card
// ─────────────────────────────────────────────

@Composable
private fun AutoProfileBuilderCard(
    isPaidPlan: Boolean,
    isProOrAbove: Boolean,
    latestBlueprintTheme: String?,
    latestBlueprintSlotCount: Int,
    latestBlueprintDate: String?,
    onClick: () -> Unit,
    onViewLastBlueprint: () -> Unit = {}
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = NothingSurface),
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
    ) {
        Column {
            Row(
                modifier = Modifier
                    .clickable { onClick() }
                    .padding(NothingDimens.cardPadding)
                    .fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(
                    modifier = Modifier.weight(1f),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)
                ) {
                    Icon(
                        imageVector = Icons.Default.AutoAwesome,
                        contentDescription = null,
                        tint = NothingWhite,
                        modifier = Modifier.size(22.dp)
                    )
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Auto-Build Profile",
                            color = NothingWhite,
                            fontWeight = FontWeight.Bold,
                            style = MaterialTheme.typography.titleSmall,
                        )
                        Spacer(modifier = Modifier.height(NothingDimens.textGap))
                        Text(
                            text = "AI-powered profile builder",
                            color = NothingTextSecondary,
                            style = MaterialTheme.typography.labelSmall,
                        )
                    }
                }
                Icon(
                    imageVector = Icons.Default.ChevronRight,
                    contentDescription = "Open",
                    tint = NothingTextSecondary,
                    modifier = Modifier.size(20.dp)
                )
            }

            if (latestBlueprintTheme != null) {
                HorizontalDivider(color = NothingBorder, thickness = NothingDimens.borderThickness / 2)
                Row(
                    modifier = Modifier
                        .clickable { onViewLastBlueprint() }
                        .padding(NothingDimens.cardPadding)
                        .fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Last blueprint",
                            color = NothingTextTertiary,
                            style = MaterialTheme.typography.labelSmall,
                        )
                        Spacer(modifier = Modifier.height(NothingDimens.textGap))
                        Text(
                            text = latestBlueprintTheme,
                            color = NothingWhite,
                            style = MaterialTheme.typography.titleSmall,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                    Text(
                        text = "View \u2192",
                        color = NothingTextSecondary,
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
            }
        }
    }
}

// ─────────────────────────────────────────────
// Overlay Permission Dialog
// ─────────────────────────────────────────────

@Composable
private fun OverlayPermissionDialog(
    onGrantPermission: () -> Unit,
    onDismiss: () -> Unit
) {
    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Card(
            modifier = Modifier
                .fillMaxWidth(0.92f)
                .wrapContentHeight(),
            colors = CardDefaults.cardColors(containerColor = NothingSurface),
            shape = RoundedCornerShape(NothingDimens.cardRadius),
            border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(NothingDimens.cardPadding),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Icon(
                    Icons.Default.Shield,
                    contentDescription = null,
                    tint = NothingWhite,
                    modifier = Modifier.size(48.dp)
                )

                Spacer(modifier = Modifier.height(NothingDimens.elementGap))

                Text(
                    text = "Overlay Permission Required",
                    color = NothingWhite,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )

                Spacer(modifier = Modifier.height(NothingDimens.elementGap))

                Text(
                    text = "Cookd needs overlay permission to float a bubble over your dating apps.",
                    color = NothingTextSecondary,
                    style = MaterialTheme.typography.bodySmall,
                )

                Spacer(modifier = Modifier.height(NothingDimens.elementGap))

                Text(
                    text = "You control when to capture \u2022 Images are encrypted \u2022 No screenshots saved",
                    color = NothingTextTertiary,
                    style = MaterialTheme.typography.labelSmall,
                )

                Spacer(modifier = Modifier.height(NothingDimens.elementGap))

                Button(
                    onClick = onGrantPermission,
                    colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(NothingDimens.minTouchTarget),
                    shape = RoundedCornerShape(NothingDimens.pillRadius)
                ) {
                    Text(
                        "Grant Permission",
                        color = NothingBlack,
                        fontWeight = FontWeight.Bold,
                    )
                }

                Spacer(modifier = Modifier.height(NothingDimens.elementGap))

                TextButton(onClick = onDismiss) {
                    Text("Not now", color = NothingTextSecondary)
                }
            }
        }
    }
}
