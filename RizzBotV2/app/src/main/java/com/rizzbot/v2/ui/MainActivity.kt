package com.rizzbot.v2.ui

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.navigation.compose.rememberNavController
import com.rizzbot.v2.data.local.datastore.SettingsDataStore
import com.rizzbot.v2.ui.navigation.NavGraph
import com.rizzbot.v2.ui.navigation.Screen
import com.rizzbot.v2.ui.theme.RizzBotV2Theme
import com.rizzbot.v2.util.InAppUpdateHelper
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var settingsDataStore: SettingsDataStore

    private val pendingNavigation = mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        pendingNavigation.value = intent?.getStringExtra("navigate_to")

        InAppUpdateHelper.checkForUpdate(this)

        setContent {
            val onboardingCompleted by settingsDataStore.onboardingCompleted.collectAsState(initial = false)
            val navController = rememberNavController()
            val navigateTo = pendingNavigation.value

            RizzBotV2Theme {
                NavGraph(
                    navController = navController,
                    startDestination = if (onboardingCompleted) Screen.Home.route else Screen.Onboarding.route
                )
            }

            androidx.compose.runtime.LaunchedEffect(navigateTo) {
                if (navigateTo == "premium" && onboardingCompleted) {
                    navController.navigate(Screen.Premium.route)
                    pendingNavigation.value = null
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        pendingNavigation.value = intent.getStringExtra("navigate_to")
    }
}
