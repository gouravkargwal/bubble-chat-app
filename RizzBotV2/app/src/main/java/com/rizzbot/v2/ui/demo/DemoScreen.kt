package com.rizzbot.v2.ui.demo

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.ui.theme.NeonRed
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite

data class DemoScenario(
    val title: String,
    val description: String,
    val theirMessage: String,
    val direction: String,
    val replies: List<Pair<String, String>>
)

private val demoScenarios = listOf(
    DemoScenario(
        title = "Opening Move",
        description = "You matched with someone who loves hiking and photography",
        theirMessage = "Hey! I see you're into photography too \uD83D\uDCF8 What do you usually shoot?",
        direction = "Quick Reply",
        replies = listOf(
            "\uD83D\uDD25 Flirty" to "Mostly landscapes, but I have a feeling my favorite subject just matched with me \uD83D\uDE0F",
            "\uD83D\uDE0F Witty" to "Sunsets, street scenes, and the occasional food pic. What about you?",
            "\u2728 Smooth" to "I'm big on golden hour shots. I'd love to see your work sometime.",
            "\uD83D\uDCAA Bold" to "Everything that catches my eye. Right now that's you."
        )
    ),
    DemoScenario(
        title = "Get Their Number",
        description = "Conversation has been going well for a few messages",
        theirMessage = "Haha that's hilarious! You're actually really fun to talk to \uD83D\uDE04",
        direction = "Get their number",
        replies = listOf(
            "\uD83D\uDD25 Flirty" to "I'm even more fun over text \uD83D\uDE0F What's your number?",
            "\uD83D\uDE0F Witty" to "I'd say the same about you! But fair warning, I'm way funnier on iMessage.",
            "\u2728 Smooth" to "This convo is too good for this app. Drop your number?",
            "\uD83D\uDCAA Bold" to "Right back at you! Let's move to texting where the real fun happens."
        )
    ),
    DemoScenario(
        title = "Profile Opener",
        description = "Travel photos and Thai food lover",
        theirMessage = "(Profile view \u2014 no conversation yet)",
        direction = "Quick Reply (Profile detected \u2192 Openers)",
        replies = listOf(
            "\uD83D\uDD25 Flirty" to "What's your go-to Thai dish? Someone with that travel taste has good judgment \uD83C\uDF36\uFE0F",
            "\uD83D\uDE0F Witty" to "Let me guess... you've had pad thai in at least 4 different countries.",
            "\u2728 Smooth" to "Your Chiang Mai photos are incredible. Would love to compare notes.",
            "\uD83D\uDCAA Bold" to "Travel photos AND Thai food? That's like finding a unicorn."
        )
    )
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DemoScreen(onBack: () -> Unit, onContinue: () -> Unit, onPremium: () -> Unit = {}) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("See It In Action", fontWeight = FontWeight.Bold, color = NothingWhite) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = NothingWhite) } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = NothingBlack, titleContentColor = NothingWhite)
            )
        },
        containerColor = NothingBlack
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).padding(NothingDimens.screenPadding)) {
            Text("Here's what Cookd can do", color = NothingWhite, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Illustrative examples of AI-generated replies", color = NothingTextSecondary, style = MaterialTheme.typography.labelMedium)
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
            demoScenarios.forEachIndexed { index, scenario ->
                DemoCard(scenario = scenario, number = index + 1)
                Spacer(modifier = Modifier.height(NothingDimens.elementGap))
            }
            Button(
                onClick = onContinue,
                colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(NothingDimens.pillRadius)
            ) { Text("Continue", color = NothingBlack, fontWeight = FontWeight.Bold, modifier = Modifier.padding(8.dp)) }
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
            OutlinedButton(
                onClick = onPremium,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(NothingDimens.pillRadius),
                border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
            ) { Text("View Premium Plans", color = NothingTextSecondary, fontWeight = FontWeight.Bold) }
            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}

@Composable
private fun DemoCard(scenario: DemoScenario, number: Int) {
    Card(
        colors = CardDefaults.cardColors(containerColor = NothingSurface),
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
    ) {
        Column(modifier = Modifier.padding(NothingDimens.cardPadding)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier.size(28.dp).background(NothingWhite, RoundedCornerShape(6.dp)),
                    contentAlignment = Alignment.Center
                ) { Text("$number", color = NothingBlack, fontWeight = FontWeight.Bold, fontSize = 12.sp) }
                Spacer(modifier = Modifier.width(NothingDimens.elementGap))
                Column {
                    Text(scenario.title, color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleSmall)
                    Text(scenario.description, color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                }
            }
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
            Text("Their message:", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall)
            Text(scenario.theirMessage, color = NothingWhite, style = MaterialTheme.typography.bodyMedium)
            Spacer(modifier = Modifier.height(NothingDimens.textGap))
            Text("Direction: ${scenario.direction}", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.SemiBold)
            Spacer(modifier = Modifier.height(NothingDimens.textGap))
            scenario.replies.forEach { (label, reply) ->
                Card(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp),
                    colors = CardDefaults.cardColors(containerColor = NothingSurface),
                    shape = RoundedCornerShape(NothingDimens.cardRadius),
                    border = BorderStroke(NothingDimens.borderThickness, NothingBorder)
                ) {
                    Column(modifier = Modifier.padding(NothingDimens.cardPadding)) {
                        Text(label, color = NothingTextSecondary, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelSmall)
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(reply, color = NothingWhite, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
    }
}
