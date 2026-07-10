package com.rizzbot.v2.util

import android.os.Build
import android.os.Bundle
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.analytics.ktx.analytics
import com.google.firebase.crashlytics.ktx.crashlytics
import com.google.firebase.ktx.Firebase
import com.rizzbot.v2.BuildConfig
import com.rizzbot.v2.data.remote.api.HostedApi
import com.rizzbot.v2.data.remote.dto.ClientErrorRequest
import dagger.Lazy
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

@Singleton
class AnalyticsHelper @Inject constructor(
    // Lazy: HostedApi -> OkHttpClient -> AuthInterceptor -> AnalyticsHelper would
    // otherwise be a dependency cycle; Lazy defers construction past this point.
    private val hostedApi: Lazy<HostedApi>
) {

    private val analytics: FirebaseAnalytics by lazy { Firebase.analytics }
    private val crashlytics by lazy { Firebase.crashlytics }
    private val telemetryScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

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

    /** Screen view — call from each screen's entry point (e.g. LaunchedEffect(Unit)). */
    fun screenViewed(screenName: String) {
        logEvent(FirebaseAnalytics.Event.SCREEN_VIEW, mapOf(FirebaseAnalytics.Param.SCREEN_NAME to screenName))
        crashlytics.log("screen_view: $screenName")
    }

    /** Breadcrumb — leaves a trail in Crashlytics without any error. */
    fun log(message: String) {
        crashlytics.log(message)
    }

    /**
     * Non-fatal error — records to Crashlytics without crashing the app.
     * Use in catch blocks for failures that are handled but still worth investigating
     * (network errors, unexpected null state, silent purchase/auth failures).
     */
    fun recordNonFatal(throwable: Throwable, context: String? = null) {
        context?.let { crashlytics.log(it) }
        crashlytics.recordException(throwable)
        reportToBackend(
            errorType = throwable::class.java.simpleName,
            message = throwable.message ?: "",
            screen = context,
            stackTrace = throwable.stackTraceToString().take(4000)
        )
    }

    /**
     * Best-effort mirror of app-side errors into the backend's OpenObserve pipeline
     * (tagged layer="mobile"), so they show up next to backend errors instead of
     * only in Crashlytics. Never throws, never blocks the caller.
     */
    private fun reportToBackend(
        errorType: String,
        message: String,
        screen: String?,
        severity: String = "warning",
        stackTrace: String? = null
    ) {
        telemetryScope.launch {
            try {
                hostedApi.get().reportClientError(
                    ClientErrorRequest(
                        errorType = errorType,
                        message = message,
                        screen = screen,
                        severity = severity,
                        appVersion = BuildConfig.VERSION_NAME,
                        osVersion = Build.VERSION.RELEASE,
                        deviceModel = "${Build.MANUFACTURER} ${Build.MODEL}",
                        stackTrace = stackTrace
                    )
                )
            } catch (_: Exception) {
                // Swallow — telemetry reporting must never surface an error of its own.
            }
        }
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
