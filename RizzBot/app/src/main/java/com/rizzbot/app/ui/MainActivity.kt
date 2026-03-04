package com.rizzbot.app.ui

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.navigation.compose.rememberNavController
import com.rizzbot.app.data.local.datastore.SettingsDataStore
import com.rizzbot.app.overlay.OverlayService
import com.rizzbot.app.ui.navigation.RizzBotNavGraph
import com.rizzbot.app.ui.theme.RizzBotTheme
import com.rizzbot.app.util.PermissionHelper
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var settingsDataStore: SettingsDataStore
    @Inject lateinit var permissionHelper: PermissionHelper

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            val hasCompletedOnboarding by settingsDataStore.hasCompletedOnboarding
                .collectAsState(initial = false)

            RizzBotTheme {
                val navController = rememberNavController()
                RizzBotNavGraph(
                    navController = navController,
                    hasCompletedOnboarding = hasCompletedOnboarding
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Start overlay service if enabled and permissions are granted
        if (permissionHelper.areAllPermissionsGranted()) {
            startForegroundService(Intent(this, OverlayService::class.java))
        }
    }
}
