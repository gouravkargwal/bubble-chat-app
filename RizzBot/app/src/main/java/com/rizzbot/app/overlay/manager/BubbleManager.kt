package com.rizzbot.app.overlay.manager

import android.content.Context
import android.graphics.PixelFormat
import android.view.Gravity
import android.view.WindowManager
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.ComposeView
import androidx.lifecycle.setViewTreeLifecycleOwner
import androidx.savedstate.setViewTreeSavedStateRegistryOwner
import com.rizzbot.app.overlay.OverlayLifecycleOwner
import com.rizzbot.app.overlay.ui.BubbleOverlay
import com.rizzbot.app.overlay.ui.OverlayTheme
import com.rizzbot.app.util.AnalyticsHelper
import com.rizzbot.app.util.ClipboardHelper
import com.rizzbot.app.util.HapticHelper
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BubbleManager @Inject constructor(
    @ApplicationContext private val context: Context,
    private val clipboardHelper: ClipboardHelper,
    private val hapticHelper: HapticHelper,
    private val analyticsHelper: AnalyticsHelper
) {
    private val windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    private var overlayView: ComposeView? = null
    private var lifecycleOwner = OverlayLifecycleOwner()

    var bubbleState by mutableStateOf<BubbleState>(BubbleState.Hidden)
        private set

    var onRizzButtonClicked: (() -> Unit)? = null
    var onGenerateReplies: (() -> Unit)? = null
    var onRefreshChat: (() -> Unit)? = null
    var onPasteToInput: ((String) -> Unit)? = null
    var onSyncProfile: (() -> Unit)? = null
    var onRefreshReplies: (() -> Unit)? = null
    var onNewTopicClicked: (() -> Unit)? = null
    var onReadFullChat: (() -> Unit)? = null
    var onGenerateWithHint: ((String) -> Unit)? = null

    private val layoutParams = WindowManager.LayoutParams(
        WindowManager.LayoutParams.WRAP_CONTENT,
        WindowManager.LayoutParams.WRAP_CONTENT,
        WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
        PixelFormat.TRANSLUCENT
    ).apply {
        gravity = Gravity.TOP or Gravity.END
        x = 16
        y = 300
    }

    fun showRizzButton() {
        bubbleState = BubbleState.RizzButton
        ensureOverlayVisible()
    }

    fun minimizeToRizzButton() {
        bubbleState = BubbleState.RizzButton
    }

    fun hideRizzButton() {
        if (bubbleState is BubbleState.RizzButton) {
            hide()
        }
    }

    fun hideProfileOverlay() {
        if (bubbleState is BubbleState.ProfileSyncButton ||
            bubbleState is BubbleState.ProfileSyncing ||
            bubbleState is BubbleState.ProfileSynced) {
            hide()
        }
    }

    private var currentHasProfile: Boolean = false
    private var lastReplies: List<String>? = null

    fun setHasProfile(hasProfile: Boolean) {
        currentHasProfile = hasProfile
    }

    fun showActionMenu() {
        hapticHelper.tick()
        bubbleState = BubbleState.ActionMenu(currentHasProfile, lastReplies)
        ensureOverlayVisible()
    }

    fun showSuggestion(replies: List<String>) {
        hapticHelper.success()
        lastReplies = replies
        bubbleState = BubbleState.Expanded(replies, currentHasProfile)
        ensureOverlayVisible()
    }

    companion object {
        const val MAX_SUGGESTIONS = 4
    }

    fun showLoading(message: String = "Thinking...") {
        bubbleState = BubbleState.Loading(message)
        ensureOverlayVisible()
    }

    fun showError(message: String) {
        hapticHelper.error()
        bubbleState = BubbleState.Error(message)
        ensureOverlayVisible()
    }

    fun showProfileSyncing(personName: String) {
        bubbleState = BubbleState.ProfileSyncing(personName)
        ensureOverlayVisible()
    }

    fun showProfileSynced(personName: String) {
        hapticHelper.success()
        bubbleState = BubbleState.ProfileSynced(personName)
        ensureOverlayVisible()
    }

    fun showProfileSyncButton(personName: String) {
        bubbleState = BubbleState.ProfileSyncButton(personName)
        ensureOverlayVisible()
    }

    /** Toggle focusable flag so the keyboard can appear when editing the hint TextField */
    private fun setOverlayFocusable(focusable: Boolean) {
        overlayView ?: return
        if (focusable) {
            layoutParams.flags = layoutParams.flags and WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE.inv()
        } else {
            layoutParams.flags = layoutParams.flags or WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
        }
        try {
            windowManager.updateViewLayout(overlayView, layoutParams)
        } catch (_: Exception) { }
    }

    fun hide() {
        bubbleState = BubbleState.Hidden
        removeOverlay()
    }

    private fun ensureOverlayVisible() {
        if (overlayView != null) return // Already showing, state update will recompose

        val view = ComposeView(context).apply {
            setViewTreeLifecycleOwner(lifecycleOwner)
            setViewTreeSavedStateRegistryOwner(lifecycleOwner)
            setContent {
                OverlayTheme {
                    BubbleOverlay(
                        state = bubbleState,
                        onCopy = { suggestion ->
                            hapticHelper.tick()
                            clipboardHelper.copyToClipboard(suggestion)
                            analyticsHelper.logSuggestionCopied()
                        },
                        onDismiss = { hide() },
                        onMinimize = { minimizeToRizzButton() },
                        onRizzClick = { onRizzButtonClicked?.invoke() },
                        onGenerateReplies = { onGenerateReplies?.invoke() },
                        onShowLastReplies = {
                            lastReplies?.let { replies ->
                                bubbleState = BubbleState.Expanded(replies, currentHasProfile)
                            }
                        },
                        onRefreshChat = { onRefreshChat?.invoke() },
                        onPasteToInput = { text ->
                            analyticsHelper.logSuggestionPasted()
                            onPasteToInput?.invoke(text)
                        },
                        onSyncProfile = { onSyncProfile?.invoke() },
                        onRefreshReplies = { onRefreshReplies?.invoke() },
                        onNewTopicClick = { onNewTopicClicked?.invoke() },
                        onReadFullChat = { onReadFullChat?.invoke() },
                        onGenerateWithHint = { hint -> onGenerateWithHint?.invoke(hint) },
                        onFocusChanged = { focused -> setOverlayFocusable(focused) }
                    )
                }
            }
        }

        lifecycleOwner.onCreate()
        lifecycleOwner.onResume()

        try {
            windowManager.addView(view, layoutParams)
            overlayView = view
        } catch (e: Exception) {
            // Permission might have been revoked
            e.printStackTrace()
        }
    }

    private fun removeOverlay() {
        overlayView?.let { view ->
            try {
                lifecycleOwner.onPause()
                lifecycleOwner.onStop()
                windowManager.removeView(view)
                lifecycleOwner.onDestroy()
            } catch (_: Exception) { }
        }
        overlayView = null
        // Create a fresh lifecycle owner for next overlay
        lifecycleOwner = OverlayLifecycleOwner()
    }
}
