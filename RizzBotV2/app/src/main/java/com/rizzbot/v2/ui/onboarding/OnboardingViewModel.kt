package com.rizzbot.v2.ui.onboarding

import android.app.Activity
import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rizzbot.v2.data.auth.GoogleSignInHelper
import com.rizzbot.v2.data.auth.GoogleSignInFallbackRequired
import com.rizzbot.v2.data.auth.GoogleSignInResult
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
import com.rizzbot.v2.util.AnalyticsHelper
import com.rizzbot.v2.util.HapticHelper
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class OnboardingState(
    val currentStep: Int = 0,
    val isAuthenticating: Boolean = false,
    val authError: String? = null,
    val onboardingDone: Boolean = false,
    val showPaywall: Boolean = false,
    val isNewUser: Boolean = false,
    val userName: String? = null,
    val referralCode: String = "",
    val referralApplying: Boolean = false,
    val referralSuccess: String? = null,
    val referralError: String? = null,
)

@HiltViewModel
class OnboardingViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val settingsRepository: SettingsRepository,
    private val hostedRepository: HostedRepository,
    val googleSignInHelper: GoogleSignInHelper,
    private val analyticsHelper: AnalyticsHelper,
    private val hapticHelper: HapticHelper,
) : ViewModel() {

    private val _state = MutableStateFlow(OnboardingState())
    val state: StateFlow<OnboardingState> = _state.asStateFlow()
    private val _googleSignInEvents = MutableSharedFlow<Intent>(extraBufferCapacity = 1)
    val googleSignInEvents: SharedFlow<Intent> = _googleSignInEvents.asSharedFlow()

    init {
        analyticsHelper.onboardingStarted()
    }

    /**
     * Advances the onboarding to the next step.
     * Step mapping: 0 = Value Cards, 1 = Google Sign-In, 2 = Signup Bonus.
     */
    fun advanceOnboardingStep() {
        val next = _state.value.currentStep + 1
        _state.update { it.copy(currentStep = next) }
        analyticsHelper.onboardingStepCompleted(next)
    }

    /**
     * Skip value cards and go directly to sign-in.
     * Used when a returning user needs to re-authenticate.
     */
    fun skipToSignIn() {
        _state.update { it.copy(currentStep = 1) }
        analyticsHelper.onboardingStepCompleted(1)
    }

    fun signInWithGoogle(activity: Activity) {
        viewModelScope.launch {
            _state.update { it.copy(isAuthenticating = true, authError = null) }

            try {
                when (val result = googleSignInHelper.signIn(activity)) {
                    is GoogleSignInResult.Success -> handleSuccessfulSignIn(result)
                    is GoogleSignInResult.Error -> {
                        _state.update { it.copy(isAuthenticating = false, authError = result.message) }
                    }
                }
            } catch (e: GoogleSignInFallbackRequired) {
                // One-shot UI event to launch Google sign-in intent.
                _googleSignInEvents.emit(e.signInIntent)
            }
        }
    }

    fun onActivityRequiredForGoogleSignIn() {
        _state.update {
            it.copy(
                isAuthenticating = false,
                authError = "Sign-in requires an Activity context.",
            )
        }
    }

    private suspend fun handleSuccessfulSignIn(result: GoogleSignInResult.Success) {
        hapticHelper.successTap()
        analyticsHelper.authCompleted()
        // Refresh usage so the app knows the user's actual tier (force after auth)
        hostedRepository.refreshUsage(force = true)

        _state.update {
            it.copy(
                isAuthenticating = false,
                authError = null,
                userName = googleSignInHelper.getCurrentUserName(),
            )
        }

        if (result.isNewUser) {
            // New user: proceed to Signup Bonus (Step 2)
            _state.update { it.copy(isNewUser = true) }
            advanceOnboardingStep()
        } else {
            // Returning user: complete onboarding, go straight to Home
            settingsRepository.setOnboardingCompleted(true)
            analyticsHelper.onboardingCompleted()
            _state.update { it.copy(onboardingDone = true) }
        }
    }

    fun onGoogleSignInActivityResult(resultCode: Int, data: Intent?) {
        viewModelScope.launch {
            if (data == null && resultCode == Activity.RESULT_CANCELED) {
                _state.update { it.copy(isAuthenticating = false, authError = "Sign-in was cancelled.") }
                return@launch
            }

            when (val result = googleSignInHelper.finishSignInWithGoogleIntentResult(data)) {
                is GoogleSignInResult.Success -> handleSuccessfulSignIn(result)
                is GoogleSignInResult.Error -> _state.update {
                    it.copy(
                        isAuthenticating = false,
                        authError = result.message,
                    )
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
                    hapticHelper.successTap()
                    _state.update {
                        it.copy(
                            referralApplying = false,
                            referralSuccess = "+$bonus bonus replies unlocked!",
                            referralError = null,
                        )
                    }
                },
                onFailure = { error ->
                    _state.update {
                        it.copy(
                            referralApplying = false,
                            referralError = error.message,
                        )
                    }
                },
            )
        }
    }

    /**
     * Completes the onboarding flow and navigates to the Home screen.
     * Marks onboarding as complete and sets [onboardingDone] to trigger navigation.
     */
    fun completeOnboarding() {
        viewModelScope.launch {
            settingsRepository.setOnboardingCompleted(true)
            analyticsHelper.onboardingCompleted()
            _state.update { it.copy(onboardingDone = true) }
        }
    }

    /**
     * Called when the paywall is dismissed (only relevant when triggered from outside onboarding,
     * e.g. HomeScreen). Completes the onboarding if it was pending.
     */
    fun onPaywallDismissed() {
        viewModelScope.launch {
            settingsRepository.setOnboardingCompleted(true)
            analyticsHelper.onboardingCompleted()
            _state.update {
                it.copy(
                    showPaywall = false,
                    onboardingDone = true,
                )
            }
        }
    }
}
