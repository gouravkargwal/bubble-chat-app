package com.rizzbot.v2.data.remote.api

import com.rizzbot.v2.data.remote.dto.GeminiVisionRequest
import com.rizzbot.v2.data.remote.dto.GeminiResponse
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface GeminiApi {
    @POST("v1beta/models/{model}:generateContent")
    suspend fun generateContent(
        @Path("model") model: String,
        @Query("key") apiKey: String,
        @Body request: GeminiVisionRequest
    ): GeminiResponse
}
