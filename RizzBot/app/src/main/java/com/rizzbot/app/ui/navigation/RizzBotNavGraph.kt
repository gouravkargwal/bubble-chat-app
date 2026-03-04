package com.rizzbot.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.NavType
import androidx.navigation.navArgument
import com.rizzbot.app.ui.history.HistoryScreen
import com.rizzbot.app.ui.history.HistoryViewModel
import com.rizzbot.app.ui.history.detail.ConversationDetailScreen
import com.rizzbot.app.ui.history.detail.ConversationDetailViewModel
import com.rizzbot.app.ui.onboarding.OnboardingScreen
import com.rizzbot.app.ui.onboarding.OnboardingViewModel
import com.rizzbot.app.ui.settings.SettingsScreen
import com.rizzbot.app.ui.settings.SettingsViewModel

@Composable
fun RizzBotNavGraph(
    navController: NavHostController,
    hasCompletedOnboarding: Boolean
) {
    val startDestination = if (hasCompletedOnboarding) Screen.Settings.route else Screen.Onboarding.route

    NavHost(navController = navController, startDestination = startDestination) {
        composable(Screen.Onboarding.route) {
            val viewModel: OnboardingViewModel = hiltViewModel()
            OnboardingScreen(
                viewModel = viewModel,
                onOnboardingComplete = {
                    navController.navigate(Screen.Settings.route) {
                        popUpTo(Screen.Onboarding.route) { inclusive = true }
                    }
                }
            )
        }

        composable(Screen.Settings.route) {
            val viewModel: SettingsViewModel = hiltViewModel()
            SettingsScreen(
                viewModel = viewModel,
                onNavigateToHistory = {
                    navController.navigate(Screen.History.route)
                }
            )
        }

        composable(Screen.History.route) {
            val viewModel: HistoryViewModel = hiltViewModel()
            HistoryScreen(
                viewModel = viewModel,
                onBack = { navController.popBackStack() },
                onConversationClick = { personName ->
                    navController.navigate(Screen.ConversationDetail.createRoute(personName))
                }
            )
        }

        composable(
            route = Screen.ConversationDetail.route,
            arguments = listOf(navArgument("personName") { type = NavType.StringType })
        ) {
            val viewModel: ConversationDetailViewModel = hiltViewModel()
            ConversationDetailScreen(
                viewModel = viewModel,
                onBack = { navController.popBackStack() }
            )
        }
    }
}
