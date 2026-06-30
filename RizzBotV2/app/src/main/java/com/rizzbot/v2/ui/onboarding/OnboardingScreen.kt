package com.rizzbot.v2.ui.onboarding

import android.app.Activity
import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingError
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite
import com.rizzbot.v2.ui.components.CookdLogo
import kotlinx.coroutines.flow.collectLatest

@Composable
fun OnboardingScreen(
    onComplete: () -> Unit,
    onNavigateToPaywall: () -> Unit = {},
    onOpenTerms: () -> Unit = {},
    onOpenPrivacy: () -> Unit = {},
    isResumeSignIn: Boolean = false,
    viewModel: OnboardingViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    val googleSignInLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult(),
    ) { result ->
        viewModel.onGoogleSignInActivityResult(result.resultCode, result.data)
    }

    // Skip value cards if resuming sign-in (returning user who got logged out)
    LaunchedEffect(isResumeSignIn) {
        if (isResumeSignIn && state.currentStep == 0) {
            viewModel.skipToSignIn()
        }
    }

    LaunchedEffect(Unit) {
        viewModel.googleSignInEvents.collectLatest { intent ->
            googleSignInLauncher.launch(intent)
        }
    }

    LaunchedEffect(state.showPaywall) {
        if (state.showPaywall) onNavigateToPaywall()
    }

    LaunchedEffect(state.onboardingDone) {
        if (state.onboardingDone) onComplete()
    }

    Surface(modifier = Modifier.fillMaxSize(), color = NothingBlack) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = NothingDimens.screenPadding),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(modifier = Modifier.height(56.dp))

            AnimatedContent(
                targetState = state.currentStep,
                label = "onboarding_step",
                modifier = Modifier
                    .fillMaxSize()
                    .weight(1f),
            ) { step ->
                when (step) {
                    0 -> OnboardingValueCardsStep(
                        onGetStarted = { viewModel.advanceOnboardingStep() },
                    )
                    1 -> HookAndLoginStep(
                        isResumeSignIn = isResumeSignIn,
                        isAuthenticating = state.isAuthenticating,
                        authError = state.authError,
                        onOpenTerms = onOpenTerms,
                        onOpenPrivacy = onOpenPrivacy,
                        onSignIn = {
                            val activity = context as? Activity
                            if (activity != null) viewModel.signInWithGoogle(activity)
                            else viewModel.onActivityRequiredForGoogleSignIn()
                        },
                    )
                    2 -> OnboardingSignupBonusStep(
                        referralCode = state.referralCode,
                        referralApplying = state.referralApplying,
                        referralSuccess = state.referralSuccess,
                        referralError = state.referralError,
                        onReferralCodeChange = { viewModel.updateReferralCode(it) },
                        onApplyReferral = { viewModel.applyReferralCode() },
                        onStart = { viewModel.completeOnboarding() },
                        userName = state.userName,
                    )
                }
            }
        }
    }
}

@Composable
private fun HookAndLoginStep(
    isResumeSignIn: Boolean,
    isAuthenticating: Boolean,
    authError: String?,
    onOpenTerms: () -> Unit,
    onOpenPrivacy: () -> Unit,
    onSignIn: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(modifier = Modifier.height(32.dp))

        CookdLogo()

        Spacer(modifier = Modifier.height(36.dp))

        Text(
            text = if (isResumeSignIn) "Welcome back" else "Ready to level up your chats?",
            style = MaterialTheme.typography.headlineSmall,
            color = NothingWhite,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )

        Spacer(modifier = Modifier.height(NothingDimens.elementGap))

        Text(
            text = if (isResumeSignIn) "Sign in with Google to continue."
            else "Connect your Google account and let Cookd craft the perfect replies.",
            style = MaterialTheme.typography.bodyLarge,
            color = NothingTextSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(0.85f),
        )

        Spacer(modifier = Modifier.weight(1f))

        Button(
            onClick = onSignIn,
            enabled = !isAuthenticating,
            colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
            modifier = Modifier
                .fillMaxWidth()
                .height(NothingDimens.minTouchTarget),
            shape = RoundedCornerShape(NothingDimens.pillRadius),
        ) {
            if (isAuthenticating) {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    color = NothingBlack,
                    strokeWidth = 2.dp,
                )
                Spacer(modifier = Modifier.width(NothingDimens.elementGap))
                Text(
                    "Signing in...",
                    color = NothingBlack,
                    fontWeight = FontWeight.SemiBold,
                )
            } else {
                Text(
                    "Continue with Google",
                    color = NothingBlack,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }

        if (authError != null) {
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
            Text(
                authError,
                color = NothingError,
                style = MaterialTheme.typography.labelMedium,
                textAlign = TextAlign.Center,
            )
        }

        Spacer(modifier = Modifier.height(NothingDimens.elementGap))

        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                "By continuing, you agree to:",
                color = NothingTextTertiary,
                style = MaterialTheme.typography.labelSmall,
                textAlign = TextAlign.Center,
            )
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center,
            ) {
                TextButton(
                    onClick = onOpenTerms,
                    contentPadding = PaddingValues(horizontal = 4.dp, vertical = 0.dp),
                ) {
                    Text(
                        "Terms",
                        color = NothingTextSecondary,
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
                Text("\u00b7", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall)
                TextButton(
                    onClick = onOpenPrivacy,
                    contentPadding = PaddingValues(horizontal = 4.dp, vertical = 0.dp),
                ) {
                    Text(
                        "Privacy",
                        color = NothingTextSecondary,
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(32.dp))
    }
}
