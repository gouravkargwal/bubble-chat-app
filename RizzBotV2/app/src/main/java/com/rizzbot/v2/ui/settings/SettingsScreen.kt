package com.rizzbot.v2.ui.settings

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.pulltorefresh.PullToRefreshDefaults
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.*
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.positionInParent
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.roundToInt
import com.rizzbot.v2.domain.model.TierQuota
import com.rizzbot.v2.ui.theme.LockedFeatureGold

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onBack: () -> Unit,
    onPremium: () -> Unit = {},
    onSignedOut: () -> Unit = {},
    onOpenTerms: () -> Unit = {},
    onOpenPrivacy: () -> Unit = {},
    viewModel: SettingsViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    var showSignOutDialog by remember { mutableStateOf(false) }
    var showDeleteAllDataDialog by remember { mutableStateOf(false) }
    var isDeletingData by remember { mutableStateOf(false) }
    var isRefreshing by remember { mutableStateOf(false) }
    val pullRefreshState = rememberPullToRefreshState()
    val scrollState = rememberScrollState()
    var inviteSectionScrollPx by remember { mutableIntStateOf(0) }
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(state.signedOut) {
        if (state.signedOut) onSignedOut()
    }

    if (showSignOutDialog) {
        AlertDialog(
            onDismissRequest = { showSignOutDialog = false },
            title = { Text("Sign Out", color = Color.White) },
            text = { Text("Are you sure you want to sign out? You'll need to sign in again to use Cookd.", color = Color.Gray) },
            confirmButton = {
                TextButton(onClick = {
                    showSignOutDialog = false
                    viewModel.signOut()
                }) {
                    Text("Sign Out", color = Color(0xFFEF5350))
                }
            },
            dismissButton = {
                TextButton(onClick = { showSignOutDialog = false }) {
                    Text("Cancel", color = MaterialTheme.colorScheme.primary)
                }
            },
            containerColor = Color(0xFF1A1A2E)
        )
    }

    if (showDeleteAllDataDialog) {
        AlertDialog(
            onDismissRequest = { if (!isDeletingData) showDeleteAllDataDialog = false },
            title = { Text("Delete All My Data", color = Color.White) },
            text = { 
                Text(
                    "Are you sure? This will permanently wipe your chat history, roasts, and AI voice profile. This cannot be undone.",
                    color = Color.Gray
                ) 
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        isDeletingData = true
                        viewModel.deleteAllData(
                            onSuccess = {
                                isDeletingData = false
                                showDeleteAllDataDialog = false
                                // Optionally sign out after deletion
                                viewModel.signOut()
                            },
                            onError = { error ->
                                isDeletingData = false
                                coroutineScope.launch {
                                    snackbarHostState.showSnackbar(error)
                                }
                            }
                        )
                    },
                    enabled = !isDeletingData
                ) {
                    if (isDeletingData) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            color = Color(0xFFFF5252)
                        )
                    } else {
                        Text("Delete All", color = Color(0xFFFF5252))
                    }
                }
            },
            dismissButton = {
                TextButton(
                    onClick = { showDeleteAllDataDialog = false },
                    enabled = !isDeletingData
                ) {
                    Text("Cancel", color = MaterialTheme.colorScheme.primary)
                }
            },
            containerColor = Color(0xFF1A1A2E)
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text("Settings", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = Color.White)
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
        PullToRefreshBox(
            isRefreshing = isRefreshing,
            onRefresh = {
                coroutineScope.launch {
                    isRefreshing = true
                    try {
                        viewModel.refreshComplete()
                    } finally {
                        isRefreshing = false
                    }
                }
            },
            state = pullRefreshState,
            indicator = {
                PullToRefreshDefaults.Indicator(
                    modifier = Modifier.align(Alignment.TopCenter),
                    isRefreshing = isRefreshing,
                    state = pullRefreshState,
                    containerColor = Color(0xFF1A1A2E),
                    color = MaterialTheme.colorScheme.primary,
                )
            },
            modifier = Modifier.padding(padding)
        ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(16.dp)
        ) {
            // Account section
            Text("ACCOUNT", color = Color.Gray, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(8.dp))

            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    // User info
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.AccountCircle, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(32.dp))
                        Spacer(modifier = Modifier.width(12.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                state.userName ?: "User",
                                color = Color.White,
                                fontWeight = FontWeight.Bold
                            )
                            state.userEmail?.let {
                                Text(it, color = Color.Gray, fontSize = 12.sp)
                            }
                        }
                    }

                    HorizontalDivider(color = Color(0xFF252542), modifier = Modifier.padding(vertical = 12.dp))

                    // Plan info
                    val godModeExpiresAt = state.godModeExpiresAt
                    val isGodMode = godModeExpiresAt != null && godModeExpiresAt.isAfter(java.time.Instant.now())
                    // Backend returns tier="premium" when God Mode is active (via get_effective_tier)
                    // So we should show God Mode if either isGodMode is true OR tier is premium
                    val effectiveTier = if (isGodMode || state.tier == "premium") "premium" else state.tier
                    PlanStatusCard(
                        tier = effectiveTier,
                        isGodMode = isGodMode || state.tier == "premium",
                        godModeExpiresAt = godModeExpiresAt,
                        dailyLimit = state.dailyLimit,
                        billingPeriod = state.billingPeriod,
                        onUpgradeClick = onPremium,
                        onInviteClick = {
                            coroutineScope.launch {
                                scrollState.scrollTo(
                                    inviteSectionScrollPx.coerceIn(0, scrollState.maxValue)
                                )
                            }
                        }
                    )

                    // Active perks for God Mode users
                    if (state.tier == "premium" || state.tier == "god_mode") {
                        Spacer(modifier = Modifier.height(12.dp))
                        Card(
                            colors = CardDefaults.cardColors(containerColor = Color(0xFF14142B)),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(
                                modifier = Modifier.padding(14.dp),
                                verticalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Text(
                                    "Your Active Perks ✨",
                                    color = Color.White,
                                    fontWeight = FontWeight.SemiBold,
                                    fontSize = 13.sp
                                )
                                Text(
                                    text = when {
                                        TierQuota.isUnlimited(state.dailyLimit) ->
                                            "• Unlimited daily AI replies"
                                        else ->
                                            "• Up to ${state.dailyLimit} AI replies per ${TierQuota.billingPeriodNoun(state.billingPeriod)}"
                                    },
                                    color = Color.Gray,
                                    fontSize = 12.sp
                                )
                                Text("• AI Voice Cloning", color = Color.Gray, fontSize = 12.sp)
                                Text(
                                    text = when {
                                        TierQuota.isUnlimited(state.profileAuditsPerWeek) ->
                                            "• Unlimited profile photo audits"
                                        TierQuota.isNotOnPlan(state.profileAuditsPerWeek) ->
                                            "• Profile photo audits not on this plan"
                                        else ->
                                            "• Up to ${state.profileAuditsPerWeek} profile photo audit(s) per week"
                                    },
                                    color = Color.Gray,
                                    fontSize = 12.sp
                                )
                            }
                        }
                    }

                    // Usage Limits section
                    HorizontalDivider(color = Color(0xFF252542), modifier = Modifier.padding(vertical = 12.dp))
                    
                    Text(
                        "Usage Limits",
                        color = Color.White,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 14.sp
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    UsageLimitsDisplay(
                        dailyLimit = state.dailyLimit,
                        dailyUsed = state.dailyUsed,
                        billingPeriod = state.billingPeriod,
                        weeklyAuditsLimit = state.profileAuditsPerWeek,
                        weeklyAuditsUsed = state.weeklyAuditsUsed,
                        weeklyBlueprintsLimit = state.profileBlueprintsPerWeek,
                        weeklyBlueprintsUsed = state.weeklyBlueprintsUsed
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Referral section
            Text(
                "INVITE FRIENDS",
                color = Color.Gray,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.onGloballyPositioned { coordinates ->
                    inviteSectionScrollPx = coordinates.positionInParent().y.roundToInt()
                }
            )
            Spacer(modifier = Modifier.height(8.dp))

            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    state.referral?.let { referral ->
                        // My referral code
                        Text("Your Referral Code", color = Color.Gray, fontSize = 12.sp)
                        Spacer(modifier = Modifier.height(4.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                referral.referralCode,
                                color = Color.White,
                                fontWeight = FontWeight.Bold,
                                fontSize = 20.sp,
                                modifier = Modifier.weight(1f)
                            )
                            IconButton(onClick = {
                                val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                clipboard.setPrimaryClip(ClipData.newPlainText("Referral Code", referral.referralCode))
                            }) {
                                Icon(Icons.Default.ContentCopy, "Copy", tint = MaterialTheme.colorScheme.primary)
                            }
                            IconButton(
                                onClick = {
                                    val intent = Intent(Intent.ACTION_SEND).apply {
                                        type = "text/plain"
                                        putExtra(
                                            Intent.EXTRA_TEXT,
                                            "Use my code ${referral.referralCode} to unlock 24 Hours of God Mode on Cookd! https://cookd.app"
                                        )
                                    }
                                    context.startActivity(Intent.createChooser(intent, "Share Code"))
                                }
                            ) {
                                Icon(Icons.Default.Share, "Share", tint = MaterialTheme.colorScheme.primary)
                            }
                        }

                        Text(
                            "${referral.totalReferrals}/${referral.maxReferrals} friends invited  •  ${referral.bonusRepliesEarned} God Mode unlocks earned",
                            color = Color.Gray,
                            fontSize = 12.sp
                        )

                        HorizontalDivider(
                            color = Color(0xFF252542),
                            modifier = Modifier.padding(vertical = 12.dp)
                        )
                    }

                    // Apply referral code
                    Text("Have a referral code?", color = Color.Gray, fontSize = 12.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        OutlinedTextField(
                            value = state.referralCodeInput,
                            onValueChange = { viewModel.onReferralCodeChanged(it) },
                            placeholder = { Text("Enter code") },
                            modifier = Modifier.weight(1f),
                            singleLine = true,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = MaterialTheme.colorScheme.primary,
                                unfocusedBorderColor = Color(0xFF252542),
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White,
                                cursorColor = MaterialTheme.colorScheme.primary,
                                focusedPlaceholderColor = Color.Gray,
                                unfocusedPlaceholderColor = Color.Gray
                            ),
                            shape = RoundedCornerShape(8.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Button(
                            onClick = { viewModel.applyReferralCode() },
                            enabled = state.referralCodeInput.isNotBlank() && !state.isApplyingReferral,
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            if (state.isApplyingReferral) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(16.dp),
                                    color = Color.White,
                                    strokeWidth = 2.dp
                                )
                            } else {
                                Text("Apply")
                            }
                        }
                    }

                    state.referralApplyResult?.let { result ->
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            result,
                            color = if (result.startsWith("+")) Color(0xFF4CAF50) else Color(0xFFEF5350),
                            fontSize = 12.sp
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                val isGodMode = state.tier == "premium" || state.tier == "god_mode"
                if (isGodMode) {
                    // Manage subscription entry point for God Mode users
                    Button(
                        onClick = {
                            val intent = Intent(
                                Intent.ACTION_VIEW,
                                Uri.parse("https://play.google.com/store/account/subscriptions")
                            )
                            context.startActivity(intent)
                        },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF252542)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text(
                            "Manage Subscription",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                } else {
                    Button(
                        onClick = onPremium,
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = LockedFeatureGold),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text(
                            "Compare Plans & Upgrades",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Support & Links
            Text("MORE", color = Color.Gray, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(8.dp))

            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)), shape = RoundedCornerShape(16.dp)) {
                Column {
                    SettingsRow(icon = Icons.Default.SupportAgent, label = "Get Support", onClick = {
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://tawk.to/chat/cookd")))
                    })
                    HorizontalDivider(color = Color(0xFF252542))
                    SettingsRow(icon = Icons.Default.Share, label = "Share Cookd", onClick = {
                        val intent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(Intent.EXTRA_TEXT, "Check out Cookd - AI dating chat assistant! https://cookd.app")
                        }
                        context.startActivity(Intent.createChooser(intent, "Share Cookd"))
                    })
                    HorizontalDivider(color = Color(0xFF252542))
                    SettingsRow(icon = Icons.Default.Article, label = "Terms of Service", onClick = onOpenTerms)
                    HorizontalDivider(color = Color(0xFF252542))
                    SettingsRow(icon = Icons.Default.Policy, label = "Privacy Policy", onClick = onOpenPrivacy)
                    HorizontalDivider(color = Color(0xFF252542))
                    SettingsRow(icon = Icons.Default.ExitToApp, label = "Sign Out", onClick = {
                        showSignOutDialog = true
                    })
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Privacy & Data
            Text("PRIVACY & DATA", color = Color.Gray, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(8.dp))

            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
                shape = RoundedCornerShape(16.dp)
            ) {
                SettingsRow(
                    icon = Icons.Default.DeleteForever,
                    label = "Delete All My Data",
                    onClick = { showDeleteAllDataDialog = true },
                    textColor = Color(0xFFFF5252)
                )
            }

            Spacer(modifier = Modifier.height(32.dp))
            Text(
                "v2.0.0",
                color = Color.Gray,
                fontSize = 12.sp,
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Center
            )
        }
        } // PullToRefreshBox
    }
}

