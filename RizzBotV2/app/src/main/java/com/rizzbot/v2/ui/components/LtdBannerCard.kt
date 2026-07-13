package com.rizzbot.v2.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
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
 * Simple redeem code card — no pricing, no selling, no external links.
 * Google-safe: allows users who already have a code to redeem it.
 */
@Composable
fun RedeemCodeCard(
    ltdCodeInput: String = "",
    onLTDCodeChanged: (String) -> Unit = {},
    onRedeemClick: () -> Unit = {},
    isRedeemingLTD: Boolean = false,
    ltdRedeemResult: String? = null,
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = NothingBlack),
        shape = RoundedCornerShape(NothingDimens.cardRadius),
        border = androidx.compose.foundation.BorderStroke(1.dp, NeonRed)
    ) {
        Column(
            modifier = Modifier.padding(NothingDimens.cardPadding),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("Redeem Code", color = NothingTextSecondary, style = MaterialTheme.typography.labelSmall)
            Spacer(modifier = Modifier.height(NothingDimens.textGap))
            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = ltdCodeInput,
                    onValueChange = onLTDCodeChanged,
                    placeholder = { Text("LTD-XXXXXXXX", color = NothingTextTertiary) },
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
                    } else { Text("Redeem", color = NothingBlack) }
                }
            }
            if (ltdRedeemResult != null) {
                Spacer(modifier = Modifier.height(NothingDimens.textGap))
                Text(ltdRedeemResult, color = if (ltdRedeemResult.startsWith("Lifetime")) NothingSuccess else NothingError, style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}
