package com.rizzbot.app.overlay.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val VIBE_LABELS = listOf("Flirty", "Witty", "Smooth", "Bold")

@Composable
fun SuggestionCard(
    suggestions: List<String>,
    hasProfile: Boolean = false,
    onCopy: (String) -> Unit,
    onPaste: (String) -> Unit = {},
    onDismiss: () -> Unit,
    onRefreshReplies: () -> Unit = {},
    onNewTopicClick: () -> Unit = {},
    onReadFullChat: () -> Unit = {},
    onGenerateWithHint: (String) -> Unit = {},
    onFocusChanged: (Boolean) -> Unit = {}
) {
    var selectedIndex by remember { mutableIntStateOf(0) }
    var copied by remember { mutableStateOf(false) }
    var pasted by remember { mutableStateOf(false) }
    var showSyncHint by remember { mutableStateOf(false) }
    var hintText by remember { mutableStateOf("") }
    val copyButtonColor by animateColorAsState(
        targetValue = if (copied) Color(0xFF4CAF50) else MaterialTheme.colorScheme.primary,
        label = "copy_button_color"
    )

    // Reset copied/pasted when selection changes
    val selectedText = suggestions.getOrElse(selectedIndex) { suggestions.firstOrNull() ?: "" }

    Card(
        modifier = Modifier
            .widthIn(max = 300.dp)
            .heightIn(max = 520.dp)
            .padding(8.dp),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
    ) {
        Column(
            modifier = Modifier
                .padding(12.dp)
                .verticalScroll(rememberScrollState())
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "RizzBot",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold,
                    fontSize = 11.sp
                )
                IconButton(
                    onClick = onDismiss,
                    modifier = Modifier.size(24.dp)
                ) {
                    Icon(
                        Icons.Default.Close,
                        contentDescription = "Dismiss",
                        modifier = Modifier.size(16.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Spacer(Modifier.height(6.dp))

            // Reply options
            Column(
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                suggestions.forEachIndexed { index, suggestion ->
                    val isSelected = index == selectedIndex
                    val vibeLabel = VIBE_LABELS.getOrElse(index) { "Option ${index + 1}" }
                    OutlinedCard(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable {
                                selectedIndex = index
                                copied = false
                                pasted = false
                            },
                        shape = RoundedCornerShape(12.dp),
                        border = BorderStroke(
                            width = if (isSelected) 2.dp else 1.dp,
                            color = if (isSelected) MaterialTheme.colorScheme.primary
                            else MaterialTheme.colorScheme.outlineVariant
                        ),
                        colors = CardDefaults.outlinedCardColors(
                            containerColor = if (isSelected)
                                MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f)
                            else MaterialTheme.colorScheme.surface
                        )
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text(
                                text = vibeLabel,
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (isSelected) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Spacer(Modifier.height(2.dp))
                            Text(
                                text = suggestion,
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurface,
                                lineHeight = 18.sp,
                                fontSize = 13.sp
                            )
                        }
                    }
                }
            }

            Spacer(Modifier.height(8.dp))

            // Hint input field
            OutlinedTextField(
                value = hintText,
                onValueChange = { hintText = it },
                placeholder = {
                    Text(
                        "Guide AI (e.g. talk about travel)",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
                    )
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .onFocusChanged { focusState ->
                        onFocusChanged(focusState.isFocused)
                    },
                textStyle = TextStyle(fontSize = 12.sp),
                singleLine = true,
                shape = RoundedCornerShape(10.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = MaterialTheme.colorScheme.primary,
                    unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant
                )
            )

            Spacer(Modifier.height(6.dp))

            // Action row: Refresh/Generate with hint + Read Full Chat + New Topic
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                TextButton(
                    onClick = {
                        if (hintText.isNotBlank()) {
                            onGenerateWithHint(hintText)
                        } else {
                            onRefreshReplies()
                        }
                    }
                ) {
                    Icon(
                        Icons.Default.Refresh,
                        contentDescription = null,
                        modifier = Modifier.size(14.dp),
                        tint = if (hintText.isNotBlank()) MaterialTheme.colorScheme.primary
                            else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(Modifier.width(3.dp))
                    Text(
                        if (hintText.isNotBlank()) "Go" else "Refresh",
                        fontSize = 11.sp,
                        color = if (hintText.isNotBlank()) MaterialTheme.colorScheme.primary
                            else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                TextButton(onClick = onReadFullChat) {
                    Icon(
                        Icons.Default.MenuBook,
                        contentDescription = null,
                        modifier = Modifier.size(14.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(Modifier.width(3.dp))
                    Text(
                        "Read Chat",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                TextButton(
                    onClick = {
                        if (hasProfile) {
                            showSyncHint = false
                            onNewTopicClick()
                        } else {
                            showSyncHint = !showSyncHint
                        }
                    }
                ) {
                    val tint = if (hasProfile) MaterialTheme.colorScheme.onSurfaceVariant
                        else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f)
                    Icon(
                        Icons.Default.Lightbulb,
                        contentDescription = null,
                        modifier = Modifier.size(14.dp),
                        tint = tint
                    )
                    Spacer(Modifier.width(3.dp))
                    Text(
                        "New Topic",
                        fontSize = 11.sp,
                        color = tint
                    )
                }
            }

            if (showSyncHint) {
                Text(
                    text = "Sync their profile first to unlock conversation starters",
                    fontSize = 10.sp,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                )
            }

            Spacer(Modifier.height(4.dp))

            // Paste to input button (primary action)
            Button(
                onClick = {
                    pasted = true
                    onPaste(selectedText)
                },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (pasted) Color(0xFF4CAF50) else MaterialTheme.colorScheme.primary
                )
            ) {
                Icon(
                    if (pasted) Icons.Default.Check else Icons.Default.Send,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    if (pasted) "Sent!" else "Paste to Chat",
                    fontSize = 13.sp
                )
            }

            Spacer(Modifier.height(6.dp))

            // Copy button (secondary)
            OutlinedButton(
                onClick = {
                    copied = true
                    onCopy(selectedText)
                },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            ) {
                Icon(
                    if (copied) Icons.Default.Check else Icons.Default.ContentCopy,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp),
                    tint = copyButtonColor
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    if (copied) "Copied!" else "Copy Reply",
                    fontSize = 13.sp,
                    color = copyButtonColor
                )
            }
        }
    }
}
