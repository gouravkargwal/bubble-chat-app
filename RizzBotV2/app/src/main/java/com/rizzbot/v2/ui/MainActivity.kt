package com.rizzbot.v2.ui

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.navigation.compose.rememberNavController
import com.revenuecat.purchases.Purchases
import com.revenuecat.purchases.PurchasesConfiguration
import com.rizzbot.v2.BuildConfig as AppBuildConfig
import com.rizzbot.v2.data.auth.AuthManager
import com.rizzbot.v2.data.local.datastore.SettingsDataStore
import com.rizzbot.v2.data.subscription.SubscriptionManager
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.ui.navigation.NavGraph
import com.rizzbot.v2.ui.navigation.Screen
import com.rizzbot.v2.ui.theme.RizzBotV2Theme
import com.rizzbot.v2.util.InAppUpdateHelper
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.first
import javax.inject.Inject

private sealed class BootState {
    data object Refreshing : BootState()
    data class Ready(
        val onboardingCompleted: Boolean,
        val isAuthenticated: Boolean,
    ) : BootState()
}

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var settingsDataStore: SettingsDataStore
    @Inject lateinit var authManager: AuthManager
    @Inject lateinit var subscriptionManager: SubscriptionManager
    @Inject lateinit var hostedRepository: HostedRepository

    private val pendingNavigation = mutableStateOf<String?>(null)
    private val showPaywallFromIntent = mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Initialize RevenueCat with API key from BuildConfig
        Purchases.configure(
            PurchasesConfiguration.Builder(this, AppBuildConfig.REVENUE_CAT_PUBLIC_KEY)
                .build()
        )

        // Set user ID and update tier on app start if authenticated
        val userId = authManager.getUserId()
        if (userId != null && userId.isNotEmpty()) {
            kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.IO).launch {
                subscriptionManager.setUserId(userId)
            }
        }

        pendingNavigation.value = intent?.getStringExtra("navigate_to")
        
        // Check for SHOW_PAYWALL intent action
        showPaywallFromIntent.value = intent?.action == "SHOW_PAYWALL"

        InAppUpdateHelper.checkForUpdate(this)

        setContent {
            val navController = rememberNavController()
            val navigateTo = pendingNavigation.value
            val shouldShowPaywall = showPaywallFromIntent.value
            val usage by hostedRepository.usageState.collectAsState()
            val isGodMode = usage.isGodModeActive

            // Resolve onboarding/auth state before selecting a start destination.
            // This avoids rendering the onboarding screen on the first frame when DataStore emits `false` initially.
            val bootState = remember { mutableStateOf<BootState>(BootState.Refreshing) }

            LaunchedEffect(Unit) {
                val onboardingCompleted = settingsDataStore.onboardingCompleted.first()
                if (AppBuildConfig.DEBUG) {
                    android.util.Log.d("AuthDebug", "Boot onboardingCompleted=$onboardingCompleted")
                }

                var isAuthenticated = authManager.isAuthenticated()
                if (AppBuildConfig.DEBUG) {
                    android.util.Log.d(
                        "AuthDebug",
                        "Boot auth check: initial isAuthenticated=$isAuthenticated"
                    )
                }
                if (!isAuthenticated) {
                    // If Firebase still has a valid session, re-issue backend JWT before deciding route.
                    val refreshed = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
                        authManager.refreshBackendTokenIfFirebaseSignedIn()
                    }
                    isAuthenticated = refreshed && authManager.isAuthenticated()
                    if (AppBuildConfig.DEBUG) {
                        android.util.Log.d(
                            "AuthDebug",
                            "Boot auth check: refreshAttempted=true refreshed=$refreshed postIsAuthenticated=$isAuthenticated"
                        )
                    }
                }

                bootState.value = BootState.Ready(
                    onboardingCompleted = onboardingCompleted,
                    isAuthenticated = isAuthenticated
                )
                if (AppBuildConfig.DEBUG) {
                    android.util.Log.d(
                        "AuthDebug",
                        "Boot resolved: onboardingCompleted=$onboardingCompleted isAuthenticated=$isAuthenticated"
                    )
                }
            }

            val resolvedOnboardingCompleted =
                (bootState.value as? BootState.Ready)?.onboardingCompleted ?: false
            val canSkipOnboarding =
                (bootState.value as? BootState.Ready)?.onboardingCompleted == true &&
                    (bootState.value as? BootState.Ready)?.isAuthenticated == true
            val onboardingResumeForSignIn =
                (bootState.value as? BootState.Ready)?.let { ready ->
                    ready.onboardingCompleted && !ready.isAuthenticated
                } == true

            LaunchedEffect((bootState.value as? BootState.Ready)?.isAuthenticated) {
                if ((bootState.value as? BootState.Ready)?.isAuthenticated == true) {
                    hostedRepository.refreshUsage(force = false)
                }
            }

            RizzBotV2Theme(isGodMode = isGodMode) {
                when (val state = bootState.value) {
                    BootState.Refreshing -> {
                        Box(
                            modifier = Modifier.fillMaxSize(),
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                        }
                    }
                    is BootState.Ready -> {
                    NavGraph(
                        navController = navController,
                        startDestination = if (canSkipOnboarding) Screen.Home.route else Screen.Onboarding.route,
                        onboardingResumeForSignIn = onboardingResumeForSignIn
                    )
                    }
                }
            }

            LaunchedEffect(navigateTo, bootState.value) {
                if (navigateTo == "premium" && resolvedOnboardingCompleted) {
                    navController.navigate(Screen.Premium.route)
                    pendingNavigation.value = null
                }
            }
            
            // Handle paywall intent - watch both the flag and onboarding state
            LaunchedEffect(shouldShowPaywall, resolvedOnboardingCompleted, bootState.value) {
                if (shouldShowPaywall && resolvedOnboardingCompleted) {
                    // Small delay to ensure navigation graph is ready
                    kotlinx.coroutines.delay(150)
                    try {
                        // Navigate to paywall screen
                        // Check if we're not already on the premium screen
                        val currentRoute = navController.currentBackStackEntry?.destination?.route
                        if (currentRoute != Screen.Premium.route) {
                            navController.navigate(Screen.Premium.route) {
                                // Pop to Home if it exists, otherwise start fresh
                                popUpTo(Screen.Home.route) { inclusive = false }
                            }
                        }
                    } catch (e: Exception) {
                        android.util.Log.e("MainActivity", "Failed to navigate to paywall", e)
                    }
                    // Clear the flag to prevent re-triggering
                    showPaywallFromIntent.value = false
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent) // Update the intent so getIntent() returns the latest
        pendingNavigation.value = intent.getStringExtra("navigate_to")
        
        // Handle SHOW_PAYWALL intent action
        showPaywallFromIntent.value = intent.action == "SHOW_PAYWALL"
    }
}
