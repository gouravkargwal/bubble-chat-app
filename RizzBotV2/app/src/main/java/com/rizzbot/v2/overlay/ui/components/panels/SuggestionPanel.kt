package com.rizzbot.v2.overlay.ui.components.panels

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.unit.dp
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.overlay.ui.SuggestionCard
import com.rizzbot.v2.overlay.ui.theme.OverlayColors

/**
 * Panel showing generated reply suggestions
 */
@Composable
fun SuggestionPanel(
    result: SuggestionResult.Success,
    onCopy: (String, Int) -> Unit,
    onRate: (Int, Boolean, String) -> Unit,
    onRegenerate: () -> Unit,
    onClear: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val vibeLabels = listOf("\uD83D\uDD25 Flirty", "\uD83D\uDE0F Witty", "\u2728 Smooth", "\uD83D\uDCAA Bold")
    val screenHeight = LocalConfiguration.current.screenHeightDp.dp
    Column(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(max = screenHeight * 0.7f)
            .padding(16.dp)
            .verticalScroll(rememberScrollState())
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.End,
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onRegenerate) {
                Icon(Icons.Default.Refresh, "Regenerate", tint = OverlayColors.AccentPink)
            }
            IconButton(onClick = onClear) {
                Icon(Icons.Default.Delete, "Clear", tint = Color.Gray)
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        result.replies.forEachIndexed { index, reply ->
            SuggestionCard(
                label = vibeLabels.getOrElse(index) { "\uD83D\uDCAC Reply" },
                reply = reply,
                onCopy = { onCopy(reply, index) },
                onThumbsUp = { onRate(index, true, reply) },
                onThumbsDown = { onRate(index, false, reply) }
            )
            if (index < result.replies.lastIndex) {
                Spacer(modifier = Modifier.height(8.dp))
            }
        }
    }
}
