package com.rizzbot.app.ui.onboarding

import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.rizzbot.app.ui.onboarding.components.ApiKeyStep
import com.rizzbot.app.ui.onboarding.components.PermissionStep

@Composable
fun OnboardingScreen(
    viewModel: OnboardingViewModel,
    onOnboardingComplete: () -> Unit
) {
    val state by viewModel.state.collectAsState()
    val totalSteps = OnboardingViewModel.TOTAL_STEPS
    val lastStep = totalSteps - 1

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
            Spacer(Modifier.height(40.dp))

            // App branding header
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    Icons.Default.AutoAwesome,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(32.dp)
                )
                Spacer(Modifier.width(10.dp))
                Text(
                    "RizzBot",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            Spacer(Modifier.height(4.dp))

            Text(
                "Your AI-powered dating reply assistant",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(Modifier.height(24.dp))

            // Progress indicator
            LinearProgressIndicator(
                progress = { (state.currentStep + 1) / totalSteps.toFloat() },
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.primary,
                trackColor = MaterialTheme.colorScheme.surfaceVariant
            )

            Text(
                text = "Step ${state.currentStep + 1} of $totalSteps",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 8.dp)
            )

            Spacer(Modifier.height(28.dp))

            // Step content
            AnimatedContent(targetState = state.currentStep, label = "onboarding_step") { step ->
                when (step) {
                    0 -> PermissionStep(
                        isAccessibilityEnabled = state.isAccessibilityEnabled,
                        isOverlayEnabled = state.isOverlayEnabled,
                        onRefresh = { viewModel.refreshPermissions() }
                    )
                    1 -> ApiKeyStep(
                        selectedProvider = state.selectedProvider,
                        selectedModel = state.selectedModel,
                        availableModels = state.availableModels,
                        apiKey = state.apiKey,
                        onProviderSelected = { viewModel.selectProvider(it) },
                        onModelSelected = { viewModel.selectModel(it) },
                        onApiKeyChanged = { viewModel.updateApiKey(it) }
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
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text("Back")
                    }
                    Spacer(Modifier.width(12.dp))
                }

                Button(
                    onClick = {
                        if (state.currentStep < lastStep) {
                            viewModel.nextStep()
                        } else {
                            viewModel.completeOnboarding(onOnboardingComplete)
                        }
                    },
                    enabled = when (state.currentStep) {
                        0 -> state.isAccessibilityEnabled && state.isOverlayEnabled
                        1 -> state.apiKey.isNotBlank()
                        else -> true
                    },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text(
                        when {
                            state.currentStep < lastStep -> "Continue"
                            else -> "Let's Go!"
                        }
                    )
                }
            }
        }
    }
}
