package com.rizzbot.v2.capture

import android.graphics.Bitmap
import android.util.Base64
import com.rizzbot.v2.util.Constants
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.max

@Singleton
class ImageCompressor @Inject constructor() {

    suspend fun bitmapToBase64Jpeg(
        bitmap: Bitmap,
        quality: Int = Constants.IMAGE_QUALITY,
        maxDimension: Int = 1024
    ): String = withContext(Dispatchers.Default) {

        val longestEdge = max(bitmap.width, bitmap.height)

        val scaled = if (longestEdge > maxDimension) {
            val ratio = maxDimension.toFloat() / longestEdge
            val newWidth = (bitmap.width * ratio).toInt()
            val newHeight = (bitmap.height * ratio).toInt()
            Bitmap.createScaledBitmap(bitmap, newWidth, newHeight, true)
        } else {
            bitmap
        }

        val byteArray = ByteArrayOutputStream().use { stream ->
            scaled.compress(Bitmap.CompressFormat.JPEG, quality, stream)
            stream.toByteArray()
        }

        if (scaled !== bitmap) {
            scaled.recycle()
        }

        Base64.encodeToString(byteArray, Base64.NO_WRAP)
    }

    suspend fun bitmapToJpegByteArray(
        bitmap: Bitmap,
        quality: Int = Constants.IMAGE_QUALITY,
        maxDimension: Int = 1024
    ): ByteArray = withContext(Dispatchers.Default) {
        val longestEdge = max(bitmap.width, bitmap.height)
        val scaled = if (longestEdge > maxDimension) {
            val ratio = maxDimension.toFloat() / longestEdge
            val newWidth = (bitmap.width * ratio).toInt()
            val newHeight = (bitmap.height * ratio).toInt()
            Bitmap.createScaledBitmap(bitmap, newWidth, newHeight, true)
        } else {
            bitmap
        }

        val byteArray = ByteArrayOutputStream().use { stream ->
            scaled.compress(Bitmap.CompressFormat.JPEG, quality, stream)
            stream.toByteArray()
        }

        if (scaled !== bitmap) {
            scaled.recycle()
        }
        byteArray
    }
}
