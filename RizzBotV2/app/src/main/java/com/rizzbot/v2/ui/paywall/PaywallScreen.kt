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
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
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
import com.rizzbot.v2.ui.theme.NeonRed
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite

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
    val accent = NothingWhite

    var showSuccessIcon by remember { mutableStateOf(false) }
    LaunchedEffect(state.purchaseSuccess) { showSuccessIcon = state.purchaseSuccess }
    LaunchedEffect(state.readyToNavigate) { if (state.readyToNavigate) onPurchaseSuccess() }

    val headline = remember(usage.tier) { PaywallTierMarketing.headlineForAppTier(usage.tier) }

    Scaffold(
        modifier = Modifier.fillMaxSize().background(NothingBlack),
        containerColor = NothingBlack,
        topBar = {
            TopAppBar(
                title = { Text(if (state.purchaseSuccess) "You're in" else headline, color = NothingWhite, style = MaterialTheme.typography.titleMedium, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                actions = { IconButton(onClick = onDismiss) { Icon(Icons.Default.Close, contentDescription = "Close", tint = NothingWhite) } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = NothingBlack, titleContentColor = NothingWhite)
            )
        },
        bottomBar = {
            Surface(color = NothingBlack) {
                Column(Modifier.navigationBarsPadding().padding(horizontal = NothingDimens.screenPadding, vertical = 10.dp)) {
                    if (state.purchaseSuccess) {
                        Button(
                            onClick = { viewModel.refreshUserTierFromBackend() },
                            enabled = !state.isRefreshingAfterPurchase,
                            colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
                            modifier = Modifier.fillMaxWidth().heightIn(min = 46.dp),
                            shape = RoundedCornerShape(NothingDimens.pillRadius)
                        ) {
                            if (state.isRefreshingAfterPurchase) CircularProgressIndicator(color = NothingBlack, modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                            else Text("Continue", color = NothingBlack, fontWeight = FontWeight.SemiBold)
                        }
                    } else {
                        val selectedPackage = state.selectedPackage
                        if (selectedPackage != null && activity != null) {
                            val isCurrentTier = state.activeTier == state.selectedTier
                            Button(
                                onClick = { viewModel.purchasePackage(activity, selectedPackage, onPurchaseSuccess) },
                                colors = ButtonDefaults.buttonColors(containerColor = NothingWhite, disabledContainerColor = NothingSurface),
                                modifier = Modifier.fillMaxWidth().heightIn(min = 46.dp),
                                shape = RoundedCornerShape(NothingDimens.pillRadius),
                                enabled = !isCurrentTier && !state.isPurchasing
                            ) {
                                if (state.isPurchasing) CircularProgressIndicator(color = NothingBlack, modifier = Modifier.size(22.dp), strokeWidth = 2.dp)
                                else Text(if (isCurrentTier) "Current plan" else "Subscribe", color = NothingBlack, fontWeight = FontWeight.SemiBold)
                            }
                        }
                        TextButton(onClick = onDismiss, modifier = Modifier.fillMaxWidth()) { Text("Not now", color = NothingTextSecondary) }
                    }
                }
            }
        }
    ) { innerPadding ->
        AnimatedContent(targetState = state.purchaseSuccess, transitionSpec = { fadeIn(tween(280)) togetherWith fadeOut(tween(280)) }, label = "paywallContent", modifier = Modifier.padding(innerPadding)) { isSuccess ->
            if (isSuccess) {
                Column(modifier = Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = NothingDimens.screenPadding), horizontalAlignment = Alignment.CenterHorizontally) {
                    Spacer(modifier = Modifier.height(NothingDimens.elementGap))
                    Box(modifier = Modifier.size(72.dp).clip(RoundedCornerShape(NothingDimens.pillRadius)).background(NothingBorder), contentAlignment = Alignment.Center) {
                        Icon(Icons.Default.Check, contentDescription = "Unlocked", tint = NothingWhite, modifier = Modifier.size(36.dp))
                    }
                    Spacer(modifier = Modifier.height(NothingDimens.elementGap))
                    Text("Cookd is unlocked", color = NothingWhite, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
                    Spacer(modifier = Modifier.height(NothingDimens.textGap))
                    Text("Your subscription is active.", color = NothingTextSecondary, style = MaterialTheme.typography.bodyMedium, textAlign = TextAlign.Center)
                }
            } else {
                Column(modifier = Modifier.fillMaxWidth().verticalScroll(scrollState).padding(horizontal = NothingDimens.screenPadding)) {
                    Spacer(modifier = Modifier.height(NothingDimens.textGap))

                    when (val uiState = state.uiState) {
                        is PaywallUiState.Success -> {
                            Text("Choose plan", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
                            TierTabs(selectedTier = state.selectedTier, activeTier = state.activeTier, onTierSelected = { viewModel.selectTier(it) })
                            Spacer(modifier = Modifier.height(NothingDimens.elementGap))

                            Card(
                                colors = CardDefaults.cardColors(containerColor = NothingSurface),
                                shape = RoundedCornerShape(NothingDimens.cardRadius),
                                border = BorderStroke(NothingDimens.borderThickness, NothingBorder),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Column(modifier = Modifier.padding(NothingDimens.cardPadding), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    AnimatedContent(targetState = state.selectedTier, transitionSpec = { fadeIn(tween(220)) togetherWith fadeOut(tween(220)) }, label = "features") { tier ->
                                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                            PaywallTierMarketing.featureLines(tier).forEach { line ->
                                                Row(verticalAlignment = Alignment.Top) {
                                                    Icon(Icons.Default.Check, contentDescription = null, tint = NothingWhite, modifier = Modifier.size(18.dp))
                                                    Spacer(modifier = Modifier.width(NothingDimens.elementGap))
                                                    Text(line, color = NothingWhite, style = MaterialTheme.typography.bodySmall)
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
                            Text("Billing", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(NothingDimens.textGap))

                            AnimatedContent(targetState = state.selectedTier, transitionSpec = { fadeIn(tween(240)) togetherWith fadeOut(tween(240)) }, label = "packages") { tier ->
                                val packages = when (tier) { PaywallTier.Crush -> state.crushPackages; PaywallTier.Match -> state.matchPackages; PaywallTier.Rizz -> state.rizzPackages }
                                Column(verticalArrangement = Arrangement.spacedBy(NothingDimens.elementGap), modifier = Modifier.fillMaxWidth()) {
                                    packages.forEach { packageItem ->
                                        PackageCard(packageItem = packageItem, isSelected = state.selectedPackage?.identifier == packageItem.identifier, isDisabled = state.activeTier == tier, onClick = { viewModel.selectPackage(packageItem) })
                                    }
                                }
                            }
                        }
                        is PaywallUiState.Loading -> Box(modifier = Modifier.fillMaxWidth().height(160.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator(color = NothingWhite, strokeWidth = 2.dp) }
                        is PaywallUiState.Error -> {
                            Card(colors = CardDefaults.cardColors(containerColor = NothingSurface), shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder)) {
                                Text(uiState.message, color = NothingWhite, modifier = Modifier.padding(NothingDimens.cardPadding).fillMaxWidth(), textAlign = TextAlign.Center, style = MaterialTheme.typography.bodyMedium)
                            }
                            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
                            OutlinedButton(onClick = { viewModel.retryLoadOfferings() }, shape = RoundedCornerShape(NothingDimens.pillRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder)) { Text("Try again", color = NothingTextSecondary) }
                        }
                    }
                    Spacer(modifier = Modifier.height(NothingDimens.elementGap))
                }
            }
        }
    }
}

@Composable
private fun TierTabs(selectedTier: PaywallTier, activeTier: PaywallTier?, onTierSelected: (PaywallTier) -> Unit) {
    Surface(color = NothingSurface, shape = RoundedCornerShape(NothingDimens.cardRadius), border = BorderStroke(NothingDimens.borderThickness, NothingBorder), modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.fillMaxWidth().padding(4.dp).selectableGroup()) {
            PaywallTier.entries.forEach { tier ->
                val isSelected = selectedTier == tier
                val backgroundColor by animateColorAsState(targetValue = if (isSelected) NothingWhite else Color.Transparent, animationSpec = tween(240), label = "tabBg")
                val textColor by animateColorAsState(targetValue = if (isSelected) NothingBlack else NothingTextSecondary, animationSpec = tween(240), label = "tabText")
                Surface(color = backgroundColor, shape = RoundedCornerShape(8.dp), modifier = Modifier.weight(1f).semantics { selected = isSelected }.clickable(onClick = { onTierSelected(tier) }, role = Role.Tab).padding(vertical = 2.dp)) {
                    Text(if (activeTier == tier) "${tier.name} \u00b7 current" else tier.name, color = textColor, style = MaterialTheme.typography.labelSmall, fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Medium, textAlign = TextAlign.Center, maxLines = 1, modifier = Modifier.fillMaxWidth().padding(vertical = 10.dp, horizontal = 4.dp))
                }
            }
        }
    }
}

@Composable
private fun PackageCard(packageItem: com.revenuecat.purchases.Package, isSelected: Boolean, isDisabled: Boolean, onClick: () -> Unit) {
    val title = when (packageItem.identifier) { "Weekly" -> "Weekly"; "Monthly" -> "Monthly"; "premium_weekly" -> "Premium Weekly"; "premium_monthly" -> "Premium Monthly"; else -> packageItem.product.title }
    val periodText = when { packageItem.identifier.contains("weekly", ignoreCase = true) -> "Billed weekly"; packageItem.identifier.contains("monthly", ignoreCase = true) -> "Billed monthly"; else -> packageItem.product.description }
    val priceText = try { packageItem.product.price.formatted } catch (_: Exception) { try { packageItem.product.title } catch (_: Exception) { packageItem.identifier } }

    Card(
        modifier = Modifier.fillMaxWidth().semantics(mergeDescendants = true) { selected = isSelected }.graphicsLayer { alpha = if (isDisabled) 0.48f else 1f }.then(if (!isDisabled) Modifier.clickable(onClick = onClick) else Modifier),
        colors = CardDefaults.cardColors(containerColor = NothingSurface),
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        border = BorderStroke(if (isSelected) 2.dp else NothingDimens.borderThickness, if (isSelected) NothingWhite else NothingBorder)
    ) {
        Row(modifier = Modifier.fillMaxWidth().padding(NothingDimens.cardPadding), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
            Column(modifier = Modifier.weight(1f)) {
                Text(title, color = NothingWhite, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Spacer(modifier = Modifier.height(2.dp))
                Text(periodText, color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
            }
            Spacer(modifier = Modifier.width(NothingDimens.elementGap))
            Text(priceText, color = NothingWhite, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        }
    }
}
