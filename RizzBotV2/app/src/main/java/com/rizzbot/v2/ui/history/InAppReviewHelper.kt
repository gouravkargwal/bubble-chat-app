package com.rizzbot.v2.ui.history

import android.app.Activity
import android.content.Context
import com.google.android.play.core.review.ReviewManagerFactory

/**
 * Launches the Google Play In-App Review flow.
 *
 * NOTE: Ensure you have:
 * implementation("com.google.android.play:review:2.0.1")
 * (or the latest version) in your app/build.gradle.kts dependencies.
 */
fun launchInAppReview(context: Context) {
    val activity = context as? Activity ?: return
    val manager = ReviewManagerFactory.create(context)
    val request = manager.requestReviewFlow()
    request.addOnCompleteListener { task ->
        if (task.isSuccessful) {
            val reviewInfo = task.result
            val flow = manager.launchReviewFlow(activity, reviewInfo)
            flow.addOnCompleteListener {
                // Review flow finished; no further action required.
            }
        } else {
            // Failed to start review flow; ignore silently.
        }
    }
}

