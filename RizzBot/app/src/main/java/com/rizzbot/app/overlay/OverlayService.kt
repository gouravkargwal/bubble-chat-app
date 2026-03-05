package com.rizzbot.app.overlay

import android.app.Service
import android.content.Intent
import android.os.IBinder
import com.rizzbot.app.overlay.manager.BubbleManager
import com.rizzbot.app.util.NotificationHelper
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class OverlayService : Service() {

    @Inject lateinit var bubbleManager: BubbleManager
    @Inject lateinit var overlayEventBus: OverlayEventBus
    @Inject lateinit var notificationHelper: NotificationHelper

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    override fun onCreate() {
        super.onCreate()
        startForeground(
            notificationHelper.getOverlayNotificationId(),
            notificationHelper.createOverlayNotification()
        )
        observeEvents()
    }

    private fun observeEvents() {
        serviceScope.launch {
            overlayEventBus.events.collect { event ->
                when (event) {
                    is OverlayEvent.ShowSuggestion -> bubbleManager.showSuggestion(event.replies)
                    is OverlayEvent.ShowLoading -> bubbleManager.showLoading(event.message)
                    is OverlayEvent.ShowError -> bubbleManager.showError(event.message)
                    is OverlayEvent.Hide -> bubbleManager.hide()
                    is OverlayEvent.ShowRizzButton -> bubbleManager.showRizzButton()
                    is OverlayEvent.HideRizzButton -> bubbleManager.hideRizzButton()
                    is OverlayEvent.ShowProfileSyncButton -> bubbleManager.showProfileSyncButton(event.personName)
                    is OverlayEvent.ShowProfileSyncing -> bubbleManager.showProfileSyncing(event.personName)
                    is OverlayEvent.ShowProfileSynced -> bubbleManager.showProfileSynced(event.personName)
                }
            }
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        bubbleManager.hide()
        serviceScope.cancel()
    }
}
