package com.rizzbot.v2.overlay

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class OverlayEventBus @Inject constructor() {
    private val _events = MutableSharedFlow<OverlayEvent>(extraBufferCapacity = 64)
    val events: SharedFlow<OverlayEvent> = _events.asSharedFlow()

    fun send(event: OverlayEvent) {
        if (!_events.tryEmit(event)) {
            android.util.Log.w("OverlayEventBus", "Event buffer full, dropped: $event")
        }
    }
}
