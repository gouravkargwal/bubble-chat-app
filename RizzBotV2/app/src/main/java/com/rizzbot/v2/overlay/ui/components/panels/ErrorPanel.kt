package com.rizzbot.v2.overlay.ui.components.panels

import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
 * Panel showing error messages with retry/upgrade options
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
        Text(if (isQuotaExceeded) "\uD83D\uDCA8" else "\uD83D\uDE15", fontSize = 32.sp)
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            when {
                isQuotaExceeded -> "Credits exhausted. Upgrade or wait for your daily refill."
                isRateLimited -> "We're getting a lot of requests. Please try again in a minute."
                else -> "Something went wrong on our side. We're looking into it."
            },
            color = NothingWhite,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center
        )
        if (isQuotaExceeded) {
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                "Upgrade for a higher daily reply allowance",
                color = NothingTextSecondary,
                fontSize = 13.sp,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(16.dp))
            Button(
                onClick = onUpgrade,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
                shape = RoundedCornerShape(NothingDimens.cardRadius)
            ) {
                Text("Upgrade Now", color = NothingBlack)
            }
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedButton(
                onClick = onDismiss,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(NothingDimens.cardRadius),
                border = androidx.compose.foundation.BorderStroke(NothingDimens.borderThickness, NothingBorder),
            ) {
                Text("Dismiss", color = NothingWhite)
            }
        } else {
            Spacer(modifier = Modifier.height(16.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(
                    onClick = onDismiss,
                    border = androidx.compose.foundation.BorderStroke(NothingDimens.borderThickness, NothingBorder),
                ) {
                    Text("Dismiss", color = NothingWhite)
                }
                Button(
                    onClick = onRetry,
                    colors = ButtonDefaults.buttonColors(containerColor = NothingWhite),
                    shape = RoundedCornerShape(NothingDimens.cardRadius),
                ) {
                    Text("Retry", color = NothingBlack)
                }
            }
        }
    }
}
