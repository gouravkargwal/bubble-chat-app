package com.rizzbot.app.ui.onboarding

import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.rizzbot.app.ui.onboarding.components.PermissionStep
import com.rizzbot.app.ui.onboarding.components.ToneSelectionStep

@Composable
fun OnboardingScreen(
    viewModel: OnboardingViewModel,
    onOnboardingComplete: () -> Unit
) {
    val state by viewModel.state.collectAsState()

    LaunchedEffect(Unit) {
        viewModel.refreshPermissions()
    }

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 24.dp)
                .verticalScroll(rememberScrollState())
        ) {
            Spacer(Modifier.height(48.dp))

            // Progress indicator
            LinearProgressIndicator(
                progress = { (state.currentStep + 1) / 2f },
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.primary,
                trackColor = MaterialTheme.colorScheme.surfaceVariant
            )

            Text(
                text = "Step ${state.currentStep + 1} of 2",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 8.dp)
            )

            Spacer(Modifier.height(32.dp))

            // Step content
            AnimatedContent(targetState = state.currentStep, label = "onboarding_step") { step ->
                when (step) {
                    0 -> PermissionStep(
                        isAccessibilityEnabled = state.isAccessibilityEnabled,
                        isOverlayEnabled = state.isOverlayEnabled,
                        onRefresh = { viewModel.refreshPermissions() }
                    )
                    1 -> ToneSelectionStep(
                        selectedTone = state.selectedTone,
                        onToneSelected = { viewModel.selectTone(it) }
                    )
                }
            }

            Spacer(Modifier.weight(1f))

            // Navigation buttons
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 32.dp)
            ) {
                if (state.currentStep > 0) {
                    OutlinedButton(
                        onClick = { viewModel.previousStep() },
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Back")
                    }
                    Spacer(Modifier.width(12.dp))
                }

                Button(
                    onClick = {
                        if (state.currentStep < 1) {
                            viewModel.nextStep()
                        } else {
                            viewModel.completeOnboarding(onOnboardingComplete)
                        }
                    },
                    enabled = when (state.currentStep) {
                        0 -> state.isAccessibilityEnabled && state.isOverlayEnabled
                        else -> true
                    },
                    modifier = Modifier.weight(1f)
                ) {
                    Text(if (state.currentStep < 1) "Next" else "Let's Go!")
                }
            }
        }
    }
}
