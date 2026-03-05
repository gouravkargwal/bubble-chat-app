package com.rizzbot.app.accessibility.trigger

import android.util.Log
import com.rizzbot.app.accessibility.model.ParsedMessage
import com.rizzbot.app.domain.model.SuggestionResult
import com.rizzbot.app.domain.usecase.GenerateReplyUseCase
import com.rizzbot.app.domain.usecase.SaveMessageUseCase
import com.rizzbot.app.overlay.OverlayEvent
import com.rizzbot.app.overlay.OverlayEventBus
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SmartTriggerManager @Inject constructor(
    private val generateReplyUseCase: GenerateReplyUseCase,
    private val saveMessageUseCase: SaveMessageUseCase,
    private val overlayEventBus: OverlayEventBus
) {
    companion object {
        private const val TAG = "RizzBot"
    }

    private var currentPersonName: String? = null
    private var currentJob: Job? = null

    fun onChatScreenExited() {
        currentJob?.cancel()
        currentPersonName = null
        overlayEventBus.tryEmit(OverlayEvent.Hide)
    }

    fun onManualTrigger(
        personName: String,
        conversationMessages: List<ParsedMessage>,
        scope: CoroutineScope,
        profileInfo: String? = null,
        isFullRead: Boolean = false
    ) {
        currentJob?.cancel()
        currentPersonName = personName

        Log.d(TAG, "SmartTrigger: manual trigger for $personName, msgs=${conversationMessages.size}, fullRead=$isFullRead")
        overlayEventBus.tryEmit(OverlayEvent.ShowLoading("Generating replies..."))

        currentJob = scope.launch {
            val result = generateReplyUseCase(personName, conversationMessages, profileInfo, isFullRead)

            when (result) {
                is SuggestionResult.Success -> {
                    Log.d(TAG, "SmartTrigger: manual reply SUCCESS, ${result.replies.size} replies")
                    overlayEventBus.emit(OverlayEvent.ShowSuggestion(result.replies))
                }
                is SuggestionResult.Error -> {
                    Log.e(TAG, "SmartTrigger: manual reply ERROR: ${result.message}")
                    overlayEventBus.emit(OverlayEvent.ShowError(result.message))
                }
                is SuggestionResult.Loading -> { /* no-op */ }
            }
        }
    }

    fun onConversationStarterTrigger(
        personName: String,
        scope: CoroutineScope,
        profileInfo: String?
    ) {
        currentJob?.cancel()
        currentPersonName = personName

        Log.d(TAG, "SmartTrigger: new topic for $personName")
        overlayEventBus.tryEmit(OverlayEvent.ShowLoading("Finding fresh topics..."))

        currentJob = scope.launch {
            val result = generateReplyUseCase.invokeNewTopic(personName, profileInfo)

            when (result) {
                is SuggestionResult.Success -> {
                    Log.d(TAG, "SmartTrigger: new topic SUCCESS")
                    overlayEventBus.emit(OverlayEvent.ShowSuggestion(result.replies))
                }
                is SuggestionResult.Error -> {
                    Log.e(TAG, "SmartTrigger: new topic ERROR: ${result.message}")
                    overlayEventBus.emit(OverlayEvent.ShowError(result.message))
                }
                is SuggestionResult.Loading -> { /* no-op */ }
            }
        }
    }

    fun onSaveFullChat(
        personName: String,
        messages: List<ParsedMessage>,
        scope: CoroutineScope
    ) {
        Log.d(TAG, "SmartTrigger: saving full chat for $personName, ${messages.size} messages")

        scope.launch {
            try {
                saveMessageUseCase.replaceAll(personName, messages)
                Log.d(TAG, "SmartTrigger: full chat saved for $personName")
                overlayEventBus.emit(OverlayEvent.ShowRizzButton)
            } catch (e: Exception) {
                Log.e(TAG, "SmartTrigger: save full chat ERROR: ${e.message}", e)
                overlayEventBus.emit(OverlayEvent.ShowError("Failed to save chat"))
            }
        }
    }

    fun onRefreshReplies(
        personName: String,
        conversationMessages: List<ParsedMessage>,
        scope: CoroutineScope,
        profileInfo: String? = null
    ) {
        Log.d(TAG, "SmartTrigger: refresh replies for $personName")
        overlayEventBus.tryEmit(OverlayEvent.ShowLoading("Refreshing replies..."))

        currentJob = scope.launch {
            val result = generateReplyUseCase(personName, conversationMessages, profileInfo)

            when (result) {
                is SuggestionResult.Success -> {
                    Log.d(TAG, "SmartTrigger: refresh reply SUCCESS, ${result.replies.size} replies")
                    overlayEventBus.emit(OverlayEvent.ShowSuggestion(result.replies))
                }
                is SuggestionResult.Error -> {
                    Log.e(TAG, "SmartTrigger: refresh reply ERROR: ${result.message}")
                    overlayEventBus.emit(OverlayEvent.ShowError(result.message))
                }
                is SuggestionResult.Loading -> { /* no-op */ }
            }
        }
    }
}
