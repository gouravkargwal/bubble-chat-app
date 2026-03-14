package com.rizzbot.v2.ui.navigation

import androidx.compose.animation.core.EaseInOut
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import com.rizzbot.v2.ui.demo.DemoScreen
import com.rizzbot.v2.ui.history.HistoryScreen
import com.rizzbot.v2.ui.home.HomeScreen
import com.rizzbot.v2.ui.onboarding.OnboardingScreen
import com.rizzbot.v2.ui.profile.ProfileAuditorScreen
import com.rizzbot.v2.ui.profile.ProfileHistoryScreen
import com.rizzbot.v2.ui.profile.ProfileOptimizerScreen
import com.rizzbot.v2.ui.paywall.PaywallScreen
import com.rizzbot.v2.ui.settings.SettingsScreen
import com.rizzbot.v2.ui.stats.StatsScreen

private const val ANIM_DURATION = 300

@Composable
fun NavGraph(
    navController: NavHostController,
    startDestination: String
) {
    NavHost(
        navController = navController,
        startDestination = startDestination,
        enterTransition = {
            fadeIn(
                animationSpec = tween(durationMillis = ANIM_DURATION, easing = EaseInOut)
            ) + scaleIn(
                initialScale = 0.98f,
                animationSpec = tween(durationMillis = ANIM_DURATION, easing = EaseInOut)
            )
        },
        exitTransition = {
            fadeOut(
                animationSpec = tween(durationMillis = ANIM_DURATION, easing = EaseInOut)
            ) + scaleOut(
                targetScale = 0.98f,
                animationSpec = tween(durationMillis = ANIM_DURATION, easing = EaseInOut)
            )
        },
        popEnterTransition = {
            fadeIn(
                animationSpec = tween(durationMillis = ANIM_DURATION, easing = EaseInOut)
            ) + scaleIn(
                initialScale = 0.98f,
                animationSpec = tween(durationMillis = ANIM_DURATION, easing = EaseInOut)
            )
        },
        popExitTransition = {
            fadeOut(
                animationSpec = tween(durationMillis = ANIM_DURATION, easing = EaseInOut)
            ) + scaleOut(
                targetScale = 0.98f,
                animationSpec = tween(durationMillis = ANIM_DURATION, easing = EaseInOut)
            )
        }
    ) {
        composable(Screen.Onboarding.route) {
            OnboardingScreen(
                onComplete = {
                    navController.navigate(Screen.Home.route) {
                        popUpTo(Screen.Onboarding.route) { inclusive = true }
                    }
                },
                onNavigateToPaywall = {
                    navController.navigate(Screen.Premium.route) {
                        // Don't pop onboarding yet - user will come back after paywall
                    }
                },
                onTryDemo = {
                    navController.navigate(Screen.Demo.route)
                }
            )
        }
        composable(Screen.Home.route) {
            HomeScreen(
                onNavigateToSettings = { navController.navigate(Screen.Settings.route) },
                onNavigateToHistory = { navController.navigate(Screen.ReplyHistory.route) },
                onNavigateToStats = { navController.navigate(Screen.Stats.route) },
                onNavigateToProfileAuditor = { navController.navigate(Screen.ProfileAuditor.route) },
                onNavigateToProfileHistory = { navController.navigate(Screen.ProfileHistory.route) },
                onNavigateToProfileOptimizer = { navController.navigate(Screen.ProfileOptimization.route) },
                onShowPaywall = { navController.navigate(Screen.Premium.route) }
            )
        }
        composable(Screen.Settings.route) {
            SettingsScreen(
                onBack = { navController.popBackStack() },
                onPremium = { navController.navigate(Screen.Premium.route) },
                onSignedOut = {
                    navController.navigate(Screen.Onboarding.route) {
                        popUpTo(0) { inclusive = true }
                    }
                }
            )
        }
        composable(Screen.ReplyHistory.route) {
            HistoryScreen(
                onBack = { navController.popBackStack() }
            )
        }
        composable(Screen.Stats.route) {
            StatsScreen(
                onBack = { navController.popBackStack() }
            )
        }
        composable(Screen.Demo.route) {
            DemoScreen(
                onBack = { navController.popBackStack() },
                onSetupApiKey = { navController.popBackStack() },
                onPremium = { navController.navigate(Screen.Premium.route) }
            )
        }
        composable(Screen.Premium.route) {
            val previousRoute = navController.previousBackStackEntry?.destination?.route
            val isFromOnboarding = previousRoute == Screen.Onboarding.route
            
            PaywallScreen(
                onDismiss = {
                    if (isFromOnboarding) {
                        // Coming from onboarding: navigate to Home (onboarding will complete via state)
                        navController.navigate(Screen.Home.route) {
                            popUpTo(Screen.Onboarding.route) { inclusive = true }
                        }
                    } else {
                        // Normal back navigation
                        navController.popBackStack()
                    }
                },
                onPurchaseSuccess = {
                    if (isFromOnboarding) {
                        // Coming from onboarding: navigate to Home after successful purchase
                        navController.navigate(Screen.Home.route) {
                            popUpTo(Screen.Onboarding.route) { inclusive = true }
                        }
                    } else {
                        // Normal flow: just go back
                        navController.popBackStack()
                    }
                }
            )
        }
        composable(Screen.ProfileAuditor.route) {
            ProfileAuditorScreen(
                onBack = { navController.popBackStack() },
                onShowPaywall = { navController.navigate(Screen.Premium.route) }
            )
        }
        composable(Screen.ProfileHistory.route) {
            ProfileHistoryScreen(
                onBack = { navController.popBackStack() },
                onNavigateToOptimizer = { navController.navigate(Screen.ProfileOptimization.route) }
            )
        }
        composable(Screen.ProfileOptimization.route) {
            ProfileOptimizerScreen(
                onBack = { navController.popBackStack() }
            )
        }
    }
}