@Composable
private fun UsageLimitsDisplay(
    dailyLimit: Int,
    dailyUsed: Int,
    billingPeriod: String,
    weeklyAuditsLimit: Int,
    weeklyAuditsUsed: Int,
    weeklyBlueprintsLimit: Int,
    weeklyBlueprintsUsed: Int = 0
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "Daily AI Replies",
                color = Color.White,
                fontSize = 14.sp
            )
            when {
                TierQuota.isUnlimited(dailyLimit) -> Text(
                    "Unlimited",
                    color = Color(0xFF4CAF50),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
                TierQuota.isNotOnPlan(dailyLimit) -> Text(
                    "Not on your plan",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
                else -> Text(
                    "$dailyUsed of $dailyLimit used",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
            }
        }

        if (TierQuota.isFinite(dailyLimit)) {
            val progress = (dailyUsed.toFloat() / dailyLimit).coerceIn(0f, 1f)
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp)),
                color = if (progress >= 1f) Color(0xFFEF5350) else MaterialTheme.colorScheme.primary,
                trackColor = Color(0xFF252542)
            )
            Text(
                when (billingPeriod.lowercase()) {
                    "weekly" -> "Resets each billing week."
                    "monthly" -> "Resets each billing month."
                    else -> "Resets every 24 hours."
                },
                color = Color.Gray,
                fontSize = 11.sp
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
        HorizontalDivider(color = Color(0xFF252542))
        Spacer(modifier = Modifier.height(8.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "Weekly Photo Audits",
                color = Color.White,
                fontSize = 14.sp
            )
            when {
                TierQuota.isUnlimited(weeklyAuditsLimit) -> Text(
                    "Unlimited",
                    color = Color(0xFF4CAF50),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
                TierQuota.isNotOnPlan(weeklyAuditsLimit) -> Text(
                    "Not on your plan",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
                else -> Text(
                    "$weeklyAuditsUsed of $weeklyAuditsLimit used",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
            }
        }

        if (TierQuota.isFinite(weeklyAuditsLimit)) {
            val progress =
                (weeklyAuditsUsed.toFloat() / weeklyAuditsLimit).coerceIn(0f, 1f)
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp)),
                color = if (progress >= 1f) Color(0xFFEF5350) else MaterialTheme.colorScheme.primary,
                trackColor = Color(0xFF252542)
            )
            Text(
                "Resets every Monday.",
                color = Color.Gray,
                fontSize = 11.sp
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
        HorizontalDivider(color = Color(0xFF252542))
        Spacer(modifier = Modifier.height(8.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "Weekly Profile Blueprints",
                color = Color.White,
                fontSize = 14.sp
            )
            when {
                TierQuota.isUnlimited(weeklyBlueprintsLimit) -> Text(
                    "Unlimited",
                    color = Color(0xFF4CAF50),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
                TierQuota.isNotOnPlan(weeklyBlueprintsLimit) -> Text(
                    "Not on your plan",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
                else -> Text(
                    "$weeklyBlueprintsUsed of $weeklyBlueprintsLimit used",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
            }
        }

        if (TierQuota.isFinite(weeklyBlueprintsLimit)) {
            val progress =
                (weeklyBlueprintsUsed.toFloat() / weeklyBlueprintsLimit).coerceIn(0f, 1f)
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp)),
                color = if (progress >= 1f) Color(0xFFEF5350) else MaterialTheme.colorScheme.primary,
                trackColor = Color(0xFF252542)
            )
            Text(
                "Resets every Monday.",
                color = Color.Gray,
                fontSize = 11.sp
            )
        }
    }
}

@Composable
private fun PlanStatusCard(
    tier: String,
    isGodMode: Boolean,
    godModeExpiresAt: java.time.Instant?,
    dailyLimit: Int,
    billingPeriod: String,
    onUpgradeClick: () -> Unit,
    onInviteClick: () -> Unit
) {
    // Live timer state for God Mode countdown
    var currentTime by remember { mutableStateOf(java.time.Instant.now()) }
    
    // Update timer every second when in God Mode
    LaunchedEffect(godModeExpiresAt) {
        if (isGodMode && godModeExpiresAt != null) {
            while (true) {
                delay(1000L)
                currentTime = java.time.Instant.now()
            }
        }
    }
    
    // Determine card styling based on tier
    val cardBackground = if (isGodMode || tier == "premium") {
        Color(0xFF221A22) // Subtle pink tint — gold is reserved for locked / upgrade CTAs
    } else {
        Color(0xFF1A1A2E)
    }

    val cardBorder = if (isGodMode || tier == "premium") {
        BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.45f))
    } else {
        null
    }
    
    Card(
        colors = CardDefaults.cardColors(containerColor = cardBackground),
        shape = RoundedCornerShape(16.dp),
        border = cardBorder,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Icon and Plan Text Row
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    Icons.Default.WorkspacePremium,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(12.dp))

                Column(modifier = Modifier.weight(1f)) {
                    when {
                        // Check God Mode first - either isGodMode is true OR tier is premium (from backend effective tier)
                        isGodMode || tier == "premium" -> {
                            Text(
                                "GOD MODE ACTIVE",
                                color = MaterialTheme.colorScheme.primary,
                                fontWeight = FontWeight.Bold
                            )
                            godModeExpiresAt?.let { expiresAt ->
                                val duration = java.time.Duration.between(currentTime, expiresAt)
                                if (duration.isNegative || duration.isZero) {
                                    Text(
                                        "Expired",
                                        color = Color.Gray,
                                        fontSize = 12.sp
                                    )
                                } else {
                                    val hoursRemaining = duration.toHours()
                                    val minutesRemaining = duration.toMinutes() % 60
                                    val secondsRemaining = duration.seconds % 60
                                    Text(
                                        "Expires in ${hoursRemaining}h ${minutesRemaining}m ${secondsRemaining}s",
                                        color = Color.Gray,
                                        fontSize = 12.sp
                                    )
                                }
                            } ?: run {
                                Text(
                                    "Full tier perks — see Usage Limits below for your live quotas.",
                                    color = Color.Gray,
                                    fontSize = 12.sp
                                )
                            }
                        }
                        tier == "pro" -> {
                            Text(
                                "Pro Wingman Active",
                                color = Color(0xFF7C4DFF),
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                when {
                                    TierQuota.isUnlimited(dailyLimit) ->
                                        "Voice DNA and expanded vibes. Unlimited replies on your plan."
                                    TierQuota.isFinite(dailyLimit) ->
                                        "Higher reply caps than Free — up to $dailyLimit AI replies per ${TierQuota.billingPeriodNoun(billingPeriod)} • Voice DNA."
                                    else ->
                                        "Expanded tools and Voice DNA — quotas in Usage Limits below."
                                },
                                color = Color.Gray,
                                fontSize = 12.sp
                            )
                        }
                        else -> {
                            Text(
                                "Basic Wingman (Free)",
                                color = Color.White,
                                fontWeight = FontWeight.Medium
                            )
                            Text(
                                when {
                                    TierQuota.isFinite(dailyLimit) ->
                                        "Up to $dailyLimit AI replies per ${TierQuota.billingPeriodNoun(billingPeriod)}."
                                    TierQuota.isUnlimited(dailyLimit) ->
                                        "Plan includes unlimited daily replies."
                                    else ->
                                        "Standard access — see Usage Limits for quotas."
                                },
                                color = Color.Gray,
                                fontSize = 12.sp
                            )
                        }
                    }
                }
            }

            // Upgrade Button (only show if not in God Mode)
            when {
                isGodMode || tier == "premium" -> {
                    // No upgrade button when in God Mode
                }
                tier == "pro" -> {
                    Button(
                        onClick = onUpgradeClick,
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = LockedFeatureGold),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text("Upgrade Plan", fontSize = 13.sp, color = Color.Black, fontWeight = FontWeight.SemiBold)
                    }
                }
                else -> {
                    Button(
                        onClick = onUpgradeClick,
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = LockedFeatureGold),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text(
                            "Upgrade Plan",
                            fontSize = 13.sp,
                            color = Color.Black,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }
            }

            TextButton(
                onClick = onInviteClick,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    "Invite friends — earn God Mode",
                    color = Color(0xFF9E9EAE),
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium
                )
            }
        }
    }
}

@Composable
private fun SettingsRow(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    onClick: () -> Unit,
    textColor: Color = Color.White
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
        Spacer(modifier = Modifier.width(16.dp))
        Text(label, color = textColor, modifier = Modifier.weight(1f))
        Icon(Icons.Default.ChevronRight, contentDescription = null, tint = Color.Gray, modifier = Modifier.size(20.dp))
    }
}
