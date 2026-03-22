package com.rizzbot.v2.ui.paywall

import android.app.Activity
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel

private val DarkBgTop = Color(0xFF12101C)
private val DarkBgBottom = Color(0xFF0A0912)
private val CardBg = Color(0xFF1C1A28)
private val CardBorder = Color.White.copy(alpha = 0.08f)
private val MutedText = Color(0xFFB4B0C0)
/** Footer / secondary actions */
private val FooterLinkColor = Color(0xFFC8C4D4)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PaywallScreen(
    onDismiss: () -> Unit,
    onPurchaseSuccess: () -> Unit,
    onOpenTerms: () -> Unit = {},
    onOpenPrivacy: () -> Unit = {},
    viewModel: PaywallViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val usage by viewModel.usageState.collectAsState()
    val context = LocalContext.current
    val activity = context as? Activity
    val scrollState = rememberScrollState()
    val accent = MaterialTheme.colorScheme.primary

    var showSuccessIcon by remember { mutableStateOf(false) }
    LaunchedEffect(state.purchaseSuccess) {
        showSuccessIcon = state.purchaseSuccess
    }
    LaunchedEffect(state.readyToNavigate) {
        if (state.readyToNavigate) onPurchaseSuccess()
    }

    val headline = remember(usage.tier) {
        PaywallTierMarketing.headlineForAppTier(usage.tier)
    }
    val subline = remember(usage.tier) {
        PaywallTierMarketing.sublineForAppTier(usage.tier)
    }

    Scaffold(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(DarkBgTop, DarkBgBottom)
                )
            ),
        containerColor = Color.Transparent,
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = if (state.purchaseSuccess) "You're in" else headline,
                        color = Color.White,
                        fontSize = 17.sp,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                },
                actions = {
                    IconButton(onClick = onDismiss) {
                        Icon(
                            Icons.Default.Close,
                            contentDescription = "Close",
                            tint = Color.White.copy(alpha = 0.9f)
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color.Transparent,
                    titleContentColor = Color.White,
                    actionIconContentColor = Color.White
                ),
            )
        },
        bottomBar = {
            Surface(
                color = DarkBgBottom.copy(alpha = 0.97f),
                tonalElevation = 6.dp,
                shadowElevation = 12.dp,
            ) {
                Column(
                    Modifier
                        .navigationBarsPadding()
                        .padding(horizontal = 16.dp, vertical = 10.dp)
                ) {
                    HorizontalDivider(
                        color = CardBorder,
                        thickness = 1.dp,
                        modifier = Modifier.padding(bottom = 10.dp)
                    )
                    if (state.purchaseSuccess) {
                        Button(
                            onClick = { viewModel.refreshUserTierFromBackend() },
                            enabled = !state.isRefreshingAfterPurchase,
                            colors = ButtonDefaults.buttonColors(containerColor = accent),
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(min = 46.dp),
                            shape = RoundedCornerShape(12.dp),
                            contentPadding = PaddingValues(vertical = 10.dp)
                        ) {
                            if (state.isRefreshingAfterPurchase) {
                                CircularProgressIndicator(
                                    color = Color.White,
                                    modifier = Modifier.size(22.dp),
                                    strokeWidth = 2.dp
                                )
                            } else {
                                Text(
                                    "Continue",
                                    color = Color.White,
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }
                        PaywallPolicyLinks(onOpenTerms = onOpenTerms, onOpenPrivacy = onOpenPrivacy)
                    } else {
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
                                    containerColor = accent,
                                    disabledContainerColor = CardBg.copy(alpha = 0.6f)
                                ),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .heightIn(min = 46.dp),
                                shape = RoundedCornerShape(12.dp),
                                enabled = !isCurrentTier,
                                contentPadding = PaddingValues(vertical = 10.dp)
                            ) {
                                val buttonText = when {
                                    isCurrentTier -> "Current plan"
                                    isUpgradeToPremium -> "Upgrade to Premium"
                                    else -> "Subscribe"
                                }
                                Text(
                                    buttonText,
                                    color = if (isCurrentTier) Color.White.copy(alpha = 0.45f) else Color.White,
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }
                        TextButton(
                            onClick = onDismiss,
                            modifier = Modifier.fillMaxWidth(),
                            contentPadding = PaddingValues(vertical = 4.dp)
                        ) {
                            Text(
                                "Not now",
                                color = MutedText,
                                fontSize = 13.sp
                            )
                        }
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.Center,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            TextButton(
                                onClick = { viewModel.restorePurchases(onPurchaseSuccess) },
                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
                            ) {
                                Text("Restore", color = FooterLinkColor, fontSize = 12.sp)
                            }
                            Text("·", color = FooterLinkColor.copy(alpha = 0.4f), fontSize = 12.sp)
                            TextButton(
                                onClick = onOpenTerms,
                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
                            ) {
                                Text("Terms", color = FooterLinkColor, fontSize = 12.sp)
                            }
                            Text("·", color = FooterLinkColor.copy(alpha = 0.4f), fontSize = 12.sp)
                            TextButton(
                                onClick = onOpenPrivacy,
                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
                            ) {
                                Text("Privacy", color = FooterLinkColor, fontSize = 12.sp)
                            }
                        }
                    }
                }
            }
        }
    ) { innerPadding ->
        AnimatedContent(
            targetState = state.purchaseSuccess,
            transitionSpec = {
                fadeIn(tween(280)) togetherWith fadeOut(tween(280))
            },
            label = "paywallSuccessContent",
            modifier = Modifier.padding(innerPadding)
        ) { isSuccess ->
            if (isSuccess) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState())
                        .padding(horizontal = 16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Spacer(modifier = Modifier.height(8.dp))
                    AnimatedVisibility(
                        visible = showSuccessIcon,
                        enter = fadeIn(tween(320)) +
                            scaleIn(
                                initialScale = 0.75f,
                                animationSpec = tween(320, easing = FastOutSlowInEasing)
                            ),
                        exit = fadeOut(tween(180))
                    ) {
                        Surface(
                            color = accent.copy(alpha = 0.12f),
                            shape = RoundedCornerShape(999.dp),
                            modifier = Modifier.size(72.dp)
                        ) {
                            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                Icon(
                                    imageVector = Icons.Default.Check,
                                    contentDescription = "Unlocked",
                                    tint = accent,
                                    modifier = Modifier.size(36.dp)
                                )
                            }
                        }
                    }
                    Spacer(modifier = Modifier.height(14.dp))
                    Text(
                        "Cookd is unlocked",
                        color = Color.White,
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "Your subscription is active. Limits match your plan in Settings.",
                        color = MutedText,
                        fontSize = 14.sp,
                        textAlign = TextAlign.Center,
                        lineHeight = 20.sp,
                        modifier = Modifier.padding(horizontal = 8.dp)
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                }
            } else {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(scrollState)
                        .padding(horizontal = 16.dp)
                ) {
                    Spacer(modifier = Modifier.height(4.dp))

                    CurrentPlanChip(tier = usage.tier)

                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        text = subline,
                        color = MutedText,
                        fontSize = 14.sp,
                        lineHeight = 20.sp,
                        textAlign = TextAlign.Start,
                        modifier = Modifier.fillMaxWidth()
                    )

                    Spacer(modifier = Modifier.height(20.dp))

                    Text(
                        "Choose plan",
                        color = Color.White.copy(alpha = 0.5f),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        letterSpacing = 0.6.sp
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    when (val uiState = state.uiState) {
                        is PaywallUiState.Success -> {
                            TierTabs(
                                selectedTier = state.selectedTier,
                                activeTier = state.activeTier,
                                onTierSelected = { viewModel.selectTier(it) }
                            )
                            Spacer(modifier = Modifier.height(14.dp))

                            Surface(
                                shape = RoundedCornerShape(14.dp),
                                color = CardBg.copy(alpha = 0.65f),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .border(1.dp, CardBorder, RoundedCornerShape(14.dp))
                            ) {
                                Column(
                                    modifier = Modifier.padding(14.dp),
                                    verticalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    AnimatedContent(
                                        targetState = state.selectedTier,
                                        transitionSpec = {
                                            fadeIn(tween(220)) togetherWith fadeOut(tween(220))
                                        },
                                        label = "features"
                                    ) { tier ->
                                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                            PaywallTierMarketing.featureLines(tier).forEach { line ->
                                                FeatureRow(text = line, accent = accent)
                                            }
                                        }
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(16.dp))

                            Text(
                                "Billing",
                                color = Color.White.copy(alpha = 0.5f),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.SemiBold,
                                letterSpacing = 0.6.sp
                            )
                            Spacer(modifier = Modifier.height(8.dp))

                            AnimatedContent(
                                targetState = state.selectedTier,
                                transitionSpec = {
                                    fadeIn(tween(240)) togetherWith fadeOut(tween(240))
                                },
                                label = "packages"
                            ) { tier ->
                                val packages = when (tier) {
                                    PaywallTier.Pro -> state.proPackages
                                    PaywallTier.Premium -> state.premiumPackages
                                }
                                Column(
                                    verticalArrangement = Arrangement.spacedBy(10.dp),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    val isCurrentTier = state.activeTier == tier
                                    packages.forEach { packageItem ->
                                        val isMonthly =
                                            packageItem.identifier.contains("monthly", ignoreCase = true)
                                        val savingsPercentage =
                                            if (isMonthly && packages.size >= 2) {
                                                calculateSavingsPercentage(packages)
                                            } else null
                                        PackageCard(
                                            packageItem = packageItem,
                                            isSelected = state.selectedPackage?.identifier == packageItem.identifier,
                                            isDisabled = isCurrentTier,
                                            savingsPercentage = savingsPercentage,
                                            accent = accent,
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
                                    .height(160.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                CircularProgressIndicator(color = accent, strokeWidth = 2.dp)
                            }
                        }

                        is PaywallUiState.Error -> {
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = CardDefaults.cardColors(containerColor = CardBg),
                                    shape = RoundedCornerShape(14.dp)
                                ) {
                                    Text(
                                        uiState.message,
                                        color = Color.White,
                                        modifier = Modifier
                                            .padding(14.dp)
                                            .fillMaxWidth(),
                                        textAlign = TextAlign.Center,
                                        fontSize = 14.sp
                                    )
                                }
                                Spacer(modifier = Modifier.height(12.dp))
                                OutlinedButton(
                                    onClick = { viewModel.retryLoadOfferings() },
                                    shape = RoundedCornerShape(12.dp)
                                ) {
                                    Text("Try again", color = accent, fontSize = 14.sp)
                                }
                            }
                        }
                    }

                    val errorMessage = state.purchaseError
                    if (errorMessage != null) {
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            errorMessage,
                            color = Color(0xFFFF8A80),
                            fontSize = 13.sp,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }

                    if (state.uiState is PaywallUiState.Success && state.selectedPackage == null) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            "Pick a billing period to continue.",
                            color = MutedText,
                            fontSize = 13.sp,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }

                    Spacer(modifier = Modifier.height(16.dp))
                }
            }
        }
    }
}

