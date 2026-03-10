package com.rizzbot.v2.overlay.manager

import android.content.Context
import android.graphics.PixelFormat
import android.os.Build
import android.util.Log
import android.view.Gravity
import android.view.WindowManager
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
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
    private var currentDirection: DirectionWithHint? = null
    // When non-null, we're in "add more screenshots" mode and the next bubble tap
    // should append a screenshot for this direction instead of reopening the picker.
    private var pendingAppendDirection: DirectionWithHint? = null
    private var closeTargetView: ComposeView? = null
    private val _isHoveringClose = MutableStateFlow(false)

    init {
        // Default position: right edge, vertically centered
        val dm = context.resources.displayMetrics
        bubbleX = dm.widthPixels - 180 // near right edge
    }

    private val _state = MutableStateFlow<BubbleState>(BubbleState.Hidden)
    val state: StateFlow<BubbleState> = _state.asStateFlow()

    // Public flow for UI to check if bubble is actually visible (not just pref = true)
    val isActuallyShown: StateFlow<Boolean> = MutableStateFlow(false).also { flow ->
        ensureScope().launch {
            _state.collect { bubbleState ->
                flow.value = bubbleState !is BubbleState.Hidden
            }
        }
    }

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

        var initialX = 0
        var initialY = 0
        var initialTouchX = 0f
        var initialTouchY = 0f
        var isDragging = false
        var dragParams: WindowManager.LayoutParams? = null

        view.setOnTouchListener { _, event ->
            // Only allow dragging when we're in bubble mode
            if (_state.value !is BubbleState.RizzButton) {
                return@setOnTouchListener false
            }

            when (event.action) {
                android.view.MotionEvent.ACTION_DOWN -> {
                    val lp = view.layoutParams as? WindowManager.LayoutParams
                        ?: return@setOnTouchListener false

                    dragParams = lp
                    initialX = lp.x
                    initialY = lp.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    isDragging = false
                    // We handle the full gesture (tap or drag) here
                    return@setOnTouchListener true
                }

                android.view.MotionEvent.ACTION_MOVE -> {
                    val lp = dragParams ?: return@setOnTouchListener false
                    val dx = event.rawX - initialTouchX
                    val dy = event.rawY - initialTouchY

                    // Threshold to differentiate a tap from a drag
                    if (!isDragging && (kotlin.math.abs(dx) > 10 || kotlin.math.abs(dy) > 10)) {
                        isDragging = true
                        showCloseTarget()
                    }

                    if (isDragging) {
                        val dm = context.resources.displayMetrics
                        val maxY = dm.heightPixels - view.height

                        lp.x = initialX + dx.toInt()
                        // Clamp Y so it can't go off the top or bottom of the screen
                        lp.y = (initialY + dy.toInt()).coerceIn(0, maxY)

                        bubbleX = lp.x
                        bubbleY = lp.y

                        try {
                            windowManager.updateViewLayout(view, lp)
                        } catch (e: Exception) {
                            Log.w(TAG, "Failed to update layout during drag", e)
                        }

                        checkCloseTargetHover(event.rawX, event.rawY)
                        return@setOnTouchListener true
                    }
                }

                android.view.MotionEvent.ACTION_UP,
                android.view.MotionEvent.ACTION_CANCEL -> {
                    val lp = dragParams

                    if (isDragging && lp != null) {
                        val droppedOnClose = _isHoveringClose.value
                        hideCloseTarget()

                        if (droppedOnClose) {
                            hide()
                        } else {
                            // Snap to nearest Left or Right edge
                            val dm = context.resources.displayMetrics
                            val midX = dm.widthPixels / 2
                            val bubbleCenterX = lp.x + (view.width / 2)
                            val targetX = if (bubbleCenterX < midX) 0 else dm.widthPixels - view.width

                            android.animation.ValueAnimator.ofInt(lp.x, targetX).apply {
                                duration = 200 // Fast, smooth snap
                                interpolator = android.view.animation.DecelerateInterpolator()
                                addUpdateListener { animator ->
                                    val newX = animator.animatedValue as Int
                                    lp.x = newX
                                    bubbleX = newX
                                    try {
                                        windowManager.updateViewLayout(view, lp)
                                    } catch (e: Exception) {
                                        Log.w(TAG, "Failed to update layout during snap", e)
                                    }
                                }
                                start()
                            }
                        }
                        dragParams = null
                        return@setOnTouchListener true
                    } else {
                        // Treat as a simple tap to open the bubble
                        handleEvent(OverlayEvent.ShowBubble)
                        dragParams = null
                        return@setOnTouchListener true
                    }
                }
            }

            false
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
        currentDirection = null
        pendingAppendDirection = null
        hideCloseTarget()

        // Clear service enabled pref so HomeScreen doesn't show stale "active" state
        ensureScope().launch {
            settingsRepository.setServiceEnabled(false)
        }
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

    private fun showCloseTarget() {
        if (closeTargetView != null) return
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            400,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                @Suppress("DEPRECATION")
                WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
        }

        closeTargetView = ComposeView(context).apply {
            setContent {
                val hovering by _isHoveringClose.collectAsState()
                com.rizzbot.v2.overlay.ui.CloseTargetUI(isHovering = hovering)
            }
        }
        windowManager.addView(closeTargetView, params)
    }

    private fun checkCloseTargetHover(rawX: Float, rawY: Float) {
        val dm = context.resources.displayMetrics
        // Create a forgiving 300px (wider) target zone near the bottom center
        val inDropZone =
            rawY > (dm.heightPixels - 500) &&
                rawX > (dm.widthPixels / 2 - 250) &&
                rawX < (dm.widthPixels / 2 + 250)

        if (inDropZone != _isHoveringClose.value) {
            _isHoveringClose.value = inDropZone
            if (inDropZone) {
                // Haptic feedback when user hovers over the close target
                hapticHelper.lightTap()
            }
        }
    }

    private fun hideCloseTarget() {
        closeTargetView?.let {
            try {
                windowManager.removeView(it)
            } catch (e: IllegalArgumentException) {
                Log.w(TAG, "Close target view already removed", e)
            }
        }
        closeTargetView = null
        _isHoveringClose.value = false
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
                        // Restore prior state if any, otherwise show picker
                        val result = orchestrator.result.value
                        val previews = orchestrator.getPreviewBitmaps()
                        _state.value = when {
                            result is SuggestionResult.Success -> BubbleState.Expanded(result)
                            previews.isNotEmpty() -> BubbleState.ScreenshotPreview(
                                previews,
                                currentDirection ?: DirectionWithHint()
                            )
                            else -> BubbleState.DirectionPicker
                        }
                    }
                }
            }
            is OverlayEvent.HideBubble -> hide()
            is OverlayEvent.CaptureRequested -> {
                activeScope.launch {
                    // Clear previous screenshots on fresh capture/retake
                    orchestrator.clearScreenshot()
                    currentDirection = event.direction
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
                currentDirection = event.direction
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
                // We intentionally DO NOT clear screenshots here to maintain state
            }
            is OverlayEvent.CopyReply -> {
                clipboardHelper.copyToClipboard(event.reply)
                hapticHelper.lightTap()
                activeScope.launch {
                    // Backend tracks copy via trackCopy endpoint (sets copied_index in interactions table)
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
            is OverlayEvent.UpgradeTapped -> {
                val usage = hostedRepository.usageState.value
                // If user is not yet premium, send them to the upgrade screen.
                // If they're already premium, just dismiss the error instead of
                // taking them to a screen that says "you're already premium".
                if (!usage.isPremium) {
                    val intent = android.content.Intent(
                        context,
                        com.rizzbot.v2.ui.MainActivity::class.java
                    ).apply {
                        putExtra("navigate_to", "premium")
                        addFlags(
                            android.content.Intent.FLAG_ACTIVITY_NEW_TASK or
                                android.content.Intent.FLAG_ACTIVITY_SINGLE_TOP
                        )
                    }
                    context.startActivity(intent)
                }
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
            is OverlayEvent.ClearAndStartOver -> {
                orchestrator.clearScreenshot()
                currentDirection = null
                pendingAppendDirection = null
                _state.value = BubbleState.DirectionPicker
            }
        }
        eventBus.send(event)
    }
}
