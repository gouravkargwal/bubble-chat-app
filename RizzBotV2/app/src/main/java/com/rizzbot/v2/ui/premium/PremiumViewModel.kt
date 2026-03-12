package com.rizzbot.v2.ui.premium

import android.app.Activity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.android.billingclient.api.ProductDetails
import com.rizzbot.v2.data.billing.BillingManager
import com.rizzbot.v2.data.billing.PurchaseResult
import com.rizzbot.v2.domain.repository.HostedRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import javax.inject.Inject

data class PremiumUiState(
    val isReady: Boolean = false,
    val premiumWeekly: ProductDetails? = null,
    val premiumMonthly: ProductDetails? = null,
    val proWeekly: ProductDetails? = null,
    val proMonthly: ProductDetails? = null,
    val isPurchasing: Boolean = false,
    val purchaseResult: PurchaseResult? = null,
    val currentTier: String = "free",
    val isWeekly: Boolean = false
)

@HiltViewModel
class PremiumViewModel @Inject constructor(
    private val billingManager: BillingManager,
    private val hostedRepository: HostedRepository
) : ViewModel() {

    private val _isWeekly = MutableStateFlow(false)

    val uiState: StateFlow<PremiumUiState> = combine(
        billingManager.state,
        hostedRepository.usageState,
        _isWeekly
    ) { billing, usage, weekly ->
        PremiumUiState(
            isReady = billing.isReady,
            premiumWeekly = billing.products.find { it.productId == BillingManager.PREMIUM_WEEKLY },
            premiumMonthly = billing.products.find { it.productId == BillingManager.PREMIUM_MONTHLY },
            proWeekly = billing.products.find { it.productId == BillingManager.PRO_WEEKLY },
            proMonthly = billing.products.find { it.productId == BillingManager.PRO_MONTHLY },
            isPurchasing = billing.isPurchasing,
            purchaseResult = billing.purchaseResult,
            currentTier = usage.tier.ifBlank {
                if (usage.isPremium) "pro" else "free"
            }.lowercase(),
            isWeekly = weekly
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), PremiumUiState())

    init {
        billingManager.connect()
    }

    fun toggleBillingPeriod(weekly: Boolean) {
        _isWeekly.value = weekly
    }

    fun purchase(activity: Activity, productDetails: ProductDetails) {
        billingManager.launchPurchase(activity, productDetails)
    }

    fun restorePurchases() {
        billingManager.restorePurchases()
    }

    fun clearResult() {
        billingManager.clearPurchaseResult()
    }
}
