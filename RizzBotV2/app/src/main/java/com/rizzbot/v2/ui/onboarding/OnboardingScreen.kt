package com.rizzbot.v2.ui.onboarding

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.animateColorAsState
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.LifecycleResumeEffect

private val Pink = Color(0xFFE91E63)
private val PinkDark = Color(0xFFC2185B)
private val DarkBg = Color(0xFF0A0A14)
private val CardBg = Color(0xFF14142B)
private val CardBorder = Color(0xFF1E1E3F)
private val SubtleText = Color(0xFF8888AA)
private val Gold = Color(0xFFFFD700)
private val ProPurple = Color(0xFF7C4DFF)

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
        color = DarkBg
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp)
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(56.dp))

            // Step indicator — 5 steps now
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                repeat(5) { step ->
                    Box(
                        modifier = Modifier
                            .height(3.dp)
                            .weight(1f)
                            .clip(RoundedCornerShape(2.dp))
                            .background(
                                if (step <= state.currentStep)
                                    Brush.horizontalGradient(listOf(Pink, PinkDark))
                                else
                                    Brush.horizontalGradient(listOf(CardBorder, CardBorder))
                            )
                    )
                }
            }

            Spacer(modifier = Modifier.height(40.dp))

            AnimatedContent(targetState = state.currentStep, label = "step") { step ->
                when (step) {
                    0 -> WelcomeCarouselStep(
                        isAuthenticating = state.isAuthenticating,
                        authError = state.authError,
                        onSignIn = { viewModel.signInWithGoogle(context) }
                    )
                    1 -> TrialShowcaseStep(
                        onNext = { viewModel.nextStep() }
                    )
                    2 -> ReferralStep(
                        referralCode = state.referralCode,
                        isApplying = state.referralApplying,
                        successMessage = state.referralSuccess,
                        errorMessage = state.referralError,
                        onCodeChanged = { viewModel.updateReferralCode(it) },
                        onApply = { viewModel.applyReferralCode() },
                        onSkip = { viewModel.nextStep() }
                    )
                    3 -> PrivacyStep(
                        userName = state.userName,
                        onNext = { viewModel.nextStep() },
                        onTryDemo = onTryDemo
                    )
                    4 -> OverlayPermissionStep(
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

// ── Feature Carousel Data ──

private data class FeatureSlide(
    val emoji: String,
    val title: String,
    val description: String
)

private val featureSlides = listOf(
    FeatureSlide(
        emoji = "\uD83E\uDDD1\u200D\uD83D\uDCBB",
        title = "Never Sound Like a Bot",
        description = "Unlike other apps, Cookd learns your exact texting style, slang, and humor."
    ),
    FeatureSlide(
        emoji = "\uD83D\uDCAC",
        title = "Works Everywhere",
        description = "Tinder, Bumble, Hinge, iMessage — one floating bubble for all your apps."
    ),
    FeatureSlide(
        emoji = "\uD83C\uDFAF",
        title = "God Mode Unlock",
        description = "Upload your chat and let our AI write the perfect flirty, witty, or teasing reply."
    ),
)

// ── Step 0: Welcome + Feature Carousel ──

@Composable
private fun WelcomeCarouselStep(
    isAuthenticating: Boolean,
    authError: String?,
    onSignIn: () -> Unit
) {
    val pagerState = rememberPagerState(pageCount = { featureSlides.size })

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            "cookd",
            color = Color.White,
            fontSize = 32.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = (-0.5).sp
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            "Never run out of things to say",
            color = SubtleText,
            fontSize = 14.sp
        )

        Spacer(modifier = Modifier.height(32.dp))

        // Feature carousel
        HorizontalPager(
            state = pagerState,
            modifier = Modifier.fillMaxWidth()
        ) { page ->
            val slide = featureSlides[page]
            Card(
                colors = CardDefaults.cardColors(containerColor = CardBg),
                shape = RoundedCornerShape(20.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 4.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(28.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(slide.emoji, fontSize = 48.sp)
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        slide.title,
                        color = Color.White,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        slide.description,
                        color = SubtleText,
                        fontSize = 14.sp,
                        textAlign = TextAlign.Center,
                        lineHeight = 20.sp
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Page indicator dots
        Row(
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            repeat(featureSlides.size) { index ->
                val isSelected = pagerState.currentPage == index
                val color by animateColorAsState(
                    if (isSelected) Pink else CardBorder,
                    label = "dot"
                )
                Box(
                    modifier = Modifier
                        .size(if (isSelected) 8.dp else 6.dp)
                        .clip(CircleShape)
                        .background(color)
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Trial badge
        Surface(
            color = ProPurple.copy(alpha = 0.15f),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                Icon(
                    Icons.Default.Star,
                    contentDescription = null,
                    tint = Gold,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    "Sign up & get 3 days of Pro free",
                    color = Color.White,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        // Sign in button
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
                    "Start Free Pro Trial",
                    color = Color.Black,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 15.sp
                )
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Supported apps
        Text(
            "Works with Tinder \u2022 Bumble \u2022 Hinge \u2022 WhatsApp \u2022 Instagram",
            color = SubtleText.copy(alpha = 0.6f),
            fontSize = 11.sp,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(12.dp))

        Text(
            "By continuing, you agree to our Terms of Service",
            color = SubtleText.copy(alpha = 0.5f),
            fontSize = 11.sp,
            textAlign = TextAlign.Center
        )

        if (authError != null) {
            Spacer(modifier = Modifier.height(12.dp))
            Text(authError, color = Color(0xFFEF5350), fontSize = 13.sp, textAlign = TextAlign.Center)
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

// ── Step 1: Trial Showcase — What You're Getting ──

private data class PlanFeature(
    val text: String,
    val includedInFree: Boolean,
    val includedInPro: Boolean
)

private val planFeatures = listOf(
    PlanFeature("5 replies/day", includedInFree = true, includedInPro = false),
    PlanFeature("Unlimited AI Replies", includedInFree = false, includedInPro = true),
    PlanFeature("2 directions (Quick, Playful)", includedInFree = true, includedInPro = false),
    PlanFeature("All 6 directions", includedInFree = false, includedInPro = true),
    PlanFeature("1 screenshot per request", includedInFree = true, includedInPro = false),
    PlanFeature("Up to 5 screenshots", includedInFree = false, includedInPro = true),
    PlanFeature("Custom hints", includedInFree = false, includedInPro = true),
    PlanFeature("Deep Persona Sync (Sounds exactly like you)", includedInFree = false, includedInPro = true),
    PlanFeature("Conversation memory", includedInFree = false, includedInPro = true),
    PlanFeature("Profile Roaster (Upload her pics)", includedInFree = false, includedInPro = true),
)

@Composable
private fun TrialShowcaseStep(
    onNext: () -> Unit
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        // Header
        Surface(
            color = ProPurple.copy(alpha = 0.15f),
            shape = RoundedCornerShape(20.dp)
        ) {
            Text(
                "\uD83C\uDF89",
                fontSize = 40.sp,
                modifier = Modifier.padding(16.dp)
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        Text(
            "Your Pro Trial is Active!",
            color = Color.White,
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            "You have 3 days of full Pro access. Here's what you unlocked:",
            color = SubtleText,
            fontSize = 14.sp,
            textAlign = TextAlign.Center,
            lineHeight = 20.sp
        )

        Spacer(modifier = Modifier.height(24.dp))

        // Plan comparison card
        Card(
            colors = CardDefaults.cardColors(containerColor = CardBg),
            shape = RoundedCornerShape(20.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                // Column headers
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Spacer(modifier = Modifier.weight(1f))
                    Text(
                        "Free",
                        color = SubtleText,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier.width(48.dp),
                        textAlign = TextAlign.Center
                    )
                    Surface(
                        color = Gold.copy(alpha = 0.2f),
                        shape = RoundedCornerShape(6.dp),
                        modifier = Modifier.width(48.dp)
                    ) {
                        Text(
                            "God Mode",
                            color = Gold,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.padding(vertical = 4.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                planFeatures.forEach { feature ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            feature.text,
                            color = if (feature.includedInPro) Color.White else Color.White.copy(alpha = 0.7f),
                            fontSize = 13.sp,
                            modifier = Modifier.weight(1f),
                            lineHeight = 18.sp
                        )
                        // Free column
                        Box(
                            modifier = Modifier.width(48.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            if (feature.includedInFree) {
                                Icon(
                                    Icons.Default.Check,
                                    contentDescription = null,
                                    tint = SubtleText,
                                    modifier = Modifier.size(16.dp)
                                )
                            } else {
                                Text("—", color = SubtleText.copy(alpha = 0.4f), fontSize = 14.sp)
                            }
                        }
                        // Pro column
                        Box(
                            modifier = Modifier.width(48.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            if (feature.includedInPro) {
                                Box(
                                    modifier = Modifier
                                        .size(20.dp)
                                        .clip(CircleShape)
                                        .background(ProPurple.copy(alpha = 0.2f)),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        Icons.Default.Check,
                                        contentDescription = null,
                                        tint = ProPurple,
                                        modifier = Modifier.size(14.dp)
                                    )
                                }
                            } else {
                                Text("—", color = SubtleText.copy(alpha = 0.4f), fontSize = 14.sp)
                            }
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // After trial note
        Text(
            "After 3 days, you\u2019ll switch to Free. Upgrade anytime.",
            color = SubtleText,
            fontSize = 12.sp,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(24.dp))

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

        Spacer(modifier = Modifier.height(24.dp))
    }
}

// ── Step 2: Referral Code ──

@Composable
private fun ReferralStep(
    referralCode: String,
    isApplying: Boolean,
    successMessage: String?,
    errorMessage: String?,
    onCodeChanged: (String) -> Unit,
    onApply: () -> Unit,
    onSkip: () -> Unit
) {
    val focusManager = LocalFocusManager.current

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text("\uD83C\uDF81", fontSize = 48.sp)
        Spacer(modifier = Modifier.height(20.dp))
        Text(
            "Got a Referral Code?",
            color = Color.White,
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            buildAnnotatedString {
                append("Enter a friend's code to unlock ")
                withStyle(
                    style = SpanStyle(
                        color = Gold,
                        fontWeight = FontWeight.Bold
                    )
                ) {
                    append("24 Hours of God Mode")
                }
                append(" for both of you.")
            },
            color = SubtleText,
            textAlign = TextAlign.Center,
            fontSize = 14.sp,
            lineHeight = 20.sp
        )

        Spacer(modifier = Modifier.height(28.dp))

        if (successMessage != null) {
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1B5E20).copy(alpha = 0.3f)),
                shape = RoundedCornerShape(12.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Default.Check, contentDescription = null, tint = Color(0xFF4CAF50))
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(successMessage, color = Color(0xFF81C784), fontSize = 14.sp)
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Button(
                onClick = onSkip,
                colors = ButtonDefaults.buttonColors(containerColor = Pink),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(14.dp)
            ) {
                Text("Continue", fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
            }
        } else {
            OutlinedTextField(
                value = referralCode,
                onValueChange = { onCodeChanged(it.uppercase().take(12)) },
                placeholder = { Text("Enter code", color = SubtleText) },
                singleLine = true,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White,
                    cursorColor = Pink,
                    focusedBorderColor = Pink,
                    unfocusedBorderColor = CardBorder,
                    focusedContainerColor = CardBg,
                    unfocusedContainerColor = CardBg
                ),
                shape = RoundedCornerShape(14.dp),
                keyboardOptions = KeyboardOptions(
                    capitalization = KeyboardCapitalization.Characters,
                    imeAction = ImeAction.Done
                ),
                keyboardActions = KeyboardActions(
                    onDone = {
                        focusManager.clearFocus()
                        if (referralCode.isNotBlank()) onApply()
                    }
                ),
                modifier = Modifier.fillMaxWidth()
            )

            if (errorMessage != null) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(errorMessage, color = Color(0xFFEF5350), fontSize = 13.sp)
            }

            Spacer(modifier = Modifier.height(20.dp))

            Button(
                onClick = onApply,
                enabled = referralCode.isNotBlank() && !isApplying,
                colors = ButtonDefaults.buttonColors(containerColor = Pink),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(14.dp)
            ) {
                if (isApplying) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = Color.White,
                        strokeWidth = 2.dp
                    )
                } else {
                    Text("Apply Code", fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            TextButton(onClick = onSkip) {
                Text(
                    "Skip for now",
                    color = SubtleText,
                    fontSize = 14.sp
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

// ── Step 3: Privacy ──

@Composable
private fun PrivacyStep(userName: String?, onNext: () -> Unit, onTryDemo: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Icon(
            Icons.Default.Shield,
            contentDescription = null,
            tint = Pink,
            modifier = Modifier.size(56.dp)
        )
        Spacer(modifier = Modifier.height(20.dp))

        if (userName != null) {
            Text(
                "Hey $userName!",
                color = Pink,
                fontSize = 15.sp,
                fontWeight = FontWeight.Medium
            )
            Spacer(modifier = Modifier.height(4.dp))
        }

        Text(
            "Your Privacy Matters",
            color = Color.White,
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(20.dp))

        Card(
            colors = CardDefaults.cardColors(containerColor = CardBg),
            shape = RoundedCornerShape(16.dp)
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                PrivacyItem("Screenshots are captured only when you tap the bubble")
                PrivacyItem("Images are sent securely and never stored on our servers")
                PrivacyItem("Screenshots are never saved on your device")
            }
        }

        Spacer(modifier = Modifier.height(28.dp))

        Button(
            onClick = onNext,
            colors = ButtonDefaults.buttonColors(containerColor = Pink),
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
            shape = RoundedCornerShape(14.dp)
        ) {
            Text("I Understand", fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
        }

        Spacer(modifier = Modifier.height(8.dp))

        TextButton(onClick = onTryDemo) {
            Text("See it in action first", color = Pink, fontSize = 14.sp)
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
private fun PrivacyItem(text: String) {
    Row(
        modifier = Modifier.padding(vertical = 8.dp),
        verticalAlignment = Alignment.Top
    ) {
        Box(
            modifier = Modifier
                .size(22.dp)
                .clip(CircleShape)
                .background(Color(0xFF4CAF50).copy(alpha = 0.15f)),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                Icons.Default.Check,
                contentDescription = null,
                tint = Color(0xFF4CAF50),
                modifier = Modifier.size(14.dp)
            )
        }
        Spacer(modifier = Modifier.width(12.dp))
        Text(text, color = Color.White.copy(alpha = 0.9f), fontSize = 14.sp, lineHeight = 20.sp)
    }
}

// ── Step 4: Overlay Permission ──

@Composable
private fun OverlayPermissionStep(
    hasPermission: Boolean,
    onRequestPermission: () -> Unit,
    onComplete: () -> Unit
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text("\uD83D\uDCAC", fontSize = 48.sp)
        Spacer(modifier = Modifier.height(20.dp))
        Text(
            "One Last Step",
            color = Color.White,
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            "Cookd needs overlay permission to show the floating bubble over your dating apps.",
            color = SubtleText,
            textAlign = TextAlign.Center,
            fontSize = 14.sp,
            lineHeight = 20.sp
        )
        Spacer(modifier = Modifier.height(28.dp))

        if (hasPermission) {
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = Color(0xFF1B5E20).copy(alpha = 0.3f)
                ),
                shape = RoundedCornerShape(12.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Default.Check, contentDescription = null, tint = Color(0xFF4CAF50))
                    Spacer(modifier = Modifier.width(10.dp))
                    Text("Permission granted!", color = Color(0xFF81C784), fontSize = 14.sp)
                }
            }

            Spacer(modifier = Modifier.height(28.dp))
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
        } else {
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
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}
