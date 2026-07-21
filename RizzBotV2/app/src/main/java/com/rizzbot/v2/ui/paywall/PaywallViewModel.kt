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
import com.rizzbot.v2.data.auth.AuthManager
import com.rizzbot.v2.data.subscription.SubscriptionManager
import com.rizzbot.v2.util.AnalyticsHelper
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

/**
 * Mapping from entitlement ID → [PaywallTier].
 * Single source of truth for the paywall UI; add new entitlements here.
 */
private val ENTITLEMENT_TIER_MAP: Map<String, PaywallTier> = mapOf(
    "match" to PaywallTier.Match,
    "crush" to PaywallTier.Crush,
    "rizz" to PaywallTier.Rizz,
)

private val TIER_PRIORITY: List<PaywallTier> = listOf(PaywallTier.Rizz, PaywallTier.Match, PaywallTier.Crush)

sealed class PaywallUiState {
    data object Loading : PaywallUiState()
    data class Success(val packages: List<Package>) : PaywallUiState()
    data class Error(val message: String) : PaywallUiState()
}

enum class PaywallTier {
    Crush, Match, Rizz
}

data class PaywallState(
    val uiState: PaywallUiState = PaywallUiState.Loading,
    val crushPackages: List<Package> = emptyList(),
    val matchPackages: List<Package> = emptyList(),
    val rizzPackages: List<Package> = emptyList(),
    val selectedTier: PaywallTier = PaywallTier.Match,
    val selectedPackage: Package? = null,
    val activeTier: PaywallTier? = null,
    val activeProductId: String? = null,
    val purchaseError: String? = null,
    val purchaseSuccess: Boolean = false,
    val isPurchasing: Boolean = false,
    val isRefreshingAfterPurchase: Boolean = false,
    val readyToNavigate: Boolean = false
)

