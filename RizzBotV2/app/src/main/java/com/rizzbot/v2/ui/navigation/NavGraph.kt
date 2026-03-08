package com.rizzbot.v2.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.rizzbot.v2.ui.demo.DemoScreen
import com.rizzbot.v2.ui.history.HistoryScreen
import com.rizzbot.v2.ui.home.HomeScreen
import com.rizzbot.v2.ui.onboarding.OnboardingScreen
import com.rizzbot.v2.ui.premium.PremiumScreen
import com.rizzbot.v2.ui.profile.ProfileOptimizationScreen
import com.rizzbot.v2.ui.settings.SettingsScreen
import com.rizzbot.v2.ui.stats.StatsScreen
import com.rizzbot.v2.ui.sync.SyncPersonScreen

@Composable
fun NavGraph(
    navController: NavHostController,
    startDestination: String
) {
    NavHost(
        navController = navController,
        startDestination = startDestination
    ) {
        composable(Screen.Onboarding.route) {
            OnboardingScreen(
                onComplete = {
                    navController.navigate(Screen.Home.route) {
                        popUpTo(Screen.Onboarding.route) { inclusive = true }
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
                onNavigateToOptimize = { navController.navigate(Screen.ProfileOptimization.route) },
                onNavigateToSync = { navController.navigate(Screen.SyncPerson.route) }
            )
        }
        composable(Screen.Settings.route) {
            SettingsScreen(
                onBack = { navController.popBackStack() }
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
                onSetupApiKey = { navController.popBackStack() }
            )
        }
        composable(Screen.ProfileOptimization.route) {
            ProfileOptimizationScreen(
                onBack = { navController.popBackStack() }
            )
        }
        composable(Screen.SyncPerson.route) {
            SyncPersonScreen(
                onBack = { navController.popBackStack() }
            )
        }
        composable(Screen.Premium.route) {
            PremiumScreen(
                onBack = { navController.popBackStack() }
            )
        }
    }
}
