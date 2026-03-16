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
    private var timeoutJob: Job? = null
    private var currentDirection: DirectionWithHint? = null
    // When non-null, we're in "add more screenshots" mode and the next bubble tap
    // should append a screenshot for this direction instead of reopening the picker.
    private var pendingAppendDirection: DirectionWithHint? = null
    private var closeTargetView: ComposeView? = null
    private val _isHoveringClose = MutableStateFlow(false)
    private val _dockOnLeft = MutableStateFlow(false)
    val dockOnLeft: StateFlow<Boolean> = _dockOnLeft.asStateFlow()
    private val _isGalleryMode = MutableStateFlow(false)
    val isGalleryMode: StateFlow<Boolean> = _isGalleryMode.asStateFlow()
    /**
     * When non-null, the user selected a direction while in Gallery mode and we're
     * waiting for the TransparentGalleryActivity result.
     */
    private var pendingGalleryDirection: DirectionWithHint? = null

    init {
        // Default position: right edge, vertically centered
        val dm = context.resources.displayMetrics
        bubbleX = dm.widthPixels - 180 // near right edge
    }

    private val _state = MutableStateFlow<BubbleState>(BubbleState.Hidden)
    val state: StateFlow<BubbleState> = _state.asStateFlow()

    private val _showPaywall = MutableStateFlow(false)
    val showPaywall: StateFlow<Boolean> = _showPaywall.asStateFlow()

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
            // Start state collector for window layout updates and timeout management
            stateCollectorJob = it.launch {
                _state.collect { state ->
                    updateWindowForState(state)
                    handleStateChangeForTimeout(state)
                }
            }
        }
    }

    private fun isFullScreenState(state: BubbleState): Boolean = state.isExpandedState()

    private fun createParams(fullScreen: Boolean): WindowManager.LayoutParams {
        return WindowManager.LayoutParams(
            if (fullScreen) WindowManager.LayoutParams.MATCH_PARENT else WindowManager.LayoutParams.WRAP_CONTENT,
            if (fullScreen) WindowManager.LayoutParams.MATCH_PARENT else WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                @Suppress("DEPRECATION")
                WindowManager.LayoutParams.TYPE_PHONE,
            // Always use FLAG_NOT_FOCUSABLE to prevent stealing keyboard focus from dating apps
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

    /**
     * Handle state changes for session timeout management.
     * When collapsed, start 3-minute timer. When expanded, cancel timer.
     */
    private fun handleStateChangeForTimeout(state: BubbleState) {
        val activeScope = ensureScope()
        
        when {
            state is BubbleState.RizzButton || state is BubbleState.RizzButtonAddMore -> {
                // Collapsed state: Start 3-minute timeout timer
                timeoutJob?.cancel()
                timeoutJob = activeScope.launch {
                    kotlinx.coroutines.delay(3 * 60 * 1000L) // 3 minutes
                    orchestrator.clearAllState()
                    currentDirection = null
                    pendingAppendDirection = null
                    Log.d(TAG, "Session timeout: Cleared all state after 3 minutes of inactivity")
                }
            }
            state.isExpandedState() -> {
                // Expanded state: Cancel timeout (user is actively using the overlay)
                timeoutJob?.cancel()
                timeoutJob = null
            }
        }
    }

    private fun createAndAttachView(): ComposeView {
        val params = createParams(isFullScreenState(_state.value))
        val view = ComposeView(context).apply {
            setContent {
                val showPaywallState by _showPaywall.collectAsState()
                BubbleOverlay(
                    state = _state,
                    usageState = hostedRepository.usageState,
                    dockOnLeft = dockOnLeft,
                    isGalleryMode = isGalleryMode,
                    onEvent = { handleEvent(it) },
                    showPaywall = showPaywallState,
                    onDismissPaywall = { _showPaywall.value = false }
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
            Log.d(TAG, "Touch event: action=${event.action} state=${_state.value}")

            when (event.action) {
                android.view.MotionEvent.ACTION_DOWN -> {
                    val lp = view.layoutParams as? WindowManager.LayoutParams
                        ?: run {
                            Log.w(TAG, "ACTION_DOWN but layoutParams is not WindowManager.LayoutParams")
                            return@setOnTouchListener false
                        }

                    dragParams = lp
                    initialX = lp.x
                    initialY = lp.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    isDragging = false
                    Log.d(
                        TAG,
                        "ACTION_DOWN at raw=(${event.rawX}, ${event.rawY}) lp=(${lp.x}, ${lp.y})"
                    )
                    // We need to consume ACTION_DOWN to track drags, but we'll check state on ACTION_UP
                    // to decide whether to handle the tap or let Compose handle it
                    return@setOnTouchListener true
                }

                android.view.MotionEvent.ACTION_MOVE -> {
                    val lp = dragParams ?: return@setOnTouchListener true
                    val dx = event.rawX - initialTouchX
                    val dy = event.rawY - initialTouchY

                    // Threshold to differentiate a tap from a drag (use dp-scaled threshold)
                    val density = context.resources.displayMetrics.density
                    val dragThreshold = 4f * density // ~4dp
                    if (!isDragging && (kotlin.math.abs(dx) > dragThreshold || kotlin.math.abs(dy) > dragThreshold)) {
                        isDragging = true
                        Log.d(
                            TAG,
                            "Starting drag: dx=$dx dy=$dy threshold=$dragThreshold"
                        )
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
                            Log.d(TAG, "Dragging bubble to x=${lp.x}, y=${lp.y}")
                        } catch (e: Exception) {
                            Log.w(TAG, "Failed to update layout during drag", e)
                        }

                        checkCloseTargetHover(event.rawX, event.rawY)
                    }
                    // Always keep consuming MOVE events while in bubble mode
                    return@setOnTouchListener true
                }

                android.view.MotionEvent.ACTION_UP,
                android.view.MotionEvent.ACTION_CANCEL -> {
                    val lp = dragParams

                    if (isDragging && lp != null) {
                        val droppedOnClose = _isHoveringClose.value
                        Log.d(TAG, "ACTION_UP after drag. droppedOnClose=$droppedOnClose x=${lp.x}, y=${lp.y}")
                        hideCloseTarget()

                        if (droppedOnClose) {
                            hide()
                        } else {
                            // Snap to nearest Left or Right edge with spring animation
                            val dm = context.resources.displayMetrics
                            val midX = dm.widthPixels / 2
                            val bubbleCenterX = lp.x + (view.width / 2)
                            val dockLeft = bubbleCenterX < midX
                            _dockOnLeft.value = dockLeft
                            // Leave some margin so bubble doesn't go completely off-screen
                            val targetX = if (dockLeft) 8 else dm.widthPixels - view.width - 8

                            // Use spring animation for smoother, more natural edge snapping
                            android.animation.ValueAnimator.ofInt(lp.x, targetX).apply {
                                duration = 300 // Slightly longer for smoother feel
                                interpolator = android.view.animation.OvershootInterpolator(0.5f)
                                addUpdateListener { animator ->
                                    val newX = animator.animatedValue as Int
                                    lp.x = newX
                                    bubbleX = newX
                                    try {
                                        windowManager.updateViewLayout(view, lp)
                                        Log.d(TAG, "Snapping bubble to x=$newX, y=${lp.y}")
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
                        // No significant movement: this was a tap
                        dragParams = null
                        val currentState = _state.value
                        val isCollapsedState = currentState is BubbleState.RizzButton || 
                                             currentState is BubbleState.RizzButtonAddMore
                        
                        if (isCollapsedState) {
                            // In collapsed state, we should NOT handle taps here to avoid conflicts.
                            // The RizzButton's onTap handler (via Compose) should handle it.
                            // However, since we consumed ACTION_DOWN, Compose won't receive the event.
                            // So we need to manually trigger the correct behavior: just expand the bubble
                            // WITHOUT checking daily limits or launching MainActivity.
                            // We'll directly set the state to show the picker/expanded view.
                            Log.d(TAG, "ACTION_UP without drag in collapsed state - expanding bubble directly")
                            
                            val appendDirection = pendingAppendDirection
                            if (appendDirection != null) {
                                // We're in "add more screenshots" mode: append another capture
                                pendingAppendDirection = null
                                ensureScope().launch {
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
                        } else {
                            // In full-screen states, handle the tap normally
                            Log.d(TAG, "ACTION_UP without drag in full-screen state - handling tap")
                            handleEvent(OverlayEvent.ShowBubble)
                        }
                        return@setOnTouchListener true
                    }
                }
            }

            // We should never really hit this because we early-return for each action,
            // but keep it here as a safe default.
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
        // Cancel all pending coroutines (LLM calls, tracking, timeout, etc.)
        stateCollectorJob?.cancel()
        stateCollectorJob = null
        timeoutJob?.cancel()
        timeoutJob = null
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
        orchestrator.clearAllState() // Clear all state when service is hidden
        currentDirection = null
        pendingAppendDirection = null
        pendingGalleryDirection = null
        _isGalleryMode.value = false
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
        _state.value = BubbleState.Loading()
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
                com.rizzbot.v2.overlay.ui.components.shared.CloseTargetUI(isHovering = hovering)
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

    /**
     * Entry point for the transparent gallery activity to report back a selected image.
     *
     * @param imageBase64 Base64-encoded JPEG of the selected image, or null if the user cancelled.
     */
    fun handleGalleryResult(imageBase64: String?) {
        val direction = pendingGalleryDirection
        // Always clear pending state first so we don't accidentally reuse it.
        pendingGalleryDirection = null

        if (imageBase64 == null || direction == null) {
            // User cancelled or we lost the pending direction; nothing to do.
            return
        }

        val activeScope = ensureScope()
        activeScope.launch {
            // Enter processing state as soon as we have an image + direction
            _state.value = BubbleState.Loading(isProcessing = true)
            orchestrator.resetResult()
            orchestrator.clearScreenshot()

            orchestrator.generateFromExternalImages(listOf(imageBase64), direction)
            val result = orchestrator.result.value
            _state.value = when (result) {
                is SuggestionResult.Success -> BubbleState.Expanded(result)
                is SuggestionResult.Error -> BubbleState.Error(result.message, result.errorType, direction)
                is SuggestionResult.Loading -> BubbleState.Loading()
            }
        }
    }

    private fun launchTransparentGalleryActivity() {
        // Launch a tiny transparent Activity that owns the system photo picker.
        try {
            val intent = android.content.Intent(
                context,
                com.rizzbot.v2.overlay.gallery.TransparentGalleryActivity::class.java
            ).apply {
                addFlags(
                    android.content.Intent.FLAG_ACTIVITY_NEW_TASK or
                        android.content.Intent.FLAG_ACTIVITY_CLEAR_TOP
                )
            }
            context.startActivity(intent)
        } catch (e: Exception) {
            Log.w(TAG, "Failed to launch TransparentGalleryActivity", e)
            // Fall back to normal flow by clearing pending state.
            pendingGalleryDirection = null
        }
    }

    private fun launchPaywallIntent() {
        // Launch MainActivity with intent to show paywall
        try {
            val intent = android.content.Intent(context, com.rizzbot.v2.ui.MainActivity::class.java).apply {
                action = "SHOW_PAYWALL"
                flags = android.content.Intent.FLAG_ACTIVITY_NEW_TASK or
                        android.content.Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            context.startActivity(intent)
        } catch (e: Exception) {
            Log.w(TAG, "Failed to launch MainActivity for paywall", e)
        }
    }

    private fun handleEvent(event: OverlayEvent) {
        val activeScope = ensureScope()
        when (event) {
            is OverlayEvent.ShowBubble -> {
                // Always show the direction picker when bubble is tapped
                // Daily limits are checked later when user tries to generate replies
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
            is OverlayEvent.HideBubble -> hide()
            is OverlayEvent.SetGalleryMode -> {
                _isGalleryMode.value = event.isGalleryMode
            }
            is OverlayEvent.CaptureRequested -> {
                if (_isGalleryMode.value) {
                    // Save direction and hand off to a transparent gallery activity.
                    pendingGalleryDirection = event.direction
                    launchTransparentGalleryActivity()
                } else {
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
            }
            is OverlayEvent.ConfirmScreenshot -> {
                val usage = hostedRepository.usageState.value
                val isGodMode = usage.tier == "premium" || usage.tier == "god_mode"
                val hasRepliesLeft = usage.dailyUsed < usage.dailyLimit || usage.dailyLimit == 0
                
                if (!isGodMode && !hasRepliesLeft) {
                    // User hit their daily limit - redirect to paywall
                    launchPaywallIntent()
                    // Collapse the bubble
                    _state.value = BubbleState.RizzButton
                } else {
                    activeScope.launch {
                        _state.value = BubbleState.Loading()
                        orchestrator.generateFromScreenshots(event.direction)
                        val result = orchestrator.result.value
                        _state.value = when (result) {
                            is SuggestionResult.Success -> BubbleState.Expanded(result)
                            is SuggestionResult.Error -> BubbleState.Error(result.message, result.errorType, event.direction)
                            is SuggestionResult.Loading -> BubbleState.Loading()
                        }
                    }
                }
            }
            is OverlayEvent.AddMoreScreenshots -> {
                // Put the user back into bubble mode; the next tap on the bubble
                // will capture an additional screenshot for this direction.
                pendingAppendDirection = event.direction
                currentDirection = event.direction
                _state.value = BubbleState.RizzButtonAddMore
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
            is OverlayEvent.RemoveScreenshot -> {
                activeScope.launch {
                    orchestrator.removeScreenshotAt(event.index)
                    val previewBitmaps = orchestrator.getPreviewBitmaps()
                    if (previewBitmaps.isNotEmpty()) {
                        _state.value = BubbleState.ScreenshotPreview(previewBitmaps, event.direction)
                    } else {
                        _state.value = BubbleState.DirectionPicker
                    }
                }
            }
            is OverlayEvent.DismissSuggestions -> {
                // Remove aggressive collapse wiping - keep data alive for "peeking"
                // The 3-minute timeout will handle stale data cleanup
                pendingAppendDirection = null
                _state.value = BubbleState.RizzButton
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
                    
                    // Task Complete Auto-Wipe: Keep UI open for 1.5 seconds so they see success state,
                    // then collapse the bubble AND wipe all state (they're moving on)
                    kotlinx.coroutines.delay(1500L)
                    orchestrator.clearAllState()
                    currentDirection = null
                    pendingAppendDirection = null
                    timeoutJob?.cancel() // Cancel timeout since we're manually clearing
                    timeoutJob = null
                    _state.value = BubbleState.RizzButton
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
                // If user is not yet premium, launch MainActivity to show paywall
                // ModalBottomSheet doesn't work in overlay windows, so we launch the Activity instead
                if (!usage.isPremium) {
                    launchPaywallIntent()
                    // Collapse the bubble - user will see paywall in MainActivity
                    _state.value = BubbleState.RizzButton
                } else {
                    // Already premium, just dismiss
                    _state.value = BubbleState.RizzButton
                }
            }
            is OverlayEvent.Regenerate -> {
                val usage = hostedRepository.usageState.value
                val isGodMode = usage.tier == "premium" || usage.tier == "god_mode"
                val hasRepliesLeft = usage.dailyUsed < usage.dailyLimit || usage.dailyLimit == 0
                
                if (!isGodMode && !hasRepliesLeft) {
                    // User hit their daily limit - collapse FIRST, then redirect to paywall
                    _state.value = BubbleState.RizzButton
                    orchestrator.resetResult()
                    currentDirection = null
                    pendingAppendDirection = null
                    // Small delay to ensure collapse animation completes
                    activeScope.launch {
                        kotlinx.coroutines.delay(100)
                        launchPaywallIntent()
                    }
                } else {
                    activeScope.launch {
                        _state.value = BubbleState.Loading()
                        orchestrator.generateFromScreenshots(event.direction)
                        val result = orchestrator.result.value
                        _state.value = when (result) {
                            is SuggestionResult.Success -> BubbleState.Expanded(result)
                            is SuggestionResult.Error -> BubbleState.Error(result.message, result.errorType, event.direction)
                            is SuggestionResult.Loading -> BubbleState.Loading()
                        }
                    }
                }
            }
            is OverlayEvent.ClearAndStartOver -> {
                // Manual clear: User wants to start over (e.g., moved to new chat without copying)
                orchestrator.clearAllState()
                currentDirection = null
                pendingAppendDirection = null
                timeoutJob?.cancel() // Cancel timeout since we're manually clearing
                timeoutJob = null
                _state.value = BubbleState.DirectionPicker
            }
            is OverlayEvent.SetKeyboardFocus -> {
                val view = composeView ?: return
                val lp = view.layoutParams as? WindowManager.LayoutParams ?: return
                if (event.enabled) {
                    lp.flags = lp.flags and WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE.inv()
                } else {
                    lp.flags = lp.flags or WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                }
                try {
                    windowManager.updateViewLayout(view, lp)
                } catch (e: Exception) {
                    Log.w(TAG, "Failed to update focusable flag", e)
                }
            }
            is OverlayEvent.Back -> {
                val previews = orchestrator.getPreviewBitmaps()
                when (_state.value) {
                    is BubbleState.ScreenshotPreview -> {
                        // From capture, back goes to a clean start.
                        orchestrator.clearScreenshot()
                        currentDirection = null
                        pendingAppendDirection = null
                        _state.value = BubbleState.DirectionPicker
                    }
                    is BubbleState.Loading,
                    is BubbleState.Expanded,
                    is BubbleState.Error -> {
                        // From replies/error/loading, prefer going back to capture if possible.
                        if (previews.isNotEmpty()) {
                            val direction = currentDirection ?: DirectionWithHint()
                            _state.value = BubbleState.ScreenshotPreview(previews, direction)
                        } else {
                            _state.value = BubbleState.DirectionPicker
                        }
                    }
                    else -> {
                        // From picker or anything else, minimize back to the small bubble.
                        _state.value = BubbleState.RizzButton
                    }
                }
            }
        }
        eventBus.send(event)
    }
}
