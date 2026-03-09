package com.rizzbot.v2.ui.premium

import android.app.Activity
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.android.billingclient.api.ProductDetails
import com.rizzbot.v2.data.billing.PurchaseResult

private val AccentPink = Color(0xFFE91E63)
private val DarkBg = Color(0xFF0F0F1A)
private val CardBg = Color(0xFF1A1A2E)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PremiumScreen(
    onBack: () -> Unit,
    viewModel: PremiumViewModel = hiltViewModel()
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val activity = context as? Activity

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
                    containerColor = DarkBg,
                    titleContentColor = Color.White
                )
            )
        },
        containerColor = DarkBg
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            if (state.isPremium) {
                Spacer(modifier = Modifier.height(48.dp))
                Text("\u2728", fontSize = 64.sp)
                Spacer(modifier = Modifier.height(24.dp))
                Text(
                    "You're Premium!",
                    color = Color.White,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center
                )
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    "Enjoy unlimited replies and all premium features.",
                    color = Color.Gray,
                    fontSize = 14.sp,
                    textAlign = TextAlign.Center
                )
            } else if (state.purchaseResult is PurchaseResult.Success) {
                Spacer(modifier = Modifier.height(48.dp))
                Text("\uD83C\uDF89", fontSize = 64.sp)
                Spacer(modifier = Modifier.height(24.dp))
                Text(
                    "Welcome to Premium!",
                    color = Color.White,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center
                )
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    "Your subscription is now active. Enjoy unlimited replies!",
                    color = Color.Gray,
                    fontSize = 14.sp,
                    textAlign = TextAlign.Center
                )
                Spacer(modifier = Modifier.height(24.dp))
                Button(
                    onClick = {
                        viewModel.clearResult()
                        onBack()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = AccentPink),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Start Using Cookd", fontWeight = FontWeight.Bold)
                }
            } else {
                // Header
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    "Unlock Unlimited Replies",
                    color = Color.White,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    "Never run out of replies again",
                    color = Color.Gray,
                    fontSize = 14.sp,
                    textAlign = TextAlign.Center
                )

                Spacer(modifier = Modifier.height(20.dp))

                // Weekly / Monthly toggle
                BillingPeriodToggle(
                    isWeekly = state.isWeekly,
                    onToggle = { viewModel.toggleBillingPeriod(it) }
                )

                Spacer(modifier = Modifier.height(20.dp))

                // Premium tier
                val premiumProduct = if (state.isWeekly) state.premiumWeekly else state.premiumMonthly
                PricingCard(
                    title = "Premium",
                    productDetails = premiumProduct,
                    fallbackPrice = if (state.isWeekly) "$1.99" else "$4.99",
                    period = if (state.isWeekly) "wk" else "mo",
                    isRecommended = true,
                    savings = if (!state.isWeekly) "Save 40% vs weekly" else null,
                    features = listOf(
                        "50 replies/day (vs 5 free)",
                        "All 6 reply directions",
                        "Custom hints for replies",
                        "Up to 3 screenshots per request",
                        "Conversation memory (10 people)",
                        "Better AI prompt quality"
                    ),
                    isPurchasing = state.isPurchasing,
                    onPurchase = {
                        premiumProduct?.let { product ->
                            activity?.let { viewModel.purchase(it, product) }
                        }
                    }
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Pro tier
                val proProduct = if (state.isWeekly) state.proWeekly else state.proMonthly
                PricingCard(
                    title = "Pro",
                    productDetails = proProduct,
                    fallbackPrice = if (state.isWeekly) "$2.99" else "$9.99",
                    period = if (state.isWeekly) "wk" else "mo",
                    isRecommended = false,
                    savings = if (!state.isWeekly) "Save 25% vs weekly" else null,
                    features = listOf(
                        "Everything in Premium",
                        "Unlimited replies",
                        "Up to 5 screenshots per request",
                        "Voice DNA \u2014 AI learns your style",
                        "Unlimited conversation memory",
                        "Longest, highest-quality replies"
                    ),
                    isPurchasing = state.isPurchasing,
                    onPurchase = {
                        proProduct?.let { product ->
                            activity?.let { viewModel.purchase(it, product) }
                        }
                    }
                )

                // Error message
                if (state.purchaseResult is PurchaseResult.Error) {
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        (state.purchaseResult as PurchaseResult.Error).message,
                        color = Color(0xFFEF5350),
                        fontSize = 12.sp,
                        textAlign = TextAlign.Center
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                TextButton(onClick = { viewModel.restorePurchases() }) {
                    Text("Restore purchases", color = Color.Gray, fontSize = 13.sp)
                }

                Spacer(modifier = Modifier.height(4.dp))

                TextButton(onClick = onBack) {
                    Text("Continue with free plan", color = AccentPink, fontSize = 13.sp)
                }

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    "Auto-renews. Cancel anytime in Play Store.",
                    color = Color.Gray.copy(alpha = 0.6f),
                    fontSize = 11.sp,
                    textAlign = TextAlign.Center
                )

                Spacer(modifier = Modifier.height(24.dp))
            }
        }
    }
}

