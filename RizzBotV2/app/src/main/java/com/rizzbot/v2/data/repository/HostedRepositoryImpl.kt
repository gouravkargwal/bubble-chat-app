package com.rizzbot.v2.data.repository

import com.rizzbot.v2.data.local.datastore.SettingsDataStore
import com.rizzbot.v2.data.remote.api.HostedApi
import com.rizzbot.v2.data.remote.dto.HostedVisionRequest
import com.rizzbot.v2.domain.model.HostedModeState
import com.rizzbot.v2.domain.model.SuggestionResult
import com.rizzbot.v2.domain.repository.HostedRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import retrofit2.HttpException
import java.net.SocketTimeoutException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class HostedRepositoryImpl @Inject constructor(
    private val hostedApi: HostedApi,
    private val settingsDataStore: SettingsDataStore
) : HostedRepository {

    private var authToken: String? = null
    private val _hostedState = MutableStateFlow(HostedModeState())
    override val hostedState: Flow<HostedModeState> = _hostedState.asStateFlow()

    override suspend fun authenticateAnonymous(): Boolean {
        return try {
            val response = hostedApi.authenticateAnonymous()
            authToken = response.token
            _hostedState.value = _hostedState.value.copy(isAuthenticated = true)
            true
        } catch (e: Exception) {
            false
        }
    }

    override suspend fun generateHostedReply(
        systemPrompt: String,
        userPrompt: String,
        base64Image: String
    ): SuggestionResult {
        val token = authToken ?: run {
            if (!authenticateAnonymous()) {
                return SuggestionResult.Error(
                    "Failed to authenticate. Check your connection.",
                    SuggestionResult.ErrorType.UNKNOWN
                )
            }
            authToken!!
        }

        return try {
            val response = hostedApi.generateReply(
                token = "Bearer $token",
                request = HostedVisionRequest(
                    image = base64Image,
                    systemPrompt = systemPrompt,
                    userPrompt = userPrompt
                )
            )

            _hostedState.value = _hostedState.value.copy(
                dailyUsed = _hostedState.value.dailyLimit - response.usageRemaining
            )

            SuggestionResult.Success(
                replies = response.replies,
                summary = response.summary,
                personName = response.personName
            )
        } catch (e: HttpException) {
            when (e.code()) {
                401 -> {
                    authToken = null
                    _hostedState.value = _hostedState.value.copy(isAuthenticated = false)
                    SuggestionResult.Error("Session expired. Please try again.", SuggestionResult.ErrorType.INVALID_API_KEY)
                }
                429 -> SuggestionResult.Error(
                    "Daily limit reached. Upgrade to Premium for unlimited replies.",
                    SuggestionResult.ErrorType.RATE_LIMITED
                )
                else -> SuggestionResult.Error("Server error: ${e.code()}", SuggestionResult.ErrorType.UNKNOWN)
            }
        } catch (e: SocketTimeoutException) {
            SuggestionResult.Error("Request timed out. Try again.", SuggestionResult.ErrorType.TIMEOUT)
        } catch (e: Exception) {
            SuggestionResult.Error(e.message ?: "Unknown error", SuggestionResult.ErrorType.UNKNOWN)
        }
    }

    override suspend fun refreshUsage() {
        val token = authToken ?: return
        try {
            val usage = hostedApi.getUsage("Bearer $token")
            _hostedState.value = _hostedState.value.copy(
                dailyLimit = usage.dailyLimit,
                dailyUsed = usage.dailyUsed,
                isPremium = usage.isPremium
            )
        } catch (_: Exception) {}
    }

    override suspend fun redeemReferral(code: String): Result<Int> {
        return try {
            // This would call a referral endpoint — placeholder for now
            _hostedState.value = _hostedState.value.copy(
                bonusReplies = _hostedState.value.bonusReplies + 5
            )
            Result.success(5)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override fun getToken(): String? = authToken
}
