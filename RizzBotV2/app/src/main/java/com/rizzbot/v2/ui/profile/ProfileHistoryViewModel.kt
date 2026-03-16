package com.rizzbot.v2.ui.profile

import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import androidx.core.content.FileProvider
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.domain.repository.HostedRepository
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ProfileHistoryViewModel @Inject constructor(
    private val repository: HostedRepository,
    @ApplicationContext private val context: Context,
) : ViewModel() {

    private val _audits = MutableStateFlow<List<HistoryItem>>(emptyList())
    val audits: StateFlow<List<HistoryItem>> = _audits.asStateFlow()

    private var currentOffset = 0
    private var isLastPage = false
    private var isLoading = false

    // Expose isLoading as StateFlow for UI
    private val _isLoadingState = MutableStateFlow(false)
    val isLoadingState: StateFlow<Boolean> = _isLoadingState.asStateFlow()

    private val _isSharingState = MutableStateFlow(false)
    val isSharingState: StateFlow<Boolean> = _isSharingState.asStateFlow()

    private val pageSize = 20

    init {
        fetchNextPage()
    }

    fun fetchNextPage() {
        if (isLoading || isLastPage) return

        viewModelScope.launch {
            isLoading = true
            _isLoadingState.value = true
            try {
                val dtoItems = repository.getProfileAuditHistory(limit = pageSize, offset = currentOffset)
                val mapped = dtoItems.map {
                    HistoryItem(
                        id = it.id,
                        imageUrl = it.imageUrl,
                        score = it.score,
                        tier = it.tier,
                        brutalFeedback = it.brutalFeedback,
                        improvementTip = it.improvementTip,
                        createdAt = it.createdAt,
                        archetypeTitle = it.archetypeTitle,
                        roastSummary = it.roastSummary,
                        shareCardColor = it.shareCardColor,
                    )
                }
                _audits.value = _audits.value + mapped.sortedByDescending { it.score }
                currentOffset += pageSize
                if (dtoItems.size < pageSize) {
                    isLastPage = true
                }
            } catch (e: Exception) {
                android.util.Log.e("ProfileHistoryVM", "fetchNextPage failed: ${e.message}")
                // Rollback offset on error
                currentOffset = (_audits.value.size / pageSize) * pageSize
            } finally {
                isLoading = false
                _isLoadingState.value = false
            }
        }
    }

    fun refresh() {
        viewModelScope.launch {
            isLoading = true
            _isLoadingState.value = true
            currentOffset = 0
            isLastPage = false
            _audits.value = emptyList()
            try {
                val dtoItems = repository.getProfileAuditHistory(limit = pageSize, offset = 0)
                val mapped = dtoItems.map {
                    HistoryItem(
                        id = it.id,
                        imageUrl = it.imageUrl,
                        score = it.score,
                        tier = it.tier,
                        brutalFeedback = it.brutalFeedback,
                        improvementTip = it.improvementTip,
                        createdAt = it.createdAt,
                        archetypeTitle = it.archetypeTitle,
                        roastSummary = it.roastSummary,
                        shareCardColor = it.shareCardColor,
                    )
                }
                _audits.value = mapped.sortedByDescending { it.score }
                currentOffset = pageSize
                if (dtoItems.size < pageSize) {
                    isLastPage = true
                }
            } catch (e: Exception) {
                android.util.Log.e("ProfileHistoryVM", "refresh failed: ${e.message}")
            } finally {
                isLoading = false
                _isLoadingState.value = false
            }
        }
    }

    fun deletePhoto(photoId: String) {
        viewModelScope.launch {
            val result = repository.deleteProfileAuditPhoto(photoId)
            result.fold(
                onSuccess = {
                    // Remove from local state
                    _audits.value = _audits.value.filter { it.id != photoId }
                },
                onFailure = {
                    // Error handling could be added here if needed
                    android.util.Log.e("ProfileHistoryVM", "Failed to delete photo: ${it.message}")
                }
            )
        }
    }

    fun shareLatestRoast() {
        if (_isSharingState.value) return

        viewModelScope.launch {
            _isSharingState.value = true
            try {
                val bytesResult = repository.downloadProfileAuditShareCard()
                bytesResult
                    .onSuccess { bytes ->
                        val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                            ?: throw IllegalStateException("Failed to decode share card image")

                        val cacheDir = context.cacheDir
                        val file = java.io.File(cacheDir, "profile_roast_share_card.png")
                        java.io.FileOutputStream(file).use { out ->
                            bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, out)
                        }

                        val uri = FileProvider.getUriForFile(
                            context,
                            context.packageName + ".fileprovider",
                            file
                        )

                        val shareIntent = Intent(Intent.ACTION_SEND).apply {
                            type = "image/*"
                            putExtra(Intent.EXTRA_STREAM, uri)
                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                        }
                        shareIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        context.startActivity(
                            Intent.createChooser(
                                shareIntent,
                                "Share your roast"
                            ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        )
                    }
                    .onFailure {
                        android.util.Log.e("ProfileHistoryVM", "Failed to download share card: ${it.message}")
                    }
            } catch (e: Exception) {
                android.util.Log.e("ProfileHistoryVM", "shareLatestRoast failed: ${e.message}")
            } finally {
                _isSharingState.value = false
            }
        }
    }
}

