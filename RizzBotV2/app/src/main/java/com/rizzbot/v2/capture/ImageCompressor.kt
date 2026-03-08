package com.rizzbot.v2.capture

import android.graphics.Bitmap
import android.util.Base64
import com.rizzbot.v2.util.Constants
import java.io.ByteArrayOutputStream
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ImageCompressor @Inject constructor() {

    fun bitmapToBase64Jpeg(
        bitmap: Bitmap,
        quality: Int = Constants.IMAGE_QUALITY,
        maxWidth: Int = Constants.IMAGE_MAX_WIDTH
    ): String {
        val scaled = if (bitmap.width > maxWidth) {
            val ratio = maxWidth.toFloat() / bitmap.width
            val newHeight = (bitmap.height * ratio).toInt()
            Bitmap.createScaledBitmap(bitmap, maxWidth, newHeight, true)
        } else {
            bitmap
        }

        val stream = ByteArrayOutputStream()
        scaled.compress(Bitmap.CompressFormat.JPEG, quality, stream)
        val byteArray = stream.toByteArray()

        if (scaled !== bitmap) {
            scaled.recycle()
        }

        return Base64.encodeToString(byteArray, Base64.NO_WRAP)
    }
}
