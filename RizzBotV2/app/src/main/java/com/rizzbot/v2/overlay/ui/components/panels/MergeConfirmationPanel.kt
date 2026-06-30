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
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.domain.model.SuggestedMatch
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingSurface
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingTextTertiary
import com.rizzbot.v2.ui.theme.NothingWhite
@Composable
fun MergeConfirmationPanel(
    payload: SuggestedMatch,
    onYes: () -> Unit,
    onNo: () -> Unit,
    modifier: Modifier = Modifier
) {
    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(NothingDimens.cardPadding),
        verticalArrangement = Arrangement.Top
    ) {
        Text(
            text = "New Chat Detected",
            color = NothingWhite,
            fontWeight = FontWeight.Bold,
            fontSize = 16.sp
        )

        Spacer(modifier = Modifier.height(6.dp))

        Text(
            text = "Is this the same ${payload.personName} you were talking to previously?",
            color = NothingTextSecondary,
            fontSize = 13.sp
        )

        Spacer(modifier = Modifier.height(14.dp))

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(NothingDimens.cardRadius),
            colors = CardDefaults.cardColors(containerColor = NothingSurface),
            border = androidx.compose.foundation.BorderStroke(NothingDimens.borderThickness, NothingBorder),
        ) {
            Column(modifier = Modifier.padding(NothingDimens.cardPadding)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = payload.contextPreview.aiMemoryNote,
                        color = NothingWhite,
                        fontWeight = FontWeight.Medium,
                        fontSize = 13.sp
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))

                Text(
                    text = "Her last message:",
                    color = NothingTextTertiary,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 12.sp
                )
                Text(
                    text = payload.contextPreview.herLastMessage,
                    color = NothingWhite,
                    fontSize = 13.sp,
                    lineHeight = 16.sp,
                    modifier = Modifier.padding(top = 4.dp)
                )

                Spacer(modifier = Modifier.height(10.dp))

                Text(
                    text = "Your last reply:",
                    color = NothingTextTertiary,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 12.sp
                )
                Text(
                    text = payload.contextPreview.yourLastReply,
                    color = NothingWhite,
                    fontSize = 13.sp,
                    lineHeight = 16.sp,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        Button(
            onClick = onYes,
            modifier = Modifier
                .fillMaxWidth(),
            shape = RoundedCornerShape(NothingDimens.cardRadius),
            colors = androidx.compose.material3.ButtonDefaults.buttonColors(containerColor = NothingWhite)
        ) {
            Text(
                text = "Yes, Link Chats & Use Memory",
                color = NothingBlack,
                fontWeight = FontWeight.SemiBold
            )
        }

        Spacer(modifier = Modifier.height(10.dp))

        OutlinedButton(
            onClick = onNo,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(NothingDimens.cardRadius),
            border = androidx.compose.foundation.BorderStroke(NothingDimens.borderThickness, NothingBorder),
        ) {
            Text(
                text = "No, New Person",
                color = NothingWhite,
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}
