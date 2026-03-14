package com.rizzbot.v2.ui.paywall

import android.app.Activity
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel

private val DarkBg = Color(0xFF0F0F1A)
private val CardBg = Color(0xFF1A1A2E)
private val Pink = Color(0xFFE91E63)
private val GodModeGold = Color(0xFFFFD700)
private val FreeTrialGreen = Color(0xFF4CAF50)

@Composable
fun PaywallScreen(
    onDismiss: () -> Unit,
    onPurchaseSuccess: () -> Unit,
    viewModel: PaywallViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current
    val activity = context as? Activity

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = DarkBg
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp)
        ) {
            // Top Bar - Close Button
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End
            ) {
                IconButton(onClick = onDismiss) {
                    Icon(
                        Icons.Default.Close,
                        contentDescription = "Close",
                        tint = Color.White
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Hero Section
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Pulsing Emoji
                val infiniteTransition = rememberInfiniteTransition(label = "pulse")
                val scale by infiniteTransition.animateFloat(
                    initialValue = 0.9f,
                    targetValue = 1.1f,
                    animationSpec = infiniteRepeatable(
                        animation = tween(1000, easing = FastOutSlowInEasing),
                        repeatMode = RepeatMode.Reverse
                    ),
                    label = "scale"
                )

                Text(
                    "👑",
                    fontSize = 64.sp,
                    modifier = Modifier
                        .graphicsLayer {
                            scaleX = scale
                            scaleY = scale
                        }
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Headline
                Text(
                    "Unlock God Mode",
                    color = GodModeGold,
                    fontSize = 32.sp,
                    fontWeight = FontWeight.ExtraBold,
                    textAlign = TextAlign.Center
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Subheadline
                Text(
                    "Stop guessing. Start matching. Let Cookd's AI take over your dating life.",
                    color = Color.White.copy(alpha = 0.8f),
                    fontSize = 16.sp,
                    textAlign = TextAlign.Center,
                    lineHeight = 24.sp
                )
            }

            Spacer(modifier = Modifier.height(32.dp))

            // Feature Checklist
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                FeatureRow("Unlimited AI Chat Replies")
                FeatureRow("Deep Voice DNA Cloning")
                FeatureRow("Brutal Profile Audits")
            }

            Spacer(modifier = Modifier.height(32.dp))

            // Package Selector
            if (state.isLoading) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(200.dp),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = GodModeGold)
                }
            } else if (state.packages.isNotEmpty()) {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    state.packages.forEach { packageItem ->
                        PackageCard(
                            packageItem = packageItem,
                            isSelected = state.selectedPackage?.identifier == packageItem.identifier,
                            onClick = { viewModel.selectPackage(packageItem) }
                        )
                    }
                }
            } else {
                // No packages available
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = CardBg)
                ) {
                    Text(
                        "No packages available",
                        color = Color.White,
                        modifier = Modifier.padding(16.dp),
                        textAlign = TextAlign.Center
                    )
                }
            }

            // Error message
            val errorMessage = state.purchaseError
            if (errorMessage != null) {
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    errorMessage,
                    color = Color(0xFFEF5350),
                    fontSize = 14.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )
            }

            Spacer(modifier = Modifier.weight(1f))

            // CTA Button
            val selectedPackage = state.selectedPackage
            if (selectedPackage != null && activity != null) {
                // Pulsing animation for CTA
                val infiniteTransition = rememberInfiniteTransition(label = "ctaPulse")
                val ctaScale by infiniteTransition.animateFloat(
                    initialValue = 1f,
                    targetValue = 1.02f,
                    animationSpec = infiniteRepeatable(
                        animation = tween(1500, easing = FastOutSlowInEasing),
                        repeatMode = RepeatMode.Reverse
                    ),
                    label = "ctaScale"
                )

                Button(
                    onClick = {
                        viewModel.makePurchase(activity, selectedPackage, onPurchaseSuccess)
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = GodModeGold),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp)
                        .graphicsLayer {
                            scaleX = ctaScale
                            scaleY = ctaScale
                        },
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Text(
                        "Start 3-Day Free Trial",
                        color = Color.Black,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Footer
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically
            ) {
                TextButton(onClick = {
                    viewModel.restorePurchases(onPurchaseSuccess)
                }) {
                    Text(
                        "Restore Purchases",
                        color = Color.Gray,
                        fontSize = 12.sp
                    )
                }
                Text(
                    " | ",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
                TextButton(onClick = { /* TODO: Open Terms */ }) {
                    Text(
                        "Terms",
                        color = Color.Gray,
                        fontSize = 12.sp
                    )
                }
                Text(
                    " | ",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
                TextButton(onClick = { /* TODO: Open Privacy */ }) {
                    Text(
                        "Privacy",
                        color = Color.Gray,
                        fontSize = 12.sp
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))
        }
    }
}

@Composable
private fun FeatureRow(text: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            Icons.Default.Check,
            contentDescription = null,
            tint = Pink,
            modifier = Modifier.size(24.dp)
        )
        Spacer(modifier = Modifier.width(12.dp))
        Text(
            text,
            color = Color.White,
            fontSize = 16.sp,
            fontWeight = FontWeight.Medium
        )
    }
}

@Composable
private fun PackageCard(
    packageItem: com.revenuecat.purchases.Package,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    val isMonthly = packageItem.identifier.contains("monthly", ignoreCase = true) ||
                    packageItem.identifier.contains("month", ignoreCase = true)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .then(
                if (isSelected) {
                    Modifier.border(2.dp, GodModeGold, RoundedCornerShape(16.dp))
                } else {
                    Modifier
                }
            ),
        colors = CardDefaults.cardColors(
            containerColor = if (isSelected) {
                CardBg.copy(alpha = 0.8f)
            } else {
                CardBg
            }
        ),
        shape = RoundedCornerShape(16.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .then(
                    if (isSelected) {
                        Modifier.background(
                            Brush.horizontalGradient(
                                colors = listOf(
                                    GodModeGold.copy(alpha = 0.1f),
                                    GodModeGold.copy(alpha = 0.05f)
                                )
                            )
                        )
                    } else {
                        Modifier
                    }
                )
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(20.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            packageItem.product.title,
                            color = Color.White,
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            packageItem.product.description,
                            color = Color.White.copy(alpha = 0.7f),
                            fontSize = 14.sp
                        )
                    }
                    
                    // Free Trial Badge for Monthly
                    if (isMonthly) {
                        Surface(
                            color = FreeTrialGreen,
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.padding(start = 8.dp)
                        ) {
                            Text(
                                "3-Day Free Trial",
                                color = Color.White,
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }
                }
                
                Spacer(modifier = Modifier.height(12.dp))
                
                // Format price - RevenueCat Product has price property
                val priceText = try {
                    // Try to get formatted price
                    packageItem.product.price.formatted
                } catch (e: Exception) {
                    // Fallback: use product title or identifier
                    try {
                        packageItem.product.title
                    } catch (e2: Exception) {
                        packageItem.identifier
                    }
                }
                
                Text(
                    priceText,
                    color = GodModeGold,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
