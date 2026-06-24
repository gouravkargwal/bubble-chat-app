package com.rizzbot.v2.ui.openers

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

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
 * Design system rules enforced:
 * - Colors: Only [MaterialTheme.colorScheme] tokens — no hardcoded hex values.
 * - Spacing: Strict 8-point grid (4, 8, 16, 24, 32 dp).
 * - Shapes: Cards use [RoundedCornerShape(12.dp)] with 1dp crisp borders. Buttons use [CircleShape].
 * - Elevation: None. Drop shadows are forbidden.
 * - Typography: [MaterialTheme.typography.headlineMedium], [bodyLarge], [labelSmall].
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
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onBackground,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = MaterialTheme.colorScheme.onBackground,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                    titleContentColor = MaterialTheme.colorScheme.onBackground,
                ),
            )
        },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize(),
            contentPadding = PaddingValues(
                start = 16.dp,
                end = 16.dp,
                top = 16.dp,
                bottom = 32.dp,
            ),
            verticalArrangement = Arrangement.spacedBy(16.dp),
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
 * A single opener card showing the generated message, a strategy label, and a copy button.
 *
 * - Card uses MaterialTheme surface color, no elevation, crisp 1dp border.
 * - Strategy label uses [MaterialTheme.typography.labelSmall] (monospaced in the Nothing OS theme).
 * - Body text uses [MaterialTheme.typography.bodyLarge].
 * - Copy button is a pill-shaped [CircleShape] icon button.
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
            containerColor = MaterialTheme.colorScheme.surface,
        ),
        shape = RoundedCornerShape(12.dp),
        border = BorderStroke(
            width = 1.dp,
            color = MaterialTheme.colorScheme.outline,
        ),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            // Strategy label — uses labelSmall (monospaced in Nothing OS theme)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = opener.strategy,
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    text = "#${index + 1}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
                )
            }

            // Generated message
            Text(
                text = opener.text,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onBackground,
            )

            // Copy to Clipboard — pill-shaped icon button (CircleShape per spec)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
            ) {
                IconButton(
                    onClick = onCopy,
                    modifier = Modifier.size(48.dp),
                ) {
                    Icon(
                        imageVector = Icons.Default.ContentCopy,
                        contentDescription = "Copy opener",
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(16.dp),
                    )
                }
            }
        }
    }
}
