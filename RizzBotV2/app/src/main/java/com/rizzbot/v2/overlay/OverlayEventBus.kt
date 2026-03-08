package com.rizzbot.v2.overlay

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class OverlayEventBus @Inject constructor() {
    private val _events = MutableSharedFlow<OverlayEvent>(extraBufferCapacity = 10)
    val events: SharedFlow<OverlayEvent> = _events.asSharedFlow()

    fun send(event: OverlayEvent) {
        _events.tryEmit(event)
    }
}
