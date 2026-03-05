package com.rizzbot.app.overlay.manager

sealed class BubbleState {
    data object Hidden : BubbleState()
    data object Collapsed : BubbleState()
    data object RizzButton : BubbleState()
    data class ActionMenu(val hasProfile: Boolean = false, val lastReplies: List<String>? = null) : BubbleState()
    data class Expanded(val suggestions: List<String>, val hasProfile: Boolean = false) : BubbleState()
    data class Loading(val message: String) : BubbleState()
    data class Error(val message: String) : BubbleState()
    data class ProfileSyncButton(val personName: String) : BubbleState()
    data class ProfileSyncing(val personName: String) : BubbleState()
    data class ProfileSynced(val personName: String) : BubbleState()
}
