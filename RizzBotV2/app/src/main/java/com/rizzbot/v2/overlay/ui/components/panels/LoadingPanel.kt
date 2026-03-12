package com.rizzbot.v2.overlay.ui.components.panels

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.rizzbot.v2.overlay.ui.theme.OverlayColors
import kotlinx.coroutines.delay

/**
 * Loading panel shown while generating replies
 */
@Composable
fun LoadingOverlay(modifier: Modifier = Modifier) {
    var dotCount by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(500)
            dotCount = (dotCount + 1) % 4
        }
    }
    val dots = ".".repeat(dotCount)

    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        CircularProgressIndicator(color = OverlayColors.AccentPink)
        Spacer(modifier = Modifier.height(16.dp))
        Text("Cooking up replies$dots", color = Color.White)
    }
}

/**
 * Processing panel shown specifically while analyzing an uploaded image
 */
@Composable
fun ProcessingOverlay(modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        CircularProgressIndicator(color = Color(0xFFFFD700))
        Spacer(modifier = Modifier.height(16.dp))
        Text("Analyzing her vibe...", color = Color.White)
        Spacer(modifier = Modifier.height(4.dp))
        Text("Cloning your style...", color = Color.Gray)
    }
}
