package com.rizzbot.app.accessibility.trigger

import android.util.Log
import com.rizzbot.app.accessibility.model.ParsedMessage
import com.rizzbot.app.domain.model.SuggestionResult
import com.rizzbot.app.domain.model.TonePreference
import com.rizzbot.app.domain.usecase.GenerateReplyUseCase
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

    fun onRefreshReplies(
        personName: String,
        conversationMessages: List<ParsedMessage>,
        scope: CoroutineScope,
        tone: TonePreference? = null,
        profileInfo: String? = null
    ) {
        val toneLabel = tone?.label ?: "default"
        Log.d(TAG, "SmartTrigger: refresh replies for $personName, tone=$toneLabel")

        currentJob = scope.launch {
            val result = generateReplyUseCase(personName, conversationMessages, tone, profileInfo)

            when (result) {
                is SuggestionResult.Success -> {
                    Log.d(TAG, "SmartTrigger: refresh reply SUCCESS, ${result.replies.size} new replies")
                    overlayEventBus.emit(OverlayEvent.AppendSuggestion(result.replies))
                }
                is SuggestionResult.Error -> {
                    Log.e(TAG, "SmartTrigger: refresh reply ERROR: ${result.message}")
                    overlayEventBus.emit(OverlayEvent.ShowError(result.message))
                }
                is SuggestionResult.Loading -> { /* no-op */ }
            }
        }
    }

    fun onIcebreakerTrigger(
        personName: String,
        scope: CoroutineScope,
        profileInfo: String
    ) {
        currentJob?.cancel()
        currentPersonName = personName

        Log.d(TAG, "SmartTrigger: icebreaker for $personName")
        overlayEventBus.tryEmit(OverlayEvent.ShowLoading("Crafting icebreaker..."))

        currentJob = scope.launch {
            val result = generateReplyUseCase(personName, emptyList(), null, profileInfo)

            when (result) {
                is SuggestionResult.Success -> {
                    Log.d(TAG, "SmartTrigger: icebreaker SUCCESS")
                    overlayEventBus.emit(OverlayEvent.ShowSuggestion(result.replies))
                }
                is SuggestionResult.Error -> {
                    Log.e(TAG, "SmartTrigger: icebreaker ERROR: ${result.message}")
                    overlayEventBus.emit(OverlayEvent.ShowError(result.message))
                }
                is SuggestionResult.Loading -> { /* no-op */ }
            }
        }
    }

    fun onManualTrigger(
        personName: String,
        conversationMessages: List<ParsedMessage>,
        scope: CoroutineScope,
        tone: TonePreference? = null,
        profileInfo: String? = null
    ) {
        currentJob?.cancel()
        currentPersonName = personName

        val toneLabel = tone?.label ?: "default"
        Log.d(TAG, "SmartTrigger: manual trigger for $personName, tone=$toneLabel, msgs=${conversationMessages.size}")
        overlayEventBus.tryEmit(OverlayEvent.ShowLoading("Generating ${toneLabel.lowercase()} reply..."))

        currentJob = scope.launch {
            val result = generateReplyUseCase(personName, conversationMessages, tone, profileInfo)

            when (result) {
                is SuggestionResult.Success -> {
                    Log.d(TAG, "SmartTrigger: manual reply SUCCESS")
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
}
