package com.rizzbot.v2.ui.legal

import android.content.Intent
import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.platform.LocalContext

enum class LegalDocumentKind { TERMS, PRIVACY }

@Composable
fun LegalDocumentScreen(kind: LegalDocumentKind, onBack: () -> Unit) {
    val context = LocalContext.current
    val url = when (kind) {
        LegalDocumentKind.TERMS -> "https://cookdai.site/terms"
        LegalDocumentKind.PRIVACY -> "https://cookdai.site/privacy"
    }
    LaunchedEffect(Unit) {
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        context.startActivity(intent)
        onBack()
    }
}
