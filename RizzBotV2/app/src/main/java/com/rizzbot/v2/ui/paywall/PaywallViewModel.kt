package com.rizzbot.v2.ui.paywall

import android.app.Activity
import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.revenuecat.purchases.Package
import com.revenuecat.purchases.PurchaseParams
import com.revenuecat.purchases.Purchases
import com.revenuecat.purchases.PurchasesError
import com.revenuecat.purchases.models.StoreTransaction
import com.revenuecat.purchases.interfaces.PurchaseCallback
import com.revenuecat.purchases.interfaces.ReceiveCustomerInfoCallback
import com.revenuecat.purchases.interfaces.ReceiveOfferingsCallback
import com.rizzbot.v2.data.subscription.SubscriptionManager
import com.rizzbot.v2.util.HapticHelper
import com.rizzbot.v2.domain.model.UsageState
import com.rizzbot.v2.domain.repository.HostedRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class PaywallUiState {
    data object Loading : PaywallUiState()
    data class Success(val packages: List<Package>) : PaywallUiState()
    data class Error(val message: String) : PaywallUiState()
}

enum class PaywallTier {
    Pro, Premium
}

data class PaywallState(
    val uiState: PaywallUiState = PaywallUiState.Loading,
    val proPackages: List<Package> = emptyList(),
    val premiumPackages: List<Package> = emptyList(),
    val selectedTier: PaywallTier = PaywallTier.Premium,
    val selectedPackage: Package? = null,
    val activeTier: PaywallTier? = null,
    val activeProductId: String? = null,
    val purchaseError: String? = null,
    val purchaseSuccess: Boolean = false,
    val isRefreshingAfterPurchase: Boolean = false,
    val readyToNavigate: Boolean = false
)

