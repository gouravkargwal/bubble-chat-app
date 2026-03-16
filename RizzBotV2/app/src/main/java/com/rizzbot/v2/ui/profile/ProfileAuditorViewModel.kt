package com.rizzbot.v2.ui.profile

import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import androidx.core.content.FileProvider
import android.net.Uri
import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.data.remote.dto.AuditResponse
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import com.rizzbot.v2.util.compressImage
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import javax.inject.Inject

data class ProfileAuditorState(
    val selectedUris: List<Uri> = emptyList(),
    val isLoading: Boolean = false,
    val result: AuditResponseUi? = null,
    val resultPhotoIdToUri: Map<String, Uri> = emptyMap(), // Preserve URIs for result display
    val error: String? = null,
    val selectedLanguage: String = "English",
    val maxPhotosPerAudit: Int = 3,
    val showPaywall: Boolean = false,
    val tier: String = "free",
    val weeklyAuditsUsed: Int = 0,
    val profileAuditsPerWeek: Int = 1,
    val isSharing: Boolean = false
)

@HiltViewModel
class ProfileAuditorViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val hostedRepository: HostedRepository,
    private val settingsRepository: SettingsRepository
) : ViewModel() {

    private val _state = MutableStateFlow(ProfileAuditorState())
    val state: StateFlow<ProfileAuditorState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            combine(
                settingsRepository.roastLanguage,
                hostedRepository.usageState
            ) { lang, usage ->
                _state.value = _state.value.copy(
                    selectedLanguage = lang,
                    maxPhotosPerAudit = usage.maxPhotosPerAudit,
                    tier = usage.tier,
                    weeklyAuditsUsed = usage.weeklyAuditsUsed,
                    profileAuditsPerWeek = usage.profileAuditsPerWeek
                )
            }.collect {}
        }
    }

    fun onPhotosSelected(uris: List<Uri>) {
        val maxPhotos = _state.value.maxPhotosPerAudit
        val selectedPhotos = uris.take(maxPhotos)
        val exceededLimit = uris.size > maxPhotos
        
        _state.value = _state.value.copy(
            selectedUris = selectedPhotos,
            error = null,
            showPaywall = exceededLimit && hostedRepository.usageState.value.tier == "free"
        )
    }
    
    fun dismissPaywall() {
        _state.value = _state.value.copy(showPaywall = false)
    }

    fun setLanguage(language: String) {
        viewModelScope.launch {
            settingsRepository.setRoastLanguage(language)
        }
    }

    fun analyzePhotos() {
        val uris = _state.value.selectedUris
        if (uris.isEmpty() || _state.value.isLoading) {
            Log.d("ProfileAuditorVM", "analyzePhotos: aborted, uris=${uris.size}, isLoading=${_state.value.isLoading}")
            return
        }

        viewModelScope.launch {
            Log.d("ProfileAuditorVM", "analyzePhotos: starting with ${uris.size} uris")
            _state.value = _state.value.copy(isLoading = true, error = null, result = null)

            try {
                // 1. Compress all images concurrently on IO dispatcher
                val compressedBytes = withContext(Dispatchers.IO) {
                    uris.map { uri ->
                        async { compressImage(context, uri) }
                    }.mapNotNull { it.await() }
                }
                Log.d("ProfileAuditorVM", "analyzePhotos: compressed=${compressedBytes.size}")

                if (compressedBytes.isEmpty()) {
                    _state.value = _state.value.copy(
                        isLoading = false,
                        error = "Failed to read photos."
                    )
                    Log.w("ProfileAuditorVM", "analyzePhotos: no compressed photos, aborting")
                    return@launch
                }

                // 2. Create photoIdToUri mapping before clearing selectedUris
                val photoIdToUri = uris.mapIndexed { index, uri ->
                    "photo_${index + 1}" to uri
                }.toMap()

                // 3. Upload to backend
                Log.d("ProfileAuditorVM", "analyzePhotos: calling uploadPhotosForAudit")
                val currentLang = _state.value.selectedLanguage
                val result = hostedRepository.uploadPhotosForAudit(
                    compressedBytes,
                    lang = currentLang
                )
                result
                    .onSuccess { dto ->
                        Log.d("ProfileAuditorVM", "analyzePhotos: success, totalAnalyzed=${dto.totalAnalyzed}")
                        _state.value = _state.value.copy(
                            isLoading = false,
                            result = dto.toUiModel(),
                            resultPhotoIdToUri = photoIdToUri, // Preserve URIs for result display
                            selectedUris = emptyList() // Clear selected photos after successful audit
                        )
                    }
                    .onFailure { e ->
                        Log.e("ProfileAuditorVM", "analyzePhotos: failed", e)
                        _state.value = _state.value.copy(
                            isLoading = false,
                            error = e.message ?: "Failed to audit photos."
                        )
                    }
            } catch (e: Exception) {
                Log.e("ProfileAuditorVM", "analyzePhotos: exception", e)
                _state.value = _state.value.copy(
                    isLoading = false,
                    error = e.message ?: "Failed to audit photos."
                )
            }
        }
    }

    fun shareLatestRoast() {
        val currentResult = _state.value.result ?: return
        if (_state.value.isSharing) return

        viewModelScope.launch {
            _state.value = _state.value.copy(isSharing = true, error = null)
            try {
                val bytesResult = hostedRepository.downloadProfileAuditShareCard()
                bytesResult
                    .onSuccess { bytes ->
                        // Decode to bitmap and write to cache for sharing
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
                    .onFailure { e ->
                        _state.value = _state.value.copy(
                            error = e.message ?: "Failed to generate share card."
                        )
                    }
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    error = e.message ?: "Failed to generate share card."
                )
            } finally {
                _state.value = _state.value.copy(isSharing = false)
            }
        }
    }
}

private fun AuditResponse.toUiModel(): AuditResponseUi =
    AuditResponseUi(
        totalAnalyzed = totalAnalyzed,
        passedCount = passedCount,
        isHardReset = isHardReset,
        archetypeTitle = archetypeTitle,
        roastSummary = roastSummary,
        shareCardColor = shareCardColor,
        overallScore = photos.takeIf { it.isNotEmpty() }
            ?.map { it.score }
            ?.average()
            ?.let { (it * 10).toInt().coerceIn(0, 100) }
            ?: 0,
        photos = photos.map { photo ->
            PhotoFeedbackUi(
                photoId = photo.photoId,
                score = photo.score,
                tier = when (photo.tier.uppercase()) {
                    "GOD_TIER" -> PhotoTier.GOD_TIER
                    "FILLER" -> PhotoTier.FILLER
                    "GRAVEYARD" -> PhotoTier.GRAVEYARD
                    else -> PhotoTier.GRAVEYARD
                },
                brutalFeedback = photo.brutalFeedback,
                improvementTip = photo.improvementTip
            )
        }
    )

