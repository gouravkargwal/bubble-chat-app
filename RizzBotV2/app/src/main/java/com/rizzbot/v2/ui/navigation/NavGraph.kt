package com.rizzbot.v2.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.rizzbot.v2.ui.demo.DemoScreen
import com.rizzbot.v2.ui.legal.LegalDocumentKind
import com.rizzbot.v2.ui.legal.LegalDocumentScreen
import com.rizzbot.v2.ui.history.HistoryScreen
import com.rizzbot.v2.ui.home.HomeScreen
import com.rizzbot.v2.ui.onboarding.OnboardingScreen
import com.rizzbot.v2.ui.profile.ProfileAuditorScreen
import com.rizzbot.v2.ui.profile.ProfileHistoryScreen
import com.rizzbot.v2.ui.profile.ProfileOptimizerScreen
import com.rizzbot.v2.ui.profile.ProfileStrategyScreen
import com.rizzbot.v2.ui.paywall.PaywallScreen
import com.rizzbot.v2.ui.settings.SettingsScreen
import com.rizzbot.v2.ui.stats.StatsScreen

@Composable
fun NavGraph(
    navController: NavHostController,
    startDestination: String,
    onboardingResumeForSignIn: Boolean = false
) {
    NavHost(
        navController = navController,
        startDestination = startDestination,
        enterTransition = { defaultEnterTransition() },
        exitTransition = { defaultExitTransition() },
        popEnterTransition = { defaultPopEnterTransition() },
        popExitTransition = { defaultPopExitTransition() },
    ) {
        composable(Screen.Onboarding.route) {
            OnboardingScreen(
                isResumeSignIn = onboardingResumeForSignIn,
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
                },
                onOpenTerms = { navController.navigate(Screen.LegalTerms.route) },
                onOpenPrivacy = { navController.navigate(Screen.LegalPrivacy.route) }
            )
        }
        composable(Screen.Home.route) {
            HomeScreen(
                onNavigateToSettings = { navController.navigate(Screen.Settings.route) },
                onNavigateToHistory = { navController.navigate(Screen.ReplyHistory.route) },
                onNavigateToStats = { navController.navigate(Screen.Stats.route) },
                onNavigateToProfileAuditor = { navController.navigate(Screen.ProfileAuditor.route) },
                onNavigateToProfileOptimizer = { navController.navigate(Screen.ProfileOptimization.route) },
                onNavigateToProfileStrategy = { navController.navigate(Screen.ProfileStrategy.route) },
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
                },
                onOpenTerms = { navController.navigate(Screen.LegalTerms.route) },
                onOpenPrivacy = { navController.navigate(Screen.LegalPrivacy.route) }
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
                onContinue = { navController.popBackStack() },
                onPremium = { navController.navigate(Screen.Premium.route) }
            )
        }
        composable(
            route = Screen.Premium.route,
            enterTransition = { paywallEnterTransition() },
            exitTransition = { paywallExitTransition() },
            popEnterTransition = { paywallPopEnterTransition() },
            popExitTransition = { paywallPopExitTransition() },
        ) {
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
                },
                onOpenTerms = { navController.navigate(Screen.LegalTerms.route) },
                onOpenPrivacy = { navController.navigate(Screen.LegalPrivacy.route) }
            )
        }
        composable(
            route = Screen.LegalTerms.route,
            enterTransition = { legalEnterTransition() },
            exitTransition = { legalExitTransition() },
            popEnterTransition = { legalPopEnterTransition() },
            popExitTransition = { legalPopExitTransition() },
        ) {
            LegalDocumentScreen(
                kind = LegalDocumentKind.TERMS,
                onBack = { navController.popBackStack() }
            )
        }
        composable(
            route = Screen.LegalPrivacy.route,
            enterTransition = { legalEnterTransition() },
            exitTransition = { legalExitTransition() },
            popEnterTransition = { legalPopEnterTransition() },
            popExitTransition = { legalPopExitTransition() },
        ) {
            LegalDocumentScreen(
                kind = LegalDocumentKind.PRIVACY,
                onBack = { navController.popBackStack() }
            )
        }
        composable(Screen.ProfileAuditor.route) {
            ProfileAuditorScreen(
                onBack = { navController.popBackStack() },
                onShowPaywall = { navController.navigate(Screen.Premium.route) },
                onOpenPastPhotoAudits = { navController.navigate(Screen.ProfileHistory.route) }
            )
        }
        composable(Screen.ProfileHistory.route) {
            ProfileHistoryScreen(
                onBack = { navController.popBackStack() }
            )
        }
        composable(Screen.ProfileOptimization.route) {
            ProfileOptimizerScreen(
                onBack = { navController.popBackStack() },
                onViewStrategy = { navController.navigate(Screen.ProfileStrategy.route) }
            )
        }
        composable(Screen.ProfileStrategy.route) {
            ProfileStrategyScreen(
                onBack = { navController.popBackStack() }
            )
        }
    }
}
