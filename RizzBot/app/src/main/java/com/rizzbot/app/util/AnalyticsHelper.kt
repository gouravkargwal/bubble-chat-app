package com.rizzbot.app.util

import android.os.Bundle
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.analytics.ktx.analytics
import com.google.firebase.crashlytics.ktx.crashlytics
import com.google.firebase.ktx.Firebase
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AnalyticsHelper @Inject constructor() {

    private val analytics: FirebaseAnalytics by lazy { Firebase.analytics }
    private val crashlytics by lazy { Firebase.crashlytics }

    fun logEvent(name: String, params: Map<String, String> = emptyMap()) {
        val bundle = Bundle().apply {
            params.forEach { (key, value) -> putString(key, value) }
        }
        analytics.logEvent(name, bundle)
    }

    fun logReplyGenerated(provider: String, tone: String) {
        logEvent("reply_generated", mapOf("provider" to provider, "tone" to tone))
    }

    fun logProviderSelected(provider: String) {
        logEvent("provider_selected", mapOf("provider" to provider))
    }

    fun logProfileSynced() {
        logEvent("profile_synced")
    }

    fun logOnboardingCompleted() {
        logEvent("onboarding_completed")
    }

    fun logToneSelected(tone: String) {
        logEvent("tone_selected", mapOf("tone" to tone))
    }

    fun logRizzButtonClicked() {
        logEvent("rizz_button_clicked")
    }

    fun logIcebreakerClicked() {
        logEvent("icebreaker_clicked")
    }

    fun logSuggestionCopied() {
        logEvent("suggestion_copied")
    }

    fun logSuggestionPasted() {
        logEvent("suggestion_pasted")
    }

    fun logRefreshReplies() {
        logEvent("refresh_replies")
    }

    fun logChatScreenEntered(personName: String) {
        logEvent("chat_screen_entered", mapOf("person" to personName))
    }

    fun logError(message: String, throwable: Throwable? = null) {
        crashlytics.log(message)
        throwable?.let { crashlytics.recordException(it) }
    }

    fun setUserProperty(key: String, value: String) {
        analytics.setUserProperty(key, value)
    }
}
