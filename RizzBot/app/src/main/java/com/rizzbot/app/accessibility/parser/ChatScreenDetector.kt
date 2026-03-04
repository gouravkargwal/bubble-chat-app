package com.rizzbot.app.accessibility.parser

import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.rizzbot.app.util.Constants
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ChatScreenDetector @Inject constructor() {

    companion object {
        // Discovered from uiautomator dump
        private const val ID_CHAT_LAYOUT = "com.aisle.app:id/chat_layout"
        private const val ID_RECYCLER_VIEW = "com.aisle.app:id/recycler_view"
        private const val ID_EDIT_TEXT = "com.aisle.app:id/editText"
        private const val ID_HEADER_TITLE = "com.aisle.app:id/header_title"
    }

    fun isChatScreen(event: AccessibilityEvent): Boolean {
        if (event.packageName?.toString() != Constants.AISLE_PACKAGE) return false

        // Structural check - look for chat-specific views by real IDs
        val source = event.source ?: return false
        return try {
            hasChatStructure(source)
        } finally {
            source.recycle()
        }
    }

    fun isChatScreen(root: AccessibilityNodeInfo): Boolean {
        return hasChatStructure(root)
    }

    private fun hasChatStructure(node: AccessibilityNodeInfo): Boolean {
        // Check for Aisle chat screen using exact view IDs from uiautomator dump
        var hasMessageList = false
        var hasInputField = false

        val recyclerNodes = node.findAccessibilityNodeInfosByViewId(ID_RECYCLER_VIEW)
        if (recyclerNodes.isNotEmpty()) {
            hasMessageList = true
            recyclerNodes.forEach { it.recycle() }
        }

        val inputNodes = node.findAccessibilityNodeInfosByViewId(ID_EDIT_TEXT)
        if (inputNodes.isNotEmpty()) {
            hasInputField = true
            inputNodes.forEach { it.recycle() }
        }

        // If both found, it's definitely a chat screen
        if (hasMessageList && hasInputField) return true

        // Fallback: structural analysis
        return hasStructuralChatPattern(node)
    }

    private fun hasStructuralChatPattern(root: AccessibilityNodeInfo): Boolean {
        // Look for a scrollable container (message list) and an editable field
        var foundScrollable = false
        var foundEditable = false
        traverseTree(root) { node ->
            if (node.isScrollable && node.childCount > 2) foundScrollable = true
            if (node.isEditable) foundEditable = true
        }
        return foundScrollable && foundEditable
    }

    private fun traverseTree(node: AccessibilityNodeInfo, action: (AccessibilityNodeInfo) -> Unit) {
        action(node)
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            traverseTree(child, action)
            child.recycle()
        }
    }
}
