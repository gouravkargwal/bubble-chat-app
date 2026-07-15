package com.rizzbot.v2.ui.settings

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
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
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import com.rizzbot.v2.domain.model.TierQuota
import com.rizzbot.v2.ui.components.PlanCardSkeleton
import com.rizzbot.v2.ui.components.RedeemCodeCard
import com.rizzbot.v2.ui.components.RedeemCodeSkeleton
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingError
import com.rizzbot.v2.ui.theme.NothingSuccess
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite

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
    val isPullRefreshing by viewModel.isPullRefreshing.collectAsState()
    val pullRefreshState = rememberPullToRefreshState()
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    var showSignOutDialog by remember { mutableStateOf(false) }
    var showDeleteAllDataDialog by remember { mutableStateOf(false) }
    var isDeletingData by remember { mutableStateOf(false) }
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(state.signedOut) {
        if (state.signedOut) onSignedOut()
    }

    if (showSignOutDialog) {
        AlertDialog(
            onDismissRequest = { showSignOutDialog = false },
            title = { Text("Sign Out", color = NothingWhite) },
            text = { Text("Are you sure you want to sign out?", color = NothingTextSecondary) },
            confirmButton = {
                TextButton(onClick = { showSignOutDialog = false; viewModel.signOut() }) {
                    Text("Sign Out", color = NothingError)
                }
            },
            dismissButton = {
                TextButton(onClick = { showSignOutDialog = false }) {
                    Text("Cancel", color = NothingTextSecondary)
                }
            },
            containerColor = NothingSurface,
            shape = RoundedCornerShape(NothingDimens.cardRadius)
        )
    }

    if (showDeleteAllDataDialog) {
        AlertDialog(
            onDismissRequest = { if (!isDeletingData) showDeleteAllDataDialog = false },
            title = { Text("Delete All My Data", color = NothingWhite) },
            text = { Text("This will permanently wipe your data. Cannot be undone.", color = NothingTextSecondary) },
            confirmButton = {
                TextButton(
                    onClick = {
                        isDeletingData = true
                        viewModel.deleteAllData(
                            onSuccess = { isDeletingData = false; showDeleteAllDataDialog = false; viewModel.signOut() },
                            onError = { error ->
                                isDeletingData = false
                                coroutineScope.launch { snackbarHostState.showSnackbar(error) }
                            }
                        )
                    },
                    enabled = !isDeletingData
                ) { Text("Delete All", color = NothingError) }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteAllDataDialog = false }, enabled = !isDeletingData) {
                    Text("Cancel", color = NothingTextSecondary)
                }
            },
            containerColor = NothingSurface,
            shape = RoundedCornerShape(NothingDimens.cardRadius)
        )
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text("Settings", fontWeight = FontWeight.Bold, color = NothingWhite) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = NothingWhite)
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
                        .padding(NothingDimens.screenPadding)
                ) {
            // ── REDEEM CODE (simple input, no pricing/selling — Google Play safe) ──
            if (!state.isLtd) {
                Text("REDEEM CODE", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(NothingDimens.elementGap))
                if (state.usageLoaded) {
                    RedeemCodeCard(
                        ltdCodeInput = state.ltdCodeInput,
                        onLTDCodeChanged = { viewModel.onLTDCodeChanged(it) },
                        onRedeemClick = { viewModel.redeemLTDCode() },
                        isRedeemingLTD = state.isRedeemingLTD,
                        ltdRedeemResult = state.ltdRedeemResult,
                    )
                } else {
                    RedeemCodeSkeleton()
                }
                Spacer(Modifier.height(NothingDimens.sectionSpacing))
            }

            // ── ACCOUNT + PLAN CARD ──
            Text("ACCOUNT", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(NothingDimens.elementGap))

            if (state.usageLoaded) {
                Card(
                    colors = CardDefaults.cardColors(containerColor = NothingSurface),
                    shape = RoundedCornerShape(NothingDimens.cardRadius),
                    border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
                ) {
                    Column(Modifier.padding(NothingDimens.cardPadding)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.AccountCircle, contentDescription = null, tint = NothingWhite, modifier = Modifier.size(36.dp))
                            Spacer(Modifier.width(NothingDimens.elementGap))
                            Column(Modifier.weight(1f)) {
                                Text(state.userName ?: "User", color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall)
                                state.userEmail?.let {
                                    Spacer(Modifier.height(2.dp))
                                    Text(it, color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                                }
                            }
                        }

                        HorizontalDivider(color = NothingBorder, modifier = Modifier.padding(vertical = NothingDimens.elementGap))

                        CompactPlanCard(
                            tier = state.tier,
                            isOnTrial = state.isOnTrial,
                            trialDaysRemaining = state.trialDaysRemaining,
                            creditsRemaining = state.creditsRemaining,
                            creditsPeriodLimit = state.creditsPeriodLimit,
                            billingPeriod = state.billingPeriod,
                            onUpgradeClick = onPremium,
                            isLtd = state.isLtd,
                        )
                    }
                }
            } else {
                PlanCardSkeleton()
            }

            Spacer(modifier = Modifier.height(NothingDimens.sectionSpacing))
            Text("INVITE FRIENDS", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))

            Card(
                colors = CardDefaults.cardColors(containerColor = NothingSurface),
                shape = RoundedCornerShape(NothingDimens.cardRadius),
                border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
            ) {
                Column(modifier = Modifier.padding(NothingDimens.cardPadding)) {
                    state.referral?.let { referral ->
                        Text("Your Referral Code", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                        Spacer(modifier = Modifier.height(NothingDimens.textGap))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(referral.referralCode, color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
                            IconButton(onClick = {
                                val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                clipboard.setPrimaryClip(ClipData.newPlainText("Referral Code", referral.referralCode))
                            }) { Icon(Icons.Default.ContentCopy, "Copy", tint = NothingTextSecondary) }
                            IconButton(onClick = {
                                val shareText = "Use my code ${referral.referralCode} to join me on Cookd! 🚀\n\nhttps://play.google.com/store/apps/details?id=com.cookd.mobile"
                                val intent = Intent(Intent.ACTION_SEND).apply {
                                    type = "text/plain"
                                    putExtra(Intent.EXTRA_TEXT, shareText)
                                }
                                context.startActivity(Intent.createChooser(intent, "Share Code"))
                            }) { Icon(Icons.Default.Share, "Share", tint = NothingTextSecondary) }
                        }
                        Text("${referral.totalReferrals}/${referral.maxReferrals} invited", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall)
                        HorizontalDivider(color = NothingBorder, modifier = Modifier.padding(vertical = NothingDimens.elementGap))
                    }

                    Text("Have a referral code?", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall)
                    Spacer(modifier = Modifier.height(NothingDimens.textGap))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        OutlinedTextField(
                            value = state.referralCodeInput,
                            onValueChange = { viewModel.onReferralCodeChanged(it) },
                            placeholder = { Text("Enter code", color = NothingTextTertiary) },
                            modifier = Modifier.weight(1f),
                            singleLine = true,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = NothingWhite,
                                unfocusedBorderColor = NothingBorder,
                                focusedTextColor = NothingWhite,
                                unfocusedTextColor = NothingWhite,
                                cursorColor = NothingWhite,
                            ),
                            shape = RoundedCornerShape(NothingDimens.cardRadius)
                        )
                        Spacer(modifier = Modifier.width(NothingDimens.elementGap))
                        Button(
                            onClick = { viewModel.applyReferralCode() },
                            enabled = state.referralCodeInput.isNotBlank() && !state.isApplyingReferral,
                            colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
                            shape = RoundedCornerShape(NothingDimens.pillRadius)
                        ) { Text("Apply", color = NothingBlack) }
                    }
                }
            }

            Spacer(modifier = Modifier.height(NothingDimens.sectionSpacing))
            Text("MORE", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))

            Card(
                colors = CardDefaults.cardColors(containerColor = NothingSurface),
                shape = RoundedCornerShape(NothingDimens.cardRadius),
                border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
            ) {
                Column {
                    SettingsRow(icon = Icons.Default.Email, label = "Email Support", onClick = {})
                    HorizontalDivider(color = NothingBorder)
                    SettingsRow(icon = Icons.Default.Share, label = "Share Cookd", onClick = {
                        val shareText = "Check out Cookd — AI replies for dating apps! 🚀\n\nhttps://play.google.com/store/apps/details?id=com.cookd.mobile"
                        val intent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(Intent.EXTRA_TEXT, shareText)
                        }
                        context.startActivity(Intent.createChooser(intent, "Share Cookd"))
                    })
                    HorizontalDivider(color = NothingBorder)
                    SettingsRow(icon = Icons.Default.Article, label = "Terms of Service", onClick = onOpenTerms)
                    HorizontalDivider(color = NothingBorder)
                    SettingsRow(icon = Icons.Default.Policy, label = "Privacy Policy", onClick = onOpenPrivacy)
                    HorizontalDivider(color = NothingBorder)
                    SettingsRow(icon = Icons.Default.ExitToApp, label = "Sign Out", onClick = { showSignOutDialog = true })
                }
            }

            Spacer(modifier = Modifier.height(NothingDimens.sectionSpacing))
            Text("PRIVACY & DATA", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))

            Card(
                colors = CardDefaults.cardColors(containerColor = NothingSurface),
                shape = RoundedCornerShape(NothingDimens.cardRadius),
                border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
            ) {
                Column {
                    // Marketing consent toggle
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(horizontal = NothingDimens.cardPadding, vertical = NothingDimens.elementGap),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Share, contentDescription = null, tint = NothingWhite, modifier = Modifier.size(22.dp))
                        Spacer(modifier = Modifier.width(NothingDimens.elementGap))
                        Column(modifier = Modifier.weight(1f)) {
                            Text("Allow marketing use of my data", color = NothingWhite, style = MaterialTheme.typography.titleSmall)
                            Text("Your name and chat messages may appear in Cookd social media videos", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                        }
                        Switch(
                            checked = state.marketingConsent,
                            onCheckedChange = { viewModel.setMarketingConsent(it) },
                            colors = SwitchDefaults.colors(checkedTrackColor = NothingWhite, checkedThumbColor = NothingBlack)
                        )
                    }
                    HorizontalDivider(color = NothingBorder)
                    SettingsRow(icon = Icons.Default.DeleteForever, label = "Delete All My Data", onClick = { showDeleteAllDataDialog = true }, textColor = NothingError)
                }
            }

            Spacer(modifier = Modifier.height(NothingDimens.sectionSpacing))
            Text("v2.0.0", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center)
            }
        }
    }
    }
}

