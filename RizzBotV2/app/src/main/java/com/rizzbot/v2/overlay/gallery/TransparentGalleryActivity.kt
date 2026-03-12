package com.rizzbot.v2.overlay.gallery

import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.lifecycle.lifecycleScope
import com.rizzbot.v2.capture.ImageCompressor
import com.rizzbot.v2.overlay.manager.BubbleManager
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Transparent activity that briefly appears above the current app to let the user
 * pick a photo from the gallery, then hands the result back to the overlay bubble.
 */
@AndroidEntryPoint
class TransparentGalleryActivity : ComponentActivity() {

    @Inject lateinit var bubbleManager: BubbleManager
    @Inject lateinit var imageCompressor: ImageCompressor

    private val pickMedia = registerForActivityResult(
        ActivityResultContracts.PickVisualMedia()
    ) { uri: Uri? ->
        if (uri == null) {
            // User cancelled
            bubbleManager.handleGalleryResult(null)
            finish()
        } else {
            handlePickedUri(uri)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Immediately launch the picker; this activity itself shows no UI chrome.
        pickMedia.launch(
            androidx.activity.result.PickVisualMediaRequest(
                ActivityResultContracts.PickVisualMedia.ImageOnly
            )
        )
    }

    private fun handlePickedUri(uri: Uri) {
        lifecycleScope.launch {
            try {
                val bitmap = contentResolver.openInputStream(uri)?.use { input ->
                    android.graphics.BitmapFactory.decodeStream(input)
                }

                if (bitmap == null) {
                    bubbleManager.handleGalleryResult(null)
                    finish()
                    return@launch
                }

                val base64 = imageCompressor.bitmapToBase64Jpeg(bitmap)
                // Let the bubble manager drive loading state and reply generation.
                bubbleManager.handleGalleryResult(base64)
            } catch (_: Exception) {
                bubbleManager.handleGalleryResult(null)
            } finally {
                finish()
            }
        }
    }
}

