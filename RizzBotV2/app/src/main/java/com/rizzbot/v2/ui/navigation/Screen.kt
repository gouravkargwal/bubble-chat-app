package com.rizzbot.v2.ui.navigation

sealed class Screen(val route: String) {
    data object Onboarding : Screen("onboarding")
    data object Home : Screen("home")
    data object Settings : Screen("settings")
    data object ReplyHistory : Screen("reply_history")
    data object Stats : Screen("stats")
    data object Demo : Screen("demo")
    data object ProfileOptimization : Screen("profile_optimization")
    data object SyncPerson : Screen("sync_person")
    data object Premium : Screen("premium")
    data object ProfileAuditor : Screen("profile_auditor")
    data object ProfileHistory : Screen("profile_history")
    data object ProfileStrategy : Screen("profile_strategy")
}
