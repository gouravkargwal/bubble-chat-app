package com.rizzbot.v2.ui.paywall

import android.app.Activity
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
    // Local animation flag for the success checkmark
    var showSuccessIcon by remember { mutableStateOf(false) }
    LaunchedEffect(state.purchaseSuccess) {
        if (state.purchaseSuccess) {
            showSuccessIcon = true
        } else {
            showSuccessIcon = false
        }
    }
    LaunchedEffect(state.readyToNavigate) {
        if (state.readyToNavigate) {
            onPurchaseSuccess()
        }
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = DarkBg
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .padding(horizontal = 24.dp)
        ) {
            // Top Bar - Close Button
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp, bottom = 8.dp),
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

            // Scrollable content area - takes remaining space but scrolls if needed
            val scrollState = rememberScrollState()
            Column(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
            ) {
                AnimatedContent(
                    targetState = state.purchaseSuccess,
                    transitionSpec = {
                        fadeIn(animationSpec = tween(300)) togetherWith
                            fadeOut(animationSpec = tween(300))
                    },
                    label = "paywallSuccessContent"
                ) { isSuccess ->
                    if (isSuccess) {
                        // Post-purchase success UX
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 8.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            AnimatedVisibility(
                                visible = showSuccessIcon,
                                enter = fadeIn(animationSpec = tween(350)) +
                                    scaleIn(
                                        initialScale = 0.7f,
                                        animationSpec = tween(350, easing = FastOutSlowInEasing)
                                    ),
                                exit = fadeOut(animationSpec = tween(200))
                            ) {
                                Surface(
                                    color = Pink.copy(alpha = 0.15f),
                                    shape = RoundedCornerShape(999.dp),
                                    modifier = Modifier
                                        .size(88.dp)
                                ) {
                                    Box(
                                        contentAlignment = Alignment.Center,
                                        modifier = Modifier.fillMaxSize()
                                    ) {
                                        Icon(
                                            imageVector = Icons.Default.Check,
                                            contentDescription = "Premium unlocked",
                                            tint = Pink,
                                            modifier = Modifier.size(40.dp)
                                        )
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(16.dp))

                            Text(
                                "You’re in. Welcome to Premium 🎉",
                                color = Color.White,
                                fontSize = 24.sp,
                                fontWeight = FontWeight.Bold,
                                textAlign = TextAlign.Center
                            )

                            Spacer(modifier = Modifier.height(12.dp))

                            Text(
                                "Your account has been upgraded. Enjoy higher limits and all premium features right away.",
                                color = Color.White.copy(alpha = 0.8f),
                                fontSize = 16.sp,
                                textAlign = TextAlign.Center,
                                lineHeight = 24.sp
                            )
                        }
                    } else {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .verticalScroll(scrollState)
                        ) {
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

                // Tier Tabs (Pro vs Premium)
                when (val uiState = state.uiState) {
                    is PaywallUiState.Success -> {
                        TierTabs(
                            selectedTier = state.selectedTier,
                            activeTier = state.activeTier,
                            onTierSelected = { viewModel.selectTier(it) }
                        )
                        
                        Spacer(modifier = Modifier.height(24.dp))
                        
                        // Dynamic Feature List based on selected tier
                        AnimatedContent(
                            targetState = state.selectedTier,
                            transitionSpec = {
                                fadeIn(animationSpec = tween(300)) togetherWith
                                fadeOut(animationSpec = tween(300))
                            },
                            label = "features"
                        ) { tier ->
                            when (tier) {
                                PaywallTier.Pro -> {
                                    Column(
                                        modifier = Modifier.fillMaxWidth(),
                                        verticalArrangement = Arrangement.spacedBy(16.dp)
                                    ) {
                                        FeatureRow("Unlimited Chat")
                                        FeatureRow("Advanced Replies")
                                    }
                                }
                                PaywallTier.Premium -> {
                                    Column(
                                        modifier = Modifier.fillMaxWidth(),
                                        verticalArrangement = Arrangement.spacedBy(16.dp)
                                    ) {
                                        FeatureRow("Everything in Pro")
                                        FeatureRow("AI Twin Mode")
                                        FeatureRow("God-Mode Auditor")
                                    }
                                }
                            }
                        }
                        
                        Spacer(modifier = Modifier.height(32.dp))
                        
                        // Package Cards for selected tier
                        AnimatedContent(
                            targetState = state.selectedTier,
                            transitionSpec = {
                                fadeIn(animationSpec = tween(300)) + slideInHorizontally(
                                    initialOffsetX = { it },
                                    animationSpec = tween(300)
                                ) togetherWith
                                fadeOut(animationSpec = tween(300)) + slideOutHorizontally(
                                    targetOffsetX = { -it },
                                    animationSpec = tween(300)
                                )
                            },
                            label = "packages"
                        ) { tier ->
                            val packages = when (tier) {
                                PaywallTier.Pro -> state.proPackages
                                PaywallTier.Premium -> state.premiumPackages
                            }
                            
                            Column(
                                modifier = Modifier.fillMaxWidth(),
                                verticalArrangement = Arrangement.spacedBy(12.dp)
                            ) {
                                val isCurrentTier = state.activeTier == tier

                                packages.forEach { packageItem ->
                                    val isMonthly = packageItem.identifier.contains("monthly", ignoreCase = true)
                                    val savingsPercentage = if (isMonthly && packages.size >= 2) {
                                        calculateSavingsPercentage(packages)
                                    } else null
                                    
                                    PackageCard(
                                        packageItem = packageItem,
                                        isSelected = state.selectedPackage?.identifier == packageItem.identifier,
                                        isDisabled = isCurrentTier,
                                        savingsPercentage = savingsPercentage,
                                        onClick = { viewModel.selectPackage(packageItem) }
                                    )
                                }
                            }
                        }
                    }
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

                            // Add bottom padding to ensure content doesn't get cut off
                            Spacer(modifier = Modifier.height(24.dp))
                        }
                    }
                }
            }

            // Fixed bottom section with consistent spacing
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .navigationBarsPadding()
                    .padding(top = 16.dp, bottom = 12.dp)
            ) {
                if (state.purchaseSuccess) {
                    // Success primary CTA — refreshes backend data before navigating
                    Button(
                        onClick = { viewModel.refreshUserTierFromBackend() },
                        enabled = !state.isRefreshingAfterPurchase,
                        colors = ButtonDefaults.buttonColors(containerColor = Pink),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(56.dp),
                        shape = RoundedCornerShape(16.dp)
                    ) {
                        if (state.isRefreshingAfterPurchase) {
                            CircularProgressIndicator(
                                color = Color.White,
                                modifier = Modifier.size(24.dp),
                                strokeWidth = 2.dp
                            )
                        } else {
                            Text(
                                "Start Exploring 🚀",
                                color = Color.White,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                } else {
                    // Purchase CTA
                    val selectedPackage = state.selectedPackage
                    if (selectedPackage != null && activity != null) {
                        val isUpgradeToPremium =
                            state.activeTier == PaywallTier.Pro && state.selectedTier == PaywallTier.Premium
                        val isCurrentTier = state.activeTier == state.selectedTier

                        Button(
                            onClick = {
                                viewModel.purchasePackage(activity, selectedPackage, onPurchaseSuccess)
                            },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Pink,
                                disabledContainerColor = CardBg.copy(alpha = 0.5f)
                            ),
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(56.dp),
                            shape = RoundedCornerShape(16.dp),
                            enabled = state.purchaseError == null && !isCurrentTier
                        ) {
                            val buttonText = when {
                                isCurrentTier -> "Current Plan"
                                isUpgradeToPremium -> "Upgrade to Premium"
                                else -> "Subscribe Now"
                            }
                            val textColor = if (isCurrentTier) {
                                Color.White.copy(alpha = 0.5f)
                            } else {
                                Color.White
                            }

                            Text(
                                buttonText,
                                color = textColor,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }

                    // "I'll try first" dismiss button
                    TextButton(
                        onClick = onDismiss,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            "I'll try first",
                            color = Color.White.copy(alpha = 0.5f),
                            fontSize = 14.sp
                        )
                    }

                    // Footer
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        TextButton(onClick = { viewModel.restorePurchases(onPurchaseSuccess) }) {
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
                }
            }
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
private fun TierTabs(
    selectedTier: PaywallTier,
    activeTier: PaywallTier?,
    onTierSelected: (PaywallTier) -> Unit
) {
    Surface(
        color = CardBg,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(4.dp)
        ) {
            // Pro Tab
            TabButton(
                text = if (activeTier == PaywallTier.Pro) "Pro (Current)" else "Pro",
                isSelected = selectedTier == PaywallTier.Pro,
                onClick = { onTierSelected(PaywallTier.Pro) },
                modifier = Modifier.weight(1f)
            )
            
            Spacer(modifier = Modifier.width(4.dp))
            
            // Premium Tab
            TabButton(
                text = "Premium",
                isSelected = selectedTier == PaywallTier.Premium,
                onClick = { onTierSelected(PaywallTier.Premium) },
                modifier = Modifier.weight(1f)
            )
        }
    }
}

@Composable
private fun TabButton(
    text: String,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val backgroundColor by animateColorAsState(
        targetValue = if (isSelected) Pink else Color.Transparent,
        animationSpec = tween(300),
        label = "tabBackground"
    )
    
    val textColor by animateColorAsState(
        targetValue = if (isSelected) Color.White else Color.White.copy(alpha = 0.7f),
        animationSpec = tween(300),
        label = "tabText"
    )
    
    Surface(
        color = backgroundColor,
        shape = RoundedCornerShape(8.dp),
        modifier = modifier
            .clickable(onClick = onClick)
            .padding(vertical = 12.dp)
    ) {
        Text(
            text = text,
            color = textColor,
            fontSize = 16.sp,
            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp)
        )
    }
}

private fun calculateSavingsPercentage(packages: List<com.revenuecat.purchases.Package>): Int? {
    val weekly = packages.find { it.identifier.contains("weekly", ignoreCase = true) }
    val monthly = packages.find { it.identifier.contains("monthly", ignoreCase = true) }
    
    if (weekly == null || monthly == null) return null
    
    return try {
        val weeklyPrice = weekly.product.price.amountMicros / 1_000_000.0
        val monthlyPrice = monthly.product.price.amountMicros / 1_000_000.0
        
        // Calculate monthly equivalent of weekly (4.33 weeks per month)
        val weeklyMonthlyEquivalent = weeklyPrice * 4.33
        
        if (weeklyMonthlyEquivalent > monthlyPrice) {
            val savings = ((weeklyMonthlyEquivalent - monthlyPrice) / weeklyMonthlyEquivalent) * 100
            savings.toInt()
        } else {
            null
        }
    } catch (e: Exception) {
        null
    }
}

@Composable
private fun PackageCard(
    packageItem: com.revenuecat.purchases.Package,
    isSelected: Boolean,
    isDisabled: Boolean,
    savingsPercentage: Int?,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .graphicsLayer { alpha = if (isDisabled) 0.5f else 1f }
            .then(
                if (!isDisabled) Modifier.clickable(onClick = onClick) else Modifier
            )
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
                    
                    // Savings Badge for Monthly packages
                    if (savingsPercentage != null) {
                        Surface(
                            color = Pink,
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.padding(start = 8.dp)
                        ) {
                            Text(
                                "Save $savingsPercentage%",
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
