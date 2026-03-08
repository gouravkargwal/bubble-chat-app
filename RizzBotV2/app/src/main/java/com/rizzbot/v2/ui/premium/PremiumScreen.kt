package com.rizzbot.v2.ui.premium

import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PremiumScreen(
    onBack: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Go Premium", fontWeight = FontWeight.Bold) },
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
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(48.dp))

            Text("\uD83D\uDE80", fontSize = 64.sp)
            Spacer(modifier = Modifier.height(24.dp))

            Text(
                "Premium is Coming Soon",
                color = Color.White,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                "We're building something amazing. Premium will let you use RizzBot without needing your own API key.",
                color = Color.Gray,
                fontSize = 14.sp,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(32.dp))

            // Preview of tiers
            PricingPreviewCard(
                title = "Premium",
                price = "$4.99/mo",
                isRecommended = true,
                features = listOf(
                    "Unlimited AI replies",
                    "No API key needed",
                    "Profile optimization (unlimited)",
                    "Priority response speed"
                )
            )

            Spacer(modifier = Modifier.height(12.dp))

            PricingPreviewCard(
                title = "Pro",
                price = "$9.99/mo",
                isRecommended = false,
                features = listOf(
                    "Everything in Premium",
                    "Conversation analytics",
                    "Win rate tracking",
                    "Style learning (auto-adapt)"
                )
            )

            Spacer(modifier = Modifier.height(24.dp))

            TextButton(onClick = onBack) {
                Text("For now, use your own API key (free, unlimited)", color = Color(0xFFE91E63), fontSize = 13.sp)
            }

            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}

@Composable
private fun PricingPreviewCard(
    title: String,
    price: String,
    isRecommended: Boolean,
    features: List<String>
) {
    val borderModifier = if (isRecommended) {
        Modifier.border(2.dp, Color(0xFFE91E63), RoundedCornerShape(16.dp))
    } else {
        Modifier
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .then(borderModifier),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1A1A2E)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(title, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                if (isRecommended) {
                    Spacer(modifier = Modifier.width(8.dp))
                    Card(
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFE91E63)),
                        shape = RoundedCornerShape(4.dp)
                    ) {
                        Text(
                            "COMING SOON",
                            color = Color.White,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                        )
                    }
                }
            }
            Text(price, color = Color(0xFFE91E63), fontWeight = FontWeight.Bold, fontSize = 28.sp)

            Spacer(modifier = Modifier.height(12.dp))

            features.forEach { feature ->
                Row(modifier = Modifier.padding(vertical = 3.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Check, contentDescription = null, tint = Color(0xFF4CAF50), modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(feature, color = Color.White, fontSize = 14.sp)
                }
            }
        }
    }
}
