package com.rizzbot.v2.data.remote.api

import com.rizzbot.v2.data.remote.dto.AnthropicVisionRequest
import com.rizzbot.v2.data.remote.dto.AnthropicResponse
import retrofit2.http.Body
import retrofit2.http.POST

interface AnthropicApi {
    @POST("v1/messages")
    suspend fun createMessage(@Body request: AnthropicVisionRequest): AnthropicResponse
}
