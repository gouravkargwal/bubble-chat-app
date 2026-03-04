package com.rizzbot.app.ui.navigation

sealed class Screen(val route: String) {
    data object Onboarding : Screen("onboarding")
    data object Settings : Screen("settings")
    data object History : Screen("history")
    data object ConversationDetail : Screen("conversation_detail/{personName}") {
        fun createRoute(personName: String): String = "conversation_detail/$personName"
    }
}
