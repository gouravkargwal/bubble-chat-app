package com.rizzbot.v2.ui.onboarding

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.PhotoCamera
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingError
import com.rizzbot.v2.ui.theme.NothingSuccess
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite
import com.rizzbot.v2.util.Constants

/** Matches backend FREE_SIGNUP_CREDITS in tier_config.py — 15 one-time signup bonus credits (updated Jan 2025). */
private val freeCreditsCount = Constants.SIGNUP_BONUS_CREDITS

/**
 * Signup bonus screen shown to new users after Google Sign-In.
 *
 * Welcomes the user with a prominent free-credits hero card, compact benefit highlights,
 * and an optional referral code field — all on a single non-scrollable screen.
 */
@Composable
fun OnboardingSignupBonusStep(
    referralCode: String,
    referralApplying: Boolean,
    referralSuccess: String?,
    referralError: String?,
    onReferralCodeChange: (String) -> Unit,
    onApplyReferral: () -> Unit,
    onStart: () -> Unit,
    userName: String?,
) {
    val context = LocalContext.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = NothingDimens.screenPadding),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(modifier = Modifier.height(24.dp))

        // ── Welcome icon ──
        Box(
            modifier = Modifier
                .size(56.dp)
                .clip(RoundedCornerShape(14.dp))
                .background(NothingBorder),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = Icons.Filled.Star,
                contentDescription = null,
                tint = NothingWhite,
                modifier = Modifier.size(28.dp),
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        // ── Headline ──
        Text(
            text = if (!userName.isNullOrBlank()) "You're in, $userName!" else "You're in!",
            style = MaterialTheme.typography.headlineMedium,
            color = NothingWhite,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )

        Spacer(modifier = Modifier.height(4.dp))

        // ── Subtitle ──
        Text(
            text = "Here's a welcome gift to get you started.",
            style = MaterialTheme.typography.bodyLarge,
            color = NothingTextSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(0.85f),
        )

        Spacer(modifier = Modifier.height(24.dp))

        // ── Free Credits Hero Card ──
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(NothingDimens.cardRadius))
                .background(NothingSurface)
                .border(NothingDimens.borderThickness, NothingBorder, RoundedCornerShape(NothingDimens.cardRadius))
                .padding(vertical = 20.dp),
            contentAlignment = Alignment.Center,
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                // FREE badge
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(4.dp))
                        .background(NothingWhite)
                        .padding(horizontal = 10.dp, vertical = 3.dp),
                ) {
                    Text(
                        text = "FREE",
                        color = NothingBlack,
                        fontWeight = FontWeight.ExtraBold,
                        style = MaterialTheme.typography.labelSmall,
                        letterSpacing = 1.sp,
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Credit count
                Text(
                    text = "$freeCreditsCount",
                    fontSize = 48.sp,
                    color = NothingWhite,
                    fontWeight = FontWeight.Bold,
                )

                Spacer(modifier = Modifier.height(2.dp))

                Text(
                    text = "free replies",
                    style = MaterialTheme.typography.titleSmall,
                    color = NothingTextSecondary,
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Description
                Text(
                    text = "No trial. No credit card. Just start replying.",
                    style = MaterialTheme.typography.labelMedium,
                    color = NothingTextTertiary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth(0.8f),
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // ── Compact benefit highlights ──
        BenefitLine(
            icon = Icons.Filled.Edit,
            text = "AI replies that sound like you",
        )
        Spacer(modifier = Modifier.height(6.dp))
        BenefitLine(
            icon = Icons.Filled.PhotoCamera,
            text = "Profile audit to improve your matches",
        )

        Spacer(modifier = Modifier.weight(1f))

        // ── Compact referral section ──
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedTextField(
                value = referralCode,
                onValueChange = {
                    onReferralCodeChange(it)
                },
                placeholder = {
                    Text("Referral code", color = NothingTextTertiary)
                },
                modifier = Modifier.weight(1f),
                singleLine = true,
                textStyle = MaterialTheme.typography.bodySmall.copy(
                    color = NothingWhite,
                ),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedTextColor = NothingWhite,
                    unfocusedTextColor = NothingWhite,
                    focusedBorderColor = NothingWhite,
                    unfocusedBorderColor = NothingBorder,
                    cursorColor = NothingWhite,
                ),
                shape = RoundedCornerShape(NothingDimens.cardRadius),
            )

            Button(
                onClick = onApplyReferral,
                enabled = !referralApplying && referralCode.isNotBlank(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = NothingSurface,
                ),
                shape = RoundedCornerShape(NothingDimens.pillRadius),
                modifier = Modifier.height(48.dp),
            ) {
                if (referralApplying) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        color = NothingWhite,
                        strokeWidth = 2.dp,
                    )
                } else {
                    Text(
                        "Apply",
                        color = NothingWhite,
                        fontWeight = FontWeight.SemiBold,
                        style = MaterialTheme.typography.labelMedium,
                    )
                }
            }
        }

        // Referral feedback
        if (referralSuccess != null) {
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = referralSuccess,
                color = NothingSuccess,
                style = MaterialTheme.typography.labelSmall,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
        }
        if (referralError != null) {
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = referralError,
                color = NothingError,
                style = MaterialTheme.typography.labelSmall,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        Spacer(modifier = Modifier.height(12.dp))

        // ── CTA button ──
        Button(
            onClick = onStart,
            colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
            modifier = Modifier
                .fillMaxWidth()
                .height(NothingDimens.minTouchTarget),
            shape = RoundedCornerShape(NothingDimens.pillRadius),
        ) {
            Text(
                "Start using Cookd",
                color = NothingBlack,
                fontWeight = FontWeight.Bold,
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
    }
}

@Composable
private fun BenefitLine(
    icon: ImageVector,
    text: String,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(NothingDimens.cardRadius))
            .background(NothingSurface)
            .border(NothingDimens.borderThickness, NothingBorder, RoundedCornerShape(NothingDimens.cardRadius))
            .padding(horizontal = NothingDimens.cardPadding, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Box(
            modifier = Modifier
                .size(28.dp)
                .clip(RoundedCornerShape(6.dp))
                .background(NothingBorder),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = NothingWhite,
                modifier = Modifier.size(16.dp),
            )
        }
        Text(
            text = text,
            color = NothingWhite,
            fontWeight = FontWeight.Medium,
            style = MaterialTheme.typography.labelMedium,
        )
    }
}
