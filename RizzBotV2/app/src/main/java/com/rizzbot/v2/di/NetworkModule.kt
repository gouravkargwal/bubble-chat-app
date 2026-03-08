package com.rizzbot.v2.di

import com.rizzbot.v2.BuildConfig
import com.rizzbot.v2.data.remote.LlmClientFactory
import com.rizzbot.v2.data.remote.api.HostedApi
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideJson(): Json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
        isLenient = true
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient {
        return OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .apply {
                if (BuildConfig.DEBUG) {
                    addInterceptor(HttpLoggingInterceptor().apply {
                        level = HttpLoggingInterceptor.Level.BODY
                    })
                }
            }
            .build()
    }

    @Provides
    @Singleton
    fun provideConverterFactory(json: Json): retrofit2.Converter.Factory {
        return json.asConverterFactory("application/json".toMediaType())
    }

    @Provides
    @Singleton
    fun provideLlmClientFactory(
        okHttpClient: OkHttpClient,
        converterFactory: retrofit2.Converter.Factory
    ): LlmClientFactory = LlmClientFactory(okHttpClient, converterFactory)

    @Provides
    @Singleton
    fun provideHostedApi(
        okHttpClient: OkHttpClient,
        converterFactory: retrofit2.Converter.Factory
    ): HostedApi {
        return retrofit2.Retrofit.Builder()
            .baseUrl("https://api.rizzbot.app/")
            .client(okHttpClient)
            .addConverterFactory(converterFactory)
            .build()
            .create(HostedApi::class.java)
    }
}
