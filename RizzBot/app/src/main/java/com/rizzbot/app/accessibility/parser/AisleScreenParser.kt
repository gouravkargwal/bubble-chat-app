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
        val orderedMessages = assignOrderedTimestamps(messages)
        Log.d(TAG, "ScreenParser: person=$personName, messages=${orderedMessages.size}")
        orderedMessages.forEach { msg ->
            val dir = if (msg.isIncoming) "THEM" else "YOU"
            Log.d(TAG, "  [$dir] ${msg.text.take(40)}")
        }

        return ParsedChatScreen(personName, orderedMessages)
    }

    /**
     * Scroll-and-collect: scrolls up to load older messages, waits for new content
     * to appear, then scrolls back down. Call from a background thread.
     */
    fun parseScreenWithScroll(root: AccessibilityNodeInfo, maxScrolls: Int = 20): ParsedChatScreen? {
        val rootBounds = Rect()
        root.getBoundsInScreen(rootBounds)
        if (rootBounds.width() > 0) screenWidth = rootBounds.width()

        val personName = findPersonName(root) ?: findPersonNameFallback(root)
        if (personName == null) {
            Log.e(TAG, "ScreenParser: could not find person name (scroll)")
            return null
        }

        // PHASE 1: Scroll all the way to the top
        val recyclerNodes = root.findAccessibilityNodeInfosByViewId(ID_RECYCLER_VIEW)
        val recycler = recyclerNodes.firstOrNull()
        var scrollsUp = 0

        if (recycler != null && recycler.isScrollable) {
            for (scroll in 1..maxScrolls) {
                val scrolled = recycler.performAction(AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD)
                if (!scrolled) {
                    Log.d(TAG, "ScreenParser: reached top after $scroll scrolls")
                    break
                }
                scrollsUp++
                Thread.sleep(800)
                root.refresh()
            }
            Log.d(TAG, "ScreenParser: scrolled up $scrollsUp times")
        }

        // PHASE 2: Collect messages scrolling down (chronological order)
        root.refresh()
        Thread.sleep(500)

        // Collect from current (topmost) view
        val messageList = mutableListOf<ParsedMessage>()
        // Track last N messages to dedup overlapping scroll windows
        var lastBatchTexts = listOf<String>()

        fun collectNewMessages(r: AccessibilityNodeInfo): Int {
            val msgs = extractMessages(r).ifEmpty { extractMessagesFallback(r) }
            if (msgs.isEmpty()) return 0

            // Find where the overlap ends between previous batch and this batch
            val currentTexts = msgs.map { "${if (it.isIncoming) "T" else "Y"}:${it.text}" }

            if (lastBatchTexts.isEmpty()) {
                messageList.addAll(msgs)
                lastBatchTexts = currentTexts
                return msgs.size
            }

            // Find the last message from previous batch in current batch to skip overlap
            // Look for the longest matching suffix of lastBatch in the prefix of currentBatch
            var overlapEnd = 0
            if (lastBatchTexts.isNotEmpty()) {
                // Try to find where the new messages start by matching the last few msgs
                // of the previous batch with the beginning of this batch
                val lastFew = lastBatchTexts.takeLast(minOf(5, lastBatchTexts.size))
                for (startIdx in 0..minOf(currentTexts.size - 1, currentTexts.size)) {
                    val remaining = currentTexts.subList(startIdx, minOf(startIdx + lastFew.size, currentTexts.size))
                    if (remaining.size >= lastFew.size && remaining.subList(0, lastFew.size) == lastFew) {
                        overlapEnd = startIdx + lastFew.size
                        break
                    }
                }
                // If no overlap found, try matching just the last message
                if (overlapEnd == 0 && lastBatchTexts.isNotEmpty()) {
                    val lastMsg = lastBatchTexts.last()
                    val idx = currentTexts.indexOf(lastMsg)
                    if (idx >= 0) {
                        overlapEnd = idx + 1
                    }
                }
            }

            val newMsgs = msgs.subList(overlapEnd, msgs.size)
            messageList.addAll(newMsgs)
            lastBatchTexts = currentTexts
            return newMsgs.size
        }

        collectNewMessages(root)
        Log.d(TAG, "ScreenParser: initial collection: ${messageList.size} msgs")

        // Scroll down to collect the rest
        if (recycler != null && recycler.isScrollable && scrollsUp > 0) {
            var noNewMessageScrolls = 0
            for (scroll in 1..(scrollsUp + 5)) { // scroll down a bit extra to be safe
                recycler.refresh()
                val scrolled = recycler.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
                if (!scrolled) {
                    Log.d(TAG, "ScreenParser: reached bottom after $scroll forward scrolls")
                    break
                }
                Thread.sleep(800)
                root.refresh()

                val newMsgs = collectNewMessages(root)
                Log.d(TAG, "ScreenParser: scroll down $scroll — new=$newMsgs, total=${messageList.size}")

                if (newMsgs == 0) {
                    noNewMessageScrolls++
                    if (noNewMessageScrolls >= 2) {
                        Log.d(TAG, "ScreenParser: no new messages for 2 forward scrolls, at bottom")
                        break
                    }
                } else {
                    noNewMessageScrolls = 0
                }
            }
        }

        recyclerNodes.forEach { it.recycle() }

        // Messages are already in chronological order (oldest first) since we scrolled top→bottom
        val orderedMessages = assignOrderedTimestamps(messageList)
        Log.d(TAG, "ScreenParser(scroll): person=$personName, messages=${orderedMessages.size}")
        return ParsedChatScreen(personName, orderedMessages)
    }

    /**
     * Assigns sequential timestamps to messages based on their screen order.
     * Uses current time as the latest message timestamp, spacing them 1 minute apart.
     * Larger spacing prevents ordering conflicts across multiple parse sessions.
     */
    private fun assignOrderedTimestamps(messages: List<ParsedMessage>): List<ParsedMessage> {
        if (messages.isEmpty()) return messages
        val now = System.currentTimeMillis()
        val spacingMs = 60_000L // 1 minute between messages
        // Space messages apart, newest message gets 'now'
        return messages.mapIndexed { index, msg ->
            msg.copy(timestamp = now - ((messages.size - 1 - index) * spacingMs))
        }
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
                        val timeText = findTimestampInNode(child)
                        messages.add(ParsedMessage(text = text, isIncoming = false, timestampText = timeText))
                    }
                }
                ID_CHAT_LAYOUT_PARTNER -> {
                    val text = findTextById(child, ID_MESSAGE_TXT_PARTNER)
                    if (!text.isNullOrBlank()) {
                        val timeText = findTimestampInNode(child)
                        messages.add(ParsedMessage(text = text, isIncoming = true, timestampText = timeText))
                    }
                }
            }
            child.recycle()
        }

        recycler.recycle()
        return messages
    }

    private val TIME_PATTERN = Regex(
        """(\d{1,2}:\d{2}\s*(AM|PM|am|pm)?)|""" +
        """(Yesterday|Today|Just now)|""" +
        """(\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))|""" +
        """((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2})"""
    )

    private fun findTimestampInNode(node: AccessibilityNodeInfo): String? {
        // Look for short text nodes that match time patterns
        val texts = mutableListOf<String>()
        collectTexts(node, texts)
        return texts.firstOrNull { text ->
            text.length in 3..20 && TIME_PATTERN.containsMatchIn(text)
        }
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
