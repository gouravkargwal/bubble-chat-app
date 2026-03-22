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
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val AccentPink = Color(0xFFE91E63)
private val RecommendedGlow = AccentPink.copy(alpha = 0.22f)
private val CardShape = RoundedCornerShape(16.dp)

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

    val borderColor = if (isRecommended) AccentPink.copy(alpha = 0.85f) else Color.White.copy(alpha = 0.08f)

    Card(
        modifier = modifier
            .fillMaxWidth()
            .border(
                BorderStroke(
                    width = if (isRecommended) 1.5.dp else 1.dp,
                    color = borderColor
                ),
                CardShape
            )
            .clickable {
                onCopy()
                copied = true
            },
        shape = CardShape,
        colors = CardDefaults.cardColors(containerColor = Color(0xFF252542)),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier
                .drawBehind {
                    drawLine(
                        color = AccentPink,
                        start = Offset(0f, 0f),
                        end = Offset(0f, size.height),
                        strokeWidth = 3.dp.toPx()
                    )

                    if (isRecommended) {
                        drawCircle(
                            color = RecommendedGlow,
                            radius = size.height * 0.9f,
                            center = Offset(size.width * 0.1f, size.height / 2f)
                        )
                    }
                }
                .padding(14.dp)
        ) {
            // Header: Wingman's Choice badge or original vibe label
            Text(
                text = if (isRecommended) "✨ WINGMAN'S CHOICE" else label,
                color = AccentPink,
                fontWeight = FontWeight.Bold,
                fontSize = 12.sp
            )

            Spacer(modifier = Modifier.height(4.dp))

            // Strategy capsule badge
            Box(
                modifier = Modifier
                    .align(Alignment.Start)
                    .border(
                        BorderStroke(1.dp, Color.White.copy(alpha = 0.18f)),
                        shape = RoundedCornerShape(999.dp)
                    )
                    .padding(horizontal = 8.dp, vertical = 2.dp)
            ) {
                Text(
                    text = strategyLabel,
                    color = Color.White.copy(alpha = 0.9f),
                    fontSize = 10.sp
                )
            }

            Spacer(modifier = Modifier.height(6.dp))

            Text(reply, color = Color.White, fontSize = 14.sp)

            // Coach tooltip / reasoning, only for Wingman's Choice
            if (isRecommended && !coachReasoning.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = coachReasoning,
                    color = Color.LightGray.copy(alpha = 0.9f),
                    fontSize = 11.sp,
                    fontStyle = FontStyle.Italic
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
                        tint = if (copied) Color(0xFF4CAF50) else Color.Gray,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        if (copied) "Copied!" else "Copy",
                        color = if (copied) Color(0xFF4CAF50) else Color.Gray,
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
                            tint = if (rated == true) Color(0xFF4CAF50) else Color.Gray,
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
                            tint = if (rated == false) Color(0xFFEF5350) else Color.Gray,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }
            }
        }
    }
}
