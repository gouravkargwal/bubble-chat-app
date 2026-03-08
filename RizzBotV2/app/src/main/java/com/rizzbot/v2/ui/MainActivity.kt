package com.rizzbot.v2.ui

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.navigation.compose.rememberNavController
import com.rizzbot.v2.data.local.datastore.SettingsDataStore
import com.rizzbot.v2.ui.navigation.NavGraph
import com.rizzbot.v2.ui.navigation.Screen
import com.rizzbot.v2.ui.theme.RizzBotV2Theme
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var settingsDataStore: SettingsDataStore

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            val onboardingCompleted by settingsDataStore.onboardingCompleted.collectAsState(initial = false)
            val navController = rememberNavController()

            RizzBotV2Theme {
                NavGraph(
                    navController = navController,
                    startDestination = if (onboardingCompleted) Screen.Home.route else Screen.Onboarding.route
                )
            }
        }
    }
}
