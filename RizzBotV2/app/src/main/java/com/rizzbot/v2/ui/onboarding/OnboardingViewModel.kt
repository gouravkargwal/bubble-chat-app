package com.rizzbot.v2.ui.onboarding

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.data.auth.GoogleSignInHelper
import com.rizzbot.v2.data.auth.GoogleSignInResult
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import com.rizzbot.v2.util.AnalyticsHelper
import com.rizzbot.v2.util.PermissionHelper
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class OnboardingState(
    val currentStep: Int = 0,
    val hasOverlayPermission: Boolean = false,
    val isAuthenticating: Boolean = false,
    val authError: String? = null,
    val onboardingDone: Boolean = false,
    val userName: String? = null,
    val referralCode: String = "",
    val referralApplying: Boolean = false,
    val referralSuccess: String? = null,
    val referralError: String? = null
)

@HiltViewModel
class OnboardingViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val settingsRepository: SettingsRepository,
    private val hostedRepository: HostedRepository,
    val googleSignInHelper: GoogleSignInHelper,
    private val permissionHelper: PermissionHelper,
    private val analyticsHelper: AnalyticsHelper
) : ViewModel() {

    private val _state = MutableStateFlow(OnboardingState())
    val state: StateFlow<OnboardingState> = _state.asStateFlow()

    init {
        analyticsHelper.onboardingStarted()
        refreshPermissions()
    }

    fun refreshPermissions() {
        _state.update { it.copy(hasOverlayPermission = permissionHelper.canDrawOverlays()) }
    }

    fun nextStep() {
        val next = _state.value.currentStep + 1
        _state.update { it.copy(currentStep = next) }
        analyticsHelper.onboardingStepCompleted(next)
    }

    fun signInWithGoogle(activityContext: Context) {
        viewModelScope.launch {
            _state.update { it.copy(isAuthenticating = true, authError = null) }
            when (val result = googleSignInHelper.signIn(activityContext)) {
                is GoogleSignInResult.Success -> {
                    analyticsHelper.authCompleted()
                    // Refresh usage so the app knows the user's actual tier
                    hostedRepository.refreshUsage()
                    _state.update {
                        it.copy(
                            isAuthenticating = false,
                            userName = googleSignInHelper.getCurrentUserName()
                        )
                    }
                    nextStep()
                }
                is GoogleSignInResult.Error -> {
                    _state.update {
                        it.copy(isAuthenticating = false, authError = result.message)
                    }
                }
            }
        }
    }

    fun updateReferralCode(code: String) {
        _state.update { it.copy(referralCode = code, referralError = null) }
    }

    fun applyReferralCode() {
        val code = _state.value.referralCode.trim()
        if (code.isEmpty()) return
        viewModelScope.launch {
            _state.update { it.copy(referralApplying = true, referralError = null) }
            val result = hostedRepository.applyReferralCode(code)
            result.fold(
                onSuccess = { bonus ->
                    _state.update {
                        it.copy(
                            referralApplying = false,
                            referralSuccess = "+$bonus bonus replies unlocked!",
                            referralError = null
                        )
                    }
                },
                onFailure = { error ->
                    _state.update {
                        it.copy(
                            referralApplying = false,
                            referralError = error.message
                        )
                    }
                }
            )
        }
    }

    fun completeOnboarding() {
        viewModelScope.launch {
            settingsRepository.setOnboardingCompleted(true)
            analyticsHelper.onboardingCompleted()
            _state.update { it.copy(onboardingDone = true) }
        }
    }
}
