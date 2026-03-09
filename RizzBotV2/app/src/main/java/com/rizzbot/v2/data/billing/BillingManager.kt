package com.rizzbot.v2.data.billing

import android.app.Activity
import android.content.Context
import android.util.Log
import com.android.billingclient.api.*
import com.rizzbot.v2.domain.repository.HostedRepository
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

data class BillingState(
    val isReady: Boolean = false,
    val products: List<ProductDetails> = emptyList(),
    val isPurchasing: Boolean = false,
    val purchaseResult: PurchaseResult? = null
)

sealed class PurchaseResult {
    data object Success : PurchaseResult()
    data class Error(val message: String) : PurchaseResult()
    data object Cancelled : PurchaseResult()
}

@Singleton
class BillingManager @Inject constructor(
    @ApplicationContext private val context: Context,
    private val hostedRepository: HostedRepository
) : PurchasesUpdatedListener {

    companion object {
        private const val TAG = "BillingManager"
        const val PREMIUM_WEEKLY = "cookd_premium_weekly"
        const val PREMIUM_MONTHLY = "cookd_premium_monthly"
        const val PRO_WEEKLY = "cookd_pro_weekly"
        const val PRO_MONTHLY = "cookd_pro_monthly"
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    private val _state = MutableStateFlow(BillingState())
    val state: StateFlow<BillingState> = _state.asStateFlow()

    private val billingClient: BillingClient = BillingClient.newBuilder(context)
        .setListener(this)
        .enablePendingPurchases()
        .build()

    fun connect() {
        billingClient.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(result: BillingResult) {
                if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                    Log.d(TAG, "Billing client connected")
                    _state.value = _state.value.copy(isReady = true)
                    queryProducts()
                    restorePurchases()
                } else {
                    Log.e(TAG, "Billing setup failed: ${result.debugMessage}")
                }
            }

            override fun onBillingServiceDisconnected() {
                Log.w(TAG, "Billing service disconnected")
                _state.value = _state.value.copy(isReady = false)
            }
        })
    }

    private fun queryProducts() {
        val productList = listOf(
            PREMIUM_WEEKLY, PREMIUM_MONTHLY, PRO_WEEKLY, PRO_MONTHLY
        ).map { productId ->
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(productId)
                .setProductType(BillingClient.ProductType.SUBS)
                .build()
        }

        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(productList)
            .build()

        billingClient.queryProductDetailsAsync(params) { result, productDetailsList ->
            if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                Log.d(TAG, "Products loaded: ${productDetailsList.size}")
                _state.value = _state.value.copy(products = productDetailsList)
            } else {
                Log.e(TAG, "Failed to query products: ${result.debugMessage}")
            }
        }
    }

    fun launchPurchase(activity: Activity, productDetails: ProductDetails) {
        val offerToken = productDetails.subscriptionOfferDetails?.firstOrNull()?.offerToken
            ?: return

        val productDetailsParams = BillingFlowParams.ProductDetailsParams.newBuilder()
            .setProductDetails(productDetails)
            .setOfferToken(offerToken)
            .build()

        val billingFlowParams = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(listOf(productDetailsParams))
            .build()

        _state.value = _state.value.copy(isPurchasing = true, purchaseResult = null)
        billingClient.launchBillingFlow(activity, billingFlowParams)
    }

    override fun onPurchasesUpdated(result: BillingResult, purchases: List<Purchase>?) {
        when (result.responseCode) {
            BillingClient.BillingResponseCode.OK -> {
                purchases?.forEach { purchase ->
                    if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
                        verifyAndAcknowledge(purchase)
                    }
                }
            }
            BillingClient.BillingResponseCode.USER_CANCELED -> {
                _state.value = _state.value.copy(
                    isPurchasing = false,
                    purchaseResult = PurchaseResult.Cancelled
                )
            }
            else -> {
                _state.value = _state.value.copy(
                    isPurchasing = false,
                    purchaseResult = PurchaseResult.Error(result.debugMessage)
                )
            }
        }
    }

    private fun verifyAndAcknowledge(purchase: Purchase) {
        scope.launch {
            val productId = purchase.products.firstOrNull() ?: return@launch
            val verified = hostedRepository.verifyPurchase(
                purchaseToken = purchase.purchaseToken,
                productId = productId,
                orderId = purchase.orderId
            )

            if (verified) {
                _state.value = _state.value.copy(
                    isPurchasing = false,
                    purchaseResult = PurchaseResult.Success
                )
            } else {
                _state.value = _state.value.copy(
                    isPurchasing = false,
                    purchaseResult = PurchaseResult.Error("Verification failed. Please contact support.")
                )
            }
        }
    }

    fun restorePurchases() {
        val params = QueryPurchasesParams.newBuilder()
            .setProductType(BillingClient.ProductType.SUBS)
            .build()

        billingClient.queryPurchasesAsync(params) { result, purchases ->
            if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                purchases.filter { it.purchaseState == Purchase.PurchaseState.PURCHASED }
                    .forEach { verifyAndAcknowledge(it) }
            }
        }
    }

    fun clearPurchaseResult() {
        _state.value = _state.value.copy(purchaseResult = null)
    }

    fun disconnect() {
        billingClient.endConnection()
    }
}
