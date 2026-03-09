package com.rizzbot.v2.data.auth

import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthInterceptor @Inject constructor(
    private val authManager: dagger.Lazy<AuthManager>
) : Interceptor {

    private val skipPaths = listOf("/auth/firebase")

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()

        // Skip auth for auth endpoints
        if (skipPaths.any { request.url.encodedPath.contains(it) }) {
            return chain.proceed(request)
        }

        // Add token if available
        val token = authManager.get().getToken()
        val authenticatedRequest = if (token != null) {
            request.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        } else {
            request
        }

        val response = chain.proceed(authenticatedRequest)

        // On 401, clear stale token — user will need to re-sign-in
        if (response.code == 401) {
            authManager.get().clearAuth()
        }

        return response
    }
}
