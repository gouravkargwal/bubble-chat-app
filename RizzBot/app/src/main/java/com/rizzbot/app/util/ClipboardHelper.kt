package com.rizzbot.app.util

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ClipboardHelper @Inject constructor(
    @ApplicationContext private val context: Context
) {
    fun copyToClipboard(text: String) {
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val clip = ClipData.newPlainText("RizzBot Suggestion", text)
        clipboard.setPrimaryClip(clip)
        Toast.makeText(context, "Copied! Paste it in chat", Toast.LENGTH_SHORT).show()
    }
}
