package com.rizzbot.app.overlay

sealed class OverlayEvent {
    data class ShowSuggestion(val replies: List<String>) : OverlayEvent()
    data class ShowLoading(val message: String = "Cooking up a reply...") : OverlayEvent()
    data class ShowError(val message: String) : OverlayEvent()
    data object Hide : OverlayEvent()
    data object ShowRizzButton : OverlayEvent()
    data object HideRizzButton : OverlayEvent()
    data class ShowProfileSyncButton(val personName: String) : OverlayEvent()
    data class ShowProfileSyncing(val personName: String) : OverlayEvent()
    data class ShowProfileSynced(val personName: String) : OverlayEvent()
}
