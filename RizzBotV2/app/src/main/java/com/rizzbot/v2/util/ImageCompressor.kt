package com.rizzbot.v2.util

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.InputStream
import kotlin.math.max

suspend fun compressImage(
    context: Context,
    uri: Uri,
    maxWidth: Int = 1024,
    maxHeight: Int = 1024,
    quality: Int = 75
): ByteArray? = withContext(Dispatchers.IO) {
    val resolver = context.contentResolver

    // 1) Read EXIF rotation FIRST (Needs a fresh stream)
    val rotationDegrees = resolver.openInputStream(uri)?.use { stream ->
        exifToDegrees(readExifOrientation(stream))
    } ?: 0f

    // 2) Bounds-only decode to prevent OOM
    val boundsOptions = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    resolver.openInputStream(uri)?.use { stream ->
        BitmapFactory.decodeStream(stream, null, boundsOptions)
    }
    
    if (boundsOptions.outWidth <= 0 || boundsOptions.outHeight <= 0) {
        return@withContext null // Invalid image
    }

    // 3) Calculate safe sample size
    boundsOptions.inSampleSize = calculateInSampleSize(
        boundsOptions.outWidth, 
        boundsOptions.outHeight, 
        maxWidth, 
        maxHeight
    )
    boundsOptions.inJustDecodeBounds = false // Now we are ready to actually load it

    // 4) Safely load the downscaled bitmap into memory
    val sampledBitmap: Bitmap = resolver.openInputStream(uri)?.use { stream ->
        BitmapFactory.decodeStream(stream, null, boundsOptions)
    } ?: return@withContext null

    // 5) Apply EXIF Rotation
    val rotatedBitmap = if (rotationDegrees != 0f) {
        val matrix = Matrix().apply { postRotate(rotationDegrees) }
        val rotated = Bitmap.createBitmap(
            sampledBitmap, 0, 0, sampledBitmap.width, sampledBitmap.height, matrix, true
        )
        if (rotated !== sampledBitmap) sampledBitmap.recycle()
        rotated
    } else {
        sampledBitmap
    }

    // 6) Exact clamp (inSampleSize only does powers of 2, so it might still be slightly too big)
    val finalBitmap = if (rotatedBitmap.width > maxWidth || rotatedBitmap.height > maxHeight) {
        val ratio = minOf(
            maxWidth.toFloat() / rotatedBitmap.width,
            maxHeight.toFloat() / rotatedBitmap.height
        )
        val targetW = (rotatedBitmap.width * ratio).toInt().coerceAtLeast(1)
        val targetH = (rotatedBitmap.height * ratio).toInt().coerceAtLeast(1)
        val scaled = Bitmap.createScaledBitmap(rotatedBitmap, targetW, targetH, true)
        if (scaled !== rotatedBitmap) rotatedBitmap.recycle()
        scaled
    } else {
        rotatedBitmap
    }

    // 7) Compress to JPEG Bytes
    val byteArray = ByteArrayOutputStream().use { stream ->
        finalBitmap.compress(Bitmap.CompressFormat.JPEG, quality, stream)
        stream.toByteArray()
    }

    finalBitmap.recycle()

    byteArray
}

private fun calculateInSampleSize(width: Int, height: Int, reqWidth: Int, reqHeight: Int): Int {
    var inSampleSize = 1
    if (height > reqHeight || width > reqWidth) {
        val halfHeight = height / 2
        val halfWidth = width / 2
        while ((halfHeight / inSampleSize) >= reqHeight && (halfWidth / inSampleSize) >= reqWidth) {
            inSampleSize *= 2
        }
    }
    return max(1, inSampleSize)
}

private fun readExifOrientation(inputStream: InputStream): Int {
    return try {
        val exif = ExifInterface(inputStream)
        exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_UNDEFINED)
    } catch (e: Exception) {
        ExifInterface.ORIENTATION_UNDEFINED
    }
}

private fun exifToDegrees(orientation: Int): Float = when (orientation) {
    ExifInterface.ORIENTATION_ROTATE_90 -> 90f
    ExifInterface.ORIENTATION_ROTATE_180 -> 180f
    ExifInterface.ORIENTATION_ROTATE_270 -> 270f
    else -> 0f
}