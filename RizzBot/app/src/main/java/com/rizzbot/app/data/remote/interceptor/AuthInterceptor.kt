package com.rizzbot.app.data.remote.interceptor

import com.rizzbot.app.util.Constants
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthInterceptor @Inject constructor() : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request().newBuilder()
            .addHeader("Authorization", "Bearer ${Constants.GROQ_API_KEY}")
            .addHeader("Content-Type", "application/json")
            .build()
        return chain.proceed(request)
    }
}
