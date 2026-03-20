package com.rizzbot.v2.overlay.ui.components.panels

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.overlay.manager.BubbleState
import com.rizzbot.v2.overlay.ui.theme.OverlayColors

/**
 * Header component for all full-screen panels showing step progress and navigation
 */
@Composable
fun BubbleHeader(
    currentState: BubbleState,
    onBack: () -> Unit,
    onClose: () -> Unit,
    onStartOver: () -> Unit
) {
    val (step, title, subtitle) = when (currentState) {
        is BubbleState.DirectionPicker -> Triple(
            1,
            "Step 1 of 3",
            "Pick the vibe"
        )
        is BubbleState.ScreenshotPreview -> Triple(
            2,
            "Step 2 of 3",
            "Check your screenshots"
        )
        is BubbleState.Loading -> Triple(
            3,
            "Step 3 of 3",
            "Cooking up replies"
        )
        is BubbleState.Expanded -> Triple(
            3,
            "Step 3 of 3",
            "Pick a reply"
        )
        is BubbleState.Error -> Triple(
            3,
            "Step 3 of 3",
            "Something went wrong"
        )
        is BubbleState.RequiresUserConfirmation -> Triple(
            3,
            "Step 3 of 3",
            "New chat detected"
        )
        else -> Triple(0, "", "")
    }

    if (step == 0) return

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color.White.copy(alpha = 0.02f))
            .padding(horizontal = 8.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (step > 1) {
                IconButton(onClick = onBack) {
                    Icon(
                        imageVector = Icons.Default.ArrowBack,
                        contentDescription = "Back",
                        tint = Color.White
                    )
                }
            }
        }

        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.weight(1f)
        ) {
            Text(
                text = title,
                color = Color.White,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold
            )
            if (subtitle.isNotEmpty()) {
                Text(
                    text = subtitle,
                    color = Color.Gray,
                    fontSize = 11.sp
                )
            }
        }

        Row(verticalAlignment = Alignment.CenterVertically) {
            if (step > 1) {
                TextButton(onClick = onStartOver) {
                    Text("Start over", color = OverlayColors.AccentPink, fontSize = 11.sp)
                }
            }
            IconButton(onClick = onClose) {
                Icon(
                    imageVector = Icons.Default.Close,
                    contentDescription = "Close",
                    tint = Color.White
                )
            }
        }
    }
}
