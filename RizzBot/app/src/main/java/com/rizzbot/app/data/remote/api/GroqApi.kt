package com.rizzbot.app.data.remote.api

import com.rizzbot.app.data.remote.dto.GroqRequest
import com.rizzbot.app.data.remote.dto.GroqResponse
import retrofit2.http.Body
import retrofit2.http.POST

interface GroqApi {

    @POST("openai/v1/chat/completions")
    suspend fun createChatCompletion(
        @Body request: GroqRequest
    ): GroqResponse
}
