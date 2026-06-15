package com.rizzbot.v2.overlay

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.IBinder
import android.provider.Settings
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.rizzbot.v2.R
import com.rizzbot.v2.capture.ScreenCaptureManager
import com.rizzbot.v2.overlay.manager.BubbleManager
import com.rizzbot.v2.ui.MainActivity
import com.rizzbot.v2.util.Constants
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

private const val TAG = "OverlayService"

@AndroidEntryPoint
class OverlayService : Service() {

    @Inject lateinit var bubbleManager: BubbleManager
    @Inject lateinit var screenCaptureManager: ScreenCaptureManager

    private var homeReceiverRegistered = false

    private val homeReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == Intent.ACTION_CLOSE_SYSTEM_DIALOGS) {
                bubbleManager.collapseIfExpanded()
            }
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        // startForeground must run within ~5s of startForegroundService(); do it first and
        // never let a failure leave the service half-started. If it throws, bail out cleanly.
        try {
            createNotificationChannel()
            startForeground(Constants.NOTIFICATION_ID, buildNotification())
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start foreground; stopping service", e)
            stopSelf()
            return
        }

        // Overlay permission can be revoked at any time. Without it, addView() throws
        // BadTokenException and crashes the process — so verify before showing anything.
        if (!Settings.canDrawOverlays(this)) {
            Log.w(TAG, "Overlay permission not granted; stopping service")
            stopSelf()
            return
        }

        registerHomeReceiver()

        // Provide a foreground-service-context launcher so CaptureConsentActivity bypasses
        // Android 14+ background-activity-launch restrictions on restrictive OEM devices.
        screenCaptureManager.activityLauncher = { intent -> startActivity(intent) }

        try {
            bubbleManager.show()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to show bubble; stopping service", e)
            stopSelf()
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Service may already be running (e.g. user dismissed bubble via drag) while the process
        // stays alive; [onCreate] is skipped so we must show the bubble here too.
        if (!Settings.canDrawOverlays(this)) {
            Log.w(TAG, "Overlay permission not granted; stopping service")
            stopSelf()
            return START_NOT_STICKY
        }
        try {
            bubbleManager.show()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to show bubble in onStartCommand", e)
        }
        return START_STICKY
    }

    override fun onDestroy() {
        screenCaptureManager.activityLauncher = null
        unregisterHomeReceiver()
        try {
            bubbleManager.hide()
        } catch (e: Exception) {
            Log.w(TAG, "Failed to hide bubble during destroy", e)
        }
        super.onDestroy()
    }

    /**
     * Registers [homeReceiver] with [ContextCompat.RECEIVER_NOT_EXPORTED]. Android 14+ throws
     * SecurityException if the export flag is omitted for a non-system broadcast — this was the
     * crash that killed the process on every toggle-on.
     */
    private fun registerHomeReceiver() {
        if (homeReceiverRegistered) return
        try {
            ContextCompat.registerReceiver(
                this,
                homeReceiver,
                IntentFilter(Intent.ACTION_CLOSE_SYSTEM_DIALOGS),
                ContextCompat.RECEIVER_NOT_EXPORTED
            )
            homeReceiverRegistered = true
        } catch (e: Exception) {
            // Non-fatal: home-press collapse is a nicety, not core functionality.
            Log.w(TAG, "Failed to register home receiver", e)
        }
    }

    private fun unregisterHomeReceiver() {
        if (!homeReceiverRegistered) return
        try {
            unregisterReceiver(homeReceiver)
        } catch (e: IllegalArgumentException) {
            Log.w(TAG, "Home receiver already unregistered", e)
        }
        homeReceiverRegistered = false
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                Constants.NOTIFICATION_CHANNEL_ID,
                getString(R.string.notification_channel_name),
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = getString(R.string.notification_channel_description)
                setShowBadge(false)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, Constants.NOTIFICATION_CHANNEL_ID)
            .setContentTitle(getString(R.string.notification_title))
            .setContentText(getString(R.string.notification_text))
            .setSmallIcon(android.R.drawable.ic_menu_send)
            .setOngoing(true)
            .setContentIntent(pendingIntent)
            .build()
    }
}
