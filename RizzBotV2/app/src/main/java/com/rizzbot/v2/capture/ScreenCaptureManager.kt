package com.rizzbot.v2.capture

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.DisplayMetrics
import android.view.WindowManager
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.suspendCancellableCoroutine
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

@Singleton
class ScreenCaptureManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null

    companion object {
        private var pendingConsentCallback: ((resultCode: Int, data: Intent?) -> Unit)? = null

        fun onConsentResult(resultCode: Int, data: Intent?) {
            pendingConsentCallback?.invoke(resultCode, data)
            pendingConsentCallback = null
        }
    }

    suspend fun requestConsent(): Pair<Int, Intent?> = suspendCancellableCoroutine { cont ->
        pendingConsentCallback = { resultCode, data ->
            cont.resume(Pair(resultCode, data))
        }
        cont.invokeOnCancellation { pendingConsentCallback = null }

        val intent = Intent(context, CaptureConsentActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    suspend fun captureScreenshot(resultCode: Int, data: Intent?): Bitmap {
        if (resultCode != Activity.RESULT_OK || data == null) {
            throw CaptureException("User denied screen capture permission")
        }

        // Start foreground service with mediaProjection type before creating projection
        CaptureService.start(context)
        // Small delay to let the foreground service start
        kotlinx.coroutines.delay(200)

        try {
            val projectionManager = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            mediaProjection = projectionManager.getMediaProjection(resultCode, data)
                ?: throw CaptureException("Failed to create MediaProjection")

            val bitmap = captureFrame()
            return bitmap
        } finally {
            CaptureService.stop(context)
        }
    }

    private suspend fun captureFrame(): Bitmap = suspendCancellableCoroutine { cont ->
        val wm = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val metrics = DisplayMetrics()
        @Suppress("DEPRECATION")
        wm.defaultDisplay.getRealMetrics(metrics)

        val width = metrics.widthPixels
        val height = metrics.heightPixels
        val density = metrics.densityDpi

        val imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
        val handler = Handler(Looper.getMainLooper())

        // Android 14+ requires registering a callback before createVirtualDisplay
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            mediaProjection?.registerCallback(object : MediaProjection.Callback() {
                override fun onStop() {
                    releaseCapture(imageReader)
                }
            }, handler)
        }

        virtualDisplay = mediaProjection?.createVirtualDisplay(
            "RizzBotCapture",
            width, height, density,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader.surface,
            null, handler
        )

        // Delay slightly to let the virtual display render a frame
        handler.postDelayed({
            try {
                val image = imageReader.acquireLatestImage()
                if (image != null) {
                    val planes = image.planes
                    val buffer = planes[0].buffer
                    val pixelStride = planes[0].pixelStride
                    val rowStride = planes[0].rowStride
                    val rowPadding = rowStride - pixelStride * width

                    val bitmap = Bitmap.createBitmap(
                        width + rowPadding / pixelStride,
                        height,
                        Bitmap.Config.ARGB_8888
                    )
                    bitmap.copyPixelsFromBuffer(buffer)
                    image.close()

                    // Crop to actual screen width (remove row padding)
                    val croppedBitmap = if (rowPadding > 0) {
                        Bitmap.createBitmap(bitmap, 0, 0, width, height).also {
                            bitmap.recycle()
                        }
                    } else {
                        bitmap
                    }

                    releaseCapture(imageReader)
                    cont.resume(croppedBitmap)
                } else {
                    releaseCapture(imageReader)
                    cont.resumeWithException(CaptureException("Failed to acquire image"))
                }
            } catch (e: Exception) {
                releaseCapture(imageReader)
                cont.resumeWithException(CaptureException("Capture failed: ${e.message}"))
            }
        }, 150)

        cont.invokeOnCancellation { releaseCapture(imageReader) }
    }

    private fun releaseCapture(imageReader: ImageReader? = null) {
        try {
            virtualDisplay?.release()
            virtualDisplay = null
            imageReader?.close()
            mediaProjection?.stop()
            mediaProjection = null
        } catch (_: Exception) {}
    }
}

class CaptureException(message: String) : Exception(message)
