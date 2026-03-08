package com.rizzbot.v2.data.remote.api

import com.rizzbot.v2.data.remote.dto.HostedVisionRequest
import com.rizzbot.v2.data.remote.dto.HostedVisionResponse
import com.rizzbot.v2.data.remote.dto.HostedUsageResponse
import com.rizzbot.v2.data.remote.dto.HostedAuthResponse
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

interface HostedApi {
    @POST("api/v1/auth/anonymous")
    suspend fun authenticateAnonymous(): HostedAuthResponse

    @POST("api/v1/vision/generate")
    suspend fun generateReply(
        @Header("Authorization") token: String,
        @Body request: HostedVisionRequest
    ): HostedVisionResponse

    @GET("api/v1/usage")
    suspend fun getUsage(
        @Header("Authorization") token: String
    ): HostedUsageResponse
}
