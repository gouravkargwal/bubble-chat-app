package com.rizzbot.v2.ui.demo

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

data class DemoScenario(
    val title: String,
    val description: String,
    val theirMessage: String,
    val direction: String,
    val replies: List<Pair<String, String>> // label to reply
)

private val demoScenarios = listOf(
    DemoScenario(
        title = "Opening Move",
        description = "You matched with someone who loves hiking and photography",
        theirMessage = "Hey! I see you're into photography too \uD83D\uDCF8 What do you usually shoot?",
        direction = "Quick Reply",
        replies = listOf(
            "\uD83D\uDD25 Flirty" to "Mostly landscapes, but I have a feeling my favorite subject just matched with me \uD83D\uDE0F",
            "\uD83D\uDE0F Witty" to "Sunsets, street scenes, and the occasional food pic when it's too pretty not to. What about you \u2014 mountains or cityscapes?",
            "\u2728 Smooth" to "I'm big on golden hour shots \u2014 there's something about that light. I'd love to see your work sometime, maybe over coffee?",
            "\uD83D\uDCAA Bold" to "Everything that catches my eye. Right now that's you, your hiking pics, and wondering which trail we should hit first"
        )
    ),
    DemoScenario(
        title = "Get Their Number",
        description = "Conversation has been going well for a few messages",
        theirMessage = "Haha that's hilarious! You're actually really fun to talk to \uD83D\uDE04",
        direction = "\uD83D\uDD25 Get their number",
        replies = listOf(
            "\uD83D\uDD25 Flirty" to "I'm even more fun over text \uD83D\uDE0F What's your number? This app keeps burying our chat",
            "\uD83D\uDE0F Witty" to "I'd say the same about you! But fair warning, I'm way funnier on iMessage. 555-... just kidding, you go first \uD83D\uDE02",
            "\u2728 Smooth" to "Honestly this convo is too good for an app that sends notifications once a day. Drop your number and let's keep this going?",
            "\uD83D\uDCAA Bold" to "Right back at you! So are we gonna keep fighting with this app or move to texting where the real fun happens?"
        )
    ),
    DemoScenario(
        title = "Profile Opener",
        description = "You're viewing someone's profile \u2014 they have travel photos and mention loving Thai food",
        theirMessage = "(Profile view \u2014 no conversation yet)",
        direction = "Quick Reply (Profile detected \u2192 Openers)",
        replies = listOf(
            "\uD83D\uDD25 Flirty" to "I need to know \u2014 what's your go-to Thai dish? Because someone with that travel taste clearly has good judgment \uD83C\uDF36\uFE0F",
            "\uD83D\uDE0F Witty" to "Let me guess... you've had pad thai in at least 4 different countries and ranked them all. Am I close?",
            "\u2728 Smooth" to "Your Chiang Mai photos are incredible. I spent 2 weeks there last year \u2014 would love to compare notes over som tum sometime",
            "\uD83D\uDCAA Bold" to "Travel photos that actually look interesting AND you like Thai food? That's like finding a unicorn on here. When are we getting Pad See Ew?"
        )
    )
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DemoScreen(
    onBack: () -> Unit,
    onContinue: () -> Unit,
    onPremium: () -> Unit = {}
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("See It In Action", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF0F0F1A),
                    titleContentColor = Color.White
                )
            )
        },
        containerColor = Color(0xFF0F0F1A)
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp)
        ) {
            Text(
                "Here's what Cookd can do",
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
            Text(
                "Illustrative examples of AI-generated replies",
                color = Color.Gray,
                fontSize = 13.sp
            )

            Spacer(modifier = Modifier.height(20.dp))

            demoScenarios.forEachIndexed { index, scenario ->
                DemoCard(scenario = scenario, number = index + 1)
                Spacer(modifier = Modifier.height(16.dp))
            }

            Spacer(modifier = Modifier.height(8.dp))

            // CTA
            Button(
                onClick = onContinue,
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE91E63)),
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("Continue", modifier = Modifier.padding(8.dp), fontWeight = FontWeight.Bold)
            }

            Spacer(modifier = Modifier.height(12.dp))

            OutlinedButton(
                onClick = onPremium,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("View Premium Plans", color = Color(0xFFE91E63), fontWeight = FontWeight.Bold)
            }

            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}

@Composable
private fun DemoCard(scenario: DemoScenario, number: Int) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Header
            Row(verticalAlignment = Alignment.CenterVertically) {
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFE91E63)),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        "$number",
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                    )
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(scenario.title, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    Text(scenario.description, color = Color.Gray, fontSize = 12.sp)
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Their message bubble
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF252542)),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("Their message:", color = Color.Gray, fontSize = 11.sp)
                    Text(scenario.theirMessage, color = Color.White, fontSize = 14.sp)
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Direction used
            Text(
                "Direction: ${scenario.direction}",
                color = Color(0xFFE91E63),
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Reply suggestions
            scenario.replies.forEach { (label, reply) ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 3.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF252542)),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        Text(label, color = Color(0xFFE91E63), fontWeight = FontWeight.Bold, fontSize = 11.sp)
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(reply, color = Color.White, fontSize = 13.sp)
                    }
                }
            }
        }
    }
}
