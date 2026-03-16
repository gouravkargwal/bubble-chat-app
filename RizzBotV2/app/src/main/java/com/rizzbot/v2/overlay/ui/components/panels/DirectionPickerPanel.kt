package com.rizzbot.v2.overlay.ui.components.panels

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import com.rizzbot.v2.domain.model.ConversationDirection
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.overlay.ui.theme.OverlayColors

/**
 * Panel for selecting conversation direction and vibe
 */
@Composable
fun DirectionPicker(
    allowedDirections: List<String>,
    customHintsEnabled: Boolean,
    isGalleryMode: Boolean,
    isLoading: Boolean = false,
    onInputModeChanged: (Boolean) -> Unit,
    onDirectionSelected: (DirectionWithHint) -> Unit,
    onUpgrade: () -> Unit,
    onDismiss: () -> Unit,
    onKeyboardFocus: (Boolean) -> Unit = {},
    modifier: Modifier = Modifier
) {
    var customHint by remember { mutableStateOf("") }
    var showCustomInput by remember { mutableStateOf(false) }
    val focusRequester = remember { FocusRequester() }
    val keyboardController = LocalSoftwareKeyboardController.current
    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .fillMaxWidth()
            .verticalScroll(scrollState)
            .padding(16.dp)
    ) {
        InputModeToggle(
            isGalleryMode = isGalleryMode,
            isLoading = isLoading,
            onInputModeChanged = onInputModeChanged
        )
        Spacer(modifier = Modifier.height(8.dp))

        // Show all 7 directions - locked ones will show with lock icon
        ConversationDirection.entries.forEach { direction ->
            // Match enum name (e.g., "REVIVE_CHAT") to backend format (e.g., "revive_chat")
            val dirKey = direction.name.lowercase()
            val isLocked = allowedDirections.isNotEmpty() && dirKey !in allowedDirections

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 2.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(
                        if (isLocked) Color(0xFFE91E63).copy(alpha = 0.05f)
                        else Color.White.copy(alpha = 0.05f)
                    )
                    .clickable(enabled = !isLoading) {
                        if (isLocked) onUpgrade() else onDirectionSelected(DirectionWithHint(direction))
                    }
                    .then(
                        if (isLocked) Modifier
                            .border(
                                width = 1.dp,
                                color = OverlayColors.AccentPink.copy(alpha = 0.9f),
                                shape = RoundedCornerShape(12.dp)
                            )
                        else Modifier
                    )
                    .padding(vertical = 10.dp, horizontal = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(direction.emoji, fontSize = 20.sp)
                Spacer(modifier = Modifier.width(12.dp))
                Text(
                    direction.displayName,
                    color = if (isLocked) Color.Gray else Color.White,
                    fontSize = 14.sp
                )
                if (isLocked) {
                    Spacer(modifier = Modifier.weight(1f))
                    Text("\uD83D\uDD12", fontSize = 14.sp)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        "UNLOCK",
                        color = OverlayColors.AccentPink,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }

        // Custom hint option
        if (!showCustomInput) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 2.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.White.copy(alpha = if (customHintsEnabled) 0.05f else 0.02f))
                    .clickable(enabled = !isLoading) {
                        if (customHintsEnabled) {
                            showCustomInput = true
                            onKeyboardFocus(true)
                        } else {
                            onUpgrade()
                        }
                    }
                    .then(
                        if (!customHintsEnabled) Modifier
                            .border(
                                width = 1.dp,
                                color = OverlayColors.AccentPink.copy(alpha = 0.9f),
                                shape = RoundedCornerShape(12.dp)
                            )
                        else Modifier
                    )
                    .padding(vertical = 10.dp, horizontal = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("\u270D\uFE0F", fontSize = 20.sp)
                Spacer(modifier = Modifier.width(12.dp))
                Text(
                    "Custom hint",
                    color = if (customHintsEnabled) Color.White else Color.Gray,
                    fontSize = 14.sp
                )
                if (!customHintsEnabled) {
                    Spacer(modifier = Modifier.weight(1f))
                    Text("\uD83D\uDD12", fontSize = 14.sp)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        "UNLOCK",
                        color = OverlayColors.AccentPink,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        } else {
            LaunchedEffect(Unit) {
                focusRequester.requestFocus()
                keyboardController?.show()
            }
            OutlinedTextField(
                value = customHint,
                onValueChange = { customHint = it },
                placeholder = { Text("e.g., mention that I also love hiking", color = Color.Gray) },
                modifier = Modifier
                    .fillMaxWidth()
                    .focusRequester(focusRequester),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White,
                    focusedBorderColor = OverlayColors.AccentPink,
                    unfocusedBorderColor = Color.Gray
                ),
                singleLine = true
            )
            Spacer(modifier = Modifier.height(8.dp))
            Button(
                onClick = {
                    keyboardController?.hide()
                    onKeyboardFocus(false)
                    onDirectionSelected(DirectionWithHint(customHint = customHint))
                },
                enabled = !isLoading,
                colors = ButtonDefaults.buttonColors(containerColor = OverlayColors.AccentPink),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (isLoading) "Cooking..." else "Generate")
            }
        }
    }
}

@Composable
private fun InputModeToggle(
    isGalleryMode: Boolean,
    isLoading: Boolean = false,
    onInputModeChanged: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(24.dp))
            .background(Color.White.copy(alpha = 0.06f))
            .padding(2.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        val liveSelected = !isGalleryMode
        val gallerySelected = isGalleryMode

        ModeChip(
            label = "📸 Live Screen",
            selected = liveSelected,
            enabled = !isLoading,
            onClick = { if (!liveSelected) onInputModeChanged(false) },
            modifier = Modifier.weight(1f)
        )
        Spacer(modifier = Modifier.width(4.dp))
        ModeChip(
            label = "🖼️ Gallery",
            selected = gallerySelected,
            enabled = !isLoading,
            onClick = { if (!gallerySelected) onInputModeChanged(true) },
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun ModeChip(
    label: String,
    selected: Boolean,
    enabled: Boolean = true,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val background =
        if (selected) OverlayColors.AccentPink.copy(alpha = 0.95f)
        else Color.Transparent
    val contentColor =
        if (selected) Color.Black
        else Color.White.copy(alpha = 0.85f)

    Row(
        modifier = modifier
            .clip(RoundedCornerShape(20.dp))
            .background(background)
            .clickable(enabled = enabled, onClick = onClick)
            .padding(vertical = 6.dp, horizontal = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            color = if (enabled) contentColor else contentColor.copy(alpha = 0.5f),
            fontSize = 12.sp,
            fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal
        )
    }
}
