package com.rizzbot.v2.data.subscription

import com.revenuecat.purchases.CustomerInfo
import com.revenuecat.purchases.Purchases
import com.revenuecat.purchases.PurchasesError
import com.revenuecat.purchases.interfaces.ReceiveCustomerInfoCallback
import com.revenuecat.purchases.interfaces.LogInCallback
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SubscriptionManager @Inject constructor() {
    private val _userTier = MutableStateFlow<String>("free")
    val userTier: StateFlow<String> = _userTier.asStateFlow()

    /**
     * Update the RevenueCat user ID when user authenticates.
     * Call this after successful authentication with the backend user_id.
     */
    suspend fun setUserId(userId: String): Result<Unit> {
        return try {
            // Bridge RevenueCat callback API into coroutines
            val (customerInfo, created) = suspendCancellableCoroutine<Pair<CustomerInfo, Boolean>> { cont ->
                Purchases.sharedInstance.logIn(
                    userId,
                    object : LogInCallback {
                        override fun onReceived(customerInfo: CustomerInfo, created: Boolean) {
                            if (cont.isActive) cont.resume(Pair(customerInfo, created))
                        }

                        override fun onError(error: PurchasesError) {
                            if (cont.isActive) cont.resumeWithException(
                                RuntimeException(error.message)
                            )
                        }
                    }
                )
            }

            android.util.Log.d(
                "SubscriptionManager",
                "LogIn completed. Created: $created, userId: $userId"
            )

            updateUserTier()
            Result.success(Unit)
        } catch (e: Exception) {
            android.util.Log.e("SubscriptionManager", "Failed to set user ID: ${e.message}")
            Result.failure(e)
        }
    }

    /**
     * Fetch CustomerInfo from RevenueCat and update local tier state.
     * Returns "premium", "pro", or "free" based on active entitlements.
     */
    suspend fun updateUserTier(): Result<String> {
        return try {
            // Use the official callback-based API and wrap it in a coroutine
            val customerInfo: CustomerInfo = suspendCancellableCoroutine { cont ->
                Purchases.sharedInstance.getCustomerInfo(
                    object : ReceiveCustomerInfoCallback {
                        override fun onReceived(customerInfo: CustomerInfo) {
                            if (cont.isActive) cont.resume(customerInfo)
                        }

                        override fun onError(error: PurchasesError) {
                            if (cont.isActive) cont.resumeWithException(
                                Exception(error.message)
                            )
                        }
                    }
                )
            }
            val tier = when {
                customerInfo.entitlements["premium"]?.isActive == true -> "premium"
                customerInfo.entitlements["pro"]?.isActive == true -> "pro"
                else -> "free"
            }
            _userTier.value = tier
            android.util.Log.d("SubscriptionManager", "User tier updated: $tier")
            Result.success(tier)
        } catch (e: Exception) {
            android.util.Log.e("SubscriptionManager", "Failed to update user tier: ${e.message}")
            Result.failure(e)
        }
    }

    fun getCurrentTier(): String = _userTier.value
}
