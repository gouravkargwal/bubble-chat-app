package com.rizzbot.v2.overlay.ui.components.panels

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.overlay.ui.SuggestionCard
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite

/**
 * Panel showing generated reply suggestions with context header and clear action buttons.
 *
 * @param directionName Human-readable direction name (e.g. "Quick reply").
 * @param screenshotCount Number of screenshots used for generation.
 * @param hintText Optional custom hint text the user provided.
 */
@Composable
fun SuggestionPanel(
    result: SuggestionResult.Success,
    directionName: String = "",
    screenshotCount: Int = 0,
    hintText: String? = null,
    onCopy: (String, Int) -> Unit,
    onRate: (Int, Boolean, String) -> Unit,
    onRegenerate: () -> Unit,
    onClear: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val vibeLabels = listOf("Flirty", "Witty", "Smooth", "Bold")
    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = NothingDimens.screenPadding),
    ) {
        // ── Context header bar ──────────────────────────────────
        ContextHeader(
            directionName = directionName,
            screenshotCount = screenshotCount,
            hintText = hintText,
            onEditSettings = onDismiss,
        )

        Spacer(modifier = Modifier.height(NothingDimens.elementGap))

        // ── Section title ──────────────────────────────────────
        Text(
            text = "Your Replies",
            color = NothingWhite,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(NothingDimens.textGap))
        Text(
            text = "Tap a reply to copy, or use thumbs to rate each option",
            color = NothingTextSecondary,
            style = MaterialTheme.typography.bodySmall,
        )

        Spacer(modifier = Modifier.height(NothingDimens.elementGap))

        // ── Scrollable replies ─────────────────────────────────
        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(scrollState),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
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

            // Bottom spacer so cards don't stick to action buttons
            Spacer(modifier = Modifier.height(8.dp))
        }

        // ── Bottom action bar ──────────────────────────────────
        ActionBar(
            onRegenerate = onRegenerate,
            onStartOver = onClear,
        )
        Spacer(modifier = Modifier.height(24.dp))
    }
}

// ── Context header ──────────────────────────────────────────────

@Composable
private fun ContextHeader(
    directionName: String,
    screenshotCount: Int,
    hintText: String?,
    onEditSettings: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(NothingDimens.cardRadius))
            .background(NothingSurface)
            .border(
                BorderStroke(NothingDimens.borderThickness, NothingBorder),
                RoundedCornerShape(NothingDimens.cardRadius),
            )
            .padding(NothingDimens.cardPadding),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        // Direction badge
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(NothingDimens.pillRadius))
                .background(NothingWhite.copy(alpha = 0.1f))
                .padding(horizontal = 10.dp, vertical = 4.dp),
        ) {
            Text(
                text = directionName,
                color = NothingWhite,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
            )
        }

        Spacer(modifier = Modifier.width(8.dp))

        // Screenshot count
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                Icons.Default.Image,
                contentDescription = null,
                tint = NothingTextSecondary,
                modifier = Modifier.size(14.dp),
            )
            Spacer(modifier = Modifier.width(3.dp))
            Text(
                text = "$screenshotCount ${if (screenshotCount == 1) "screenshot" else "screenshots"}",
                color = NothingTextSecondary,
                fontSize = 12.sp,
            )
        }

        // Hint badge (if present)
        if (!hintText.isNullOrBlank()) {
            Spacer(modifier = Modifier.width(8.dp))
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(NothingDimens.pillRadius))
                    .background(NothingTextTertiary.copy(alpha = 0.15f))
                    .padding(horizontal = 8.dp, vertical = 3.dp),
            ) {
                Text(
                    text = "Hint",
                    color = NothingTextTertiary,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Medium,
                )
            }
        }

        Spacer(modifier = Modifier.weight(1f))

        // Edit button — go back to direction step to change settings (preserves direction + images)
        Button(
            onClick = onEditSettings,
            colors = ButtonDefaults.buttonColors(
                containerColor = NothingSurface,
                contentColor = NothingTextSecondary,
            ),
            shape = RoundedCornerShape(NothingDimens.pillRadius),
            modifier = Modifier.height(32.dp),
            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp),
        ) {
            Icon(
                Icons.Default.Edit,
                contentDescription = null,
                modifier = Modifier.size(14.dp),
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = "Edit",
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium,
            )
        }
    }
}

// ── Bottom action bar ──────────────────────────────────────────

@Composable
private fun ActionBar(
    onRegenerate: () -> Unit,
    onStartOver: () -> Unit,
) {
    Column {
        // Regenerate — primary action
        Button(
            onClick = onRegenerate,
            colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
            modifier = Modifier
                .fillMaxWidth()
                .height(NothingDimens.minTouchTarget),
            shape = RoundedCornerShape(NothingDimens.pillRadius),
        ) {
            Icon(
                Icons.Default.Refresh,
                contentDescription = null,
                tint = NothingBlack,
                modifier = Modifier.size(18.dp),
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Regenerate",
                color = NothingBlack,
                fontWeight = FontWeight.Bold,
            )
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Start Over — secondary, no icon (clear visual distinction from back navigation)
        OutlinedButton(
            onClick = onStartOver,
            modifier = Modifier
                .fillMaxWidth()
                .height(NothingDimens.minTouchTarget),
            shape = RoundedCornerShape(NothingDimens.pillRadius),
            border = BorderStroke(NothingDimens.borderThickness, NothingBorder),
        ) {
            Text(
                text = "Start Over",
                color = NothingTextSecondary,
                fontWeight = FontWeight.Medium,
            )
        }
    }
}
