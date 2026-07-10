package com.rizzbot.v2.data.auth

import com.rizzbot.v2.util.AnalyticsHelper
import okhttp3.Interceptor
import okhttp3.Response
import java.security.SecureRandom
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.runBlocking

@Singleton
class AuthInterceptor @Inject constructor(
    private val authManager: dagger.Lazy<AuthManager>,
    private val analyticsHelper: AnalyticsHelper
) : Interceptor {

    private val skipPaths = listOf("/auth/firebase")
    private companion object {
        private const val RETRY_HEADER = "X-Auth-Retry"
        private val random = SecureRandom()

        /**
         * W3C traceparent (00-<32 hex trace-id>-<16 hex span-id>-01) so the backend's
         * OpenTelemetry pipeline continues this trace instead of starting a new one —
         * lets a mobile request be matched to the backend trace/logs it caused.
         */
        private fun newTraceparent(): String {
            val traceId = ByteArray(16).also { random.nextBytes(it) }.joinToString("") { "%02x".format(it) }
            val spanId = ByteArray(8).also { random.nextBytes(it) }.joinToString("") { "%02x".format(it) }
            return "00-$traceId-$spanId-01"
        }
    }

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request().newBuilder()
            .header("traceparent", newTraceparent())
            .build()
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
            analyticsHelper.log("auth_refresh_retry_still_401 path=$requestPath")
            authManager.get().clearAuth()
            return response
        }

        val refreshed = runBlocking {
            authManager.get().refreshBackendTokenIfFirebaseSignedIn()
        }

        if (!refreshed) {
            analyticsHelper.log("auth_refresh_failed path=$requestPath")
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

        // Must close the original response before issuing another request on this call,
        // or OkHttp throws "cannot make a new request because the previous response is still open".
        response.close()

        val retryResponse = chain.proceed(retryRequest)
        if (retryResponse.code == 401) {
            authManager.get().clearAuth()
        }
        return retryResponse
    }
}
