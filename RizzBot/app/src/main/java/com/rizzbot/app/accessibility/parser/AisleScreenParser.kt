package com.rizzbot.app.accessibility.parser

import android.graphics.Rect
import android.util.Log
import android.view.accessibility.AccessibilityNodeInfo
import com.rizzbot.app.accessibility.model.ParsedChatScreen
import com.rizzbot.app.accessibility.model.ParsedMessage
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AisleScreenParser @Inject constructor() {

    companion object {
        private const val TAG = "RizzBot"

        // --- Primary IDs (update these after running uiautomator dump) ---
        private const val ID_HEADER_TITLE = "com.aisle.app:id/header_title"
        private const val ID_RECYCLER_VIEW = "com.aisle.app:id/recycler_view"
        private const val ID_CHAT_LAYOUT_INITIATOR = "com.aisle.app:id/chat_layout_initiator"
        private const val ID_CHAT_LAYOUT_PARTNER = "com.aisle.app:id/chat_layout_partner"
        private const val ID_MESSAGE_TXT_INITIATOR = "com.aisle.app:id/message_txt_initiator"
        private const val ID_MESSAGE_TXT_PARTNER = "com.aisle.app:id/message_txt_partner"
    }

    private var screenWidth: Int = 1080 // Updated dynamically

    fun parseScreen(root: AccessibilityNodeInfo): ParsedChatScreen? {
        // Get screen width for bounds-based direction detection
        val rootBounds = Rect()
        root.getBoundsInScreen(rootBounds)
        if (rootBounds.width() > 0) screenWidth = rootBounds.width()

        val personName = findPersonName(root) ?: findPersonNameFallback(root)
        if (personName == null) {
            Log.e(TAG, "ScreenParser: could not find person name")
            return null
        }

        val messages = extractMessages(root).ifEmpty { extractMessagesFallback(root) }
        Log.d(TAG, "ScreenParser: person=$personName, messages=${messages.size}")
        messages.forEach { msg ->
            val dir = if (msg.isIncoming) "THEM" else "YOU"
            Log.d(TAG, "  [$dir] ${msg.text.take(40)}")
        }

        return ParsedChatScreen(personName, messages)
    }

    // --- Primary ID-based parsing ---

    private fun findPersonName(root: AccessibilityNodeInfo): String? {
        val nodes = root.findAccessibilityNodeInfosByViewId(ID_HEADER_TITLE)
        if (nodes.isNotEmpty()) {
            val name = nodes[0].text?.toString()
            nodes.forEach { it.recycle() }
            return name?.takeIf { it.isNotBlank() }
        }
        return null
    }

    private fun extractMessages(root: AccessibilityNodeInfo): List<ParsedMessage> {
        val messages = mutableListOf<ParsedMessage>()

        val recyclerNodes = root.findAccessibilityNodeInfosByViewId(ID_RECYCLER_VIEW)
        if (recyclerNodes.isEmpty()) return messages
        val recycler = recyclerNodes[0]

        for (i in 0 until recycler.childCount) {
            val child = recycler.getChild(i) ?: continue
            val childId = child.viewIdResourceName ?: ""

            when (childId) {
                ID_CHAT_LAYOUT_INITIATOR -> {
                    val text = findTextById(child, ID_MESSAGE_TXT_INITIATOR)
                    if (!text.isNullOrBlank()) {
                        messages.add(ParsedMessage(text = text, isIncoming = false))
                    }
                }
                ID_CHAT_LAYOUT_PARTNER -> {
                    val text = findTextById(child, ID_MESSAGE_TXT_PARTNER)
                    if (!text.isNullOrBlank()) {
                        messages.add(ParsedMessage(text = text, isIncoming = true))
                    }
                }
            }
            child.recycle()
        }

        recycler.recycle()
        return messages
    }

    // --- Fallback: structural/bounds-based parsing ---

    private fun findPersonNameFallback(root: AccessibilityNodeInfo): String? {
        // Strategy: find the first meaningful text at the top of the screen (toolbar area)
        // Typically the person name is in a toolbar/header within the top ~150dp
        val candidates = mutableListOf<Pair<String, Rect>>()
        collectTextNodes(root, candidates)

        // Find text nodes in the top portion of the screen (header area)
        val headerTexts = candidates
            .filter { (text, bounds) ->
                bounds.top < 200 && // Near top of screen
                text.length in 2..30 && // Reasonable name length
                !text.contains(":") && // Not a timestamp
                !text.matches(Regex("\\d+")) && // Not a number
                text != "Online" && text != "Offline" && text != "typing..." &&
                !text.startsWith("Last seen")
            }
            .sortedBy { it.second.top }

        Log.d(TAG, "ScreenParser fallback: header candidates = ${headerTexts.map { it.first }}")
        return headerTexts.firstOrNull()?.first
    }

    private fun extractMessagesFallback(root: AccessibilityNodeInfo): List<ParsedMessage> {
        val messages = mutableListOf<ParsedMessage>()

        // Find the scrollable container (RecyclerView / message list)
        val scrollable = findScrollableContainer(root) ?: return messages
        val midX = screenWidth / 2

        Log.d(TAG, "ScreenParser fallback: found scrollable with ${scrollable.childCount} children, screenWidth=$screenWidth")

        for (i in 0 until scrollable.childCount) {
            val child = scrollable.getChild(i) ?: continue
            val text = extractAllText(child)
            if (text.isNotBlank()) {
                // Bounds-based direction: left-aligned = incoming, right-aligned = outgoing
                val bounds = Rect()
                child.getBoundsInScreen(bounds)
                val centerX = (bounds.left + bounds.right) / 2
                val isIncoming = centerX < midX

                Log.d(TAG, "  Fallback msg: center=$centerX mid=$midX incoming=$isIncoming text=\"${text.take(40)}\"")
                messages.add(ParsedMessage(text = text, isIncoming = isIncoming))
            }
            child.recycle()
        }

        return messages
    }

    private fun findScrollableContainer(node: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        // Look for a scrollable container with multiple children (the message list)
        if (node.isScrollable && node.childCount > 1) {
            val className = node.className?.toString() ?: ""
            if (className.contains("RecyclerView") || className.contains("ListView") || className.contains("ScrollView")) {
                return node
            }
            // Even without class name match, a scrollable with many children is likely the message list
            if (node.childCount > 2) return node
        }

        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            val result = findScrollableContainer(child)
            if (result != null) return result
            child.recycle()
        }
        return null
    }

    private fun extractAllText(node: AccessibilityNodeInfo): String {
        val texts = mutableListOf<String>()
        collectTexts(node, texts)
        // Filter out timestamps and status text
        return texts
            .filter { text ->
                text.length > 1 &&
                !text.matches(Regex("\\d{1,2}:\\d{2}\\s*(AM|PM|am|pm)?")) &&
                !text.matches(Regex("\\d{1,2}/\\d{1,2}/\\d{2,4}")) &&
                text != "Delivered" && text != "Seen" && text != "Sent" &&
                text != "Read" && text != "✓" && text != "✓✓"
            }
            .joinToString(" ")
    }

    private fun collectTexts(node: AccessibilityNodeInfo, result: MutableList<String>) {
        node.text?.toString()?.takeIf { it.isNotBlank() }?.let { result.add(it) }
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            collectTexts(child, result)
            child.recycle()
        }
    }

    private fun collectTextNodes(node: AccessibilityNodeInfo, result: MutableList<Pair<String, Rect>>) {
        val text = node.text?.toString()
        if (!text.isNullOrBlank()) {
            val bounds = Rect()
            node.getBoundsInScreen(bounds)
            result.add(text to bounds)
        }
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            collectTextNodes(child, result)
            child.recycle()
        }
    }

    private fun findTextById(parent: AccessibilityNodeInfo, viewId: String): String? {
        val nodes = parent.findAccessibilityNodeInfosByViewId(viewId)
        if (nodes.isNotEmpty()) {
            val text = nodes[0].text?.toString()
            nodes.forEach { it.recycle() }
            return text
        }
        return null
    }
}
