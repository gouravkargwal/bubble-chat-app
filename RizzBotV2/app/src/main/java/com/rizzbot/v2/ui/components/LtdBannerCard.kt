package com.rizzbot.v2.ui.components

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Whatshot
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.ui.theme.NeonRed
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingError
import com.rizzbot.v2.ui.theme.NothingSuccess
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite

/**
 * LTD offer configuration — fetched from `GET /api/v1/billing/ltd/banner-config`.
 * Server-controlled: update [LTD_CONFIG] in the backend, all banners update instantly.
 */
data class LtdBannerConfig(
    val enabled: Boolean = true,
    val price: Int = 999,
    val currency: String = "₹",
    val compareAt: Int = 4799,
    val sticky: String = "Pays for itself in 4 months",
    val badge: String = "LIMITED OFFER",
    val badgeIcon: String = "🔥",
    val title: String = "Lifetime Access",
    val spotsRemaining: Int = 658,
    val totalSpots: Int = 1000,
    val scarcityLabel: String = "licenses claimed",
    val directions: Int = 9,
    val noExpiry: Boolean = true,
    val benefitDirectionsLabel: String = "directions",
    val benefitNoExpiryLabel: String = "no expiry",
    val benefitNoExpiryValue: String = "∞",
    val ctaText: String = "Claim Your Lifetime License",
    val redeemTitle: String = "Already have a code?",
    val redeemPlaceholder: String = "LTD-XXXXXXXX",
    val redeemCtaText: String = "Redeem",
    val landingUrl: String = "https://cookd.app/#pricing",
    val hideIfLtdActive: Boolean = true,
)

/**
 * Reusable LTD offer card with neon red urgency styling.
 *
 * Used in Settings, Paywall, Home, and credit-exhausted modals.
 * All copy comes from [config] — server-controlled via GET /banner-config.
 */
@Composable
fun LtdBannerCard(
    config: LtdBannerConfig = LtdBannerConfig(),
    onClaimClick: (() -> Unit)? = null,
    showRedeem: Boolean = false,
    ltdCodeInput: String = "",
    onLTDCodeChanged: (String) -> Unit = {},
    onRedeemClick: () -> Unit = {},
    isRedeemingLTD: Boolean = false,
    ltdRedeemResult: String? = null,
) {
    val context = LocalContext.current
    val handleClaim = onClaimClick ?: {
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(config.landingUrl)))
    }

    if (!config.enabled) return

    Card(
        colors = CardDefaults.cardColors(containerColor = NothingBlack),
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        border = BorderStroke(1.dp, NeonRed)
    ) {
        Column(
            modifier = Modifier.padding(NothingDimens.cardPadding),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // ── Scarcity badge ──
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(4.dp))
                    .background(NeonRed)
                    .padding(horizontal = 10.dp, vertical = 3.dp)
            ) {
                Text("${config.badgeIcon} ${config.badge}", color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelSmall)
            }

            Spacer(modifier = Modifier.height(12.dp))
            Text(config.title, color = NothingWhite, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleLarge)
            Spacer(modifier = Modifier.height(4.dp))

            // ── Price anchoring ──
            Row(verticalAlignment = Alignment.Bottom) {
                Text("${config.currency}${config.price}", color = NeonRed, fontWeight = FontWeight.ExtraBold, fontSize = 32.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Text("${config.currency}${config.compareAt}", color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall, textDecoration = TextDecoration.LineThrough)
            }
            Text(config.sticky, color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall)

            Spacer(modifier = Modifier.height(16.dp))

            // ── Scarcity bar ──
            Box(
                modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(4.dp)).background(NeonRed.copy(alpha = 0.15f)).padding(horizontal = 12.dp, vertical = 8.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Whatshot, contentDescription = null, tint = NeonRed, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    val claimedSpots = (config.totalSpots - config.spotsRemaining).coerceAtLeast(0)
                    Text("$claimedSpots of ${config.totalSpots} ${config.scarcityLabel}", color = NeonRed, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.labelSmall)
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // ── Benefits row ──
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                val benefits = listOf(
                    config.benefitNoExpiryValue to "unlimited",
                    "${config.directions}" to config.benefitDirectionsLabel,
                    config.benefitNoExpiryValue to config.benefitNoExpiryLabel
                )
                benefits.forEach { (num, label) ->
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(num, color = NothingWhite, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        Text(label, color = NothingTextTertiary, style = MaterialTheme.typography.labelSmall, fontSize = 10.sp)
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // ── CTA ──
            Button(
                onClick = handleClaim,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = NeonRed),
                shape = RoundedCornerShape(NothingDimens.pillRadius)
            ) { Text(config.ctaText, color = NothingWhite, fontWeight = FontWeight.Bold) }

            if (showRedeem) {
                Spacer(modifier = Modifier.height(12.dp))
                HorizontalDivider(color = NothingBorder)
                Spacer(modifier = Modifier.height(12.dp))

                Text(config.redeemTitle, color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
                Spacer(modifier = Modifier.height(NothingDimens.textGap))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    OutlinedTextField(
                        value = ltdCodeInput,
                        onValueChange = onLTDCodeChanged,
                        placeholder = { Text(config.redeemPlaceholder, color = NothingTextTertiary) },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = NeonRed, unfocusedBorderColor = NothingBorder,
                            focusedTextColor = NothingWhite, unfocusedTextColor = NothingWhite, cursorColor = NothingWhite,
                        ),
                        shape = RoundedCornerShape(NothingDimens.cardRadius)
                    )
                    Spacer(modifier = Modifier.width(NothingDimens.elementGap))
                    Button(
                        onClick = onRedeemClick,
                        enabled = ltdCodeInput.isNotBlank() && !isRedeemingLTD,
                        colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
                        shape = RoundedCornerShape(NothingDimens.pillRadius)
                    ) {
                        if (isRedeemingLTD) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), color = NothingBlack, strokeWidth = 2.dp)
                        } else { Text(config.redeemCtaText, color = NothingBlack) }
                    }
                }
                if (ltdRedeemResult != null) {
                    Spacer(modifier = Modifier.height(NothingDimens.textGap))
                    Text(ltdRedeemResult, color = if (ltdRedeemResult.startsWith("Lifetime")) NothingSuccess else NothingError, style = MaterialTheme.typography.labelSmall)
                }
            }
        }
    }
}
