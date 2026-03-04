package com.rizzbot.app.overlay

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class OverlayEventBus @Inject constructor() {
    private val _events = MutableSharedFlow<OverlayEvent>(replay = 0, extraBufferCapacity = 1)
    val events: SharedFlow<OverlayEvent> = _events

    suspend fun emit(event: OverlayEvent) {
        _events.emit(event)
    }

    fun tryEmit(event: OverlayEvent) {
        _events.tryEmit(event)
    }
}
