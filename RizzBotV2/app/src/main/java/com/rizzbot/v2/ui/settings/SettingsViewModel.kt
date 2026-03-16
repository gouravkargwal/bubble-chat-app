package com.rizzbot.v2.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.data.auth.GoogleSignInHelper
import com.rizzbot.v2.domain.model.ReferralInfo
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsState(
    val isPremium: Boolean = false,
    val tier: String = "free",
    val dailyLimit: Int = 5,
    val dailyUsed: Int = 0,
    val weeklyUsed: Int = 0,
    val monthlyUsed: Int = 0,
    val billingPeriod: String = "daily",
    val profileAuditsPerWeek: Int = 1,
    val weeklyAuditsUsed: Int = 0,
    val profileBlueprintsPerWeek: Int = 0,
    val godModeExpiresAt: java.time.Instant? = null,
    val userName: String? = null,
    val userEmail: String? = null,
    val signedOut: Boolean = false,
    val referral: ReferralInfo? = null,
    val referralCodeInput: String = "",
    val referralApplyResult: String? = null,
    val isApplyingReferral: Boolean = false,
    val roastLanguage: String = "English"
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val hostedRepository: HostedRepository,
    private val googleSignInHelper: GoogleSignInHelper,
    private val settingsRepository: SettingsRepository
) : ViewModel() {

    private val _state = MutableStateFlow(SettingsState())
    val state: StateFlow<SettingsState> = _state.asStateFlow()

    init {
        _state.update {
            it.copy(
                userName = googleSignInHelper.getCurrentUserName(),
                userEmail = googleSignInHelper.getCurrentUserEmail()
            )
        }

        viewModelScope.launch {
            hostedRepository.refreshUsage(force = false) // Use cache if available
            hostedRepository.usageState.collect { usage ->
                _state.update {
                    it.copy(
                        isPremium = usage.isPremium,
                        tier = usage.tier,
                        dailyLimit = usage.dailyLimit,
                        dailyUsed = usage.dailyUsed,
                        weeklyUsed = usage.weeklyUsed,
                        monthlyUsed = usage.monthlyUsed,
                        billingPeriod = usage.billingPeriod,
                        profileAuditsPerWeek = usage.profileAuditsPerWeek,
                        weeklyAuditsUsed = usage.weeklyAuditsUsed,
                        profileBlueprintsPerWeek = usage.profileBlueprintsPerWeek,
                        godModeExpiresAt = usage.godModeExpiresAt
                    )
                }
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
                onSuccess = { response ->
                    val info = hostedRepository.getReferralInfo()
                    _state.update {
                        it.copy(
                            isApplyingReferral = false,
                            referralApplyResult = "+${response.durationHours} hours of God Mode unlocked!",
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
                onSuccess = {
                    onSuccess()
                },
                onFailure = { e ->
                    onError(e.message ?: "Failed to delete data. Please try again.")
                }
            )
        }
    }
}
