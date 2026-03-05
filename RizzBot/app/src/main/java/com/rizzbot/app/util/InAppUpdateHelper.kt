package com.rizzbot.app.util

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.net.HttpURLConnection
import java.net.URL

@Serializable
data class GitHubRelease(
    val tag_name: String,
    val html_url: String,
    val assets: List<GitHubAsset> = emptyList()
)

@Serializable
data class GitHubAsset(
    val name: String,
    val browser_download_url: String
)

data class UpdateInfo(
    val latestVersion: String,
    val downloadUrl: String,
    val releaseUrl: String,
    val isUpdateAvailable: Boolean
)

object InAppUpdateHelper {

    private const val TAG = "InAppUpdate"
    private const val REPO = "gouravkargwal/bubble-chat-app"

    private val json = Json { ignoreUnknownKeys = true }

    suspend fun checkForUpdate(currentVersion: String): UpdateInfo? = withContext(Dispatchers.IO) {
        try {
            val url = URL("https://api.github.com/repos/$REPO/releases/latest")
            val connection = url.openConnection() as HttpURLConnection
            connection.requestMethod = "GET"
            connection.setRequestProperty("Accept", "application/vnd.github.v3+json")
            connection.connectTimeout = 10_000
            connection.readTimeout = 10_000

            if (connection.responseCode != 200) {
                Log.d(TAG, "GitHub API returned ${connection.responseCode}")
                return@withContext null
            }

            val body = connection.inputStream.bufferedReader().readText()
            val release = json.decodeFromString<GitHubRelease>(body)

            val latestVersion = release.tag_name.removePrefix("v")
            val apkAsset = release.assets.firstOrNull { it.name.endsWith(".apk") }

            val isNewer = isNewerVersion(currentVersion, latestVersion)

            Log.d(TAG, "Current: $currentVersion, Latest: $latestVersion, Update: $isNewer")

            UpdateInfo(
                latestVersion = latestVersion,
                downloadUrl = apkAsset?.browser_download_url ?: release.html_url,
                releaseUrl = release.html_url,
                isUpdateAvailable = isNewer
            )
        } catch (e: Exception) {
            Log.d(TAG, "Update check failed: ${e.message}")
            null
        }
    }

    private fun isNewerVersion(current: String, latest: String): Boolean {
        val currentParts = current.split(".").mapNotNull { it.toIntOrNull() }
        val latestParts = latest.split(".").mapNotNull { it.toIntOrNull() }

        for (i in 0 until maxOf(currentParts.size, latestParts.size)) {
            val c = currentParts.getOrElse(i) { 0 }
            val l = latestParts.getOrElse(i) { 0 }
            if (l > c) return true
            if (l < c) return false
        }
        return false
    }
}
