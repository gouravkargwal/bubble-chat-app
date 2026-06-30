package com.rizzbot.v2.overlay.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.ThumbDown
import androidx.compose.material.icons.filled.ThumbUp
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.ui.theme.NeonRed
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingError
import com.rizzbot.v2.ui.theme.NothingSuccess
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite

@Composable
fun SuggestionCard(
    label: String,
    reply: String,
    strategyLabel: String,
    isRecommended: Boolean,
    coachReasoning: String?,
    onCopy: () -> Unit,
    onThumbsUp: () -> Unit,
    onThumbsDown: () -> Unit,
    modifier: Modifier = Modifier
) {
    var copied by remember { mutableStateOf(false) }
    var rated by remember { mutableStateOf<Boolean?>(null) }

    val borderColor = if (isRecommended) NothingWhite.copy(alpha = 0.85f) else NothingBorder

    Card(
        modifier = modifier
            .fillMaxWidth()
            .border(
                BorderStroke(
                    width = if (isRecommended) 1.5.dp else NothingDimens.borderThickness,
                    color = borderColor
                ),
                RoundedCornerShape(NothingDimens.cardRadius)
            )
            .clickable {
                onCopy()
                copied = true
            },
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        colors = CardDefaults.cardColors(containerColor = NothingSurface),
    ) {
        Column(
            modifier = Modifier
                .padding(NothingDimens.cardPadding)
        ) {
            // Header: Wingman's Choice badge or original vibe label
            Text(
                text = if (isRecommended) "WINGMAN'S CHOICE" else label,
                color = if (isRecommended) NeonRed else NothingWhite,
                fontWeight = FontWeight.Bold,
                fontSize = 11.sp,
                letterSpacing = 0.8.sp,
            )

            Spacer(modifier = Modifier.height(4.dp))

            // Strategy capsule badge
            Box(
                modifier = Modifier
                    .align(Alignment.Start)
                    .border(
                        BorderStroke(NothingDimens.borderThickness, NothingBorder),
                        shape = RoundedCornerShape(NothingDimens.pillRadius)
                    )
                    .padding(horizontal = 8.dp, vertical = 2.dp)
            ) {
                Text(
                    text = strategyLabel,
                    color = NothingTextSecondary,
                    fontSize = 10.sp,
                )
            }

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                reply,
                color = NothingWhite,
                fontSize = 14.sp,
                lineHeight = 18.sp,
            )

            // Coach tooltip / reasoning, only for Wingman's Choice
            if (isRecommended && !coachReasoning.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = coachReasoning,
                    color = NothingTextTertiary,
                    fontSize = 11.sp,
                    fontStyle = FontStyle.Italic,
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Copy button
                TextButton(onClick = {
                    onCopy()
                    copied = true
                }) {
                    Icon(
                        Icons.Default.ContentCopy,
                        contentDescription = "Copy",
                        tint = if (copied) NothingSuccess else NothingTextSecondary,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        if (copied) "Copied" else "Copy",
                        color = if (copied) NothingSuccess else NothingTextSecondary,
                        fontSize = 12.sp
                    )
                }

                // Rating buttons
                Row {
                    IconButton(
                        onClick = {
                            if (rated == null) {
                                rated = true
                                onThumbsUp()
                            }
                        },
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(
                            Icons.Default.ThumbUp,
                            "Like",
                            tint = if (rated == true) NothingSuccess else NothingTextSecondary,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                    IconButton(
                        onClick = {
                            if (rated == null) {
                                rated = false
                                onThumbsDown()
                            }
                        },
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(
                            Icons.Default.ThumbDown,
                            "Dislike",
                            tint = if (rated == false) NothingError else NothingTextSecondary,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }
            }
        }
    }
}