@HiltViewModel
class PaywallViewModel @Inject constructor(
    private val subscriptionManager: SubscriptionManager,
    private val hostedRepository: HostedRepository,
    private val hapticHelper: HapticHelper,
) : ViewModel() {

    private val _state = MutableStateFlow(PaywallState())
    val state: StateFlow<PaywallState> = _state.asStateFlow()

    /** Live app tier + limits (same source as Settings) for paywall context copy */
    val usageState: StateFlow<UsageState> = hostedRepository.usageState

    init {
        fetchOfferings()
        observeActiveTier()
    }

    private fun observeActiveTier() {
        // Read current entitlements from RevenueCat to infer active tier
        Purchases.sharedInstance.getCustomerInfo(
            object : ReceiveCustomerInfoCallback {
                override fun onReceived(customerInfo: com.revenuecat.purchases.CustomerInfo) {
                    val premiumEntitlement = customerInfo.entitlements["premium"]
                    val proEntitlement = customerInfo.entitlements["pro"]

                    val hasPremium = premiumEntitlement?.isActive == true
                    val hasPro = proEntitlement?.isActive == true

                    val tier = when {
                        hasPremium -> PaywallTier.Premium
                        hasPro -> PaywallTier.Pro
                        else -> null
                    }

                    val activeId = when {
                        hasPremium -> premiumEntitlement?.productIdentifier
                        hasPro -> proEntitlement?.productIdentifier
                        else -> null
                    }

                    _state.update { it.copy(activeTier = tier, activeProductId = activeId) }
                }

                override fun onError(error: PurchasesError) {
                    // Non-fatal for UI; leave activeTier as-is
                }
            }
        )
    }

    fun retryLoadOfferings() {
        fetchOfferings()
    }

    private fun fetchOfferings() {
        _state.update { 
            it.copy(
                uiState = PaywallUiState.Loading,
                purchaseError = null
            ) 
        }
        
        Purchases.sharedInstance.getOfferings(
            object : ReceiveOfferingsCallback {
                override fun onReceived(offerings: com.revenuecat.purchases.Offerings) {
                    // Get the "default" offering
                    val defaultOffering = offerings["default"] ?: offerings.current
                    
                    if (defaultOffering == null) {
                        _state.update {
                            it.copy(
                                uiState = PaywallUiState.Error("No default offering found")
                            )
                        }
                        return
                    }

                    // Use the correct accessors for Pro packages
                    // RevenueCat Offering has weekly and monthly properties for standard packages
                    // 1. Get standard Pro packages (These are null-safe by default)
                    val weeklyPackage = defaultOffering.weekly
                    val monthlyPackage = defaultOffering.monthly

                    // 2. Safely find Premium packages using .find {} instead of .getPackage()
                    // .find returns null if not found, instead of crashing the app.
                    val premiumWeeklyPackage = defaultOffering.availablePackages.find { it.identifier == "premium_weekly" }
                    val premiumMonthlyPackage = defaultOffering.availablePackages.find { it.identifier == "premium_monthly" }

                    val proPackages = listOfNotNull(weeklyPackage, monthlyPackage)
                    val premiumPackages = listOfNotNull(premiumWeeklyPackage, premiumMonthlyPackage)
                    
                    // Default to Premium Monthly
                    val defaultSelected = premiumMonthlyPackage ?: premiumPackages.firstOrNull()

                    if (proPackages.isEmpty() && premiumPackages.isEmpty()) {
                        _state.update {
                            it.copy(
                                uiState = PaywallUiState.Error("No packages found in default offering")
                            )
                        }
                    } else {
                        _state.update {
                            it.copy(
                                uiState = PaywallUiState.Success(proPackages + premiumPackages),
                                proPackages = proPackages,
                                premiumPackages = premiumPackages,
                                selectedTier = PaywallTier.Premium,
                                selectedPackage = defaultSelected
                            )
                        }
                    }
                }

                override fun onError(error: PurchasesError) {
                    Log.e("PaywallViewModel", "Failed to fetch offerings: ${error.message}")
                    _state.update {
                        it.copy(
                            uiState = PaywallUiState.Error("Failed to load offerings: ${error.message}")
                        )
                    }
                }
            }
        )
    }

    fun selectTier(tier: PaywallTier) {
        _state.update {
            val packages = when (tier) {
                PaywallTier.Pro -> it.proPackages
                PaywallTier.Premium -> it.premiumPackages
            }
            val defaultPackage = packages.firstOrNull { 
                it.identifier.contains("monthly", ignoreCase = true) 
            } ?: packages.firstOrNull()
            
            it.copy(
                selectedTier = tier,
                selectedPackage = defaultPackage,
                purchaseError = null
            )
        }
    }

    fun selectPackage(packageToSelect: Package) {
        hapticHelper.lightTap()
        _state.update {
            it.copy(
                selectedPackage = packageToSelect,
                purchaseError = null
            )
        }
    }

    fun purchasePackage(
        activity: Activity,
        packageToBuy: Package,
        onSuccess: () -> Unit = {}
    ) {
        _state.update { it.copy(purchaseError = null, purchaseSuccess = false) }
        
        // For now, use the standard purchase flow. RevenueCat + Google Play will handle
        // subscription replacement with their default proration behavior when upgrading.
        val purchaseParams = PurchaseParams.Builder(activity, packageToBuy).build()
        Purchases.sharedInstance.purchase(
            purchaseParams,
            object : PurchaseCallback {
                override fun onCompleted(
                    storeTransaction: StoreTransaction,
                    customerInfo: com.revenuecat.purchases.CustomerInfo
                ) {
                    // Show success screen immediately — no network wait for the user
                    hapticHelper.successTap()
                    _state.update { it.copy(purchaseError = null, purchaseSuccess = true) }

                    // Sync tier in background so it's ready before "Start Exploring" navigates away
                    viewModelScope.launch {
                        subscriptionManager.updateUserTier()
                        Log.d("PaywallViewModel", "Purchase tier sync complete")
                    }
                }

                override fun onError(error: PurchasesError, userCancelled: Boolean) {
                    val errorMessage = if (userCancelled) {
                        null
                    } else {
                        "Purchase failed: ${error.message}"
                    }
                    if (!userCancelled) {
                        Log.e("PaywallViewModel", "Purchase failed: ${error.message}")
                    }
                    _state.update {
                        it.copy(
                            purchaseError = errorMessage,
                            purchaseSuccess = false
                        )
                    }
                }
            }
        )
    }

    // Keep the old method for backward compatibility
    fun makePurchase(
        activity: Activity,
        packageToBuy: Package,
        onSuccess: () -> Unit
    ) {
        purchasePackage(activity, packageToBuy, onSuccess)
    }

    fun restorePurchases(onSuccess: () -> Unit) {
        _state.update { it.copy(purchaseError = null) }
        
        Purchases.sharedInstance.restorePurchases(
            object : ReceiveCustomerInfoCallback {
                override fun onReceived(customerInfo: com.revenuecat.purchases.CustomerInfo) {
                    // Check if user has active entitlements and update tier
                    viewModelScope.launch {
                        subscriptionManager.updateUserTier()
                        
                        val hasActiveEntitlements = customerInfo.entitlements.active.isNotEmpty()
                        if (hasActiveEntitlements) {
                            _state.update { it.copy(purchaseError = null, purchaseSuccess = true) }
                        } else {
                            _state.update {
                                it.copy(purchaseError = "No active subscriptions found")
                            }
                        }
                    }
                }

                override fun onError(error: PurchasesError) {
                    _state.update {
                        it.copy(purchaseError = "Restore failed: ${error.message}")
                    }
                }
            }
        )
    }

    /**
     * Force-refresh tier and usage from the backend, bypassing the cache.
     * Sets readyToNavigate=true when done so the UI navigates only after data is fresh.
     */
    fun refreshUserTierFromBackend() {
        _state.update { it.copy(isRefreshingAfterPurchase = true, readyToNavigate = false) }
        viewModelScope.launch {
            try {
                subscriptionManager.updateUserTier()
                hostedRepository.refreshUsage(force = true)
            } catch (e: Exception) {
                Log.w("PaywallViewModel", "Failed to refresh user tier from backend", e)
            } finally {
                _state.update { it.copy(isRefreshingAfterPurchase = false, readyToNavigate = true) }
            }
        }
    }
}