@Composable
private fun CompactPlanCard(
    tier: String,
    isOnTrial: Boolean = false,
    trialDaysRemaining: Int = 0,
    creditsRemaining: Int,
    creditsPeriodLimit: Int,
    billingPeriod: String,
    onUpgradeClick: () -> Unit,
    isLtd: Boolean = false,
) {
    val isPaidPlan = tier in listOf(TierQuota.PLAN_CRUSH, TierQuota.PLAN_MATCH)

    Card(
        colors = CardDefaults.cardColors(containerColor = NothingSurface),
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        border = BorderStroke(NothingDimens.borderThickness, NothingBorder),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(NothingDimens.cardPadding)) {
            // Plan name row
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.WorkspacePremium, contentDescription = null, tint = NothingWhite, modifier = Modifier.size(24.dp))
                Spacer(modifier = Modifier.width(NothingDimens.elementGap))
                Column(modifier = Modifier.weight(1f)) {
                    val planName = when {
                        isLtd -> "Match Plan \u221E (Lifetime)"
                        isOnTrial -> "Free Trial Active"
                        tier == TierQuota.PLAN_CRUSH -> "Crush Plan Active"
                        tier == TierQuota.PLAN_MATCH -> "Match Plan Active"
                        tier == TierQuota.PLAN_RIZZ -> "Rizz Plan Active"
                        else -> "Basic (Free)"
                    }
                    Text(planName, color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall)
                    if (isLtd) {
                        Text("Pay once, own forever \u2728", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                    } else if (isOnTrial) {
                        Text("$trialDaysRemaining days left", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                    }
                }
                if (isLtd) {
                    Column(horizontalAlignment = Alignment.End) {
                        Text("∞", color = NothingSuccess, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                        Text("unlimited", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall)
                    }
                } else {
                    Text("$creditsRemaining", color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                }
            }

            if (isLtd) {
                // LTD: clean unlimited summary — no numbers, no progress bar
                Spacer(modifier = Modifier.height(8.dp))
                Box(
                    modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(NothingBorder.copy(alpha = 0.15f)).padding(horizontal = 12.dp, vertical = 10.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceEvenly, modifier = Modifier.fillMaxWidth()) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text("∞", color = NothingSuccess, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                            Text("conversations", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall)
                        }
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text("9", color = NothingWhite, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                            Text("directions", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall)
                        }
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text("∞", color = NothingSuccess, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                            Text("no expiry", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }
            } else {
                // Credit description
                Text(
                    when {
                        isPaidPlan -> "per ${TierQuota.billingPeriodNoun(billingPeriod)}"
                        else -> "Signup bonus + ${TierQuota.FREE_DAILY_CREDITS}/day free"
                    },
                    color = NothingTextTertiary,
                    style = MaterialTheme.typography.labelSmall,
                )

                // Progress bar for paid plans
                if (isPaidPlan && creditsPeriodLimit > 0) {
                    Spacer(modifier = Modifier.height(6.dp))
                    val creditsUsed = (creditsPeriodLimit - creditsRemaining).coerceAtLeast(0)
                    val progress = (creditsUsed.toFloat() / creditsPeriodLimit).coerceIn(0f, 1f)
                    LinearProgressIndicator(
                        progress = { progress },
                        modifier = Modifier.fillMaxWidth().height(4.dp).clip(RoundedCornerShape(2.dp)),
                        color = if (progress >= 0.8f) NothingError else NothingWhite,
                        trackColor = NothingBorder,
                    )
                    val resetText = TierQuota.billingPeriodNoun(billingPeriod)
                    Text(
                        "${creditsUsed}/${creditsPeriodLimit} used • resets $resetText",
                        color = NothingTextTertiary,
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
            }

            // Upgrade CTA — hidden for LTD users who already have the top tier
            if (!isLtd && (!isPaidPlan || isOnTrial)) {
                Spacer(modifier = Modifier.height(NothingDimens.elementGap))
                Button(
                    onClick = onUpgradeClick,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
                    shape = RoundedCornerShape(NothingDimens.pillRadius)
                ) { Text("Upgrade", color = NothingBlack, fontWeight = FontWeight.SemiBold) }
            }
        }
    }
}
@Composable
private fun SettingsRow(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String, onClick: () -> Unit, textColor: Color = NothingWhite) {
    Row(
        modifier = Modifier.fillMaxWidth().clickable { onClick() }.padding(horizontal = NothingDimens.cardPadding, vertical = NothingDimens.elementGap),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = NothingWhite, modifier = Modifier.size(22.dp))
        Spacer(modifier = Modifier.width(NothingDimens.elementGap))
        Text(label, color = textColor, style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
        Icon(Icons.Default.ChevronRight, contentDescription = null, tint = NothingTextSecondary, modifier = Modifier.size(20.dp))
    }
}
