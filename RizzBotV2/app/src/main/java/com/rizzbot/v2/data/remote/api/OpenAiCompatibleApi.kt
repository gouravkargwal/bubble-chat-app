package com.rizzbot.v2.data.remote.api

import com.rizzbot.v2.data.remote.dto.OpenAiVisionRequest
import com.rizzbot.v2.data.remote.dto.OpenAiResponse
import retrofit2.http.Body
import retrofit2.http.POST

interface OpenAiCompatibleApi {
    @POST("v1/chat/completions")
    suspend fun chatCompletion(@Body request: OpenAiVisionRequest): OpenAiResponse
}