@HiltViewModel
class PaywallViewModel @Inject constructor(
    private val subscriptionManager: SubscriptionManager,
    private val hostedRepository: HostedRepository,
    private val hapticHelper: HapticHelper,
    private val authManager: AuthManager,
    private val analyticsHelper: AnalyticsHelper,
) : ViewModel() {

    init {
        analyticsHelper.screenViewed("Paywall")
    }

    private val _state = MutableStateFlow(PaywallState())
    val state: StateFlow<PaywallState> = _state.asStateFlow()

    /** Live app tier + limits (same source as Settings) for paywall context copy */
    val usageState: StateFlow<UsageState> = hostedRepository.usageState

    init {
        fetchOfferings()
        observeActiveTier()
    }

    private fun observeActiveTier() {
        Purchases.sharedInstance.getCustomerInfo(
            object : ReceiveCustomerInfoCallback {
                override fun onReceived(customerInfo: com.revenuecat.purchases.CustomerInfo) {
                    applyRcCustomerInfo(customerInfo)
                }

                override fun onError(error: PurchasesError) {
                    // Non-fatal for UI; leave activeTier as-is
                }
            }
        )
    }

    /** Resolve [PaywallTier] from RevenueCat entitlements dynamically. */
    private fun resolveActiveTier(customerInfo: com.revenuecat.purchases.CustomerInfo): PaywallTier? {
        for (tier in TIER_PRIORITY) {
            val entitlementKey = ENTITLEMENT_TIER_MAP.entries.firstOrNull { it.value == tier }?.key ?: continue
            if (customerInfo.entitlements[entitlementKey]?.isActive == true) {
                return tier
            }
        }
        return null
    }

    /** Align paywall UI with RevenueCat entitlements (same keys as [SubscriptionManager]). */
    private fun applyRcCustomerInfo(customerInfo: com.revenuecat.purchases.CustomerInfo) {
        val activeTier = resolveActiveTier(customerInfo)
        val activeProductId = if (activeTier != null) {
            val entitlementKey = ENTITLEMENT_TIER_MAP.entries.firstOrNull { it.value == activeTier }?.key
            if (entitlementKey != null) customerInfo.entitlements[entitlementKey]?.productIdentifier else null
        } else null

        _state.update { it.copy(activeTier = activeTier, activeProductId = activeProductId) }
    }

    private fun hasCookdPaidEntitlement(customerInfo: com.revenuecat.purchases.CustomerInfo): Boolean {
        return ENTITLEMENT_TIER_MAP.keys.any { key ->
            customerInfo.entitlements[key]?.isActive == true
        }
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

                    // Match packages by RevenueCat package identifiers (configured in RC dashboard).
                    val crushPackages = defaultOffering.availablePackages.filter { pkg ->
                        pkg.identifier.contains("weekly", ignoreCase = true) ||
                        pkg.identifier.contains("crush", ignoreCase = true)
                    }
                    val matchPackages = defaultOffering.availablePackages.filter { pkg ->
                        (pkg.identifier.contains("monthly", ignoreCase = true) &&
                            !pkg.identifier.contains("crush", ignoreCase = true) &&
                            !pkg.identifier.contains("rizz", ignoreCase = true)) ||
                        pkg.identifier.contains("match", ignoreCase = true)
                    }
                    val rizzPackages = defaultOffering.availablePackages.filter { pkg ->
                        pkg.identifier.contains("rizz", ignoreCase = true) ||
                        pkg.identifier.contains("premium", ignoreCase = true)
                    }

                    val defaultSelected = matchPackages.firstOrNull() ?: rizzPackages.firstOrNull() ?: crushPackages.firstOrNull()

                    if (crushPackages.isEmpty() && matchPackages.isEmpty() && rizzPackages.isEmpty()) {
                        _state.update {
                            it.copy(uiState = PaywallUiState.Error("No packages found in default offering"))
                        }
                    } else {
                        _state.update {
                            it.copy(
                                uiState = PaywallUiState.Success(crushPackages + matchPackages + rizzPackages),
                                crushPackages = crushPackages,
                                matchPackages = matchPackages,
                                rizzPackages = rizzPackages,
                                selectedTier = PaywallTier.Match,
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
                PaywallTier.Crush -> it.crushPackages
                PaywallTier.Match -> it.matchPackages
                PaywallTier.Rizz -> it.rizzPackages
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
        // Prevent double-tap launching two billing flows at once — that races two
        // ProxyBillingActivity instances and can crash with a null PendingIntent.
        if (_state.value.isPurchasing) return
        _state.update { it.copy(purchaseError = null, purchaseSuccess = false, isPurchasing = true) }

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
                    applyRcCustomerInfo(customerInfo)
                    _state.update { it.copy(purchaseError = null, purchaseSuccess = true, isPurchasing = false) }

                    // Sync backend + RevenueCat in background
                    viewModelScope.launch {
                        // Refresh backend usage — guaranteed to see the new tier now
                        hostedRepository.refreshUsage(force = true)

                        // Sync local RevenueCat tier (catches any edge case)
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
                        analyticsHelper.recordNonFatal(
                            RuntimeException("Purchase failed: ${error.message}"),
                            context = "paywall_purchase_error package=${packageToBuy.identifier}"
                        )
                    }
                    _state.update {
                        it.copy(
                            purchaseError = errorMessage,
                            purchaseSuccess = false,
                            isPurchasing = false
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

    fun restorePurchases() {
        _state.update { it.copy(purchaseError = null) }

        // Restore must run after RevenueCat knows the same app user ID as the backend, otherwise
        // Play purchases stay on the anonymous RC profile and won't unlock this account.
        viewModelScope.launch {
            val userId = authManager.getUserId()
            if (!userId.isNullOrEmpty()) {
                subscriptionManager.setUserId(userId)
            }

            Purchases.sharedInstance.restorePurchases(
                object : ReceiveCustomerInfoCallback {
                    override fun onReceived(customerInfo: com.revenuecat.purchases.CustomerInfo) {
                        viewModelScope.launch {
                            subscriptionManager.updateUserTier()
                            applyRcCustomerInfo(customerInfo)

                            if (hasCookdPaidEntitlement(customerInfo)) {
                                // Force-refresh backend usage so tier syncs even if webhook is delayed
                                hostedRepository.refreshUsage(force = true)
                                hapticHelper.successTap()
                                _state.update { it.copy(purchaseError = null, purchaseSuccess = true) }
                            } else {
                                _state.update {
                                    it.copy(
                                        purchaseError = "No active Cookd subscription found for this Google account."
                                    )
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
