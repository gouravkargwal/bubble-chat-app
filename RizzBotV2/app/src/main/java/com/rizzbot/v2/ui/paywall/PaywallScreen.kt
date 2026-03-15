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
                // Headline
                Text(
                    "Unlock Cookd Pro & Premium",
                    color = Color.White,
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Subheadline
                Text(
                    "Get unlimited AI-powered replies, profile optimization, and more",
                    color = Color.White.copy(alpha = 0.7f),
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
                FeatureRow("Unlimited AI Chat")
                FeatureRow("Profile Auditor")
                FeatureRow("AI Twin")
            }

            Spacer(modifier = Modifier.height(32.dp))

            // Package Selector
            when (val uiState = state.uiState) {
                is PaywallUiState.Loading -> {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(200.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(color = Pink)
                    }
                }
                is PaywallUiState.Success -> {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        // Pro Plans Section
                        if (state.proPackages.isNotEmpty()) {
                            Text(
                                "Pro Plans",
                                color = Color.White,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.SemiBold,
                                modifier = Modifier.padding(bottom = 8.dp)
                            )
                            
                            state.proPackages.forEach { packageItem ->
                                PackageCard(
                                    packageItem = packageItem,
                                    isSelected = state.selectedPackage?.identifier == packageItem.identifier,
                                    isBestValue = false,
                                    onClick = { viewModel.selectPackage(packageItem) }
                                )
                            }
                            
                            Spacer(modifier = Modifier.height(8.dp))
                        }
                        
                        // Premium Plans Section
                        if (state.premiumPackages.isNotEmpty()) {
                            Text(
                                "Premium Plans",
                                color = Color.White,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.SemiBold,
                                modifier = Modifier.padding(bottom = 8.dp)
                            )
                            
                            state.premiumPackages.forEach { packageItem ->
                                val isBestValue = packageItem.identifier == "premium_monthly"
                                PackageCard(
                                    packageItem = packageItem,
                                    isSelected = state.selectedPackage?.identifier == packageItem.identifier,
                                    isBestValue = isBestValue,
                                    onClick = { viewModel.selectPackage(packageItem) }
                                )
                            }
                        }
                    }
                }
                is PaywallUiState.Error -> {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = CardBg)
                    ) {
                        Text(
                            uiState.message,
                            color = Color.White,
                            modifier = Modifier.padding(16.dp),
                            textAlign = TextAlign.Center
                        )
                    }
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
                Button(
                    onClick = {
                        viewModel.purchasePackage(activity, selectedPackage, onPurchaseSuccess)
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Pink),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp),
                    shape = RoundedCornerShape(16.dp),
                    enabled = state.purchaseError == null && !state.purchaseSuccess
                ) {
                    Text(
                        "Subscribe Now",
                        color = Color.White,
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
    isBestValue: Boolean,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .then(
                if (isSelected) {
                    Modifier.border(2.dp, Pink, RoundedCornerShape(16.dp))
                } else {
                    Modifier.border(1.dp, Color.White.copy(alpha = 0.1f), RoundedCornerShape(16.dp))
                }
            ),
        colors = CardDefaults.cardColors(
            containerColor = if (isSelected) {
                CardBg.copy(alpha = 0.9f)
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
                                    Pink.copy(alpha = 0.15f),
                                    Pink.copy(alpha = 0.05f)
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
                    verticalAlignment = Alignment.Top
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        // Package name
                        Text(
                            text = when (packageItem.identifier) {
                                "Weekly" -> "Pro Weekly"
                                "Monthly" -> "Pro Monthly"
                                "premium_weekly" -> "Premium Weekly"
                                "premium_monthly" -> "Premium Monthly"
                                else -> packageItem.product.title
                            },
                            color = Color.White,
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        // Period description
                        val periodText = when {
                            packageItem.identifier.contains("weekly", ignoreCase = true) -> "Billed weekly"
                            packageItem.identifier.contains("monthly", ignoreCase = true) -> "Billed monthly"
                            else -> packageItem.product.description
                        }
                        Text(
                            periodText,
                            color = Color.White.copy(alpha = 0.7f),
                            fontSize = 14.sp
                        )
                    }
                    
                    // Best Value Badge
                    if (isBestValue) {
                        Surface(
                            color = Pink,
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.padding(start = 8.dp)
                        ) {
                            Text(
                                "Best Value",
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
                    packageItem.product.price.formatted
                } catch (e: Exception) {
                    try {
                        packageItem.product.title
                    } catch (e2: Exception) {
                        packageItem.identifier
                    }
                }
                
                Text(
                    priceText,
                    color = Pink,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
