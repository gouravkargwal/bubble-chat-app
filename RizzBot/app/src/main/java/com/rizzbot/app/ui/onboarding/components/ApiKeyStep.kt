package com.rizzbot.app.ui.onboarding.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.rizzbot.app.domain.model.LlmModel
import com.rizzbot.app.domain.model.LlmProvider

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ApiKeyStep(
    selectedProvider: LlmProvider,
    selectedModel: LlmModel,
    availableModels: List<LlmModel>,
    apiKey: String,
    onProviderSelected: (LlmProvider) -> Unit,
    onModelSelected: (LlmModel) -> Unit,
    onApiKeyChanged: (String) -> Unit
) {
    var showKey by remember { mutableStateOf(false) }

    Column {
        Text(
            "Set Up Your AI",
            style = MaterialTheme.typography.headlineSmall
        )

        Spacer(Modifier.height(8.dp))

        Text(
            "Choose an AI provider and enter your API key. We recommend Groq — it's free and fast!",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(Modifier.height(24.dp))

        // Provider picker
        Text(
            "Provider",
            style = MaterialTheme.typography.labelLarge
        )
        Spacer(Modifier.height(8.dp))
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            LlmProvider.entries.forEach { provider ->
                FilterChip(
                    selected = provider == selectedProvider,
                    onClick = { onProviderSelected(provider) },
                    label = { Text(provider.displayName) }
                )
            }
        }

        Spacer(Modifier.height(20.dp))

        // Model picker
        Text(
            "Model",
            style = MaterialTheme.typography.labelLarge
        )
        Spacer(Modifier.height(8.dp))
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            availableModels.forEach { model ->
                FilterChip(
                    selected = model == selectedModel,
                    onClick = { onModelSelected(model) },
                    label = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(model.displayName)
                            if (model.isRecommended) {
                                Spacer(Modifier.width(4.dp))
                                Icon(
                                    Icons.Default.Star,
                                    contentDescription = "Recommended",
                                    modifier = Modifier.size(14.dp),
                                    tint = MaterialTheme.colorScheme.primary
                                )
                            }
                        }
                    }
                )
            }
        }

        Spacer(Modifier.height(20.dp))

        // API Key
        Text(
            "API Key",
            style = MaterialTheme.typography.labelLarge
        )
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(
            value = apiKey,
            onValueChange = onApiKeyChanged,
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text("Paste your API key here") },
            visualTransformation = if (showKey) VisualTransformation.None else PasswordVisualTransformation(),
            trailingIcon = {
                IconButton(onClick = { showKey = !showKey }) {
                    Icon(
                        if (showKey) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                        contentDescription = if (showKey) "Hide" else "Show"
                    )
                }
            },
            singleLine = true,
            shape = RoundedCornerShape(12.dp)
        )

        Spacer(Modifier.height(4.dp))

        Text(
            selectedProvider.keyHelperText,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
