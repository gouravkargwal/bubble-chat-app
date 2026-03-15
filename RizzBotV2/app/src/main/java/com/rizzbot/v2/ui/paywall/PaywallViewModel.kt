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

data class PaywallState(
    val uiState: PaywallUiState = PaywallUiState.Loading,
    val packages: List<Package> = emptyList(),
    val proPackages: List<Package> = emptyList(),
    val premiumPackages: List<Package> = emptyList(),
    val selectedPackage: Package? = null,
    val purchaseError: String? = null,
    val purchaseSuccess: Boolean = false
)

@HiltViewModel
class PaywallViewModel @Inject constructor(
    private val subscriptionManager: SubscriptionManager
) : ViewModel() {

    private val _state = MutableStateFlow(PaywallState())
    val state: StateFlow<PaywallState> = _state.asStateFlow()

    init {
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

                    // Extract the 4 specific packages
                    val weeklyPackage = defaultOffering.availablePackages.find { 
                        it.identifier == "Weekly" 
                    }
                    val monthlyPackage = defaultOffering.availablePackages.find { 
                        it.identifier == "Monthly" 
                    }
                    val premiumWeeklyPackage = defaultOffering.availablePackages.find { 
                        it.identifier == "premium_weekly" 
                    }
                    val premiumMonthlyPackage = defaultOffering.availablePackages.find { 
                        it.identifier == "premium_monthly" 
                    }

                    val allPackages = listOfNotNull(
                        weeklyPackage,
                        monthlyPackage,
                        premiumWeeklyPackage,
                        premiumMonthlyPackage
                    )

                    val proPackages = listOfNotNull(weeklyPackage, monthlyPackage)
                    val premiumPackages = listOfNotNull(premiumWeeklyPackage, premiumMonthlyPackage)

                    // Default to Premium Monthly as "Best Value"
                    val defaultSelected = premiumMonthlyPackage ?: allPackages.firstOrNull()

                    if (allPackages.isEmpty()) {
                        _state.update {
                            it.copy(
                                uiState = PaywallUiState.Error("No packages found in default offering")
                            )
                        }
                    } else {
                        _state.update {
                            it.copy(
                                uiState = PaywallUiState.Success(allPackages),
                                packages = allPackages,
                                proPackages = proPackages,
                                premiumPackages = premiumPackages,
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

    fun selectPackage(packageToSelect: Package) {
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
        
        val purchaseParams = PurchaseParams.Builder(activity, packageToBuy).build()
        Purchases.sharedInstance.purchase(
            purchaseParams,
            object : PurchaseCallback {
                override fun onCompleted(
                    storeTransaction: StoreTransaction,
                    customerInfo: com.revenuecat.purchases.CustomerInfo
                ) {
                    // Check entitlements and update user tier
                    viewModelScope.launch {
                        val tier = when {
                            customerInfo.entitlements["premium"]?.isActive == true -> {
                                // Premium entitlement active -> God Mode (premium tier)
                                "premium"
                            }
                            customerInfo.entitlements["pro"]?.isActive == true -> {
                                // Pro entitlement active -> Pro
                                "pro"
                            }
                            else -> "free"
                        }
                        
                        // Update tier via SubscriptionManager
                        subscriptionManager.updateUserTier()
                        
                        Log.d("PaywallViewModel", "Purchase successful. Tier: $tier")
                        _state.update { 
                            it.copy(
                                purchaseError = null,
                                purchaseSuccess = true
                            ) 
                        }
                        onSuccess()
                    }
                }

                override fun onError(error: PurchasesError, userCancelled: Boolean) {
                    val errorMessage = if (userCancelled) {
                        "Purchase cancelled"
                    } else {
                        "Purchase failed: ${error.message}"
                    }
                    Log.e("PaywallViewModel", errorMessage)
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
                            _state.update { it.copy(purchaseError = null) }
                            onSuccess()
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
}
