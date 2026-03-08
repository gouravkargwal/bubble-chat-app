package com.rizzbot.v2.data.remote

import com.rizzbot.v2.data.remote.api.AnthropicApi
import com.rizzbot.v2.data.remote.api.GeminiApi
import com.rizzbot.v2.data.remote.api.OpenAiCompatibleApi
import okhttp3.OkHttpClient
import retrofit2.Converter
import retrofit2.Retrofit
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LlmClientFactory @Inject constructor(
    private val okHttpClient: OkHttpClient,
    private val converterFactory: Converter.Factory
) {
    private val cache = mutableMapOf<String, Any>()

    fun openAiCompatible(baseUrl: String, apiKey: String): OpenAiCompatibleApi {
        val key = "openai_$baseUrl"
        @Suppress("UNCHECKED_CAST")
        return cache.getOrPut(key) {
            val client = okHttpClient.newBuilder()
                .addInterceptor { chain ->
                    val request = chain.request().newBuilder()
                        .addHeader("Authorization", "Bearer $apiKey")
                        .build()
                    chain.proceed(request)
                }
                .build()

            Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(client)
                .addConverterFactory(converterFactory)
                .build()
                .create(OpenAiCompatibleApi::class.java)
        } as OpenAiCompatibleApi
    }

    fun anthropic(apiKey: String): AnthropicApi {
        @Suppress("UNCHECKED_CAST")
        return cache.getOrPut("anthropic") {
            val client = okHttpClient.newBuilder()
                .addInterceptor { chain ->
                    val request = chain.request().newBuilder()
                        .addHeader("x-api-key", apiKey)
                        .addHeader("anthropic-version", "2023-06-01")
                        .build()
                    chain.proceed(request)
                }
                .build()

            Retrofit.Builder()
                .baseUrl("https://api.anthropic.com/")
                .client(client)
                .addConverterFactory(converterFactory)
                .build()
                .create(AnthropicApi::class.java)
        } as AnthropicApi
    }

    fun gemini(apiKey: String): GeminiApi {
        @Suppress("UNCHECKED_CAST")
        return cache.getOrPut("gemini") {
            Retrofit.Builder()
                .baseUrl("https://generativelanguage.googleapis.com/")
                .client(okHttpClient)
                .addConverterFactory(converterFactory)
                .build()
                .create(GeminiApi::class.java)
        } as GeminiApi
    }

    fun clearCache() {
        cache.clear()
    }
}
