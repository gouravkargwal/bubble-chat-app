package com.rizzbot.v2.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.data.auth.GoogleSignInHelper
import com.rizzbot.v2.domain.model.ReferralInfo
import com.rizzbot.v2.domain.model.TierQuota
import com.rizzbot.v2.domain.model.UsageState
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.Dispatchers
import javax.inject.Inject

data class SettingsState(
    val tier: String = TierQuota.PLAN_FREE,
    val creditsRemaining: Int = 0,
    val creditsPeriodLimit: Int = 0,
    val billingPeriod: String = "monthly",
    val tierExpiresAt: Long? = null,
    val userName: String? = null,
    val userEmail: String? = null,
    val signedOut: Boolean = false,
    val referral: ReferralInfo? = null,
    val referralCodeInput: String = "",
    val referralApplyResult: String? = null,
    val isApplyingReferral: Boolean = false,
    val roastLanguage: String = "English"
) {
    val isPaidPlan: Boolean get() = tier == TierQuota.PLAN_CRUSH || tier == TierQuota.PLAN_MATCH || tier == TierQuota.PLAN_RIZZ
    val canGenerate: Boolean get() = creditsRemaining > 0
    val creditsUsed: Int get() = (creditsPeriodLimit - creditsRemaining).coerceAtLeast(0)
}

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val hostedRepository: HostedRepository,
    private val googleSignInHelper: GoogleSignInHelper,
    private val settingsRepository: SettingsRepository
) : ViewModel() {

    private val _state = MutableStateFlow(SettingsState())
    val state: StateFlow<SettingsState> = _state.asStateFlow()

    private fun applyUsageSnapshot(usage: UsageState) {
        _state.update {
            it.copy(
                tier = usage.tier,
                creditsRemaining = usage.creditsRemaining,
                creditsPeriodLimit = usage.creditsPeriodLimit,
                billingPeriod = usage.billingPeriod,
                tierExpiresAt = usage.tierExpiresAt,
            )
        }
    }

    init {
        _state.update {
            it.copy(
                userName = googleSignInHelper.getCurrentUserName(),
                userEmail = googleSignInHelper.getCurrentUserEmail()
            )
        }

        viewModelScope.launch {
            hostedRepository.refreshUsage(force = true)
            hostedRepository.usageState.collect { usage -> applyUsageSnapshot(usage) }
        }

        viewModelScope.launch {
            val info = hostedRepository.getReferralInfo()
            _state.update { it.copy(referral = info) }
        }

        viewModelScope.launch {
            settingsRepository.roastLanguage.collect { lang ->
                _state.update { it.copy(roastLanguage = lang) }
            }
        }
    }

    suspend fun refreshComplete() {
        withContext(Dispatchers.IO) {
            hostedRepository.refreshUsage(force = true)
        }
        applyUsageSnapshot(hostedRepository.usageState.value)
        val info = withContext(Dispatchers.IO) { hostedRepository.getReferralInfo() }
        _state.update { it.copy(referral = info) }
    }

    fun refresh() {
        viewModelScope.launch { refreshComplete() }
    }

    fun onReferralCodeChanged(code: String) {
        _state.update { it.copy(referralCodeInput = code, referralApplyResult = null) }
    }

    fun applyReferralCode() {
        val code = _state.value.referralCodeInput.trim()
        if (code.isEmpty()) return

        viewModelScope.launch {
            _state.update { it.copy(isApplyingReferral = true, referralApplyResult = null) }
            val result = hostedRepository.applyReferralCode(code)
            result.fold(
                onSuccess = { _ ->
                    val info = hostedRepository.getReferralInfo()
                    _state.update {
                        it.copy(
                            isApplyingReferral = false,
                            referralApplyResult = "Referral applied! ${TierQuota.REFEREE_CREDITS} bonus credits added.",
                            referralCodeInput = "",
                            referral = info
                        )
                    }
                },
                onFailure = { e ->
                    _state.update {
                        it.copy(
                            isApplyingReferral = false,
                            referralApplyResult = e.message
                        )
                    }
                }
            )
        }
    }

    fun setRoastLanguage(language: String) {
        viewModelScope.launch {
            settingsRepository.setRoastLanguage(language)
        }
    }

    fun signOut() {
        googleSignInHelper.signOut()
        _state.update { it.copy(signedOut = true) }
    }

    fun deleteAllData(onSuccess: () -> Unit, onError: (String) -> Unit) {
        viewModelScope.launch {
            val result = hostedRepository.deleteAllUserData()
            result.fold(
                onSuccess = { onSuccess() },
                onFailure = { e -> onError(e.message ?: "Failed to delete data. Please try again.") }
            )
        }
    }
}