@Composable
private fun CurrentPlanChip(tier: String) {
    val (label, container, border) = when (tier) {
        "premium", "god_mode" -> Triple(
            "Your plan: Premium",
            Color(0xFF2A2418),
            Color(0xFFFFD700).copy(alpha = 0.35f)
        )
        "pro" -> Triple(
            "Your plan: Pro",
            Color(0xFF22182A),
            Color(0xFFB388FF).copy(alpha = 0.35f)
        )
        else -> Triple(
            "Your plan: Free",
            CardBg.copy(alpha = 0.8f),
            CardBorder
        )
    }
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(container)
            .border(1.dp, border, RoundedCornerShape(999.dp))
            .padding(horizontal = 12.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            label,
            color = Color.White.copy(alpha = 0.92f),
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium
        )
    }
}

@Composable
private fun PaywallPolicyLinks(
    onOpenTerms: () -> Unit,
    onOpenPrivacy: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 8.dp),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically
    ) {
        TextButton(onClick = onOpenTerms, contentPadding = PaddingValues(4.dp)) {
            Text("Terms", color = FooterLinkColor, fontSize = 12.sp)
        }
        Text("·", color = FooterLinkColor.copy(alpha = 0.4f), fontSize = 12.sp)
        TextButton(onClick = onOpenPrivacy, contentPadding = PaddingValues(4.dp)) {
            Text("Privacy", color = FooterLinkColor, fontSize = 12.sp)
        }
    }
}

