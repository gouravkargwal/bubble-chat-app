package com.rizzbot.v2.overlay.ui.components.panels

import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingWhite

/**
 * Panel for previewing captured screenshots before generating replies
 */
@Composable
fun ScreenshotPreviewPanel(
    bitmaps: List<Bitmap>,
    maxScreenshots: Int,
    canGenerate: Boolean = true,
    isLoading: Boolean = false,
    onConfirm: () -> Unit,
    onAddMore: () -> Unit,
    onRetake: () -> Unit,
    onRemoveScreenshot: (Int) -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(NothingDimens.cardPadding)
    ) {
        // ── 2-column screenshot grid ──
        if (bitmaps.isNotEmpty()) {
            // Chunk bitmaps into pairs for 2-column layout
            val rows = bitmaps.chunked(2)
            rows.forEachIndexed { rowIndex, rowBitmaps ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    rowBitmaps.forEachIndexed { colIndex, bitmap ->
                        val idx = rowIndex * 2 + colIndex
                        ScreenshotGridCell(
                            bitmap = bitmap,
                            label = "Screenshot ${idx + 1}",
                            isLoading = isLoading,
                            onRemove = { onRemoveScreenshot(idx) },
                            modifier = Modifier.weight(1f)
                        )
                    }
                    // Fill remaining space if odd count
                    if (rowBitmaps.size < 2) {
                        Spacer(modifier = Modifier.weight(1f))
                    }
                }
                Spacer(modifier = Modifier.height(8.dp))
            }

            // Add-more button row (only when under max and even count)
            if (bitmaps.size % 2 == 0 && bitmaps.size < maxScreenshots) {
                AddMoreGridCell(
                    currentCount = bitmaps.size,
                    maxScreenshots = maxScreenshots,
                    isLoading = isLoading,
                    onAddMore = onAddMore,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
            }
        }

        Text(
            when {
                bitmaps.size == 1 && maxScreenshots > 1 ->
                    "Tip: Add more screenshots for better context (${bitmaps.size}/$maxScreenshots)"
                bitmaps.size == 1 ->
                    "1 screenshot captured"
                else ->
                    "${bitmaps.size}/$maxScreenshots screenshots ready"
            },
            color = NothingTextSecondary,
            fontSize = 13.sp,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(12.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedButton(
                onClick = onRetake,
                enabled = !isLoading,
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(NothingDimens.cardRadius)
            ) {
                Text("Retake", color = NothingWhite)
            }
            if (bitmaps.size < maxScreenshots) {
                OutlinedButton(
                    onClick = onAddMore,
                    enabled = !isLoading,
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(NothingDimens.cardRadius)
                ) {
                    Text("+ Add more", color = NothingWhite)
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        Button(
            onClick = onConfirm,
            enabled = canGenerate && !isLoading,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
            shape = RoundedCornerShape(NothingDimens.cardRadius)
        ) {
            Text(
                when {
                    isLoading -> "Cooking..."
                    !canGenerate -> "Out of free replies"
                    else -> "Generate replies"
                },
                color = NothingBlack,
            )
        }
    }
}

@Composable
private fun ScreenshotGridCell(
    bitmap: Bitmap,
    label: String,
    isLoading: Boolean,
    onRemove: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(modifier = modifier.height(140.dp)) {
        // Screenshot image
        Image(
            bitmap = bitmap.asImageBitmap(),
            contentDescription = label,
            modifier = Modifier
                .fillMaxSize()
                .clip(RoundedCornerShape(NothingDimens.cardRadius))
                .border(NothingDimens.borderThickness, NothingBorder, RoundedCornerShape(NothingDimens.cardRadius)),
            contentScale = ContentScale.Crop
        )

        // Label overlay at bottom
        Box(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .fillMaxWidth()
                .background(
                    NothingBlack.copy(alpha = 0.6f),
                    RoundedCornerShape(bottomStart = NothingDimens.cardRadius, bottomEnd = NothingDimens.cardRadius)
                )
                .padding(horizontal = 8.dp, vertical = 4.dp)
        ) {
            Text(
                text = label,
                color = NothingWhite.copy(alpha = 0.8f),
                fontSize = 11.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth()
            )
        }

        // Remove button
        IconButton(
            onClick = { if (!isLoading) onRemove() },
            enabled = !isLoading,
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(4.dp)
                .size(28.dp)
                .background(NothingBlack.copy(alpha = 0.85f), CircleShape)
        ) {
            Icon(
                imageVector = Icons.Default.Close,
                contentDescription = "Remove screenshot",
                tint = NothingWhite,
                modifier = Modifier.size(14.dp)
            )
        }
    }
}

@Composable
private fun AddMoreGridCell(
    currentCount: Int,
    maxScreenshots: Int,
    isLoading: Boolean,
    onAddMore: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .height(80.dp)
            .clip(RoundedCornerShape(NothingDimens.cardRadius))
            .border(
                NothingDimens.borderThickness,
                NothingBorder.copy(alpha = 0.4f),
                RoundedCornerShape(NothingDimens.cardRadius)
            )
            .background(NothingSurface)
            .padding(12.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = "+",
                color = NothingTextSecondary,
                fontSize = 22.sp
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = "$currentCount of $maxScreenshots",
                color = NothingTextSecondary,
                fontSize = 11.sp
            )
        }
    }
}
