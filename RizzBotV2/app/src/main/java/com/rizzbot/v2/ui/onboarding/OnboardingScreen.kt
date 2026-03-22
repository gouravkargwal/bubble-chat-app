package com.rizzbot.v2.ui.onboarding

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.clickable
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.foundation.text.ClickableText
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.delay

private val Pink = Color(0xFFE91E63)
private val PinkDark = Color(0xFFC2185B)
private val DarkBg = Color(0xFF0A0A14)
private val CardBg = Color(0xFF14142B)
private val CardBorder = Color(0xFF1E1E3F)
private val SubtleText = Color(0xFF8888AA)
private val ProPurple = Color(0xFF7C4DFF)

@Composable
fun OnboardingScreen(
    onComplete: () -> Unit,
    onNavigateToPaywall: () -> Unit = {},
    onTryDemo: () -> Unit = {},
    onOpenTerms: () -> Unit = {},
    onOpenPrivacy: () -> Unit = {},
    isResumeSignIn: Boolean = false,
    viewModel: OnboardingViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    val googleSignInLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { result ->
        viewModel.onGoogleSignInActivityResult(result.resultCode, result.data)
    }

    LaunchedEffect(Unit) {
        viewModel.googleSignInEvents.collectLatest { intent ->
            googleSignInLauncher.launch(intent)
        }
    }

    LifecycleResumeEffect(Unit) {
        viewModel.refreshPermissions()
        onPauseOrDispose {}
    }

    LaunchedEffect(state.showPaywall) {
        if (state.showPaywall) {
            onNavigateToPaywall()
        }
    }

    LaunchedEffect(state.onboardingDone) {
        if (state.onboardingDone) onComplete()
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = DarkBg
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(56.dp))

            if (isResumeSignIn && state.currentStep == 0) {
                Text(
                    text = "Sign in again to use Cookd",
                    color = SubtleText,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(24.dp))
            } else {
                // Step indicator — 4 steps
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    repeat(4) { step ->
                        val filled = step <= state.currentStep
                        val trackColor by animateColorAsState(
                            targetValue = if (filled) Pink else CardBorder,
                            animationSpec = tween(280, easing = FastOutSlowInEasing),
                            label = "onboardingStepColor",
                        )
                        val trackHeight by animateDpAsState(
                            targetValue = if (filled) 4.dp else 3.dp,
                            animationSpec = tween(280, easing = FastOutSlowInEasing),
                            label = "onboardingStepHeight",
                        )
                        Box(
                            modifier = Modifier
                                .height(trackHeight)
                                .weight(1f)
                                .clip(RoundedCornerShape(2.dp))
                                .then(
                                    if (filled) {
                                        Modifier.background(
                                            Brush.horizontalGradient(listOf(Pink, PinkDark)),
                                        )
                                    } else {
                                        Modifier.background(trackColor)
                                    },
                                )
                        )
                    }
                }
                Spacer(modifier = Modifier.height(40.dp))
            }

            AnimatedContent(
                targetState = state.currentStep,
                label = "step",
                modifier = Modifier.fillMaxSize().weight(1f)
            ) { step ->
                when (step) {
                    0 -> HookAndLoginStep(
                        isResumeSignIn = isResumeSignIn,
                        isAuthenticating = state.isAuthenticating,
                        authError = state.authError,
                        onOpenTerms = onOpenTerms,
                        onOpenPrivacy = onOpenPrivacy,
                        onSignIn = {
                            val activity = context as? Activity
                            if (activity != null) {
                                viewModel.signInWithGoogle(activity)
                            } else {
                                viewModel.onActivityRequiredForGoogleSignIn()
                            }
                        }
                    )
                    1 -> VibeCheckStep(
                        selectedVibe = state.onboardingVibe,
                        onSelectVibe = { viewModel.setOnboardingVibe(it) },
                        onNext = { viewModel.completeVibeStep() }
                    )
                    2 -> InteractiveDemoStep(
                        onNext = { viewModel.nextStep() },
                        onTryDemo = onTryDemo
                    )
                    3 -> TrustAndTechStep(
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

// ── Step 0: Hook and Login ──

@Composable
private fun HookAndLoginStep(
    isResumeSignIn: Boolean,
    isAuthenticating: Boolean,
    authError: String?,
    onOpenTerms: () -> Unit,
    onOpenPrivacy: () -> Unit,
    onSignIn: () -> Unit
) {
    val context = LocalContext.current
    
    // Animated hero graphic
    val infiniteTransition = rememberInfiniteTransition(label = "heroPulse")
    val scale by infiniteTransition.animateFloat(
        initialValue = 0.8f,
        targetValue = 1.2f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "scale"
    )
    
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(20.dp))
        
        // Animated Hero Graphic
        Box(
            modifier = Modifier
                .size(120.dp)
                .graphicsLayer {
                    scaleX = scale
                    scaleY = scale
                }
                .clip(CircleShape)
                .background(
                    Brush.radialGradient(
                        colors = listOf(
                            Pink.copy(alpha = 0.3f),
                            Color.Transparent
                        )
                    )
                ),
            contentAlignment = Alignment.Center
        ) {
            Text(
                "✨",
                fontSize = 48.sp
            )
        }
        
        Spacer(modifier = Modifier.height(32.dp))
        
        Text(
            if (isResumeSignIn) "Welcome back" else "Never drop the ball on a match again.",
            color = Color.White,
            fontSize = 28.sp,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
            lineHeight = 36.sp
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            if (isResumeSignIn) {
                "Your setup is saved. Sign in with Google to keep using replies, audits, and your profile tools."
            } else {
                "Upload a screenshot. Let Cookd write the perfect reply."
            },
            color = SubtleText,
            fontSize = 16.sp,
            textAlign = TextAlign.Center,
            lineHeight = 24.sp
        )
        
        Spacer(modifier = Modifier.weight(1f))
        
        // Google Sign In button
        Button(
            onClick = onSignIn,
            enabled = !isAuthenticating,
            colors = ButtonDefaults.buttonColors(containerColor = Color.White),
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
            shape = RoundedCornerShape(14.dp)
        ) {
            if (isAuthenticating) {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    color = Color.Black,
                    strokeWidth = 2.dp
                )
                Spacer(modifier = Modifier.width(10.dp))
                Text("Signing in...", color = Color.Black, fontWeight = FontWeight.SemiBold)
            } else {
                Text(
                    "Continue with Google",
                    color = Color.Black,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 15.sp
                )
            }
        }
        
        if (authError != null) {
            Spacer(modifier = Modifier.height(12.dp))
            Text(authError, color = Color(0xFFEF5350), fontSize = 13.sp, textAlign = TextAlign.Center)
        }
        
        Spacer(modifier = Modifier.height(12.dp))

        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "By continuing, you agree to:",
                color = SubtleText.copy(alpha = 0.5f),
                fontSize = 11.sp,
                textAlign = TextAlign.Center
            )
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                TextButton(
                    onClick = onOpenTerms,
                    contentPadding = PaddingValues(horizontal = 4.dp, vertical = 0.dp)
                ) {
                    Text("Terms", color = Pink, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                }
                Text("·", color = SubtleText.copy(alpha = 0.4f), fontSize = 11.sp)
                TextButton(
                    onClick = onOpenPrivacy,
                    contentPadding = PaddingValues(horizontal = 4.dp, vertical = 0.dp)
                ) {
                    Text("Privacy", color = Pink, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

// ── Step 1: Vibe Check ──

@Composable
private fun VibeCheckStep(
    selectedVibe: String?,
    onSelectVibe: (String) -> Unit,
    onNext: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(20.dp))

        Text(
            "What's your texting vibe?",
            color = Color.White,
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(40.dp))

        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            VibeCard(
                emoji = "🔥",
                title = "Flirty & Direct",
                isSelected = selectedVibe == "flirty",
                onClick = { onSelectVibe("flirty") }
            )
            VibeCard(
                emoji = "😏",
                title = "Playful & Teasing",
                isSelected = selectedVibe == "playful",
                onClick = { onSelectVibe("playful") }
            )
            VibeCard(
                emoji = "🧠",
                title = "Witty & Sarcastic",
                isSelected = selectedVibe == "witty",
                onClick = { onSelectVibe("witty") }
            )
        }

        Spacer(modifier = Modifier.weight(1f))

        Button(
            onClick = onNext,
            enabled = selectedVibe != null,
            colors = ButtonDefaults.buttonColors(containerColor = Pink),
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
            shape = RoundedCornerShape(14.dp)
        ) {
            Text("Next", fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
private fun VibeCard(
    emoji: String,
    title: String,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .then(
                if (isSelected) {
                    Modifier.border(2.dp, Pink, RoundedCornerShape(16.dp))
                } else {
                    Modifier
                }
            ),
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = if (isSelected) 4.dp else 2.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(emoji, fontSize = 32.sp)
            Spacer(modifier = Modifier.width(16.dp))
            Text(
                title,
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.weight(1f))
            if (isSelected) {
                Icon(
                    Icons.Default.Check,
                    contentDescription = null,
                    tint = Pink,
                    modifier = Modifier.size(24.dp)
                )
            }
        }
    }
}

// ── Step 2: Interactive Demo ──

@Composable
private fun InteractiveDemoStep(
    onNext: () -> Unit,
    onTryDemo: () -> Unit
) {
    var chatState by remember { mutableStateOf(0) } // 0 = waiting, 1 = typing, 2 = done
    var typingDots by remember { mutableStateOf(".") }
    val demoScroll = rememberScrollState()
    
    // Animate typing dots
    LaunchedEffect(chatState) {
        if (chatState == 1) {
            while (chatState == 1) {
                typingDots = "."
                delay(300)
                typingDots = ".."
                delay(300)
                typingDots = "..."
                delay(300)
            }
        }
    }
    
    // Auto-advance to done state after 1.5 seconds
    LaunchedEffect(chatState) {
        if (chatState == 1) {
            delay(1500)
            chatState = 2
        }
    }
    
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(20.dp))

        // Chat interface (scrollable so layout works without invalid nested weights)
        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .verticalScroll(demoScroll),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Received message (left)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Start
            ) {
                Box(
                    modifier = Modifier
                        .background(
                            color = CardBg,
                            shape = RoundedCornerShape(20.dp, 20.dp, 20.dp, 4.dp)
                        )
                        .padding(horizontal = 16.dp, vertical = 12.dp)
                ) {
                    Text(
                        "I'm so bored right now. Entertain me.",
                        color = Color.White,
                        fontSize = 15.sp
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            // Action area or generated message
            when (chatState) {
                0 -> {
                    TextButton(onClick = onTryDemo) {
                        Text("Browse full scenario examples", color = SubtleText, fontSize = 13.sp)
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    // Cook a Reply button with pulsing animation
                    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
                    val scale by infiniteTransition.animateFloat(
                        initialValue = 1f,
                        targetValue = 1.05f,
                        animationSpec = infiniteRepeatable(
                            animation = tween(1000, easing = FastOutSlowInEasing),
                            repeatMode = RepeatMode.Reverse
                        ),
                        label = "scale"
                    )
                    
                    Button(
                        onClick = { chatState = 1 },
                        colors = ButtonDefaults.buttonColors(containerColor = Pink),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(56.dp)
                            .graphicsLayer {
                                scaleX = scale
                                scaleY = scale
                            },
                        shape = RoundedCornerShape(16.dp)
                    ) {
                        Text(
                            "✨ Cook a Reply",
                            color = Color.White,
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
                1 -> {
                    // Typing indicator (right)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.End
                    ) {
                        Box(
                            modifier = Modifier
                                .background(
                                    color = CardBg,
                                    shape = RoundedCornerShape(20.dp, 20.dp, 4.dp, 20.dp)
                                )
                                .padding(horizontal = 16.dp, vertical = 12.dp)
                        ) {
                            Text(
                                typingDots,
                                color = Color.White,
                                fontSize = 20.sp
                            )
                        }
                    }
                }
                2 -> {
                    // Generated message (right)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.End
                    ) {
                        Box(
                            modifier = Modifier
                                .background(
                                    color = Pink,
                                    shape = RoundedCornerShape(20.dp, 20.dp, 4.dp, 20.dp)
                                )
                                .padding(horizontal = 16.dp, vertical = 12.dp)
                        ) {
                            Text(
                                "Good thing I'm here to save you from yourself. Drinks or coffee?",
                                color = Color.White,
                                fontSize = 15.sp
                            )
                        }
                    }
                }
            }
        }
        
        // Continue button (only shown when done)
        if (chatState == 2) {
            Button(
                onClick = onNext,
                colors = ButtonDefaults.buttonColors(containerColor = Pink),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(14.dp)
            ) {
                Text("Continue", fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
            }
        }
        
        Spacer(modifier = Modifier.height(24.dp))
    }
}

// ── Step 3: Trust and Tech ──

@Composable
private fun TrustAndTechStep(
    hasPermission: Boolean,
    onRequestPermission: () -> Unit,
    onComplete: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(40.dp))
        
        Icon(
            Icons.Default.Shield,
            contentDescription = null,
            tint = Pink,
            modifier = Modifier.size(64.dp)
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        Text(
            "One Last Step.",
            color = Color.White,
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            "To put that magic button inside your apps, we need overlay permission. You choose when to capture; images are sent over TLS for processing. Details are in Privacy.",
            color = SubtleText,
            fontSize = 15.sp,
            textAlign = TextAlign.Center,
            lineHeight = 22.sp,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
        
        Spacer(modifier = Modifier.height(32.dp))
        
        // Privacy items
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            PrivacyItem("You trigger capture with the bubble — not automatically in the background")
            PrivacyItem("Images are encrypted in transit; see Privacy Policy in the app for retention details")
            PrivacyItem("Cookd does not save screenshots to your camera roll")
        }
        
        Spacer(modifier = Modifier.weight(1f))
        
        if (!hasPermission) {
            Button(
                onClick = onRequestPermission,
                colors = ButtonDefaults.buttonColors(containerColor = Pink),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(14.dp)
            ) {
                Text("Grant Permission", fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
            }
        } else {
            Button(
                onClick = onComplete,
                colors = ButtonDefaults.buttonColors(containerColor = Pink),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(14.dp)
            ) {
                Text("Start Using Cookd", fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
            }
        }
        
        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
private fun PrivacyItem(text: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            Icons.Default.Check,
            contentDescription = null,
            tint = Color(0xFF4CAF50),
            modifier = Modifier.size(20.dp)
        )
        Spacer(modifier = Modifier.width(12.dp))
        Text(
            text,
            color = Color.White,
            fontSize = 14.sp,
            modifier = Modifier.weight(1f)
        )
    }
}
