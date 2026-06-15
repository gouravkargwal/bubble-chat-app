package com.rizzbot.v2.overlay.gallery

import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.lifecycleScope
import com.rizzbot.v2.capture.ImageCompressor
import com.rizzbot.v2.overlay.manager.BubbleManager
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import javax.inject.Inject

/**
 * Transparent activity that briefly appears above the current app to let the user
 * pick one or more photos from the gallery, then hands the results back to the overlay bubble.
 *
 * The number of selectable images is capped by [EXTRA_MAX_ITEMS] (the user's per-request tier
 * limit). When the cap is 1 we use the single-item picker; otherwise the multi-select picker.
 */
@AndroidEntryPoint
class TransparentGalleryActivity : ComponentActivity() {

    @Inject lateinit var bubbleManager: BubbleManager
    @Inject lateinit var imageCompressor: ImageCompressor

    private val imageRequest = PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)

    // Registered unconditionally (before STARTED) so the result survives recreation. The single
    // picker is used when maxItems <= 1, the multi picker otherwise.
    private val pickSingle = registerForActivityResult(
        ActivityResultContracts.PickVisualMedia()
    ) { uri: Uri? -> handleUris(listOfNotNull(uri)) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val maxItems = intent.getIntExtra(EXTRA_MAX_ITEMS, 1).coerceAtLeast(1)

        try {
            if (maxItems <= 1) {
                pickSingle.launch(imageRequest)
            } else {
                // PickMultipleVisualMedia requires maxItems >= 2; registered here because the cap
                // is only known at launch time (still before STARTED, so registration is valid).
                val pickMultiple = registerForActivityResult(
                    ActivityResultContracts.PickMultipleVisualMedia(maxItems)
                ) { uris: List<Uri> -> handleUris(uris) }
                pickMultiple.launch(imageRequest)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to launch photo picker", e)
            bubbleManager.handleGalleryResult(null)
            finish()
        }
    }

    private fun handleUris(uris: List<Uri>) {
        if (uris.isEmpty()) {
            // User cancelled.
            bubbleManager.handleGalleryResult(null)
            finish()
            return
        }

        lifecycleScope.launch {
            val base64List = withContext(Dispatchers.IO) {
                uris.mapNotNull { uri ->
                    runCatching {
                        contentResolver.openInputStream(uri)?.use { input ->
                            BitmapFactory.decodeStream(input)
                        }?.let { bitmap -> imageCompressor.bitmapToBase64Jpeg(bitmap) }
                    }.getOrNull()
                }
            }
            // Pass null when nothing decoded so the bubble returns to the picker rather than
            // generating from an empty list.
            bubbleManager.handleGalleryResult(base64List.ifEmpty { null })
            finish()
        }
    }

    companion object {
        private const val TAG = "TransparentGallery"
        const val EXTRA_MAX_ITEMS = "extra_max_items"
    }
}
