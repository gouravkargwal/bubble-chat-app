package com.rizzbot.app.accessibility.parser

import android.graphics.Rect
import android.util.Log
import android.view.accessibility.AccessibilityNodeInfo

/**
 * Debug utility: dumps the accessibility view tree to logcat.
 * Run on a chat screen / profile page, then check `adb logcat -s RizzBot:D`
 * to discover real view IDs for Aisle.
 */
object ViewTreeDumper {

    private const val TAG = "RizzBot"

    fun dump(root: AccessibilityNodeInfo, label: String = "ViewTree") {
        Log.d(TAG, "=== $label DUMP START ===")
        dumpNode(root, depth = 0)
        Log.d(TAG, "=== $label DUMP END ===")
    }

    private fun dumpNode(node: AccessibilityNodeInfo, depth: Int) {
        val indent = "  ".repeat(depth)
        val bounds = Rect()
        node.getBoundsInScreen(bounds)
        val id = node.viewIdResourceName ?: "(no-id)"
        val cls = node.className?.toString()?.substringAfterLast('.') ?: "?"
        val text = node.text?.toString()?.take(50) ?: ""
        val desc = node.contentDescription?.toString()?.take(30) ?: ""
        val flags = buildList {
            if (node.isScrollable) add("scroll")
            if (node.isEditable) add("edit")
            if (node.isClickable) add("click")
            if (node.isFocusable) add("focus")
        }.joinToString(",")

        Log.d(TAG, "$indent[$cls] id=$id text=\"$text\" desc=\"$desc\" bounds=$bounds flags=[$flags] children=${node.childCount}")

        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            dumpNode(child, depth + 1)
            child.recycle()
        }
    }
}
