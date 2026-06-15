package com.rizzbot.v2.capture

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.os.Bundle
import android.util.Log
import com.rizzbot.v2.util.Constants

class CaptureConsentActivity : Activity() {

    /** Guards against double-delivering the consent result (onActivityResult + onDestroy fallback). */
    private var resultDelivered = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        try {
            val mediaProjectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            startActivityForResult(
                mediaProjectionManager.createScreenCaptureIntent(),
                Constants.CAPTURE_REQUEST_CODE
            )
        } catch (e: Exception) {
            // If the consent intent can't be launched, deliver a cancellation so the waiting
            // capture coroutine resumes instead of hanging forever.
            Log.e("CaptureConsent", "Failed to launch screen-capture consent", e)
            deliverResult(RESULT_CANCELED, null)
            finish()
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == Constants.CAPTURE_REQUEST_CODE) {
            deliverResult(resultCode, data)
        }
        finish()
    }

    override fun onDestroy() {
        // Fallback: if the activity is torn down before a result was delivered (e.g. killed by
        // the system or swiped away), resolve the pending consent as cancelled so the capture
        // coroutine never waits forever — which would leave the bubble stuck/invisible.
        if (!resultDelivered) {
            deliverResult(RESULT_CANCELED, null)
        }
        super.onDestroy()
    }

    private fun deliverResult(resultCode: Int, data: Intent?) {
        if (resultDelivered) return
        resultDelivered = true
        ScreenCaptureManager.onConsentResult(resultCode, data)
    }
}
