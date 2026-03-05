package com.rizzbot.app.accessibility.parser

import android.util.Log
import android.view.accessibility.AccessibilityNodeInfo
import com.rizzbot.app.util.AnalyticsHelper
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Monitors target app accessibility layouts for changes.
 * When a target app updates and renames/removes view IDs we depend on,
 * this detects it and reports via Firebase Crashlytics (non-fatal) + Analytics.
 *
 * Per-app ID templates are maintained manually and updated when warnings occur.
 * The parsers have structural fallbacks so the app won't crash,
 * but accuracy may degrade. Crashlytics alerts us to update the IDs.
 */
@Singleton
class LayoutHealthChecker @Inject constructor(
    private val analyticsHelper: AnalyticsHelper
) {

    /**
     * Custom exception for Crashlytics grouping — each layout change
     * appears as a distinct non-fatal issue in the dashboard.
     */
    class LayoutChangeException(message: String) : Exception(message)

    companion object {
        private const val TAG = "RizzBot.LayoutHealth"
        private const val APP_NAME = "aisle"

        // Critical IDs that our parsers depend on — update these when Aisle changes layout
        private val CHAT_SCREEN_IDS = listOf(
            "com.aisle.app:id/recycler_view",
            "com.aisle.app:id/editText",
            "com.aisle.app:id/header_title"
        )

        private val CHAT_MESSAGE_IDS = listOf(
            "com.aisle.app:id/chat_layout_initiator",
            "com.aisle.app:id/chat_layout_partner",
            "com.aisle.app:id/message_txt_initiator",
            "com.aisle.app:id/message_txt_partner"
        )

        private val PROFILE_IDS = listOf(
            "com.aisle.app:id/profile_rv",
            "com.aisle.app:id/user_name_text_below",
            "com.aisle.app:id/user_name_top",
            "com.aisle.app:id/user_age"
        )
    }

    private var chatScreenChecked = false
    private var chatMessageChecked = false
    private var profileChecked = false

    private val missingIds = mutableSetOf<String>()
    private val foundIds = mutableSetOf<String>()

    fun checkChatScreen(root: AccessibilityNodeInfo) {
        if (chatScreenChecked) return
        chatScreenChecked = true
        checkIds(root, CHAT_SCREEN_IDS, "ChatScreen")
    }

    fun checkChatMessages(root: AccessibilityNodeInfo) {
        if (chatMessageChecked) return
        chatMessageChecked = true
        checkIds(root, CHAT_MESSAGE_IDS, "ChatMessages")
    }

    fun checkProfile(root: AccessibilityNodeInfo) {
        if (profileChecked) return
        profileChecked = true
        checkIds(root, PROFILE_IDS, "Profile")
    }

    private fun checkIds(root: AccessibilityNodeInfo, ids: List<String>, context: String) {
        val missing = mutableListOf<String>()
        val found = mutableListOf<String>()

        for (id in ids) {
            val nodes = root.findAccessibilityNodeInfosByViewId(id)
            if (nodes.isNullOrEmpty()) {
                missing.add(id)
                missingIds.add(id)
            } else {
                found.add(id)
                foundIds.add(id)
                nodes.forEach { it.recycle() }
            }
        }

        if (missing.isNotEmpty()) {
            Log.w(TAG, "[$context] LAYOUT CHANGE DETECTED! Missing ${missing.size}/${ids.size} IDs:")
            missing.forEach { Log.w(TAG, "  MISSING: $it") }
            found.forEach { Log.d(TAG, "  OK: $it") }

            // Fire Crashlytics non-fatal so we get alerted in dashboard
            val missingStr = missing.joinToString(", ") { it.substringAfterLast("/") }
            analyticsHelper.logError(
                "LayoutChange[$context] Missing ${missing.size}/${ids.size}: $missingStr",
                LayoutChangeException("$APP_NAME $context: $missingStr")
            )

            // Fire Analytics event for aggregate tracking
            analyticsHelper.logEvent(
                "layout_health_degraded",
                mapOf(
                    "app" to APP_NAME,
                    "area" to context,
                    "missing_count" to missing.size.toString(),
                    "total_count" to ids.size.toString(),
                    "missing_ids" to missingStr
                )
            )
        } else {
            Log.d(TAG, "[$context] All ${ids.size} expected IDs found. Layout unchanged.")
        }
    }

    fun reset() {
        chatScreenChecked = false
        chatMessageChecked = false
        profileChecked = false
        missingIds.clear()
        foundIds.clear()
    }
}
