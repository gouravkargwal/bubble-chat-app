package com.rizzbot.v2.ui.paywall

import android.app.Activity
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
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class PaywallState(
    val isLoading: Boolean = true,
    val packages: List<Package> = emptyList(),
    val selectedPackage: Package? = null,
    val purchaseError: String? = null
)

@HiltViewModel
class PaywallViewModel @Inject constructor() : ViewModel() {

    private val _state = MutableStateFlow(PaywallState())
    val state: StateFlow<PaywallState> = _state.asStateFlow()

    init {
        fetchOfferings()
    }

    private fun fetchOfferings() {
        _state.update { it.copy(isLoading = true, purchaseError = null) }
        
        Purchases.sharedInstance.getOfferings(
            object : ReceiveOfferingsCallback {
                override fun onReceived(offerings: com.revenuecat.purchases.Offerings) {
                    val availablePackages = offerings.current?.availablePackages ?: emptyList()
                    _state.update {
                        it.copy(
                            isLoading = false,
                            packages = availablePackages,
                            selectedPackage = availablePackages.firstOrNull()
                        )
                    }
                }

                override fun onError(error: PurchasesError) {
                    _state.update {
                        it.copy(
                            isLoading = false,
                            purchaseError = "Failed to load offerings: ${error.message}"
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

    fun makePurchase(
        activity: Activity,
        packageToBuy: Package,
        onSuccess: () -> Unit
    ) {
        _state.update { it.copy(purchaseError = null) }
        
        val purchaseParams = PurchaseParams.Builder(activity, packageToBuy).build()
        Purchases.sharedInstance.purchase(
            purchaseParams,
            object : PurchaseCallback {
                override fun onCompleted(
                    storeTransaction: StoreTransaction,
                    customerInfo: com.revenuecat.purchases.CustomerInfo
                ) {
                    _state.update { it.copy(purchaseError = null) }
                    onSuccess()
                }

                override fun onError(error: PurchasesError, userCancelled: Boolean) {
                    val errorMessage = if (userCancelled) {
                        "Purchase cancelled"
                    } else {
                        "Purchase failed: ${error.message}"
                    }
                    _state.update { it.copy(purchaseError = errorMessage) }
                }
            }
        )
    }

    fun restorePurchases(onSuccess: () -> Unit) {
        _state.update { it.copy(purchaseError = null) }
        
        Purchases.sharedInstance.restorePurchases(
            object : ReceiveCustomerInfoCallback {
                override fun onReceived(customerInfo: com.revenuecat.purchases.CustomerInfo) {
                    // Check if user has active entitlements
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

                override fun onError(error: PurchasesError) {
                    _state.update {
                        it.copy(purchaseError = "Restore failed: ${error.message}")
                    }
                }
            }
        )
    }
}
