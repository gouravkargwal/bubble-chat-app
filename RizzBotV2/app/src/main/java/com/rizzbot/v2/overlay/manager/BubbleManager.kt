package com.rizzbot.v2.overlay.manager

import android.content.Context
import android.graphics.PixelFormat
import android.os.Build
import android.util.Log
import android.view.Gravity
import android.view.WindowManager
import androidx.compose.ui.platform.ComposeView
import androidx.lifecycle.setViewTreeLifecycleOwner
import androidx.savedstate.setViewTreeSavedStateRegistryOwner
import com.rizzbot.v2.capture.ScreenCaptureOrchestrator
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.overlay.OverlayEvent
import com.rizzbot.v2.overlay.OverlayEventBus
import com.rizzbot.v2.overlay.OverlayLifecycleOwner
import com.rizzbot.v2.overlay.ui.BubbleOverlay
import com.rizzbot.v2.util.ClipboardHelper
import com.rizzbot.v2.util.HapticHelper
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

private const val TAG = "BubbleManager"

@Singleton
class BubbleManager @Inject constructor(
    @ApplicationContext private val context: Context,
    private val eventBus: OverlayEventBus,
    private val orchestrator: ScreenCaptureOrchestrator,
    private val clipboardHelper: ClipboardHelper,
    private val hapticHelper: HapticHelper,
    private val settingsRepository: SettingsRepository,
    private val hostedRepository: HostedRepository
) {
    private var scope: CoroutineScope? = null
    private val windowManager by lazy { context.getSystemService(Context.WINDOW_SERVICE) as WindowManager }
    private var composeView: ComposeView? = null
    private val lifecycleOwner = OverlayLifecycleOwner()
    private var bubbleX: Int
    private var bubbleY = 400
    private var stateCollectorJob: Job? = null
    // When non-null, we're in "add more screenshots" mode and the next bubble tap
    // should append a screenshot for this direction instead of reopening the picker.
    private var pendingAppendDirection: DirectionWithHint? = null

    init {
        // Default position: right edge, vertically centered
        val dm = context.resources.displayMetrics
        bubbleX = dm.widthPixels - 180 // near right edge
    }

    private val _state = MutableStateFlow<BubbleState>(BubbleState.Hidden)
    val state: StateFlow<BubbleState> = _state.asStateFlow()

    private fun ensureScope(): CoroutineScope {
        return scope ?: CoroutineScope(SupervisorJob() + Dispatchers.Main).also {
            scope = it
            // Start state collector for window layout updates
            stateCollectorJob = it.launch {
                _state.collect { state ->
                    updateWindowForState(state)
                }
            }
        }
    }

    private fun isFullScreenState(state: BubbleState): Boolean = when (state) {
        is BubbleState.DirectionPicker,
        is BubbleState.ScreenshotPreview,
        is BubbleState.Loading,
        is BubbleState.Expanded,
        is BubbleState.Error -> true
        else -> false
    }

    private fun createParams(fullScreen: Boolean): WindowManager.LayoutParams {
        return WindowManager.LayoutParams(
            if (fullScreen) WindowManager.LayoutParams.MATCH_PARENT else WindowManager.LayoutParams.WRAP_CONTENT,
            if (fullScreen) WindowManager.LayoutParams.MATCH_PARENT else WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                @Suppress("DEPRECATION")
                WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            if (!fullScreen) {
                x = bubbleX
                y = bubbleY
            }
        }
    }

    private fun updateWindowForState(state: BubbleState) {
        val view = composeView ?: return
        val params = createParams(isFullScreenState(state))
        try {
            windowManager.updateViewLayout(view, params)
        } catch (e: IllegalArgumentException) {
            Log.w(TAG, "View not attached when updating layout", e)
        }
    }

    private fun createAndAttachView(): ComposeView {
        val params = createParams(isFullScreenState(_state.value))
        val view = ComposeView(context).apply {
            setContent {
                BubbleOverlay(
                    state = _state,
                    usageState = hostedRepository.usageState,
                    onEvent = { handleEvent(it) }
                )
            }
        }
        view.setViewTreeLifecycleOwner(lifecycleOwner)
        view.setViewTreeSavedStateRegistryOwner(lifecycleOwner)
        windowManager.addView(view, params)
        return view
    }

    fun show() {
        if (composeView != null) return

        ensureScope()
        lifecycleOwner.onCreate()
        lifecycleOwner.onResume()
        composeView = createAndAttachView()

        if (_state.value is BubbleState.Hidden) {
            _state.value = BubbleState.RizzButton
        }
    }

    fun hide() {
        // Cancel all pending coroutines (LLM calls, tracking, etc.)
        stateCollectorJob?.cancel()
        stateCollectorJob = null
        scope?.cancel()
        scope = null

        lifecycleOwner.onPause()
        lifecycleOwner.onDestroy()
        composeView?.let {
            try {
                windowManager.removeView(it)
            } catch (e: IllegalArgumentException) {
                Log.w(TAG, "View already removed", e)
            }
        }
        composeView = null
        _state.value = BubbleState.Hidden
        orchestrator.clearScreenshot()
    }

    fun hideForCapture() {
        composeView?.let {
            try {
                windowManager.removeView(it)
            } catch (e: IllegalArgumentException) {
                Log.w(TAG, "View already removed during capture hide", e)
            }
        }
        composeView = null
        _state.value = BubbleState.Capturing
    }

    fun restoreAfterCapture() {
        _state.value = BubbleState.Loading
        if (composeView == null) {
            composeView = createAndAttachView()
        }
    }

    private fun handleEvent(event: OverlayEvent) {
        val activeScope = ensureScope()
        when (event) {
            is OverlayEvent.ShowBubble -> {
                val usage = hostedRepository.usageState.value
                if (usage.dailyRemaining <= 0 && usage.bonusReplies <= 0 && !usage.isPremium) {
                    _state.value = BubbleState.Error(
                        "Daily free limit reached",
                        SuggestionResult.ErrorType.QUOTA_EXCEEDED
                    )
                } else {
                    val appendDirection = pendingAppendDirection
                    if (appendDirection != null) {
                        // We're in "add more screenshots" mode: append another capture
                        // without clearing previous ones, after the user tapped the bubble again.
                        pendingAppendDirection = null
                        activeScope.launch {
                            hideForCapture()
                            kotlinx.coroutines.delay(300)

                            try {
                                orchestrator.captureScreenshot()
                            } finally {
                                if (composeView == null) {
                                    composeView = createAndAttachView()
                                }
                            }

                            val previewBitmaps = orchestrator.getPreviewBitmaps()
                            if (previewBitmaps.isNotEmpty()) {
                                _state.value = BubbleState.ScreenshotPreview(previewBitmaps, appendDirection)
                            } else {
                                val result = orchestrator.result.value
                                _state.value = when (result) {
                                    is SuggestionResult.Error -> BubbleState.Error(result.message, result.errorType)
                                    else -> BubbleState.Error("Screenshot capture failed", SuggestionResult.ErrorType.UNKNOWN)
                                }
                            }
                        }
                    } else {
                        // Normal flow: show direction picker for first capture
                        _state.value = BubbleState.DirectionPicker
                    }
                }
            }
            is OverlayEvent.HideBubble -> hide()
            is OverlayEvent.CaptureRequested -> {
                activeScope.launch {
                    // Clear previous screenshots on fresh capture/retake
                    orchestrator.clearScreenshot()
                    // Hide overlay before capture so it's not in the screenshot
                    hideForCapture()
                    kotlinx.coroutines.delay(300)

                    try {
                        orchestrator.captureScreenshot()
                    } finally {
                        // Restore overlay to show screenshot preview
                        if (composeView == null) {
                            composeView = createAndAttachView()
                        }
                    }

                    // Show preview so user can confirm before sending
                    val previewBitmaps = orchestrator.getPreviewBitmaps()
                    if (previewBitmaps.isNotEmpty()) {
                        _state.value = BubbleState.ScreenshotPreview(previewBitmaps, event.direction)
                    } else {
                        // Capture failed, result already has the error
                        val result = orchestrator.result.value
                        _state.value = when (result) {
                            is SuggestionResult.Error -> BubbleState.Error(result.message, result.errorType)
                            else -> BubbleState.Error("Screenshot capture failed", SuggestionResult.ErrorType.UNKNOWN)
                        }
                    }
                }
            }
            is OverlayEvent.ConfirmScreenshot -> {
                activeScope.launch {
                    _state.value = BubbleState.Loading
                    orchestrator.generateFromScreenshots(event.direction)
                    val result = orchestrator.result.value
                    _state.value = when (result) {
                        is SuggestionResult.Success -> BubbleState.Expanded(result)
                        is SuggestionResult.Error -> BubbleState.Error(result.message, result.errorType, event.direction)
                        is SuggestionResult.Loading -> BubbleState.Loading
                    }
                }
            }
            is OverlayEvent.AddMoreScreenshots -> {
                // Put the user back into bubble mode; the next tap on the bubble
                // will capture an additional screenshot for this direction.
                pendingAppendDirection = event.direction
                _state.value = BubbleState.RizzButton
            }
            is OverlayEvent.RetakeLastScreenshot -> {
                activeScope.launch {
                    // Remove the last screenshot, then capture a new one to replace it
                    orchestrator.removeLastScreenshot()
                    hideForCapture()
                    kotlinx.coroutines.delay(300)

                    try {
                        orchestrator.captureScreenshot()
                    } finally {
                        if (composeView == null) {
                            composeView = createAndAttachView()
                        }
                    }

                    val previewBitmaps = orchestrator.getPreviewBitmaps()
                    if (previewBitmaps.isNotEmpty()) {
                        _state.value = BubbleState.ScreenshotPreview(previewBitmaps, event.direction)
                    } else {
                        val result = orchestrator.result.value
                        _state.value = when (result) {
                            is SuggestionResult.Error -> BubbleState.Error(result.message, result.errorType)
                            else -> BubbleState.Error("Screenshot capture failed", SuggestionResult.ErrorType.UNKNOWN)
                        }
                    }
                }
            }
            is OverlayEvent.DismissSuggestions -> {
                _state.value = BubbleState.RizzButton
                orchestrator.clearScreenshot()
            }
            is OverlayEvent.CopyReply -> {
                clipboardHelper.copyToClipboard(event.reply)
                hapticHelper.lightTap()
                activeScope.launch {
                    settingsRepository.incrementRepliesCopied()
                    if (event.interactionId.isNotEmpty()) {
                        try {
                            hostedRepository.trackCopy(event.interactionId, event.vibeIndex)
                        } catch (e: Exception) {
                            Log.w(TAG, "Failed to track copy", e)
                        }
                    }
                }
            }
            is OverlayEvent.RateReply -> {
                activeScope.launch {
                    if (event.interactionId.isNotEmpty()) {
                        try {
                            hostedRepository.trackRating(event.interactionId, event.vibeIndex, event.isPositive)
                        } catch (e: Exception) {
                            Log.w(TAG, "Failed to track rating", e)
                        }
                    }
                }
            }
            is OverlayEvent.BubbleDragged -> {
                bubbleX += event.deltaX
                bubbleY += event.deltaY
                val view = composeView ?: return
                val params = view.layoutParams as? WindowManager.LayoutParams ?: return
                params.x = bubbleX
                params.y = bubbleY
                try {
                    windowManager.updateViewLayout(view, params)
                } catch (e: IllegalArgumentException) {
                    Log.w(TAG, "View not attached during drag", e)
                }
                return // don't send drag events to eventBus
            }
            is OverlayEvent.UpgradeTapped -> {
                val intent = android.content.Intent(context, com.rizzbot.v2.ui.MainActivity::class.java).apply {
                    putExtra("navigate_to", "premium")
                    addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK or android.content.Intent.FLAG_ACTIVITY_SINGLE_TOP)
                }
                context.startActivity(intent)
                _state.value = BubbleState.RizzButton
            }
            is OverlayEvent.Regenerate -> {
                activeScope.launch {
                    _state.value = BubbleState.Loading
                    orchestrator.generateFromScreenshots(event.direction)
                    val result = orchestrator.result.value
                    _state.value = when (result) {
                        is SuggestionResult.Success -> BubbleState.Expanded(result)
                        is SuggestionResult.Error -> BubbleState.Error(result.message, result.errorType, event.direction)
                        is SuggestionResult.Loading -> BubbleState.Loading
                    }
                }
            }
        }
        eventBus.send(event)
    }
}
