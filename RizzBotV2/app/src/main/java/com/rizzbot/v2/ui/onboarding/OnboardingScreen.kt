package com.rizzbot.v2.ui.onboarding

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Shield
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
import androidx.lifecycle.compose.LifecycleResumeEffect

@Composable
fun OnboardingScreen(
    onComplete: () -> Unit,
    onTryDemo: () -> Unit = {},
    viewModel: OnboardingViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    LifecycleResumeEffect(Unit) {
        viewModel.refreshPermissions()
        onPauseOrDispose {}
    }

    LaunchedEffect(state.onboardingDone) {
        if (state.onboardingDone) onComplete()
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Color(0xFF0F0F1A)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp)
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(48.dp))

            // Step indicator — 3 steps
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                repeat(3) { step ->
                    Box(
                        modifier = Modifier
                            .height(4.dp)
                            .weight(1f)
                            .background(
                                if (step <= state.currentStep) Color(0xFFE91E63) else Color.Gray,
                                RoundedCornerShape(2.dp)
                            )
                    )
                }
            }

            Spacer(modifier = Modifier.height(32.dp))

            AnimatedContent(targetState = state.currentStep, label = "step") { step ->
                when (step) {
                    0 -> GoogleSignInStep(
                        isAuthenticating = state.isAuthenticating,
                        authError = state.authError,
                        onSignIn = { viewModel.signInWithGoogle(context) }
                    )
                    1 -> PrivacyStep(
                        userName = state.userName,
                        onNext = { viewModel.nextStep() },
                        onTryDemo = onTryDemo
                    )
                    2 -> OverlayPermissionStep(
                        hasPermission = state.hasOverlayPermission,
                        onRequestPermission = {
                            val intent = Intent(
                                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                                Uri.parse("package:${context.packageName}")
                            )
                            context.startActivity(intent)
                        },
                        onComplete = { viewModel.completeOnboarding() }
                    )
                }
            }
        }
    }
}

@Composable
private fun GoogleSignInStep(
    isAuthenticating: Boolean,
    authError: String?,
    onSignIn: () -> Unit
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text("\uD83D\uDD25", fontSize = 56.sp)
        Spacer(modifier = Modifier.height(24.dp))
        Text("Welcome to Cookd", color = Color.White, fontSize = 28.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            "Your AI-powered dating chat assistant.\nSign in to get started.",
            color = Color.Gray,
            textAlign = TextAlign.Center,
            fontSize = 14.sp,
            lineHeight = 20.sp
        )

        Spacer(modifier = Modifier.height(32.dp))

        // Multi-app badge
        Card(
            colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
            shape = RoundedCornerShape(12.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text("Works on any chat app", color = Color.Gray, fontSize = 12.sp)
                Spacer(modifier = Modifier.height(8.dp))
                Row(
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    listOf("Tinder", "Bumble", "Hinge", "WhatsApp", "Instagram").forEach { app ->
                        Card(
                            colors = CardDefaults.cardColors(containerColor = Color(0xFF252542)),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Text(
                                app,
                                color = Color.White,
                                fontSize = 10.sp,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(32.dp))

        Button(
            onClick = onSignIn,
            enabled = !isAuthenticating,
            colors = ButtonDefaults.buttonColors(containerColor = Color.White),
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp)
        ) {
            if (isAuthenticating) {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    color = Color.Black,
                    strokeWidth = 2.dp
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Signing in...", color = Color.Black)
            } else {
                Icon(
                    Icons.Default.AccountCircle,
                    contentDescription = null,
                    tint = Color.Black,
                    modifier = Modifier.size(20.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    "Continue with Google",
                    color = Color.Black,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(vertical = 4.dp)
                )
            }
        }

        if (authError != null) {
            Spacer(modifier = Modifier.height(12.dp))
            Text(authError, color = Color(0xFFEF5350), fontSize = 13.sp, textAlign = TextAlign.Center)
        }
    }
}

@Composable
private fun PrivacyStep(userName: String?, onNext: () -> Unit, onTryDemo: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Icon(
            Icons.Default.Shield,
            contentDescription = null,
            tint = Color(0xFFE91E63),
            modifier = Modifier.size(64.dp)
        )
        Spacer(modifier = Modifier.height(24.dp))

        if (userName != null) {
            Text("Hey $userName!", color = Color(0xFFE91E63), fontSize = 16.sp, fontWeight = FontWeight.Medium)
            Spacer(modifier = Modifier.height(4.dp))
        }

        Text("Your Privacy Matters", color = Color.White, fontSize = 24.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(16.dp))

        Card(
            colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
            shape = RoundedCornerShape(16.dp)
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                PrivacyItem("Screenshots are captured ONLY when you tap the bubble")
                PrivacyItem("Images are sent securely to our servers and never stored")
                PrivacyItem("Screenshots are NEVER saved on your device")
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        Button(
            onClick = onNext,
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63)),
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp)
        ) {
            Text("I Understand", modifier = Modifier.padding(8.dp))
        }

        Spacer(modifier = Modifier.height(8.dp))

        TextButton(onClick = onTryDemo) {
            Text("See it in action first", color = Color(0xFFE91E63), fontSize = 14.sp)
        }
    }
}

@Composable
private fun PrivacyItem(text: String) {
    Row(
        modifier = Modifier.padding(vertical = 6.dp),
        verticalAlignment = Alignment.Top
    ) {
        Icon(Icons.Default.Check, contentDescription = null, tint = Color(0xFF4CAF50), modifier = Modifier.size(20.dp))
        Spacer(modifier = Modifier.width(12.dp))
        Text(text, color = Color.White, fontSize = 14.sp)
    }
}

@Composable
private fun OverlayPermissionStep(
    hasPermission: Boolean,
    onRequestPermission: () -> Unit,
    onComplete: () -> Unit
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text("\uD83D\uDD32", fontSize = 56.sp)
        Spacer(modifier = Modifier.height(24.dp))
        Text("Overlay Permission", color = Color.White, fontSize = 24.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            "Cookd needs to display a floating bubble over other apps so you can get suggestions without switching apps.",
            color = Color.Gray,
            textAlign = TextAlign.Center,
            fontSize = 14.sp
        )
        Spacer(modifier = Modifier.height(24.dp))

        if (hasPermission) {
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1B5E20)),
                shape = RoundedCornerShape(12.dp)
            ) {
                Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Check, contentDescription = null, tint = Color(0xFF4CAF50))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Permission granted!", color = Color.White)
                }
            }

            Spacer(modifier = Modifier.height(24.dp))
            Button(
                onClick = onComplete,
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63)),
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("Get Started!", modifier = Modifier.padding(8.dp))
            }
        } else {
            Button(
                onClick = onRequestPermission,
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63)),
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("Grant Permission", modifier = Modifier.padding(8.dp))
            }
        }
    }
}
