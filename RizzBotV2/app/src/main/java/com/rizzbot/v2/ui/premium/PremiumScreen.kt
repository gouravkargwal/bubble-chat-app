package com.rizzbot.v2.ui.premium

import android.app.Activity
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.width
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
import androidx.compose.ui.graphics.Brush
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
private val PremiumGold = Color(0xFFFFD700)
private val PremiumCardBg = Color(0xFF101018)

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
            // Persistent header
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                "Compare Plans",
                color = Color.White,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                "Choose the right wingman: Free, Pro, or God Mode.",
                color = Color.Gray,
                fontSize = 14.sp,
                textAlign = TextAlign.Center
            )

            if (state.purchaseResult is PurchaseResult.Success) {
                VoiceDNACalibrationModal(
                    onDismiss = {
                        viewModel.clearResult()
                        onBack()
                    },
                    onImagesSelected = { uris: List<Uri> ->
                        // TODO: send URIs to backend vision/generate endpoint with dummy direction
                        viewModel.clearResult()
                        onBack()
                    }
                )
            } else {
                val currentTier = state.currentTier.lowercase()

                if (currentTier == "premium" || currentTier == "god_mode") {
                    // Success screen for God Mode / Premium
                    Spacer(modifier = Modifier.height(32.dp))
                    Text("\u2728", fontSize = 64.sp)
                    Spacer(modifier = Modifier.height(24.dp))
                    Text(
                        "GOD MODE ACTIVE",
                        color = Color(0xFFFFD700),
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        "You\u2019re fully upgraded. Here\u2019s what you just unlocked:",
                        color = Color.Gray,
                        fontSize = 14.sp,
                        textAlign = TextAlign.Center
                    )

                    Spacer(modifier = Modifier.height(20.dp))

                    // Benefit list
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(CardBg, RoundedCornerShape(16.dp))
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        BenefitRow("Unlimited AI wingman replies")
                        BenefitRow("AI Voice Cloning that matches your texting style")
                        BenefitRow("Profile Roaster for deep-dive psychology reads")
                        BenefitRow("Semantic profile that learns your humor & slang")
                    }

                    Spacer(modifier = Modifier.height(24.dp))

                    Button(
                        onClick = onBack,
                        colors = ButtonDefaults.buttonColors(containerColor = AccentPink),
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(52.dp)
                    ) {
                        Text(
                            "Back to Home",
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 15.sp
                        )
                    }
                } else {
                    Spacer(modifier = Modifier.height(16.dp))

                    VisualHook()

                    Spacer(modifier = Modifier.height(20.dp))

                    // Weekly / Monthly toggle
                    BillingPeriodToggle(
                        isWeekly = state.isWeekly,
                        onToggle = { viewModel.toggleBillingPeriod(it) }
                    )

                    Spacer(modifier = Modifier.height(20.dp))

                    val isFreeTier = currentTier == "free"
                    val isProTier = currentTier == "pro"

                    if (isProTier) {
                        // Pro banner
                        Card(
                            colors = CardDefaults.cardColors(containerColor = CardBg),
                            shape = RoundedCornerShape(16.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier.padding(16.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    Icons.Default.WorkspacePremium,
                                    contentDescription = null,
                                    tint = Color(0xFF7C4DFF),
                                    modifier = Modifier.size(24.dp)
                                )
                                Spacer(modifier = Modifier.width(12.dp))
                                Column {
                                    Text(
                                        "You are currently on the Pro Plan.",
                                        color = Color.White,
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 14.sp
                                    )
                                    Text(
                                        "Unlock God Mode to max out your AI wingman.",
                                        color = Color.Gray,
                                        fontSize = 12.sp
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(16.dp))
                    }

                    // Pricing cards – Pro as default hero, God Mode as upsell
                    if (isFreeTier || isProTier) {
                        // Pro card (shown first as default choice)
                        val proProductDetails =
                            if (state.isWeekly) state.premiumWeekly else state.premiumMonthly
                        PricingCard(
                            title = "Pro",
                            productDetails = proProductDetails,
                            fallbackPrice = if (state.isWeekly) "$4.99" else "$14.99",
                            period = if (state.isWeekly) "wk" else "mo",
                            features = listOf(
                                "⚡ Floating Bubble (Works inside Tinder/Hinge)",
                                "Unlimited AI Replies",
                                "Unlock 'Ask Out' & 'Tease' directions",
                                "Basic Voice Match (Learns your emojis/punctuation)",
                                "Unlimited conversation memory"
                            ),
                            isPurchasing = state.isPurchasing,
                            onPurchase = {
                                proProductDetails?.let { product ->
                                    activity?.let { viewModel.purchase(it, product) }
                                }
                            },
                            badge = if (!state.isWeekly) "MOST POPULAR" else null
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        // God Mode card (secondary upsell)
                        val godModeProductDetails =
                            if (state.isWeekly) state.proWeekly else state.proMonthly
                        PricingCard(
                            title = "God Mode",
                            productDetails = godModeProductDetails,
                            fallbackPrice = if (state.isWeekly) "$8.99" else "$29.99",
                            period = if (state.isWeekly) "wk" else "mo",
                            features = listOf(
                                "Everything in Pro, PLUS:",
                                "AI Clones Your Texting Style (100% Undetectable)",
                                "Profile Roaster (Upload her pics for psychology reads)",
                                "God-Tier Flirting & Creativity (Gemini Pro Engine)"
                            ),
                            isPurchasing = state.isPurchasing,
                            onPurchase = {
                                godModeProductDetails?.let { product ->
                                    activity?.let { viewModel.purchase(it, product) }
                                }
                            },
                            badge = if (!state.isWeekly) "POWER USER" else null,
                            ctaLabel = if (isProTier) "Upgrade to God Mode" else "Go God Mode",
                            isPremiumTier = true
                        )
                    }

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
}

@Composable
private fun VisualHook() {
    Card(
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(20.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            ChatBubble(
                text = "I noticed your picture in Paris. Did you enjoy it?",
                isMe = false,
                bubbleColor = Color(0xFF2A2A3C),
                textColor = Color.White
            )
            ChatBubble(
                text = "Greetings! Yes, the architecture was splendid. 🤖🚩",
                isMe = true,
                bubbleColor = Color(0xFFB71C1C),
                textColor = Color.White
            )
            ChatBubble(
                text = "lmao not the eiffel tower pic... u actually speak french or just went for the croissants 🧑🔥",
                isMe = true,
                bubbleColor = Color(0xFF1B5E20),
                textColor = Color.White
            )
        }
    }
}

@Composable
private fun BenefitRow(text: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            Icons.Default.Check,
            contentDescription = null,
            tint = Color(0xFF4CAF50),
            modifier = Modifier.size(18.dp)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text,
            color = Color.White,
            fontSize = 14.sp
        )
    }
}

@Composable
private fun BillingPeriodToggle(
    isWeekly: Boolean,
    onToggle: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(999.dp))
            .background(Color(0xFF1F1F30)),
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        val weeklySelected = isWeekly
        val monthlySelected = !isWeekly

        fun segmentColor(selected: Boolean) =
            if (selected) AccentPink else Color.Transparent

        fun textColor(selected: Boolean) =
            if (selected) Color.White else Color.Gray

        Box(
            modifier = Modifier
                .weight(1f)
                .clip(RoundedCornerShape(999.dp))
                .background(segmentColor(weeklySelected))
                .clickable { if (!weeklySelected) onToggle(true) }
                .padding(vertical = 10.dp),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "Weekly",
                color = textColor(weeklySelected),
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold
            )
        }

        Box(
            modifier = Modifier
                .weight(1f)
                .clip(RoundedCornerShape(999.dp))
                .background(segmentColor(monthlySelected))
                .clickable { if (!monthlySelected) onToggle(false) }
                .padding(vertical = 10.dp),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "Monthly",
                color = textColor(monthlySelected),
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}

@Composable
private fun ChatBubble(
    text: String,
    isMe: Boolean,
    bubbleColor: Color,
    textColor: Color
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isMe) Arrangement.End else Arrangement.Start
    ) {
        Box(
            modifier = Modifier
                .background(
                    color = bubbleColor,
                    shape = RoundedCornerShape(18.dp)
                )
                .padding(horizontal = 12.dp, vertical = 8.dp)
        ) {
            Text(
                text = text,
                color = textColor,
                fontSize = 13.sp
            )
        }
    }
}