@Composable
private fun BillingPeriodToggle(
    isWeekly: Boolean,
    onToggle: (Boolean) -> Unit
) {
    val shape = RoundedCornerShape(12.dp)
    Row(
        modifier = Modifier
            .clip(shape)
            .background(CardBg)
            .border(1.dp, Color.White.copy(alpha = 0.08f), shape)
            .padding(4.dp)
    ) {
        PeriodTab(
            label = "Weekly",
            selected = isWeekly,
            onClick = { onToggle(true) },
            modifier = Modifier.weight(1f)
        )
        PeriodTab(
            label = "Monthly",
            badge = "BEST VALUE",
            selected = !isWeekly,
            onClick = { onToggle(false) },
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun PeriodTab(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    badge: String? = null
) {
    val bg = if (selected) AccentPink else Color.Transparent
    val textColor = if (selected) Color.White else Color.Gray

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(10.dp))
            .background(bg)
            .clickable { onClick() }
            .padding(vertical = 10.dp),
        contentAlignment = Alignment.Center
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(label, color = textColor, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            if (badge != null && selected) {
                Spacer(modifier = Modifier.width(6.dp))
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.2f)),
                    shape = RoundedCornerShape(4.dp)
                ) {
                    Text(
                        badge,
                        color = Color.White,
                        fontSize = 8.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun PricingCard(
    title: String,
    productDetails: ProductDetails?,
    fallbackPrice: String,
    period: String,
    isRecommended: Boolean,
    savings: String?,
    features: List<String>,
    isPurchasing: Boolean,
    onPurchase: () -> Unit
) {
    val price = productDetails?.subscriptionOfferDetails?.firstOrNull()
        ?.pricingPhases?.pricingPhaseList?.firstOrNull()
        ?.formattedPrice ?: fallbackPrice

    val borderModifier = if (isRecommended) {
        Modifier.border(2.dp, AccentPink, RoundedCornerShape(16.dp))
    } else {
        Modifier
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .then(borderModifier),
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(title, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                if (isRecommended) {
                    Spacer(modifier = Modifier.width(8.dp))
                    Card(
                        colors = CardDefaults.cardColors(containerColor = AccentPink),
                        shape = RoundedCornerShape(4.dp)
                    ) {
                        Text(
                            "POPULAR",
                            color = Color.White,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                        )
                    }
                }
            }

            Row(verticalAlignment = Alignment.Bottom) {
                Text(price, color = AccentPink, fontWeight = FontWeight.Bold, fontSize = 28.sp)
                Text("/$period", color = AccentPink.copy(alpha = 0.7f), fontSize = 14.sp,
                    modifier = Modifier.padding(bottom = 4.dp))
            }

            savings?.let {
                Text(it, color = Color(0xFF4CAF50), fontSize = 12.sp, fontWeight = FontWeight.Medium)
            }

            Spacer(modifier = Modifier.height(12.dp))

            features.forEach { feature ->
                Row(
                    modifier = Modifier.padding(vertical = 3.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        Icons.Default.Check,
                        contentDescription = null,
                        tint = Color(0xFF4CAF50),
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(feature, color = Color.White, fontSize = 14.sp)
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = onPurchase,
                enabled = productDetails != null && !isPurchasing,
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isRecommended) AccentPink else Color(0xFF252542),
                    disabledContainerColor = Color(0xFF252542).copy(alpha = 0.5f)
                ),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                if (isPurchasing) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        color = Color.White,
                        strokeWidth = 2.dp
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                }
                Text(
                    if (productDetails == null) "Loading..." else "Subscribe",
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
