package com.rizzbot.v2.overlay.ui.components.panels

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.overlay.ui.SuggestionCard
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingWhite

/**
 * Compact suggestion panel designed for the overlay bubble where screen space is limited.
 *
 * Strips out the context header, section title, instructional text, and redundant action buttons
 * that the full [SuggestionPanel] includes — the [BubbleHeader] already shows step context and
 * provides "Start over" and "Close" actions. Only "Regenerate" is shown here.
 */
@Composable
fun OverlaySuggestionPanel(
    result: SuggestionResult.Success,
    onCopy: (String, Int) -> Unit,
    onRate: (Int, Boolean, String) -> Unit,
    onRegenerate: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val vibeLabels = listOf("Flirty", "Witty", "Smooth", "Bold")
    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 12.dp),
    ) {
        // ── Scrollable reply cards ─────────────────────────────
        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(scrollState),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Spacer(modifier = Modifier.height(4.dp))

            result.replies.forEachIndexed { index, replyOption ->
                val label = vibeLabels.getOrElse(index) { "Reply" }

                val strategy =
                    if (replyOption.strategyLabel.isNotBlank() && replyOption.strategyLabel != "STANDARD") {
                        replyOption.strategyLabel.uppercase()
                    } else {
                        "REPLY"
                    }

                val isRecommended = replyOption.isRecommended
                val coachReasoning = replyOption.coachReasoning.takeIf { it.isNotBlank() }

                SuggestionCard(
                    label = label,
                    reply = replyOption.text,
                    strategyLabel = "[ $strategy ]",
                    isRecommended = isRecommended,
                    coachReasoning = coachReasoning,
                    onCopy = { onCopy(replyOption.text, index) },
                    onThumbsUp = { onRate(index, true, replyOption.text) },
                    onThumbsDown = { onRate(index, false, replyOption.text) },
                )
            }

            Spacer(modifier = Modifier.height(4.dp))
        }

        // ── Regenerate button (primary action only) ────────────
        // "Start Over" is handled by the BubbleHeader above.
        Button(
            onClick = onRegenerate,
            colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
            modifier = Modifier
                .fillMaxWidth()
                .height(44.dp),
            shape = RoundedCornerShape(999.dp),
        ) {
            Icon(
                Icons.Default.Refresh,
                contentDescription = null,
                tint = NothingBlack,
                modifier = Modifier.size(16.dp),
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = "Regenerate",
                color = NothingBlack,
                fontWeight = FontWeight.Bold,
                fontSize = 13.sp,
            )
        }

        Spacer(modifier = Modifier.height(8.dp))
    }
}
