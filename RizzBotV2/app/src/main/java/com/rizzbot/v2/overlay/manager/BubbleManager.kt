package com.rizzbot.v2.overlay.manager

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.animation.ValueAnimator
import android.content.Context
import android.graphics.PixelFormat
import android.os.Build
import android.util.Log
import android.view.Gravity
import android.view.MotionEvent
import android.view.WindowManager
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.platform.ComposeView
import androidx.lifecycle.setViewTreeLifecycleOwner
import androidx.savedstate.setViewTreeSavedStateRegistryOwner
import com.rizzbot.v2.capture.ScreenCaptureOrchestrator
import com.rizzbot.v2.domain.model.DirectionWithHint
import com.rizzbot.v2.domain.model.TierQuota
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.overlay.OverlayEvent
import com.rizzbot.v2.overlay.OverlayEventBus
import com.rizzbot.v2.overlay.OverlayLifecycleOwner
import com.rizzbot.v2.overlay.ui.BubbleOverlay
import com.rizzbot.v2.util.ClipboardHelper
import com.rizzbot.v2.util.HapticHelper
import com.rizzbot.v2.BuildConfig
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

private const val TAG = "BubbleManager"

/** Matches snap-to-edge X inset in [handleCollapsedOverlayMotionEvent]. */
private const val BUBBLE_EDGE_MARGIN_PX = 8

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
    private var bubbleX: Int = 0
    private var bubbleY: Int = 0
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

    /** Never cancelled in [hide]; keeps [isActuallyShown] in sync with [_state]. */
    private val bubbleFlowScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    private val _mergeInFlight = MutableStateFlow(false)

    /**
     * Vision API in progress ([SuggestionResult.Loading]) or merge resolution in flight.
     * Used to keep the overlay collapsed with a pulsing bubble during work, and to show
     * the full loading panel + bubble if the user opens the overlay mid-request.
     */
    val overlayAsyncWorkInFlight: StateFlow<Boolean> = combine(
        orchestrator.result,
        _mergeInFlight
    ) { result, merging ->
        result is SuggestionResult.Loading || merging
    }.stateIn(bubbleFlowScope, SharingStarted.Eagerly, false)

    /** Avoid redundant [WindowManager.updateViewLayout] when only in-overlay content changes. */
    private var lastAppliedExpandedLayout: Boolean? = null

    private var dragInitialX = 0
    private var dragInitialY = 0
    private var dragInitialTouchX = 0f
    private var dragInitialTouchY = 0f
    private var isDraggingBubble = false
    private var dragLayoutParams: WindowManager.LayoutParams? = null
    private var bubbleSnapAnimator: ValueAnimator? = null

    init {
        applyDefaultBubblePositionTopRight()
    }

    private val _state = MutableStateFlow<BubbleState>(BubbleState.Hidden)
    val state: StateFlow<BubbleState> = _state.asStateFlow()


    // Public flow for UI to check if bubble is actually visible (not just pref = true).
    // Must not use [ensureScope]: that scope is cancelled in [hide] and would stop updates.
    val isActuallyShown: StateFlow<Boolean> = _state
        .map { bubbleState -> bubbleState !is BubbleState.Hidden }
        .stateIn(bubbleFlowScope, SharingStarted.Eagerly, false)

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

    private fun cancelBubbleSnapAnimation() {
        bubbleSnapAnimator?.cancel()
        bubbleSnapAnimator = null
    }

    /**
     * Drag / tap for the collapsed bubble window. Driven from Compose via [pointerInteropFilter]
     * so [MotionEvent.rawX]/[MotionEvent.rawY] match the bottom close zone logic.
     */
    private fun handleCollapsedOverlayMotionEvent(view: ComposeView, event: MotionEvent): Boolean {
        if (BuildConfig.DEBUG) {
            Log.d(TAG, "Touch event: action=${event.action} state=${_state.value}")
        }

        when (event.action) {
            MotionEvent.ACTION_DOWN -> {
                cancelBubbleSnapAnimation()
                val lp = view.layoutParams as? WindowManager.LayoutParams
                    ?: run {
                        Log.w(TAG, "ACTION_DOWN but layoutParams is not WindowManager.LayoutParams")
                        return false
                    }

                dragLayoutParams = lp
                dragInitialX = lp.x
                dragInitialY = lp.y
                dragInitialTouchX = event.rawX
                dragInitialTouchY = event.rawY
                isDraggingBubble = false
                Log.d(
                    TAG,
                    "ACTION_DOWN at raw=(${event.rawX}, ${event.rawY}) lp=(${lp.x}, ${lp.y})"
                )
                return true
            }

            MotionEvent.ACTION_MOVE -> {
                val lp = dragLayoutParams ?: return true
                val dx = event.rawX - dragInitialTouchX
                val dy = event.rawY - dragInitialTouchY

                val density = context.resources.displayMetrics.density
                val dragThreshold = 4f * density
                if (!isDraggingBubble &&
                    (kotlin.math.abs(dx) > dragThreshold || kotlin.math.abs(dy) > dragThreshold)
                ) {
                    isDraggingBubble = true
                    Log.d(TAG, "Starting drag: dx=$dx dy=$dy threshold=$dragThreshold")
                    showCloseTarget()
                }

                if (isDraggingBubble) {
                    val dm = context.resources.displayMetrics
                    val maxX = (dm.widthPixels - view.width).coerceAtLeast(0)
                    val maxY = (dm.heightPixels - view.height).coerceAtLeast(0)

                    lp.x = (dragInitialX + dx.toInt()).coerceIn(0, maxX)
                    lp.y = (dragInitialY + dy.toInt()).coerceIn(0, maxY)

                    bubbleX = lp.x
                    bubbleY = lp.y

                    try {
                        windowManager.updateViewLayout(view, lp)
                    } catch (e: Exception) {
                        Log.w(TAG, "Failed to update layout during drag", e)
                    }

                    checkCloseTargetHover(event.rawX, event.rawY)
                }
                return true
            }

            MotionEvent.ACTION_UP,
            MotionEvent.ACTION_CANCEL -> {
                val lp = dragLayoutParams

                if (isDraggingBubble && lp != null) {
                    val droppedOnClose = _isHoveringClose.value
                    Log.d(TAG, "ACTION_UP after drag. droppedOnClose=$droppedOnClose x=${lp.x}, y=${lp.y}")
                    hideCloseTarget()

                    if (droppedOnClose) {
                        hide()
                    } else {
                        val dm = context.resources.displayMetrics
                        val midX = dm.widthPixels / 2
                        val bubbleCenterX = lp.x + (view.width / 2)
                        val dockLeft = bubbleCenterX < midX
                        _dockOnLeft.value = dockLeft
                        val targetX = if (dockLeft) BUBBLE_EDGE_MARGIN_PX
                        else dm.widthPixels - view.width - BUBBLE_EDGE_MARGIN_PX

                        cancelBubbleSnapAnimation()
                        bubbleSnapAnimator = ValueAnimator.ofInt(lp.x, targetX).apply {
                            duration = 300
                            interpolator = android.view.animation.OvershootInterpolator(0.5f)
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
                            addListener(object : AnimatorListenerAdapter() {
                                override fun onAnimationEnd(animation: Animator) {
                                    if (bubbleSnapAnimator === animation) bubbleSnapAnimator = null
                                }

                                override fun onAnimationCancel(animation: Animator) {
                                    if (bubbleSnapAnimator === animation) bubbleSnapAnimator = null
                                }
                            })
                            start()
                        }
                    }
                    dragLayoutParams = null
                    isDraggingBubble = false
                    return true
                } else {
                    dragLayoutParams = null
                    isDraggingBubble = false
                    val currentState = _state.value
                    val isCollapsedState = currentState is BubbleState.RizzButton ||
                        currentState is BubbleState.RizzButtonAddMore

                    if (isCollapsedState) {
                        Log.d(TAG, "ACTION_UP without drag in collapsed state - expanding bubble directly")

                        val appendDirection = pendingAppendDirection
                        if (appendDirection != null) {
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
                                        is SuggestionResult.RequiresUserConfirmation -> BubbleState.RequiresUserConfirmation(result.suggestedMatch)
                                        else -> BubbleState.Error("Screenshot capture failed", SuggestionResult.ErrorType.UNKNOWN)
                                    }
                                }
                            }
                        } else {
                            val result = orchestrator.result.value
                            val previews = orchestrator.getPreviewBitmaps()
                            _state.value = when {
                                _mergeInFlight.value -> BubbleState.Loading()
                                result is SuggestionResult.Success -> BubbleState.Expanded(result)
                                result is SuggestionResult.RequiresUserConfirmation -> BubbleState.RequiresUserConfirmation(result.suggestedMatch)
                                result is SuggestionResult.Loading -> BubbleState.Loading()
                                previews.isNotEmpty() -> BubbleState.ScreenshotPreview(
                                    previews,
                                    currentDirection ?: DirectionWithHint()
                                )
                                else -> BubbleState.DirectionPicker
                            }
                        }
                    } else {
                        Log.d(TAG, "ACTION_UP without drag in full-screen state - handling tap")
                        handleEvent(OverlayEvent.ShowBubble)
                    }
                    return true
                }
            }
        }

        return false
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
        val expanded = isFullScreenState(state)
        if (lastAppliedExpandedLayout == expanded) return
        lastAppliedExpandedLayout = expanded
        val params = createParams(expanded)
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
                BubbleOverlay(
                    state = _state,
                    usageState = hostedRepository.usageState,
                    dockOnLeft = dockOnLeft,
                    isGalleryMode = isGalleryMode,
                    asyncWorkInFlight = overlayAsyncWorkInFlight,
                    onEvent = { handleEvent(it) },
                    onCollapsedOverlayMotionEvent = { event -> handleCollapsedOverlayMotionEvent(this@apply, event) },
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

        // Service activation: always dock top-right (not a stale X/Y from a prior session).
        applyDefaultBubblePositionTopRight()

        ensureScope()
        lifecycleOwner.onCreate()
        lifecycleOwner.onResume()
        composeView = createAndAttachView()

        if (_state.value is BubbleState.Hidden) {
            _state.value = BubbleState.RizzButton
        }

        // After layout, snap X using real width so the bubble hugs the right edge.
        composeView?.post {
            snapCollapsedBubbleToTopRight()
        }
    }

    fun hide() {
        cancelBubbleSnapAnimation()
        dragLayoutParams = null
        isDraggingBubble = false
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
        lastAppliedExpandedLayout = null
        _state.value = BubbleState.Hidden
        orchestrator.clearAllState() // Clear all state when service is hidden
        currentDirection = null
        pendingAppendDirection = null
        pendingGalleryDirection = null
        _isGalleryMode.value = false
        _mergeInFlight.value = false
        hideCloseTarget()

        resetBubblePositionForNextShow()

        // Clear service enabled pref so HomeScreen doesn't show stale "active" state
        ensureScope().launch {
            settingsRepository.setServiceEnabled(false)
        }
    }

    /**
     * Default / post-[hide] position: top-right (status bar + inset), dock hints on the right.
     * Uses an estimated window width until the real layout is known.
     */
    private fun applyDefaultBubblePositionTopRight() {
        val dm = context.resources.displayMetrics
        _dockOnLeft.value = false
        val estimatedWidth = (220 * dm.density).toInt().coerceAtLeast(160)
        bubbleX = (dm.widthPixels - estimatedWidth - BUBBLE_EDGE_MARGIN_PX)
            .coerceAtLeast(BUBBLE_EDGE_MARGIN_PX)
        val statusBarId = context.resources.getIdentifier("status_bar_height", "dimen", "android")
        val statusBarH = if (statusBarId > 0) {
            context.resources.getDimensionPixelSize(statusBarId)
        } else {
            (24 * dm.density).toInt()
        }
        bubbleY = (statusBarH + (12 * dm.density).toInt()).coerceAtLeast(0)
    }

    private fun resetBubblePositionForNextShow() {
        applyDefaultBubblePositionTopRight()
    }

    /**
     * Precise top-right dock using measured overlay size (collapsed bubble only).
     */
    private fun snapCollapsedBubbleToTopRight(layoutRetriesLeft: Int = 8) {
        val view = composeView ?: return
        if (isFullScreenState(_state.value)) return
        if (view.width <= 0) {
            if (layoutRetriesLeft > 0) {
                view.post { snapCollapsedBubbleToTopRight(layoutRetriesLeft - 1) }
            }
            return
        }
        val dm = context.resources.displayMetrics
        val lp = view.layoutParams as? WindowManager.LayoutParams ?: return
        val newX = (dm.widthPixels - view.width - BUBBLE_EDGE_MARGIN_PX)
            .coerceAtLeast(BUBBLE_EDGE_MARGIN_PX)
        val statusBarId = context.resources.getIdentifier("status_bar_height", "dimen", "android")
        val statusBarH = if (statusBarId > 0) {
            context.resources.getDimensionPixelSize(statusBarId)
        } else {
            (24 * dm.density).toInt()
        }
        val newY = (statusBarH + (12 * dm.density).toInt()).coerceAtLeast(0)
        val maxY = (dm.heightPixels - view.height).coerceAtLeast(0)
        lp.x = newX
        lp.y = newY.coerceIn(0, maxY)
        bubbleX = lp.x
        bubbleY = lp.y
        _dockOnLeft.value = false
        try {
            windowManager.updateViewLayout(view, lp)
        } catch (e: Exception) {
            Log.w(TAG, "snapCollapsedBubbleToTopRight failed", e)
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
        lastAppliedExpandedLayout = null
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
            // Required: standalone overlay windows have no Activity; Compose needs these for recomposer setup.
            setViewTreeLifecycleOwner(lifecycleOwner)
            setViewTreeSavedStateRegistryOwner(lifecycleOwner)
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
     * Removes the overlay window so system UI (e.g. photo picker) is not drawn underneath
     * [TYPE_APPLICATION_OVERLAY]. Restored via [ensureComposeOverlayAttached] from
     * [handleGalleryResult] or failed launch.
     */
    private fun suspendOverlayForGalleryPicker() {
        hideCloseTarget()
        composeView?.let {
            try {
                windowManager.removeView(it)
            } catch (e: IllegalArgumentException) {
                Log.w(TAG, "Overlay already removed for gallery picker", e)
            }
        }
        composeView = null
        lastAppliedExpandedLayout = null
    }

    private fun ensureComposeOverlayAttached() {
        if (composeView == null) {
            composeView = createAndAttachView()
        }
    }

    /**
     * Entry point for the transparent gallery activity to report back a selected image.
     *
     * @param imageBase64 Base64-encoded JPEG of the selected image, or null if the user cancelled.
     */
    fun handleGalleryResult(imageBase64: String?) {
        val direction = pendingGalleryDirection
        pendingGalleryDirection = null

        if (_state.value is BubbleState.Hidden) {
            return
        }

        ensureComposeOverlayAttached()

        if (imageBase64 == null) {
            if (direction != null) {
                _state.value = BubbleState.DirectionPicker
            }
            return
        }
        if (direction == null) {
            return
        }

        val activeScope = ensureScope()
        activeScope.launch {
            _state.value = BubbleState.RizzButton
            orchestrator.resetResult()
            orchestrator.clearScreenshot()

            orchestrator.generateFromExternalImages(listOf(imageBase64), direction)
            val result = orchestrator.result.value
            _state.value = when (result) {
                is SuggestionResult.Success -> BubbleState.Expanded(result)
                is SuggestionResult.Error -> BubbleState.Error(result.message, result.errorType, direction)
                is SuggestionResult.RequiresUserConfirmation -> BubbleState.RequiresUserConfirmation(result.suggestedMatch)
                is SuggestionResult.Loading -> BubbleState.Loading()
                is SuggestionResult.Idle -> BubbleState.DirectionPicker
            }
        }
    }

    private fun launchTransparentGalleryActivity() {
        try {
            suspendOverlayForGalleryPicker()
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
            pendingGalleryDirection = null
            ensureComposeOverlayAttached()
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
                                is SuggestionResult.RequiresUserConfirmation -> BubbleState.RequiresUserConfirmation(result.suggestedMatch)
                                else -> BubbleState.Error("Screenshot capture failed", SuggestionResult.ErrorType.UNKNOWN)
                            }
                        }
                    }
                } else {
                    // Restore prior state if any, otherwise show picker
                    val result = orchestrator.result.value
                    val previews = orchestrator.getPreviewBitmaps()
                    _state.value = when {
                        _mergeInFlight.value -> BubbleState.Loading()
                        result is SuggestionResult.Success -> BubbleState.Expanded(result)
                        result is SuggestionResult.RequiresUserConfirmation -> BubbleState.RequiresUserConfirmation(result.suggestedMatch)
                        result is SuggestionResult.Loading -> BubbleState.Loading()
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
                val hasRepliesLeft =
                    TierQuota.isUnlimited(usage.dailyLimit) ||
                        usage.dailyUsed < usage.dailyLimit
                
                if (!isGodMode && !hasRepliesLeft) {
                    // User hit their daily limit - redirect to paywall
                    launchPaywallIntent()
                    // Collapse the bubble
                    _state.value = BubbleState.RizzButton
                } else {
                    activeScope.launch {
                        _state.value = BubbleState.RizzButton
                        orchestrator.generateFromScreenshots(event.direction)
                        val result = orchestrator.result.value
                        _state.value = when (result) {
                            is SuggestionResult.Success -> BubbleState.Expanded(result)
                            is SuggestionResult.Error -> BubbleState.Error(result.message, result.errorType, event.direction)
                            is SuggestionResult.RequiresUserConfirmation -> BubbleState.RequiresUserConfirmation(result.suggestedMatch)
                            is SuggestionResult.Loading -> BubbleState.Loading()
                            is SuggestionResult.Idle -> BubbleState.Error(
                                "Something went wrong",
                                SuggestionResult.ErrorType.UNKNOWN,
                                event.direction
                            )
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
                            is SuggestionResult.RequiresUserConfirmation -> BubbleState.RequiresUserConfirmation(result.suggestedMatch)
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
            is OverlayEvent.ConfirmMerge -> {
                val payload = (_state.value as? BubbleState.RequiresUserConfirmation)?.payload
                if (payload == null) {
                    Log.w(TAG, "ConfirmMerge ignored: no pending confirmation state")
                    return
                }

                activeScope.launch {
                    val direction = currentDirection ?: DirectionWithHint()
                    _state.value = BubbleState.RizzButton
                    _mergeInFlight.value = true
                    try {
                        val result = hostedRepository.resolveConversationMerge(
                            suggestedConversationId = payload.conversationId,
                            isMatch = event.isMatch,
                            newOcrText = payload.personName
                        )

                        _state.value = when (result) {
                            is SuggestionResult.Success -> BubbleState.Expanded(result)
                            is SuggestionResult.Error -> BubbleState.Error(
                                message = result.message,
                                errorType = result.errorType,
                                direction = direction
                            )
                            is SuggestionResult.RequiresUserConfirmation -> BubbleState.RequiresUserConfirmation(
                                payload = result.suggestedMatch
                            )
                            is SuggestionResult.Loading -> BubbleState.Loading()
                            is SuggestionResult.Idle -> BubbleState.Error(
                                "Something went wrong",
                                SuggestionResult.ErrorType.UNKNOWN,
                                direction
                            )
                        }
                    } finally {
                        _mergeInFlight.value = false
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
                val hasRepliesLeft =
                    TierQuota.isUnlimited(usage.dailyLimit) ||
                        usage.dailyUsed < usage.dailyLimit
                
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
                        _state.value = BubbleState.RizzButton
                        orchestrator.generateFromScreenshots(event.direction)
                        val result = orchestrator.result.value
                        _state.value = when (result) {
                            is SuggestionResult.Success -> BubbleState.Expanded(result)
                            is SuggestionResult.Error -> BubbleState.Error(result.message, result.errorType, event.direction)
                            is SuggestionResult.RequiresUserConfirmation -> BubbleState.RequiresUserConfirmation(result.suggestedMatch)
                            is SuggestionResult.Loading -> BubbleState.Loading()
                            is SuggestionResult.Idle -> BubbleState.Error(
                                "Something went wrong",
                                SuggestionResult.ErrorType.UNKNOWN,
                                event.direction
                            )
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
                    is BubbleState.RequiresUserConfirmation,
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
