package com.rizzbot.app.data.remote

import com.rizzbot.app.data.remote.api.AnthropicApi
import com.rizzbot.app.data.remote.api.GeminiApi
import com.rizzbot.app.data.remote.api.OpenAiCompatibleApi
import com.rizzbot.app.domain.model.LlmProvider
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LlmClientFactory @Inject constructor(
    private val json: Json
) {

    fun createOpenAiCompatibleApi(baseUrl: String, apiKey: String): OpenAiCompatibleApi {
        val client = buildClient { chain ->
            val request = chain.request().newBuilder()
                .addHeader("Authorization", "Bearer $apiKey")
                .addHeader("Content-Type", "application/json")
                .build()
            chain.proceed(request)
        }
        return buildRetrofit(baseUrl, client).create(OpenAiCompatibleApi::class.java)
    }

    fun createAnthropicApi(apiKey: String): AnthropicApi {
        val client = buildClient { chain ->
            val request = chain.request().newBuilder()
                .addHeader("x-api-key", apiKey)
                .addHeader("anthropic-version", "2023-06-01")
                .addHeader("Content-Type", "application/json")
                .build()
            chain.proceed(request)
        }
        return buildRetrofit(LlmProvider.ANTHROPIC.baseUrl, client).create(AnthropicApi::class.java)
    }

    fun createGeminiApi(): GeminiApi {
        val client = buildClient()
        return buildRetrofit(LlmProvider.GEMINI.baseUrl, client).create(GeminiApi::class.java)
    }

    private fun buildClient(interceptor: okhttp3.Interceptor? = null): OkHttpClient {
        return OkHttpClient.Builder().apply {
            interceptor?.let { addInterceptor(it) }
            addInterceptor(HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            })
            connectTimeout(30, TimeUnit.SECONDS)
            readTimeout(60, TimeUnit.SECONDS)
        }.build()
    }

    private fun buildRetrofit(baseUrl: String, client: OkHttpClient): Retrofit {
        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
    }
}
