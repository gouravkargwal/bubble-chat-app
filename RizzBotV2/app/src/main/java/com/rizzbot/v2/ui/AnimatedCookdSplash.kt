package com.rizzbot.v2.ui

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.rizzbot.v2.R
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingWhite
import com.rizzbot.v2.ui.components.CookdLogo
import kotlinx.coroutines.delay

/**
 * An elegant animated splash screen that replaces the static [BrandedBootScreen].
 *
 * Animation sequence:
 * 1. Logo scales in (0.8 → 1.0) with fade-in over 600ms
 * 2. Divider line draws from center outward
 * 3. Tagline fades in
 * 4. Holds final state until the parent navigates away
 */
@Composable
fun AnimatedCookdSplash() {
    // Phase tracking to synchronize animations sequentially
    var phase by remember { mutableStateOf(0) }

    val logoScale by animateFloatAsState(
        targetValue = if (phase >= 1) 1f else 0.8f,
        animationSpec = tween(600, easing = FastOutSlowInEasing),
        label = "logoScale",
    )
    val logoAlpha by animateFloatAsState(
        targetValue = if (phase >= 1) 1f else 0f,
        animationSpec = tween(500, easing = FastOutSlowInEasing),
        label = "logoAlpha",
    )
    val dividerAlpha by animateFloatAsState(
        targetValue = if (phase >= 2) 1f else 0f,
        animationSpec = tween(400, easing = FastOutSlowInEasing),
        label = "dividerAlpha",
    )
    val taglineAlpha by animateFloatAsState(
        targetValue = if (phase >= 3) 1f else 0f,
        animationSpec = tween(500, easing = FastOutSlowInEasing),
        label = "taglineAlpha",
    )

    LaunchedEffect(Unit) {
        // Phase 1: Logo appears
        phase = 1
        delay(650)
        // Phase 2: Divider draws
        phase = 2
        delay(450)
        // Phase 3: Tagline fades in
        phase = 3
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(NothingBlack),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.fillMaxWidth(),
        ) {
            // ── Logo with scale + fade ──
            Box(
                modifier = Modifier
                    .graphicsLayer(
                        scaleX = logoScale,
                        scaleY = logoScale,
                        alpha = logoAlpha,
                    ),
                contentAlignment = Alignment.Center,
            ) {
                CookdLogo(size = 80.dp)
            }

            Spacer(modifier = Modifier.height(28.dp))

            Text(
                text = stringResource(R.string.app_name),
                style = MaterialTheme.typography.displaySmall,
                color = NothingWhite,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .graphicsLayer(alpha = logoAlpha),
            )

            Spacer(modifier = Modifier.height(NothingDimens.elementGap))

            // ── Animated divider line ──
            Box(
                modifier = Modifier
                    .width(40.dp)
                    .height(3.dp)
                    .clip(CircleShape)
                    .background(NothingBorder)
                    .graphicsLayer(alpha = dividerAlpha),
            )

            Spacer(modifier = Modifier.height(NothingDimens.elementGap))

            // ── Tagline ──
            Text(
                text = stringResource(R.string.boot_tagline),
                style = MaterialTheme.typography.bodyLarge,
                color = NothingTextSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .graphicsLayer(alpha = taglineAlpha),
            )
        }
    }
}
