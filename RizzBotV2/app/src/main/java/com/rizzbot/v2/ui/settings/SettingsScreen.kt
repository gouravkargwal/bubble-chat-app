package com.rizzbot.v2.ui.settings

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import kotlinx.coroutines.launch
import kotlin.math.roundToInt
import com.rizzbot.v2.R
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
    val appPublicLink = stringResource(R.string.app_public_link)
    val shareAppText = stringResource(R.string.share_app_body, appPublicLink)
    val supportEmail = stringResource(R.string.support_email)
    val supportEmailSubject = stringResource(R.string.support_email_subject)
    val supportEmailChooserTitle = stringResource(R.string.support_email_chooser_title)
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
                    val isPaidPlan = state.tier == TierQuota.PLAN_CRUSH ||
                        state.tier == TierQuota.PLAN_MATCH ||
                        state.tier == TierQuota.PLAN_RIZZ
                    PlanStatusCard(
                        tier = state.tier,
                        isPaidPlan = isPaidPlan,
                        creditsRemaining = state.creditsRemaining,
                        creditsPeriodLimit = state.creditsPeriodLimit,
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

                    // Active perks for paid users
                    if (isPaidPlan) {
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
                                    "• ${state.creditsRemaining} credits remaining this ${TierQuota.billingPeriodNoun(state.billingPeriod)}",
                                    color = Color.Gray,
                                    fontSize = 12.sp
                                )
                                Text(
                                    "• Audit costs ${TierQuota.CREDIT_COST_AUDIT} credits, Blueprint costs ${TierQuota.CREDIT_COST_BLUEPRINT} credits",
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
                        creditsRemaining = state.creditsRemaining,
                        creditsPeriodLimit = state.creditsPeriodLimit,
                        billingPeriod = state.billingPeriod,
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
                                    val text = context.getString(
                                        R.string.share_referral_body,
                                        referral.referralCode,
                                        appPublicLink
                                    )
                                    val intent = Intent(Intent.ACTION_SEND).apply {
                                        type = "text/plain"
                                        putExtra(Intent.EXTRA_TEXT, text)
                                    }
                                    context.startActivity(Intent.createChooser(intent, "Share Code"))
                                }
                            ) {
                                Icon(Icons.Default.Share, "Share", tint = MaterialTheme.colorScheme.primary)
                            }
                        }

                        Text(
                            "${referral.totalReferrals}/${referral.maxReferrals} friends invited  •  ${referral.bonusRepliesEarned} bonus credits earned",
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

                val isPaidPlanReferralSection = state.tier == TierQuota.PLAN_CRUSH ||
                    state.tier == TierQuota.PLAN_MATCH ||
                    state.tier == TierQuota.PLAN_RIZZ
                if (isPaidPlanReferralSection) {
                    // Manage subscription entry point for paid users
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
                    SettingsRow(icon = Icons.Default.Email, label = "Email Support", onClick = {
                        val mailUri = Uri.parse(
                            "mailto:${Uri.encode(supportEmail)}?subject=${Uri.encode(supportEmailSubject)}"
                        )
                        val intent = Intent(Intent.ACTION_SENDTO).apply { data = mailUri }
                        if (intent.resolveActivity(context.packageManager) != null) {
                            context.startActivity(
                                Intent.createChooser(intent, supportEmailChooserTitle)
                            )
                        } else {
                            coroutineScope.launch {
                                snackbarHostState.showSnackbar(
                                    context.getString(R.string.support_no_email_app, supportEmail)
                                )
                            }
                        }
                    })
                    HorizontalDivider(color = Color(0xFF252542))
                    SettingsRow(icon = Icons.Default.Share, label = "Share Cookd", onClick = {
                        val intent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(Intent.EXTRA_TEXT, shareAppText)
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
    creditsRemaining: Int,
    creditsPeriodLimit: Int,
    billingPeriod: String,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "Credits Remaining",
                color = Color.White,
                fontSize = 14.sp
            )
            when {
                creditsPeriodLimit <= 0 -> Text(
                    "$creditsRemaining credits",
                    color = Color(0xFF4CAF50),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
                else -> Text(
                    "$creditsRemaining of $creditsPeriodLimit",
                    color = if (creditsRemaining == 0) Color(0xFFEF5350) else Color.Gray,
                    fontSize = 12.sp
                )
            }
        }

        if (creditsPeriodLimit > 0) {
            val creditsUsed = (creditsPeriodLimit - creditsRemaining).coerceAtLeast(0)
            val progress = (creditsUsed.toFloat() / creditsPeriodLimit).coerceIn(0f, 1f)
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
                    else -> "Resets each billing period."
                },
                color = Color.Gray,
                fontSize = 11.sp
            )
        }
    }
}

@Composable
private fun PlanStatusCard(
    tier: String,
    isPaidPlan: Boolean,
    creditsRemaining: Int,
    creditsPeriodLimit: Int,
    billingPeriod: String,
    onUpgradeClick: () -> Unit,
    onInviteClick: () -> Unit
) {
    val cardBackground = if (isPaidPlan) {
        Color(0xFF221A22)
    } else {
        Color(0xFF1A1A2E)
    }

    val cardBorder = if (isPaidPlan) {
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
                    when (tier) {
                        TierQuota.PLAN_RIZZ -> {
                            Text(
                                "Rizz Plan Active",
                                color = MaterialTheme.colorScheme.primary,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                "$creditsRemaining credits remaining this ${TierQuota.billingPeriodNoun(billingPeriod)}.",
                                color = Color.Gray,
                                fontSize = 12.sp
                            )
                        }
                        TierQuota.PLAN_MATCH -> {
                            Text(
                                "Match Plan Active ⭐",
                                color = MaterialTheme.colorScheme.primary,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                "$creditsRemaining credits remaining this ${TierQuota.billingPeriodNoun(billingPeriod)}.",
                                color = Color.Gray,
                                fontSize = 12.sp
                            )
                        }
                        TierQuota.PLAN_CRUSH -> {
                            Text(
                                "Crush Plan Active",
                                color = Color(0xFFB388FF),
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                "$creditsRemaining credits remaining this ${TierQuota.billingPeriodNoun(billingPeriod)}.",
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
                                "Upgrade to get credits for AI replies, photo audits, and profile blueprints.",
                                color = Color.Gray,
                                fontSize = 12.sp
                            )
                        }
                    }
                }
            }

            // Upgrade Button (only show if not on top tier)
            if (tier != TierQuota.PLAN_RIZZ) {
                Button(
                    onClick = onUpgradeClick,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = LockedFeatureGold),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        if (isPaidPlan) "Upgrade Plan" else "Compare Plans & Upgrade",
                        fontSize = 13.sp,
                        color = Color.Black,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }

            TextButton(
                onClick = onInviteClick,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    "Invite friends — earn bonus credits",
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
