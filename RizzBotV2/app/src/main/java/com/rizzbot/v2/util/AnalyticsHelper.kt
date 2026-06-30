package com.rizzbot.v2.util

import android.os.Bundle
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.analytics.ktx.analytics
import com.google.firebase.ktx.Firebase
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AnalyticsHelper @Inject constructor() {

    private val analytics: FirebaseAnalytics by lazy { Firebase.analytics }

    fun logEvent(event: String, params: Map<String, Any?> = emptyMap()) {
        val bundle = Bundle().apply {
            params.forEach { (key, value) ->
                when (value) {
                    is String -> putString(key, value)
                    is Int -> putInt(key, value)
                    is Long -> putLong(key, value)
                    is Double -> putDouble(key, value)
                    is Boolean -> putBoolean(key, value)
                }
            }
        }
        analytics.logEvent(event, bundle)
    }

    fun setUserProperty(key: String, value: String?) {
        analytics.setUserProperty(key, value)
    }

    // Onboarding
    fun onboardingStarted() = logEvent("onboarding_started")
    fun onboardingStepCompleted(step: Int) = logEvent("onboarding_step_completed", mapOf("step" to step))
    fun onboardingCompleted() = logEvent("onboarding_completed")

    // Capture & Reply
    fun bubbleTapped() = logEvent("bubble_tapped")
    fun directionSelected(direction: String) = logEvent("direction_selected", mapOf("direction" to direction))
    fun screenshotCaptured() = logEvent("screenshot_captured")
    fun screenshotFailed(reason: String) = logEvent("screenshot_failed", mapOf("reason" to reason))
    fun replyGenerated(provider: String, latencyMs: Long) = logEvent("reply_generated", mapOf("provider" to provider, "latency_ms" to latencyMs))
    fun replyFailed(provider: String, error: String) = logEvent("reply_failed", mapOf("provider" to provider, "error" to error))
    fun replyCopied(vibeIndex: Int) = logEvent("reply_copied", mapOf("vibe_index" to vibeIndex))
    fun replyRated(vibeIndex: Int, isPositive: Boolean) = logEvent("reply_rated", mapOf("vibe_index" to vibeIndex, "is_positive" to isPositive))
    fun replyRegenerated() = logEvent("reply_regenerated")
    fun sessionMemoryUsed(turnCount: Int) = logEvent("session_memory_used", mapOf("turn_count" to turnCount))

    // Usage & Premium
    fun quotaExhausted() = logEvent("quota_exhausted")
    fun premiumViewed() = logEvent("premium_viewed")
    fun authCompleted() = logEvent("auth_completed")
}
