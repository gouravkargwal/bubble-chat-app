package com.rizzbot.v2.overlay.ui.components.panels

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.overlay.ui.theme.OverlayColors

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

    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(if (isQuotaExceeded) "\uD83D\uDCA8" else "\uD83D\uDE15", fontSize = 32.sp)
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            when {
                isQuotaExceeded -> "Daily free limit reached"
                isRateLimited -> "We're getting a lot of requests. Please try again in a minute."
                else -> {
                    // Hide low-level error details (e.g. provider quota, timeouts)
                    // behind a friendly, generic server error message.
                    "Something went wrong on our side. We're looking into it."
                }
            },
            color = Color.White,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center
        )
        if (isQuotaExceeded) {
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                "Upgrade to Premium for unlimited replies",
                color = Color.Gray,
                fontSize = 13.sp,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(16.dp))
            Button(
                onClick = onUpgrade,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = OverlayColors.AccentPink),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("Upgrade Now")
            }
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedButton(
                onClick = onDismiss,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("Dismiss", color = Color.White)
            }
        } else {
            Spacer(modifier = Modifier.height(16.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onDismiss) {
                    Text("Dismiss", color = Color.White)
                }
                Button(
                    onClick = onRetry,
                    colors = ButtonDefaults.buttonColors(containerColor = OverlayColors.AccentPink)
                ) {
                    Text("Retry")
                }
            }
        }
    }
}
