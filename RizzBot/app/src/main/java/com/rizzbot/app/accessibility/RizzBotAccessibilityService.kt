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
import com.rizzbot.app.accessibility.parser.ViewTreeDumper
import com.rizzbot.app.accessibility.trigger.SmartTriggerManager
import com.rizzbot.app.domain.model.TonePreference
import com.rizzbot.app.overlay.OverlayEvent
import com.rizzbot.app.overlay.OverlayEventBus
import com.rizzbot.app.overlay.OverlayService
import com.rizzbot.app.overlay.manager.BubbleManager
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
    @Inject lateinit var smartTriggerManager: SmartTriggerManager
    @Inject lateinit var overlayEventBus: OverlayEventBus
    @Inject lateinit var bubbleManager: BubbleManager
    @Inject lateinit var profileCacheManager: ProfileCacheManager

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

        if (packageName != Constants.AISLE_PACKAGE) return

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
            // Check logcat: adb logcat -s RizzBot:D
            if (!hasLoggedViewTree) {
                hasLoggedViewTree = true
                ViewTreeDumper.dump(root, "AisleScreen")
            }

            // Profile page: show manual sync button (call bubbleManager directly to avoid event bus dropping)
            if (aisleProfileParser.isProfilePage(root)) {
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
        bubbleManager.onRefreshChat = { handleRefreshChat() }
        bubbleManager.onToneSelected = { toneName -> handleToneSelected(toneName) }
        bubbleManager.onPasteToInput = { text -> handlePasteToInput(text) }
        bubbleManager.onSyncProfile = { handleSyncProfile() }
        bubbleManager.onRefreshReplies = { handleRefreshReplies() }
        bubbleManager.onRizzMenuRequested = { handleRizzMenuRequested() }
        bubbleManager.onIcebreakerClicked = { handleIcebreakerClick() }
    }

    private fun handleRizzButtonClick() {
        Log.d(TAG, "Rizz button clicked! Parsing screen on-demand...")
        val root = rootInActiveWindow
        if (root == null) {
            Log.e(TAG, "rootInActiveWindow is NULL!")
            return
        }
        try {
            val parsed = aisleScreenParser.parseScreen(root)
            if (parsed != null) {
                Log.d(TAG, "Parsed: person=${parsed.personName}, messages=${parsed.messages.size}")
                val profileInfo = profileCacheManager.getProfile(parsed.personName)?.toPromptString()
                smartTriggerManager.onManualTrigger(parsed.personName, parsed.messages, serviceScope, profileInfo = profileInfo)
            } else {
                Log.e(TAG, "parseScreen returned null!")
            }
        } finally {
            root.recycle()
        }
    }

    private fun handleToneSelected(toneName: String) {
        Log.d(TAG, "Tone selected: $toneName")
        val tone = try {
            TonePreference.valueOf(toneName)
        } catch (_: Exception) {
            Log.e(TAG, "Unknown tone: $toneName, defaulting to FLIRTY")
            TonePreference.FLIRTY
        }

        val root = rootInActiveWindow ?: return
        try {
            val parsed = aisleScreenParser.parseScreen(root)
            if (parsed != null) {
                Log.d(TAG, "Generating reply with tone=${tone.label} for ${parsed.personName}, msgs=${parsed.messages.size}")
                val profileInfo = profileCacheManager.getProfile(parsed.personName)?.toPromptString()
                smartTriggerManager.onManualTrigger(parsed.personName, parsed.messages, serviceScope, tone, profileInfo)
            } else {
                Log.e(TAG, "handleToneSelected: parseScreen returned null")
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
        val root = rootInActiveWindow
        if (root == null) {
            Log.e(TAG, "handleRefreshReplies: rootInActiveWindow is NULL!")
            return
        }
        try {
            val parsed = aisleScreenParser.parseScreen(root)
            if (parsed != null) {
                Log.d(TAG, "Refreshing replies for ${parsed.personName}")
                val profileInfo = profileCacheManager.getProfile(parsed.personName)?.toPromptString()
                smartTriggerManager.onRefreshReplies(parsed.personName, parsed.messages, serviceScope, profileInfo = profileInfo)
            } else {
                Log.e(TAG, "handleRefreshReplies: parseScreen returned null")
            }
        } finally {
            root.recycle()
        }
    }

    private fun handleRizzMenuRequested() {
        Log.d(TAG, "Rizz menu requested - checking profile availability")
        val root = rootInActiveWindow ?: return
        try {
            val parsed = aisleScreenParser.parseScreen(root)
            val personName = parsed?.personName
            val hasProfile = personName != null && profileCacheManager.isProfileSynced(personName)
            Log.d(TAG, "Showing RizzMenu: person=$personName, hasProfile=$hasProfile")
            bubbleManager.showRizzMenu(hasProfile)
        } finally {
            root.recycle()
        }
    }

    private fun handleIcebreakerClick() {
        Log.d(TAG, "Icebreaker requested!")
        val root = rootInActiveWindow ?: return
        try {
            val parsed = aisleScreenParser.parseScreen(root)
            if (parsed != null) {
                val profileInfo = profileCacheManager.getProfile(parsed.personName)?.toPromptString()
                if (profileInfo != null) {
                    smartTriggerManager.onIcebreakerTrigger(parsed.personName, serviceScope, profileInfo)
                } else {
                    Log.e(TAG, "handleIcebreakerClick: no profile found for ${parsed.personName}")
                }
            } else {
                Log.e(TAG, "handleIcebreakerClick: parseScreen returned null")
            }
        } finally {
            root.recycle()
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
                        Log.d(TAG, "Profile synced for $personName")
                    } else {
                        profileCacheManager.cacheProfile(visibleProfile)
                        Log.d(TAG, "Cached visible profile for $personName")
                    }
                } else {
                    profileCacheManager.cacheProfile(visibleProfile)
                }
                // Only show synced overlay if still on profile page
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
