package com.rizzbot.app.overlay

import android.os.Bundle
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleRegistry
import androidx.savedstate.SavedStateRegistry
import androidx.savedstate.SavedStateRegistryController
import androidx.savedstate.SavedStateRegistryOwner

class OverlayLifecycleOwner : SavedStateRegistryOwner {

    private val lifecycleRegistry = LifecycleRegistry(this)
    private val savedStateRegistryController = SavedStateRegistryController.create(this)

    override val lifecycle: Lifecycle get() = lifecycleRegistry
    override val savedStateRegistry: SavedStateRegistry
        get() = savedStateRegistryController.savedStateRegistry

    fun onCreate() {
        savedStateRegistryController.performRestore(null)
        handleLifecycleEvent(Lifecycle.Event.ON_CREATE)
    }

    fun onResume() {
        handleLifecycleEvent(Lifecycle.Event.ON_RESUME)
    }

    fun onPause() {
        handleLifecycleEvent(Lifecycle.Event.ON_PAUSE)
    }

    fun onStop() {
        handleLifecycleEvent(Lifecycle.Event.ON_STOP)
    }

    fun onDestroy() {
        handleLifecycleEvent(Lifecycle.Event.ON_DESTROY)
    }

    private fun handleLifecycleEvent(event: Lifecycle.Event) {
        lifecycleRegistry.handleLifecycleEvent(event)
    }
}
