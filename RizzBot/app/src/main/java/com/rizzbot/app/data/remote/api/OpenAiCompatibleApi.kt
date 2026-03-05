package com.rizzbot.app.data.remote.api

import com.rizzbot.app.data.remote.dto.ChatCompletionRequest
import com.rizzbot.app.data.remote.dto.ChatCompletionResponse
import retrofit2.http.Body
import retrofit2.http.POST

interface OpenAiCompatibleApi {

    @POST("v1/chat/completions")
    suspend fun createChatCompletion(
        @Body request: ChatCompletionRequest
    ): ChatCompletionResponse
}
