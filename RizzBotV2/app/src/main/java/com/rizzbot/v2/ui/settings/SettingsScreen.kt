package com.rizzbot.v2.ui.settings

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel

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
    var showSignOutDialog by remember { mutableStateOf(false) }

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
        Column(
            modifier = Modifier
                .padding(padding)
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
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.WorkspacePremium, contentDescription = null, tint = Color(0xFFE91E63), modifier = Modifier.size(24.dp))
                        Spacer(modifier = Modifier.width(12.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                if (state.isPremium) "Premium" else "Free Plan",
                                color = Color.White,
                                fontWeight = FontWeight.Medium
                            )
                            Text(
                                if (state.isPremium) "Unlimited replies" else "${state.dailyLimit} replies/day",
                                color = Color.Gray,
                                fontSize = 12.sp
                            )
                        }
                        if (!state.isPremium) {
                            Button(
                                onClick = onPremium,
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63)),
                                shape = RoundedCornerShape(8.dp),
                                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp)
                            ) {
                                Text("Upgrade", fontSize = 12.sp)
                            }
                        }
                    }
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
                            IconButton(onClick = {
                                val intent = Intent(Intent.ACTION_SEND).apply {
                                    type = "text/plain"
                                    putExtra(
                                        Intent.EXTRA_TEXT,
                                        "Use my code ${referral.referralCode} to get 5 bonus replies on Cookd! https://cookd.app"
                                    )
                                }
                                context.startActivity(Intent.createChooser(intent, "Share Code"))
                            }) {
                                Icon(Icons.Default.Share, "Share", tint = Color(0xFFE91E63))
                            }
                        }

                        Text(
                            "${referral.totalReferrals}/${referral.maxReferrals} friends invited  •  +${referral.bonusRepliesEarned} bonus replies",
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
                    SettingsRow(icon = Icons.Default.Logout, label = "Sign Out", onClick = {
                        showSignOutDialog = true
                    })
                }
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
    }
}

@Composable
private fun SettingsRow(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = Color(0xFFE91E63), modifier = Modifier.size(20.dp))
        Spacer(modifier = Modifier.width(16.dp))
        Text(label, color = Color.White, modifier = Modifier.weight(1f))
        Icon(Icons.Default.ChevronRight, contentDescription = null, tint = Color.Gray, modifier = Modifier.size(20.dp))
    }
}
