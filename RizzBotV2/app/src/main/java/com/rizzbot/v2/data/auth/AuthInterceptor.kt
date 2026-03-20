package com.rizzbot.v2.data.auth

import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.runBlocking

@Singleton
class AuthInterceptor @Inject constructor(
    private val authManager: dagger.Lazy<AuthManager>
) : Interceptor {

    private val skipPaths = listOf("/auth/firebase")
    private companion object {
        private const val RETRY_HEADER = "X-Auth-Retry"
    }

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val requestPath = request.url.encodedPath
        val isAuthEndpoint = skipPaths.any { requestPath.contains(it) }

        // Skip auth for auth endpoints
        if (isAuthEndpoint) {
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

        // On 401, attempt silent backend JWT refresh before clearing local auth.
        if (response.code != 401 || isAuthEndpoint) {
            return response
        }

        val alreadyRetried = request.header(RETRY_HEADER) == "1"
        if (alreadyRetried) {
            authManager.get().clearAuth()
            return response
        }

        val refreshed = runBlocking {
            authManager.get().refreshBackendTokenIfFirebaseSignedIn()
        }

        if (!refreshed) {
            authManager.get().clearAuth()
            return response
        }

        val newToken = authManager.get().getToken()
        if (newToken.isNullOrBlank()) {
            authManager.get().clearAuth()
            return response
        }

        // Retry request once with the refreshed backend JWT.
        val retryRequest = authenticatedRequest.newBuilder()
            .header("Authorization", "Bearer $newToken")
            .header(RETRY_HEADER, "1")
            .build()

        val retryResponse = chain.proceed(retryRequest)
        if (retryResponse.code == 401) {
            authManager.get().clearAuth()
        }
        return retryResponse
    }
}
