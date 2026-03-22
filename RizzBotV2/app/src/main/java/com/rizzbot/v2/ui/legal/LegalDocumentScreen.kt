package com.rizzbot.v2.ui.legal

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.rizzbot.v2.R
import java.nio.charset.StandardCharsets

enum class LegalDocumentKind {
    TERMS,
    PRIVACY,
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LegalDocumentScreen(
    kind: LegalDocumentKind,
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    val body = remember(kind) {
        val resId = when (kind) {
            LegalDocumentKind.TERMS -> R.raw.terms_of_service
            LegalDocumentKind.PRIVACY -> R.raw.privacy_policy
        }
        context.resources.openRawResource(resId).use { stream ->
            stream.bufferedReader(StandardCharsets.UTF_8).readText()
        }
    }
    val title = when (kind) {
        LegalDocumentKind.TERMS -> "Terms of Service"
        LegalDocumentKind.PRIVACY -> "Privacy Policy"
    }
    val darkBg = Color(0xFF0F0F1A)

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = title,
                        fontWeight = FontWeight.Bold,
                        fontSize = 17.sp,
                        color = Color.White,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.White,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = darkBg,
                    titleContentColor = Color.White,
                ),
            )
        },
        containerColor = darkBg,
    ) { padding ->
        Text(
            text = body,
            color = Color(0xFFB8B8C8),
            fontSize = 14.sp,
            lineHeight = 22.sp,
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
        )
    }
}