@Composable
private fun FeatureRow(text: String, accent: Color) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top
    ) {
        Icon(
            Icons.Default.Check,
            contentDescription = null,
            tint = accent,
            modifier = Modifier.size(18.dp)
        )
        Spacer(modifier = Modifier.width(10.dp))
        Text(
            text,
            color = Color.White.copy(alpha = 0.92f),
            fontSize = 13.sp,
            lineHeight = 18.sp,
            fontWeight = FontWeight.Normal
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
        color = Color.Black.copy(alpha = 0.25f),
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, CardBorder, RoundedCornerShape(12.dp))
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(4.dp)
                .selectableGroup()
        ) {
            TabButton(
                text = if (activeTier == PaywallTier.Pro) "Pro · current" else "Pro",
                isSelected = selectedTier == PaywallTier.Pro,
                onClick = { onTierSelected(PaywallTier.Pro) },
                modifier = Modifier.weight(1f)
            )
            Spacer(modifier = Modifier.width(4.dp))
            TabButton(
                text = if (activeTier == PaywallTier.Premium) "Premium · current" else "Premium",
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
    val accent = MaterialTheme.colorScheme.primary
    val backgroundColor by animateColorAsState(
        targetValue = if (isSelected) accent else Color.Transparent,
        animationSpec = tween(240),
        label = "tabBg"
    )
    val textColor by animateColorAsState(
        targetValue = if (isSelected) Color.White else MutedText,
        animationSpec = tween(240),
        label = "tabText"
    )
    Surface(
        color = backgroundColor,
        shape = RoundedCornerShape(8.dp),
        modifier = modifier
            .semantics { selected = isSelected }
            .clickable(onClick = onClick, role = Role.Tab)
            .padding(vertical = 2.dp)
    ) {
        Text(
            text = text,
            color = textColor,
            fontSize = 13.sp,
            fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Medium,
            textAlign = TextAlign.Center,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 10.dp, horizontal = 4.dp)
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
        val weeklyMonthlyEquivalent = weeklyPrice * 4.33
        if (weeklyMonthlyEquivalent > monthlyPrice) {
            (((weeklyMonthlyEquivalent - monthlyPrice) / weeklyMonthlyEquivalent) * 100).toInt()
        } else {
            null
        }
    } catch (_: Exception) {
        null
    }
}

@Composable
private fun PackageCard(
    packageItem: com.revenuecat.purchases.Package,
    isSelected: Boolean,
    isDisabled: Boolean,
    savingsPercentage: Int?,
    accent: Color,
    onClick: () -> Unit
) {
    val title = when (packageItem.identifier) {
        "Weekly" -> "Pro · Weekly"
        "Monthly" -> "Pro · Monthly"
        "premium_weekly" -> "Premium · Weekly"
        "premium_monthly" -> "Premium · Monthly"
        else -> packageItem.product.title
    }
    val periodText = when {
        packageItem.identifier.contains("weekly", ignoreCase = true) -> "Billed weekly"
        packageItem.identifier.contains("monthly", ignoreCase = true) -> "Billed monthly"
        else -> packageItem.product.description
    }
    val priceText = try {
        packageItem.product.price.formatted
    } catch (_: Exception) {
        try {
            packageItem.product.title
        } catch (_: Exception) {
            packageItem.identifier
        }
    }

    val borderColor = when {
        isSelected -> accent
        else -> CardBorder
    }
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .semantics(mergeDescendants = true) { selected = isSelected }
            .graphicsLayer { alpha = if (isDisabled) 0.48f else 1f }
            .then(if (!isDisabled) Modifier.clickable(onClick = onClick) else Modifier)
            .border(
                width = if (isSelected) 2.dp else 1.dp,
                color = borderColor,
                shape = RoundedCornerShape(14.dp)
            ),
        colors = CardDefaults.cardColors(
            containerColor = if (isSelected) accent.copy(alpha = 0.1f) else CardBg
        ),
        shape = RoundedCornerShape(14.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    title,
                    color = Color.White,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    periodText,
                    color = MutedText,
                    fontSize = 12.sp,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
            }
            Spacer(modifier = Modifier.width(10.dp))
            Column(horizontalAlignment = Alignment.End) {
                if (savingsPercentage != null) {
                    Surface(
                        color = accent.copy(alpha = 0.9f),
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        Text(
                            "−$savingsPercentage%",
                            color = Color.White,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp)
                        )
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                }
                Text(
                    priceText,
                    color = accent,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
