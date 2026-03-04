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
import com.rizzbot.app.util.ClipboardHelper
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BubbleManager @Inject constructor(
    @ApplicationContext private val context: Context,
    private val clipboardHelper: ClipboardHelper
) {
    private val windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    private var overlayView: ComposeView? = null
    private var lifecycleOwner = OverlayLifecycleOwner()

    var bubbleState by mutableStateOf<BubbleState>(BubbleState.Hidden)
        private set

    var onRizzButtonClicked: (() -> Unit)? = null
    var onRefreshChat: (() -> Unit)? = null
    var onToneSelected: ((String) -> Unit)? = null
    var onPasteToInput: ((String) -> Unit)? = null
    var onSyncProfile: (() -> Unit)? = null
    var onRefreshReplies: (() -> Unit)? = null
    var onRizzMenuRequested: (() -> Unit)? = null
    var onIcebreakerClicked: (() -> Unit)? = null

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

    fun showRizzMenu(hasProfile: Boolean = false) {
        bubbleState = BubbleState.RizzMenu(hasProfile)
        ensureOverlayVisible()
    }

    fun hideRizzButton() {
        if (bubbleState is BubbleState.RizzButton || bubbleState is BubbleState.RizzMenu) {
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

    fun showSuggestion(replies: List<String>) {
        bubbleState = BubbleState.Expanded(replies)
        ensureOverlayVisible()
    }

    fun appendSuggestions(newReplies: List<String>) {
        val current = bubbleState
        if (current is BubbleState.Expanded) {
            val combined = (current.suggestions + newReplies).take(MAX_SUGGESTIONS)
            bubbleState = BubbleState.Expanded(combined)
        } else {
            showSuggestion(newReplies.take(MAX_SUGGESTIONS))
        }
    }

    companion object {
        const val MAX_SUGGESTIONS = 4
    }

    fun showLoading(message: String = "Thinking...") {
        bubbleState = BubbleState.Loading(message)
        ensureOverlayVisible()
    }

    fun showError(message: String) {
        bubbleState = BubbleState.Error(message)
        ensureOverlayVisible()
    }

    fun showProfileSyncing(personName: String) {
        bubbleState = BubbleState.ProfileSyncing(personName)
        ensureOverlayVisible()
    }

    fun showProfileSynced(personName: String) {
        bubbleState = BubbleState.ProfileSynced(personName)
        ensureOverlayVisible()
    }

    fun showProfileSyncButton(personName: String) {
        bubbleState = BubbleState.ProfileSyncButton(personName)
        ensureOverlayVisible()
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
                            clipboardHelper.copyToClipboard(suggestion)
                        },
                        onDismiss = { hide() },
                        onRizzClick = { onRizzMenuRequested?.invoke() },
                        onGenerateReply = { onRizzButtonClicked?.invoke() },
                        onRefreshChat = { onRefreshChat?.invoke() },
                        onToneSelected = { tone -> onToneSelected?.invoke(tone) },
                        onPasteToInput = { text -> onPasteToInput?.invoke(text) },
                        onSyncProfile = { onSyncProfile?.invoke() },
                        onRefreshReplies = { onRefreshReplies?.invoke() },
                        onIcebreakerClick = { onIcebreakerClicked?.invoke() }
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