@Composable
private fun PricingCard(
    title: String,
    productDetails: ProductDetails?,
    fallbackPrice: String,
    period: String,
    features: List<String>,
    isPurchasing: Boolean,
    onPurchase: () -> Unit,
    badge: String? = null,
    ctaLabel: String? = null,
    isPremiumTier: Boolean = false
) {
    val price = productDetails?.subscriptionOfferDetails?.firstOrNull()
        ?.pricingPhases?.pricingPhaseList?.firstOrNull()
        ?.formattedPrice ?: fallbackPrice

    val border = if (isPremiumTier) {
        BorderStroke(1.5.dp, Color(0x80FFD700))
    } else {
        null
    }

    Card(
        modifier = Modifier
            .fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (isPremiumTier) PremiumCardBg else CardBg
        ),
        shape = RoundedCornerShape(16.dp),
        border = border
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    title,
                    color = if (isPremiumTier) PremiumGold else Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 20.sp
                )
                if (badge != null) {
                    Spacer(modifier = Modifier.width(8.dp))
                    Card(
                        colors = CardDefaults.cardColors(containerColor = AccentPink),
                        shape = RoundedCornerShape(4.dp)
                    ) {
                        Text(
                            badge,
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
                    containerColor = AccentPink,
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
                    if (productDetails == null) "Loading..." else (ctaLabel ?: "Subscribe"),
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
