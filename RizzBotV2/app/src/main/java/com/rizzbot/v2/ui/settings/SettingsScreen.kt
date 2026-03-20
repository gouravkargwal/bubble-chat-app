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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onBack: () -> Unit,
    onPremium: () -> Unit = {},
    onSignedOut: () -> Unit = {},
    viewModel: SettingsViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    var showSignOutDialog by remember { mutableStateOf(false) }
    var showDeleteAllDataDialog by remember { mutableStateOf(false) }
    var isDeletingData by remember { mutableStateOf(false) }
    var isRefreshing by remember { mutableStateOf(false) }

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
                    Text("Cancel", color = Color(0xFFE91E63))
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
                                // Show error toast or handle error
                                android.widget.Toast.makeText(context, error, android.widget.Toast.LENGTH_LONG).show()
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
                    Text("Cancel", color = Color(0xFFE91E63))
                }
            },
            containerColor = Color(0xFF1A1A2E)
        )
    }

    Scaffold(
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
                    viewModel.refresh()
                    delay(800L)
                    isRefreshing = false
                }
            },
            modifier = Modifier.padding(padding)
        ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
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
                        Icon(Icons.Default.AccountCircle, contentDescription = null, tint = Color(0xFFE91E63), modifier = Modifier.size(32.dp))
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
                        onUpgradeClick = onPremium,
                        onInviteClick = { /* Scroll to referral section or handle invite */ }
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
                                Text("• Unlimited Replies", color = Color.Gray, fontSize = 12.sp)
                                Text("• AI Voice Cloning", color = Color.Gray, fontSize = 12.sp)
                                Text("• Profile Roaster", color = Color.Gray, fontSize = 12.sp)
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
                        weeklyUsed = state.weeklyUsed,
                        monthlyUsed = state.monthlyUsed,
                        billingPeriod = state.billingPeriod,
                        isPremium = state.isPremium,
                        weeklyAuditsLimit = state.profileAuditsPerWeek,
                        weeklyAuditsUsed = state.weeklyAuditsUsed,
                        weeklyBlueprintsLimit = state.profileBlueprintsPerWeek,
                        weeklyBlueprintsUsed = state.weeklyBlueprintsUsed
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Referral section
            Text("INVITE FRIENDS", color = Color.Gray, fontSize = 12.sp, fontWeight = FontWeight.Bold)
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
                                Icon(Icons.Default.ContentCopy, "Copy", tint = Color(0xFFE91E63))
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
                                Icon(Icons.Default.Share, "Share", tint = Color(0xFFE91E63))
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
                                focusedBorderColor = Color(0xFFE91E63),
                                unfocusedBorderColor = Color(0xFF252542),
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White,
                                cursorColor = Color(0xFFE91E63),
                                focusedPlaceholderColor = Color.Gray,
                                unfocusedPlaceholderColor = Color.Gray
                            ),
                            shape = RoundedCornerShape(8.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Button(
                            onClick = { viewModel.applyReferralCode() },
                            enabled = state.referralCodeInput.isNotBlank() && !state.isApplyingReferral,
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63)),
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
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63)),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text(
                            "Compare Plans & Upgrades",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold
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
                    SettingsRow(icon = Icons.Default.Policy, label = "Privacy Policy", onClick = {
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://cookd.app/privacy")))
                    })
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
    weeklyUsed: Int,
    monthlyUsed: Int,
    billingPeriod: String,
    isPremium: Boolean,
    weeklyAuditsLimit: Int,
    weeklyAuditsUsed: Int,
    weeklyBlueprintsLimit: Int,
    weeklyBlueprintsUsed: Int = 0
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        // Label and usage count row
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
            if (isPremium && dailyLimit == 0) {
                Text(
                    "UNLIMITED",
                    color = Color(0xFF4CAF50),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
            } else {
                Text(
                    "$dailyUsed of $dailyLimit used",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
            }
        }
        
        // Progress bar (only show if not unlimited)
        if (!(isPremium && dailyLimit == 0)) {
            val progress = if (dailyLimit > 0) (dailyUsed.toFloat() / dailyLimit).coerceIn(0f, 1f) else 0f
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp)),
                color = if (progress >= 1f) Color(0xFFEF5350) else Color(0xFFE91E63),
                trackColor = Color(0xFF252542)
            )
            
            // Reset text
            Text(
                "Resets every 24 hours.",
                color = Color.Gray,
                fontSize = 11.sp
            )
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        HorizontalDivider(color = Color(0xFF252542))
        Spacer(modifier = Modifier.height(8.dp))
        
        // Weekly Profile Audits
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
            if (isPremium && weeklyAuditsLimit == 0) {
                Text(
                    "UNLIMITED",
                    color = Color(0xFF4CAF50),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
            } else {
                Text(
                    "$weeklyAuditsUsed of $weeklyAuditsLimit used",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
            }
        }
        
        // Progress bar (only show if not unlimited)
        if (!(isPremium && weeklyAuditsLimit == 0)) {
            val progress = if (weeklyAuditsLimit > 0) (weeklyAuditsUsed.toFloat() / weeklyAuditsLimit).coerceIn(0f, 1f) else 0f
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp)),
                color = if (progress >= 1f) Color(0xFFEF5350) else Color(0xFFE91E63),
                trackColor = Color(0xFF252542)
            )
            
            // Reset text
            Text(
                "Resets every Monday.",
                color = Color.Gray,
                fontSize = 11.sp
            )
        }

        if (weeklyBlueprintsLimit > 0) {
            Spacer(modifier = Modifier.height(16.dp))
            HorizontalDivider(color = Color(0xFF252542))
            Spacer(modifier = Modifier.height(8.dp))

            // Weekly Profile Blueprints (Auto Profile Builder)
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
                if (isPremium && weeklyBlueprintsLimit == 0) {
                    Text(
                        "UNLIMITED",
                        color = Color(0xFF4CAF50),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                } else {
                    Text(
                        "$weeklyBlueprintsUsed of $weeklyBlueprintsLimit used",
                        color = Color.Gray,
                        fontSize = 12.sp
                    )
                }
            }

            if (!(isPremium && weeklyBlueprintsLimit == 0)) {
                val progress = if (weeklyBlueprintsLimit > 0) (weeklyBlueprintsUsed.toFloat() / weeklyBlueprintsLimit).coerceIn(0f, 1f) else 0f
                LinearProgressIndicator(
                    progress = { progress },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(6.dp)
                        .clip(RoundedCornerShape(3.dp)),
                    color = if (progress >= 1f) Color(0xFFEF5350) else Color(0xFFE91E63),
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
}

@Composable
private fun PlanStatusCard(
    tier: String,
    isGodMode: Boolean,
    godModeExpiresAt: java.time.Instant?,
    dailyLimit: Int,
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
        Color(0xFF2A2A1E) // Subtle gold tint for God Mode
    } else {
        Color(0xFF1A1A2E) // Standard background
    }
    
    val cardBorder = if (isGodMode || tier == "premium") {
        BorderStroke(1.dp, Color(0xFFFFD700)) // Gold border for God Mode
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
                    tint = if (isGodMode || tier == "premium") Color(0xFFFFD700) else Color(0xFFE91E63),
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(12.dp))

                Column(modifier = Modifier.weight(1f)) {
                    when {
                        // Check God Mode first - either isGodMode is true OR tier is premium (from backend effective tier)
                        isGodMode || tier == "premium" -> {
                            Text(
                                "GOD MODE ACTIVE",
                                color = Color(0xFFFFD700),
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
                                    "Deep Persona Sync & Semantic Profiling enabled.",
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
                                "Unlimited AI Replies & Basic Voice DNA.",
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
                                "Standard access with daily limits.",
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
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFFD700)),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text("Upgrade Plan", fontSize = 13.sp, color = Color.Black, fontWeight = FontWeight.SemiBold)
                    }
                }
                else -> {
                    Button(
                        onClick = onUpgradeClick,
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63)),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text("Upgrade Plan", fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    }
                }
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
        Icon(icon, contentDescription = null, tint = Color(0xFFE91E63), modifier = Modifier.size(20.dp))
        Spacer(modifier = Modifier.width(16.dp))
        Text(label, color = textColor, modifier = Modifier.weight(1f))
        Icon(Icons.Default.ChevronRight, contentDescription = null, tint = Color.Gray, modifier = Modifier.size(20.dp))
    }
}
