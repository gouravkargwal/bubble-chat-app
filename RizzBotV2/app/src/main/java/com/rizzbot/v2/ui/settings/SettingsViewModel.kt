package com.rizzbot.v2.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.data.auth.GoogleSignInHelper
import com.rizzbot.v2.domain.model.ReferralInfo
import com.rizzbot.v2.domain.model.TierQuota
import com.rizzbot.v2.domain.model.UsageState
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import com.rizzbot.v2.util.AnalyticsHelper
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
    val marketingConsent: Boolean = true,
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
    val roastLanguage: String = "English",
    // LTD redeem
    val ltdCodeInput: String = "",
    val ltdRedeemResult: String? = null,
    val isRedeemingLTD: Boolean = false,
    // LTD status (isLtd comes from usage — no separate /ltd/status call)
    val isLtd: Boolean = false,
    val usageLoaded: Boolean = false,
) {
    val isPaidPlan: Boolean get() = tier == TierQuota.PLAN_CRUSH || tier == TierQuota.PLAN_MATCH
    val isOnTrial: Boolean
        get() {
            val expiresAt = tierExpiresAt ?: return false
            val nowSec = System.currentTimeMillis() / 1000
            val diffDays = ((expiresAt - nowSec) / 86400).toInt()
            return tier == TierQuota.PLAN_MATCH && diffDays in 0..30 && creditsPeriodLimit == 15
        }
    val trialDaysRemaining: Int
        get() {
            val expiresAt = tierExpiresAt ?: return 0
            val nowSec = System.currentTimeMillis() / 1000
            return ((expiresAt - nowSec) / 86400).toInt().coerceAtLeast(0)
        }
    val canGenerate: Boolean get() = creditsRemaining > 0
    val creditsUsed: Int get() = (creditsPeriodLimit - creditsRemaining).coerceAtLeast(0)
}

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val hostedRepository: HostedRepository,
    private val googleSignInHelper: GoogleSignInHelper,
    private val settingsRepository: SettingsRepository,
    private val analyticsHelper: AnalyticsHelper
) : ViewModel() {

    private val _state = MutableStateFlow(SettingsState())
    val state: StateFlow<SettingsState> = _state.asStateFlow()

    private val _isPullRefreshing = MutableStateFlow(false)
    val isPullRefreshing: StateFlow<Boolean> = _isPullRefreshing.asStateFlow()

    private fun applyUsageSnapshot(usage: UsageState) {
        _state.update {
            it.copy(
                tier = usage.tier,
                creditsRemaining = usage.creditsRemaining,
                creditsPeriodLimit = usage.creditsPeriodLimit,
                billingPeriod = usage.billingPeriod,
                tierExpiresAt = usage.tierExpiresAt,
                isLtd = usage.isLtd,
            )
        }
    }

    init {
        analyticsHelper.screenViewed("Settings")

        _state.update {
            it.copy(
                userName = googleSignInHelper.getCurrentUserName(),
                userEmail = googleSignInHelper.getCurrentUserEmail()
            )
        }

        viewModelScope.launch {
            hostedRepository.refreshUsage(force = true)
            hostedRepository.usageState.collect { usage ->
                applyUsageSnapshot(usage)
                _state.update { it.copy(isLtd = usage.isLtd, usageLoaded = true) }
            }
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
        viewModelScope.launch {
            settingsRepository.marketingConsent.collect { consent ->
                _state.update { it.copy(marketingConsent = consent) }
            }
        }
    }

    suspend fun refreshComplete() {
        withContext(Dispatchers.IO) {
            hostedRepository.refreshUsage(force = true)
        }
        applyUsageSnapshot(hostedRepository.usageState.value)
        val info = withContext(Dispatchers.IO) { hostedRepository.getReferralInfo() }
        _state.update {
            it.copy(
                referral = info,
            )
        }
    }

    fun refresh() {
        viewModelScope.launch {
            _isPullRefreshing.value = true
            try {
                refreshComplete()
            } finally {
                _isPullRefreshing.value = false
            }
        }
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
                    analyticsHelper.settingsReferralApplied()
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

    fun onLTDCodeChanged(code: String) {
        _state.update { it.copy(ltdCodeInput = code, ltdRedeemResult = null) }
    }

    fun redeemLTDCode() {
        val code = _state.value.ltdCodeInput.trim()
        if (code.isEmpty()) return

        viewModelScope.launch {
            _state.update { it.copy(isRedeemingLTD = true, ltdRedeemResult = null) }
            val result = hostedRepository.redeemLTDCode(code)
            result.fold(
                onSuccess = { message ->
                    analyticsHelper.settingsLtdRedeemed()
                    refreshComplete()
                    _state.update {
                        it.copy(
                            isRedeemingLTD = false,
                            ltdRedeemResult = message,
                            ltdCodeInput = "",
                        )
                    }
                },
                onFailure = { e ->
                    _state.update {
                        it.copy(
                            isRedeemingLTD = false,
                            ltdRedeemResult = e.message,
                        )
                    }
                }
            )
        }
    }

    fun setRoastLanguage(language: String) {
        analyticsHelper.settingsLanguageChanged(language)
        viewModelScope.launch {
            settingsRepository.setRoastLanguage(language)
        }
    }

    fun setMarketingConsent(enabled: Boolean) {
        analyticsHelper.settingsMarketingConsentChanged(enabled)
        viewModelScope.launch {
            settingsRepository.setMarketingConsent(enabled)
        }
    }

    fun signOut() {
        analyticsHelper.settingsSignOut()
        googleSignInHelper.signOut()
        _state.update { it.copy(signedOut = true) }
    }

    fun deleteAllData(onSuccess: () -> Unit, onError: (String) -> Unit) {
        analyticsHelper.settingsDeleteData()
        viewModelScope.launch {
            val result = hostedRepository.deleteAllUserData()
            result.fold(
                onSuccess = { onSuccess() },
                onFailure = { e -> onError(e.message ?: "Failed to delete data. Please try again.") }
            )
        }
    }
}
