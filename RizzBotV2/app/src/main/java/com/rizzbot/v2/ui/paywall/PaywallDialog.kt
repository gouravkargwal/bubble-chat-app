package com.rizzbot.v2.ui.paywall

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import com.revenuecat.purchases.ui.revenuecatui.PaywallDialog as RevenueCatPaywallDialog
import com.revenuecat.purchases.ui.revenuecatui.PaywallDialogOptions
import com.revenuecat.purchases.ui.revenuecatui.ExperimentalPreviewRevenueCatUIPurchasesAPI

@OptIn(ExperimentalMaterial3Api::class, ExperimentalPreviewRevenueCatUIPurchasesAPI::class)
@Composable
fun PaywallDialog(
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = Color(0xFF0F0F1A),
        modifier = modifier.fillMaxSize()
    ) {
        val options = PaywallDialogOptions.Builder()
            .setDismissRequest { onDismiss() }
            .build()

        RevenueCatPaywallDialog(
            paywallDialogOptions = options
        )
    }
}
