package com.rizzbot.v2.overlay.ui.components.panels

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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingWhite

/**
 * Panel showing error messages with retry/upgrade options (Nothing OS compliant).
 */
@Composable
fun ErrorPanel(
    message: String,
    errorType: SuggestionResult.ErrorType,
    onRetry: () -> Unit,
    onUpgrade: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val isQuotaExceeded = errorType == SuggestionResult.ErrorType.QUOTA_EXCEEDED
    val isRateLimited = errorType == SuggestionResult.ErrorType.RATE_LIMITED
    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(NothingDimens.cardPadding),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Nothing OS dot-matrix style icon — clean geometric shape
        Box(
            modifier = Modifier
                .size(56.dp)
                .clip(CircleShape)
                .background(NothingSurface)
                .border(NothingDimens.borderThickness, NothingBorder, CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                if (isQuotaExceeded) Icons.Default.Close else Icons.Default.Refresh,
                contentDescription = null,
                tint = NothingWhite,
                modifier = Modifier.size(28.dp)
            )
        }
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            when {
                isQuotaExceeded -> "Credits exhausted"
                isRateLimited -> "Too many requests"
                else -> "Something went wrong"
            },
            color = NothingWhite,
            fontWeight = FontWeight.Bold,
            style = MaterialTheme.typography.titleMedium,
            textAlign = TextAlign.Center
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            when {
                isQuotaExceeded -> "Upgrade or wait for your daily refill to continue."
                isRateLimited -> "Please try again in a minute."
                else -> "We're looking into it. Please try again."
            },
            color = NothingTextSecondary,
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(24.dp))

        if (isQuotaExceeded) {
            Button(
                onClick = onUpgrade,
                modifier = Modifier.fillMaxWidth().height(NothingDimens.minTouchTarget),
                colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
                shape = RoundedCornerShape(NothingDimens.pillRadius)
            ) {
                Text("Upgrade Now", color = NothingBlack, fontWeight = FontWeight.SemiBold)
            }
            Spacer(modifier = Modifier.height(10.dp))
            OutlinedButton(
                onClick = onDismiss,
                modifier = Modifier.fillMaxWidth().height(NothingDimens.minTouchTarget),
                shape = RoundedCornerShape(NothingDimens.pillRadius),
                border = androidx.compose.foundation.BorderStroke(NothingDimens.borderThickness, NothingBorder),
            ) {
                Text("Dismiss", color = NothingTextSecondary, fontWeight = FontWeight.Medium)
            }
        } else {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                OutlinedButton(
                    onClick = onDismiss,
                    modifier = Modifier.weight(1f).height(NothingDimens.minTouchTarget),
                    shape = RoundedCornerShape(NothingDimens.pillRadius),
                    border = androidx.compose.foundation.BorderStroke(NothingDimens.borderThickness, NothingBorder),
                ) {
                    Text("Dismiss", color = NothingTextSecondary)
                }
                Button(
                    onClick = onRetry,
                    modifier = Modifier.weight(1f).height(NothingDimens.minTouchTarget),
                    colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
                    shape = RoundedCornerShape(NothingDimens.pillRadius),
                ) {
                    Text("Retry", color = NothingBlack, fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}
