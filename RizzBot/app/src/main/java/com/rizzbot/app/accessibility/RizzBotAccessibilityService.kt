package com.rizzbot.app.accessibility

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.rizzbot.app.accessibility.parser.AisleProfileParser
import com.rizzbot.app.accessibility.parser.AisleScreenParser
import com.rizzbot.app.accessibility.parser.ChatScreenDetector
import com.rizzbot.app.accessibility.parser.LayoutHealthChecker
import com.rizzbot.app.accessibility.parser.ViewTreeDumper
import com.rizzbot.app.accessibility.trigger.SmartTriggerManager
import com.rizzbot.app.overlay.OverlayEvent
import com.rizzbot.app.overlay.OverlayEventBus
import com.rizzbot.app.overlay.OverlayService
import com.rizzbot.app.overlay.manager.BubbleManager
import com.rizzbot.app.util.AnalyticsHelper
import com.rizzbot.app.util.Constants
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class RizzBotAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "RizzBot"
    }

    @Inject lateinit var chatScreenDetector: ChatScreenDetector
    @Inject lateinit var aisleScreenParser: AisleScreenParser
    @Inject lateinit var aisleProfileParser: AisleProfileParser
    @Inject lateinit var layoutHealthChecker: LayoutHealthChecker
    @Inject lateinit var smartTriggerManager: SmartTriggerManager
    @Inject lateinit var overlayEventBus: OverlayEventBus
    @Inject lateinit var bubbleManager: BubbleManager
    @Inject lateinit var profileCacheManager: ProfileCacheManager
    @Inject lateinit var analyticsHelper: AnalyticsHelper

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var isInChatScreen = false
    private var isOnProfilePage = false
    private var hasLoggedViewTree = false // one-time debug dump

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.d(TAG, "AccessibilityService CONNECTED - starting OverlayService")
        startOverlayService()
    }

    private fun startOverlayService() {
        try {
            val intent = Intent(this, OverlayService::class.java)
            startForegroundService(intent)
            Log.d(TAG, "OverlayService started successfully")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start OverlayService: ${e.message}", e)
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return
        val packageName = event.packageName?.toString() ?: return

        // User left Aisle — hide all overlays unconditionally
        if (packageName != Constants.AISLE_PACKAGE) {
            if (event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
                Log.d(TAG, "Left Aisle (switched to $packageName) — hiding overlays")
                isInChatScreen = false
                isOnProfilePage = false
                smartTriggerManager.onChatScreenExited()
                bubbleManager.hide()
            }
            return
        }

        when (event.eventType) {
            AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> handleWindowStateChanged(event)
            AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED -> handleContentChanged()
            else -> {}
        }
    }

    private fun handleWindowStateChanged(event: AccessibilityEvent) {
        val wasInChat = isInChatScreen
        isInChatScreen = chatScreenDetector.isChatScreen(event)
        Log.d(TAG, "WindowStateChanged: wasInChat=$wasInChat, isInChat=$isInChatScreen, class=${event.className}")

        if (wasInChat && !isInChatScreen) {
            Log.d(TAG, "Exited chat screen")
            smartTriggerManager.onChatScreenExited()
            overlayEventBus.tryEmit(OverlayEvent.HideRizzButton)
        }

        if (isInChatScreen) {
            Log.d(TAG, "On chat screen - showing Rizz button")
            overlayEventBus.tryEmit(OverlayEvent.ShowRizzButton)
            setupManualTrigger()
        }
    }

    private fun handleContentChanged() {
        val root = rootInActiveWindow ?: return
        try {
            // One-time debug dump to discover real Aisle view IDs
            if (!hasLoggedViewTree) {
                hasLoggedViewTree = true
                ViewTreeDumper.dump(root, "AisleScreen")
            }

            // Profile page: show manual sync button
            if (aisleProfileParser.isProfilePage(root)) {
                layoutHealthChecker.checkProfile(root)
                if (!isOnProfilePage) {
                    Log.d(TAG, "Profile page detected!")
                    isOnProfilePage = true
                    isInChatScreen = false
                    bubbleManager.hideRizzButton()
                    showProfileSyncButton(root)
                }
                return
            }

            // Left profile page — dismiss any profile sync overlay
            if (isOnProfilePage) {
                isOnProfilePage = false
                bubbleManager.hideProfileOverlay()
            }

            // Chat screen detection (only to show/hide Rizz button)
            if (!isInChatScreen) {
                if (chatScreenDetector.isChatScreen(root)) {
                    layoutHealthChecker.checkChatScreen(root)
                    Log.d(TAG, "Chat screen detected via content change!")
                    isInChatScreen = true
                    overlayEventBus.tryEmit(OverlayEvent.ShowRizzButton)
                    setupManualTrigger()
                }
            }
        } finally {
            root.recycle()
        }
    }

    // --- Manual triggers (user-initiated only) ---

    private fun setupManualTrigger() {
        bubbleManager.onRizzButtonClicked = { handleRizzButtonClick() }
        bubbleManager.onGenerateReplies = { handleGenerateReplies() }
        bubbleManager.onRefreshChat = { handleRefreshChat() }
        bubbleManager.onPasteToInput = { text -> handlePasteToInput(text) }
        bubbleManager.onSyncProfile = { handleSyncProfile() }
        bubbleManager.onRefreshReplies = { handleRefreshReplies() }
        bubbleManager.onNewTopicClicked = { handleNewTopicClick() }
        bubbleManager.onReadFullChat = { handleReadFullChat() }
    }

    private fun handleRizzButtonClick() {
        Log.d(TAG, "Rizz button clicked — showing action menu")
        analyticsHelper.logRizzButtonClicked()

        // Check if profile is synced for this person so menu knows
        val root = rootInActiveWindow ?: return
        try {
            val parsed = aisleScreenParser.parseScreen(root)
            if (parsed != null) {
                val profileInfo = profileCacheManager.getProfile(parsed.personName)?.toPromptString()
                bubbleManager.setHasProfile(profileInfo != null)
            }
        } finally {
            root.recycle()
        }

        bubbleManager.showActionMenu()
    }

    private fun handleGenerateReplies() {
        Log.d(TAG, "Generate replies requested")

        val root = rootInActiveWindow ?: return
        try {
            ViewTreeDumper.dump(root, "ChatOnGenerate")
            layoutHealthChecker.checkChatMessages(root)
            val parsed = aisleScreenParser.parseScreen(root)
            if (parsed != null) {
                Log.d(TAG, "Parsed: person=${parsed.personName}, messages=${parsed.messages.size}")
                val profileInfo = profileCacheManager.getProfile(parsed.personName)?.toPromptString()
                bubbleManager.setHasProfile(profileInfo != null)
                smartTriggerManager.onManualTrigger(parsed.personName, parsed.messages, serviceScope, profileInfo)
            } else {
                Log.e(TAG, "parseScreen returned null!")
            }
        } finally {
            root.recycle()
        }
    }

    private fun handleRefreshChat() {
        Log.d(TAG, "Refresh chat requested")
        val root = rootInActiveWindow
        if (root == null) {
            Log.e(TAG, "handleRefreshChat: rootInActiveWindow is NULL!")
            return
        }
        try {
            val parsed = aisleScreenParser.parseScreen(root)
            if (parsed != null) {
                Log.d(TAG, "Refreshed: person=${parsed.personName}, messages=${parsed.messages.size}")
                overlayEventBus.tryEmit(OverlayEvent.ShowRizzButton)
            } else {
                Log.e(TAG, "handleRefreshChat: parseScreen returned null")
            }
        } finally {
            root.recycle()
        }
    }

    private fun handleRefreshReplies() {
        Log.d(TAG, "Refresh replies requested")
        analyticsHelper.logRefreshReplies()

        val root = rootInActiveWindow ?: return
        try {
            val parsed = aisleScreenParser.parseScreen(root)
            if (parsed != null) {
                Log.d(TAG, "Refreshing replies for ${parsed.personName}")
                val profileInfo = profileCacheManager.getProfile(parsed.personName)?.toPromptString()
                smartTriggerManager.onRefreshReplies(parsed.personName, parsed.messages, serviceScope, profileInfo)
            } else {
                Log.e(TAG, "handleRefreshReplies: parseScreen returned null")
            }
        } finally {
            root.recycle()
        }
    }

    private fun handleNewTopicClick() {
        Log.d(TAG, "New topic / conversation starter requested")
        analyticsHelper.logIcebreakerClicked()

        val root = rootInActiveWindow ?: return
        try {
            val parsed = aisleScreenParser.parseScreen(root)
            if (parsed != null) {
                val profileInfo = profileCacheManager.getProfile(parsed.personName)?.toPromptString()
                smartTriggerManager.onConversationStarterTrigger(parsed.personName, serviceScope, profileInfo)
            } else {
                Log.e(TAG, "handleNewTopicClick: parseScreen returned null")
            }
        } finally {
            root.recycle()
        }
    }

    private fun handleReadFullChat() {
        Log.d(TAG, "Read Full Chat requested — scrolling through chat history")
        overlayEventBus.tryEmit(OverlayEvent.ShowLoading("Reading full chat..."))

        serviceScope.launch(Dispatchers.Default) {
            val root = rootInActiveWindow ?: return@launch
            try {
                val parsed = aisleScreenParser.parseScreenWithScroll(root)
                if (parsed != null) {
                    Log.d(TAG, "Full chat read: person=${parsed.personName}, messages=${parsed.messages.size}")
                    // Just save the messages — don't generate replies
                    smartTriggerManager.onSaveFullChat(parsed.personName, parsed.messages, serviceScope)
                } else {
                    Log.e(TAG, "handleReadFullChat: parseScreenWithScroll returned null")
                    overlayEventBus.tryEmit(OverlayEvent.ShowError("Couldn't read chat"))
                }
            } finally {
                root.recycle()
            }
        }
    }

    // --- Profile sync (manual only) ---

    private fun showProfileSyncButton(root: AccessibilityNodeInfo) {
        val visibleProfile = aisleProfileParser.parseVisibleProfile(root)
        val personName = visibleProfile?.name ?: "this person"
        val isSynced = profileCacheManager.isProfileSynced(personName)
        if (isSynced) {
            bubbleManager.showProfileSynced(personName)
        } else {
            bubbleManager.showProfileSyncButton(personName)
        }
        setupManualTrigger() // Ensure callbacks are wired for profile page too
    }

    private fun handleSyncProfile() {
        Log.d(TAG, "Manual profile sync requested")
        val root = rootInActiveWindow
        if (root == null) {
            Log.e(TAG, "handleSyncProfile: rootInActiveWindow is NULL!")
            return
        }

        val visibleProfile = aisleProfileParser.parseVisibleProfile(root)
        if (visibleProfile == null) {
            Log.e(TAG, "handleSyncProfile: could not parse visible profile")
            root.recycle()
            return
        }

        val personName = visibleProfile.name
        Log.d(TAG, "Syncing profile for: $personName")
        overlayEventBus.tryEmit(OverlayEvent.ShowProfileSyncing(personName))

        serviceScope.launch {
            try {
                val freshRoot = rootInActiveWindow
                if (freshRoot != null) {
                    val fullProfile = aisleProfileParser.scrollAndCollectFullProfile(freshRoot)
                    freshRoot.recycle()

                    if (fullProfile != null) {
                        profileCacheManager.cacheProfile(fullProfile)
                        analyticsHelper.logProfileSynced()
                        Log.d(TAG, "Profile synced for $personName")
                    } else {
                        profileCacheManager.cacheProfile(visibleProfile)
                        Log.d(TAG, "Cached visible profile for $personName")
                    }
                } else {
                    profileCacheManager.cacheProfile(visibleProfile)
                }
                if (isOnProfilePage) {
                    overlayEventBus.emit(OverlayEvent.ShowProfileSynced(personName))
                } else {
                    Log.d(TAG, "Left profile page during sync, skipping overlay")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to sync profile: ${e.message}", e)
                profileCacheManager.cacheProfile(visibleProfile)
                if (isOnProfilePage) {
                    overlayEventBus.tryEmit(OverlayEvent.ShowProfileSynced(personName))
                }
            }
        }
        root.recycle()
    }

    // --- Paste to input ---

    private fun handlePasteToInput(text: String) {
        Log.d(TAG, "Paste to input requested: ${text.take(30)}...")
        val root = rootInActiveWindow
        if (root == null) {
            Log.e(TAG, "handlePasteToInput: rootInActiveWindow is null")
            return
        }
        try {
            val editTexts = mutableListOf<AccessibilityNodeInfo>()
            findEditTexts(root, editTexts)

            if (editTexts.isEmpty()) {
                Log.e(TAG, "handlePasteToInput: no EditText found")
                return
            }

            val inputField = editTexts[0]
            Log.d(TAG, "Found input field: ${inputField.viewIdResourceName}")

            val args = Bundle().apply {
                putCharSequence(
                    AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
                    text
                )
            }
            val success = inputField.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
            Log.d(TAG, "Set text result: $success")

            editTexts.forEach { it.recycle() }
        } finally {
            root.recycle()
        }
    }

    private fun findEditTexts(node: AccessibilityNodeInfo, result: MutableList<AccessibilityNodeInfo>) {
        if (node.isEditable || node.className?.toString()?.contains("EditText") == true) {
            result.add(AccessibilityNodeInfo.obtain(node))
        }
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            findEditTexts(child, result)
            child.recycle()
        }
    }

    override fun onInterrupt() {
        Log.d(TAG, "onInterrupt called")
        smartTriggerManager.onChatScreenExited()
    }

    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "onDestroy called")
        smartTriggerManager.onChatScreenExited()
    }
}
