package com.rizzbot.v2.ui.openers

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite

/**
 * Data class representing a single generated opener suggestion.
 */
data class GeneratedOpener(
    val text: String,
    val strategy: String,
)

/**
 * Displays a list of AI-generated opening messages.
 *
 * Nothing OS design rules enforced:
 * - Colors: Nothing OS palette (NothingBlack, NothingSurface, NothingWhite, NothingTextSecondary).
 * - Spacing: NothingDimens tokens for consistency across the app.
 * - Shapes: Cards use NothingDimens.cardRadius (12dp) with 1dp NothingBorder outlines.
 * - Elevation: None. Drop shadows are forbidden.
 * - Typography: NothingTypography via MaterialTheme (monospaced labels, bold titles).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GeneratedOpenersScreen(
    onBack: () -> Unit,
) {
    val context = LocalContext.current

    // Sample openers — in a real app these would come from a ViewModel.
    val openers = listOf(
        GeneratedOpener(
            text = "I usually don't match with people who look this good in golden hour lighting, but here we are \uD83D\uDE0F What's your secret \u2014 professional photographer or just naturally photo-ready?",
            strategy = "FRAME CONTROL",
        ),
        GeneratedOpener(
            text = "Okay I need the honest answer \u2014 is that a rescue dog in your third pic or did you just steal him for the profile? Either way, I'm a sucker for a good wingman \uD83D\uDC36",
            strategy = "PLAYFUL TEASE",
        ),
        GeneratedOpener(
            text = "Your travel stack is ridiculous \u2014 Kyoto, Patagonia, and Iceland in one profile? That's either a really good job or you're secretly a travel blogger. I'm gonna need the backstory on that Patagonia shot \uD83E\uDD14",
            strategy = "DETAILED OBSERVE",
        ),
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Kabir's Suggestions",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = NothingWhite,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = NothingWhite,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = NothingBlack,
                    titleContentColor = NothingWhite,
                ),
            )
        },
        containerColor = NothingBlack,
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize(),
            contentPadding = PaddingValues(
                start = NothingDimens.screenPadding,
                end = NothingDimens.screenPadding,
                top = NothingDimens.screenPadding,
                bottom = 32.dp,
            ),
            verticalArrangement = Arrangement.spacedBy(NothingDimens.sectionSpacing),
        ) {
            itemsIndexed(openers) { index, opener ->
                OpenerCard(
                    index = index,
                    opener = opener,
                    onCopy = {
                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        clipboard.setPrimaryClip(
                            ClipData.newPlainText("Generated Opener", opener.text)
                        )
                    },
                )
            }
        }
    }
}

/**
 * A single opener card following Nothing OS design system.
 *
 * - Card uses NothingSurface, no elevation, crisp 1dp NothingBorder.
 * - Strategy label uses labelSmall (monospaced in NothingTypography).
 * - Body text uses bodyMedium.
 * - Copy button is a clean icon within the card.
 */
@Composable
private fun OpenerCard(
    index: Int,
    opener: GeneratedOpener,
    onCopy: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = NothingSurface,
        ),
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        border = BorderStroke(
            width = NothingDimens.borderThickness,
            color = NothingBorder,
        ),
    ) {
        Column(
            modifier = Modifier.padding(NothingDimens.cardPadding),
            verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap),
        ) {
            // Strategy label — uses labelSmall (monospaced in Nothing OS theme)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = opener.strategy.uppercase(),
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    color = NothingTextSecondary,
                )
                Box(
                    modifier = Modifier
                        .size(24.dp)
                        .clip(RoundedCornerShape(4.dp))
                        .background(NothingBorder),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "${index + 1}",
                        style = MaterialTheme.typography.labelSmall,
                        color = NothingTextSecondary,
                        fontSize = 11.sp,
                    )
                }
            }

            // Generated message
            Text(
                text = opener.text,
                style = MaterialTheme.typography.bodyMedium,
                color = NothingWhite,
            )

            // Copy to Clipboard
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
            ) {
                IconButton(
                    onClick = onCopy,
                    modifier = Modifier.size(NothingDimens.minTouchTarget),
                ) {
                    Icon(
                        imageVector = Icons.Default.ContentCopy,
                        contentDescription = "Copy opener",
                        tint = NothingTextSecondary,
                        modifier = Modifier.size(16.dp),
                    )
                }
            }
        }
    }
}
