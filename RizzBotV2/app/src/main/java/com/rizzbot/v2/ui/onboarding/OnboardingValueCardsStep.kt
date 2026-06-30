package com.rizzbot.v2.ui.onboarding

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
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
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.Forum
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingWhite

private data class ValueCard(
    val icon: ImageVector,
    val headline: String,
    val description: String,
)

private val cards = listOf(
    ValueCard(
        icon = Icons.Filled.Forum,
        headline = "Never be left on read again",
        description = "Screenshot any conversation and let AI craft the perfect reply in your voice. Natural, flirty, witty \u2014 whatever fits.",
    ),
    ValueCard(
        icon = Icons.Filled.AutoAwesome,
        headline = "Your profile, perfected",
        description = "Get an AI-powered audit of your dating profile. See what works, what doesn\u2019t, and exactly how to improve your matches.",
    ),
    ValueCard(
        icon = Icons.Filled.Bolt,
        headline = "Always know what to say",
        description = "Real-time reply suggestions appear right inside your messaging apps. No switching back and forth \u2014 just tap and send.",
    ),
)

/**
 * Full-screen swipeable value proposition cards that introduce Cookd's core features.
 *
 * Shows 3 horizontally swipeable cards with page indicators and an always-visible
 * "Get Started" button.
 */
@Composable
fun OnboardingValueCardsStep(
    onGetStarted: () -> Unit,
) {
    val pagerState = rememberPagerState(
        pageCount = { cards.size },
    )

    Box(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.fillMaxSize()) {
            // ── Swipeable cards ──
            HorizontalPager(
                state = pagerState,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
                beyondViewportPageCount = 1,
            ) { page ->
                ValueCardContent(cards[page])
            }

            // ── Bottom: page indicators + action button ──
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 48.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                // Page dots
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    repeat(cards.size) { index ->
                        val isSelected = pagerState.currentPage == index
                        val dotSize = if (isSelected) 10.dp else 8.dp
                        val dotColor by animateColorAsState(
                            targetValue = if (isSelected) NothingWhite else NothingBorder,
                            animationSpec = tween(300, easing = FastOutSlowInEasing),
                            label = "dotColor",
                        )
                        Box(
                            modifier = Modifier
                                .size(dotSize)
                                .clip(CircleShape)
                                .background(dotColor),
                        )
                    }
                }

                Spacer(modifier = Modifier.height(32.dp))

                // Always show "Get Started" button
                Button(
                    onClick = onGetStarted,
                    colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
                    modifier = Modifier
                        .fillMaxWidth(0.8f)
                        .height(NothingDimens.minTouchTarget),
                    shape = RoundedCornerShape(NothingDimens.pillRadius),
                ) {
                    Text(
                        "Get Started",
                        color = NothingBlack,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
        }
    }
}

@Composable
private fun ValueCardContent(card: ValueCard) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = NothingDimens.screenPadding),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(modifier = Modifier.weight(0.5f))

        // Themed icon section — geometric container matching Nothing OS aesthetic
        Box(
            modifier = Modifier
                .size(88.dp)
                .clip(RoundedCornerShape(20.dp))
                .background(NothingBorder),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = card.icon,
                contentDescription = null,
                tint = NothingWhite,
                modifier = Modifier.size(44.dp),
            )
        }

        Spacer(modifier = Modifier.height(32.dp))

        // Headline
        Text(
            text = card.headline,
            style = MaterialTheme.typography.headlineSmall,
            color = NothingWhite,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )

        Spacer(modifier = Modifier.height(NothingDimens.elementGap))

        // Description
        Text(
            text = card.description,
            style = MaterialTheme.typography.bodyLarge,
            color = NothingTextSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth(0.85f),
        )

        Spacer(modifier = Modifier.weight(1f))
    }
}
