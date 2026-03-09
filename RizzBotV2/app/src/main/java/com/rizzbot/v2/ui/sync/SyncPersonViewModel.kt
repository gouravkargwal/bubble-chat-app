package com.rizzbot.v2.ui.sync

import android.graphics.Bitmap
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.capture.ImageCompressor
import com.rizzbot.v2.domain.model.PersonProfileResult
import com.rizzbot.v2.domain.usecase.SyncPersonProfileUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SyncPersonState(
    val selectedImages: List<Uri> = emptyList(),
    val result: PersonProfileResult? = null
)

@HiltViewModel
class SyncPersonViewModel @Inject constructor(
    private val syncPersonProfileUseCase: SyncPersonProfileUseCase,
    private val imageCompressor: ImageCompressor
) : ViewModel() {

    private val _state = MutableStateFlow(SyncPersonState())
    val state: StateFlow<SyncPersonState> = _state.asStateFlow()

    fun addImages(uris: List<Uri>) {
        val current = _state.value.selectedImages.toMutableList()
        uris.forEach { uri ->
            if (current.size < 5) current.add(uri)
        }
        _state.value = _state.value.copy(selectedImages = current)
    }

    fun removeImage(uri: Uri) {
        val current = _state.value.selectedImages.toMutableList()
        current.remove(uri)
        _state.value = _state.value.copy(selectedImages = current)
    }

    fun syncProfile(bitmaps: List<Bitmap>) {
        if (bitmaps.isEmpty()) return
        viewModelScope.launch {
            _state.value = _state.value.copy(result = PersonProfileResult.Loading)
            val base64List = bitmaps.map { imageCompressor.bitmapToBase64Jpeg(it) }
            val result = syncPersonProfileUseCase(base64List)
            _state.value = _state.value.copy(result = result)
        }
    }

    fun clearResult() {
        _state.value = _state.value.copy(result = null, selectedImages = emptyList())
    }
}
