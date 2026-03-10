package com.rizzbot.v2.overlay.ui.components.panels

import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.overlay.ui.theme.OverlayColors

/**
 * Panel for previewing captured screenshots before generating replies
 */
@Composable
fun ScreenshotPreviewPanel(
    bitmaps: List<Bitmap>,
    maxScreenshots: Int,
    onConfirm: () -> Unit,
    onAddMore: () -> Unit,
    onRetake: () -> Unit,
    onRemoveScreenshot: (Int) -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val screenHeight = LocalConfiguration.current.screenHeightDp.dp

    var selectedIndex by remember(bitmaps) {
        mutableIntStateOf(bitmaps.lastIndex.coerceAtLeast(0))
    }
    LaunchedEffect(bitmaps.size) {
        if (bitmaps.isEmpty()) return@LaunchedEffect
        if (selectedIndex !in bitmaps.indices) {
            selectedIndex = bitmaps.lastIndex
        }
    }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(max = screenHeight * 0.75f)
            .padding(16.dp)
    ) {
        if (bitmaps.isNotEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = screenHeight * 0.4f)
            ) {
                Image(
                    bitmap = bitmaps[selectedIndex].asImageBitmap(),
                    contentDescription = "Captured screenshot",
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .border(1.dp, Color.White.copy(alpha = 0.15f), RoundedCornerShape(12.dp)),
                    contentScale = ContentScale.Fit
                )

                IconButton(
                    onClick = { onRemoveScreenshot(selectedIndex) },
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(8.dp)
                        .size(32.dp)
                        .background(Color.Black.copy(alpha = 0.85f), CircleShape)
                ) {
                    Icon(
                        imageVector = Icons.Default.Close,
                        contentDescription = "Remove screenshot",
                        tint = Color.White,
                        modifier = Modifier.size(18.dp)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        if (bitmaps.size > 1) {
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(72.dp)
            ) {
                itemsIndexed(bitmaps) { index, bitmap ->
                    Box(
                        modifier = Modifier
                            .width(60.dp)
                            .fillMaxHeight()
                            .clip(RoundedCornerShape(10.dp))
                            .background(
                                if (index == selectedIndex) {
                                    Color.White.copy(alpha = 0.12f)
                                } else {
                                    Color.White.copy(alpha = 0.04f)
                                }
                            )
                            .clickable { selectedIndex = index }
                            .padding(2.dp)
                    ) {
                        Image(
                            bitmap = bitmap.asImageBitmap(),
                            contentDescription = "Screenshot thumbnail",
                            modifier = Modifier
                                .fillMaxSize()
                                .clip(RoundedCornerShape(8.dp)),
                            contentScale = ContentScale.Crop
                        )
                    }
                }
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
            color = Color.Gray,
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
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("Retake", color = Color.White)
            }
            if (bitmaps.size < maxScreenshots) {
                OutlinedButton(
                    onClick = onAddMore,
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("+ Add more", color = OverlayColors.AccentPink)
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        Button(
            onClick = onConfirm,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = OverlayColors.AccentPink),
            shape = RoundedCornerShape(12.dp)
        ) {
            Text("Generate replies")
        }
    }
}
