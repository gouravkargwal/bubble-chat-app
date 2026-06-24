package com.rizzbot.v2.ui.onboarding

import android.app.Activity
import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.ui.unit.sp
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

    LaunchedEffect(state.showPaywall) {
        if (state.showPaywall) onNavigateToPaywall()
    }

    LaunchedEffect(state.onboardingDone) {
        if (state.onboardingDone) onComplete()
    }

    Surface(modifier = Modifier.fillMaxSize(), color = NothingBlack) {
        Column(
            modifier = Modifier.fillMaxSize().padding(horizontal = NothingDimens.screenPadding),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(56.dp))

            if (isResumeSignIn && state.currentStep == 0) {
                Text("Sign in again to use Cookd", color = NothingTextSecondary, style = MaterialTheme.typography.titleSmall, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
                Spacer(modifier = Modifier.height(32.dp))
            }

            AnimatedContent(targetState = state.currentStep, label = "step", modifier = Modifier.fillMaxSize().weight(1f)) { step ->
                when (step) {
                    0 -> HookAndLoginStep(
                        isResumeSignIn = isResumeSignIn,
                        isAuthenticating = state.isAuthenticating,
                        authError = state.authError,
                        onOpenTerms = onOpenTerms,
                        onOpenPrivacy = onOpenPrivacy,
                        onSignIn = {
                            val activity = context as? Activity
                            if (activity != null) viewModel.signInWithGoogle(activity)
                            else viewModel.onActivityRequiredForGoogleSignIn()
                        }
                    )
                    1 -> VibeCheckStep(
                        selectedVibe = state.onboardingVibe,
                        onSelectVibe = { viewModel.setOnboardingVibe(it) },
                        onNext = { viewModel.completeVibeStep() }
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
    onSignIn: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(40.dp))

        CookdLogo()

        Spacer(modifier = Modifier.height(40.dp))

        Text(
            if (isResumeSignIn) "Welcome back" else "Never drop the ball on a match again.",
            color = NothingWhite,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
        )

        Spacer(modifier = Modifier.height(NothingDimens.elementGap))

        Text(
            if (isResumeSignIn) "Sign in with Google to continue."
            else "Upload a screenshot. Let Cookd write the perfect reply.",
            color = NothingTextSecondary,
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
        )

        Spacer(modifier = Modifier.weight(1f))

        Button(
            onClick = onSignIn,
            enabled = !isAuthenticating,
            colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
            modifier = Modifier.fillMaxWidth().height(NothingDimens.minTouchTarget),
            shape = RoundedCornerShape(NothingDimens.pillRadius)
        ) {
            if (isAuthenticating) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp), color = NothingBlack, strokeWidth = 2.dp)
                Spacer(modifier = Modifier.width(NothingDimens.elementGap))
                Text("Signing in...", color = NothingBlack, fontWeight = FontWeight.SemiBold)
            } else {
                Text("Continue with Google", color = NothingBlack, fontWeight = FontWeight.SemiBold)
            }
        }

        if (authError != null) {
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
            Text(authError, color = NothingError, style = MaterialTheme.typography.labelMedium, textAlign = TextAlign.Center)
        }

        Spacer(modifier = Modifier.height(NothingDimens.elementGap))

        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("By continuing, you agree to:", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall, textAlign = TextAlign.Center)
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Center) {
                TextButton(onClick = onOpenTerms, contentPadding = PaddingValues(horizontal = 4.dp, vertical = 0.dp)) {
                    Text("Terms", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.SemiBold)
                }
                Text("\u00b7", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall)
                TextButton(onClick = onOpenPrivacy, contentPadding = PaddingValues(horizontal = 4.dp, vertical = 0.dp)) {
                    Text("Privacy", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.SemiBold)
                }
            }
        }

        Spacer(modifier = Modifier.height(32.dp))
    }
}

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
        Spacer(modifier = Modifier.height(32.dp))

        Text("What's your texting vibe?", color = NothingWhite, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)

        Spacer(modifier = Modifier.height(48.dp))

        Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap)) {
            listOf("\uD83D\uDD25 Flirty & Direct" to "flirty", "\uD83D\uDE0F Playful & Teasing" to "playful", "\uD83E\uDDE0 Witty & Sarcastic" to "witty").forEach { (title, key) ->
                VibeCard(emoji = title.split(" ").first(), title = title, isSelected = selectedVibe == key, onClick = { onSelectVibe(key) })
            }
        }

        Spacer(modifier = Modifier.weight(1f))

        Button(
            onClick = onNext,
            enabled = selectedVibe != null,
            colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
            modifier = Modifier.fillMaxWidth().height(NothingDimens.minTouchTarget),
            shape = RoundedCornerShape(NothingDimens.pillRadius)
        ) {
            Text("Next", color = NothingBlack, fontWeight = FontWeight.Bold)
        }

        Spacer(modifier = Modifier.height(32.dp))
    }
}

@Composable
private fun VibeCard(
    emoji: String,
    title: String,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = NothingSurface),
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        border = BorderStroke(
            if (isSelected) 2.dp else NothingDimens.borderThickness,
            if (isSelected) NothingWhite else NothingBorder
        )
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(NothingDimens.cardPadding),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(emoji, fontSize = 32.sp)
            Spacer(modifier = Modifier.width(NothingDimens.elementGap))
            Text(title, color = NothingWhite, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(modifier = Modifier.weight(1f))
            if (isSelected) {
                Icon(Icons.Default.Check, contentDescription = null, tint = NothingWhite, modifier = Modifier.size(24.dp))
            }
        }
    }
}
