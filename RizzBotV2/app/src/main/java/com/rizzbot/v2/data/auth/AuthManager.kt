package com.rizzbot.v2.data.auth

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import com.rizzbot.v2.data.remote.api.HostedApi
import com.rizzbot.v2.data.remote.dto.FirebaseAuthRequest
import com.google.firebase.auth.FirebaseAuth
import com.rizzbot.v2.data.subscription.SubscriptionManager
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.Lazy
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.tasks.await

@Singleton
class AuthManager @Inject constructor(
    @ApplicationContext private val context: Context,
    private val hostedApi: dagger.Lazy<HostedApi>,
    private val subscriptionManager: Lazy<SubscriptionManager>
) {
    private companion object {
        const val PREFS_NAME = "cookd_auth"
        const val KEY_TOKEN = "jwt_token"
        const val KEY_USER_ID = "user_id"
        const val KEY_EXPIRES_AT = "expires_at"
    }

    private val prefs by lazy {
        val masterKey = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)
        EncryptedSharedPreferences.create(
            PREFS_NAME,
            masterKey,
            context,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    private val firebaseAuth: FirebaseAuth by lazy { FirebaseAuth.getInstance() }

    fun getToken(): String? = prefs.getString(KEY_TOKEN, null)

    fun isAuthenticated(): Boolean {
        val token = getToken() ?: return false
        val expiresAt = prefs.getLong(KEY_EXPIRES_AT, 0L)
        return token.isNotEmpty() && System.currentTimeMillis() / 1000 < expiresAt
    }

    fun getValidToken(): String? {
        if (isAuthenticated()) return getToken()
        return null
    }

    fun getUserId(): String? = prefs.getString(KEY_USER_ID, null)

    suspend fun authenticateFirebase(
        firebaseIdToken: String,
        googleProviderId: String?
    ): AuthResult {
        return try {
            val response = hostedApi.get().authenticateFirebase(
                FirebaseAuthRequest(
                    firebaseToken = firebaseIdToken,
                    googleProviderId = googleProviderId
                )
            )
            saveAuth(response.token, response.userId, response.expiresAt)
            
            // Sync RevenueCat user ID after authentication
            subscriptionManager.get().setUserId(response.userId)
            
            AuthResult.Success(response.isNewUser)
        } catch (e: Exception) {
            AuthResult.Error(e.message ?: "Authentication failed")
        }
    }
    
    sealed class AuthResult {
        data class Success(val isNewUser: Boolean) : AuthResult()
        data class Error(val message: String) : AuthResult()
    }

    fun clearAuth() {
        prefs.edit()
            .remove(KEY_TOKEN)
            .remove(KEY_USER_ID)
            .remove(KEY_EXPIRES_AT)
            .apply()
    }

    private fun saveAuth(token: String, userId: String, expiresAt: Long) {
        prefs.edit()
            .putString(KEY_TOKEN, token)
            .putString(KEY_USER_ID, userId)
            .putLong(KEY_EXPIRES_AT, expiresAt)
            .apply()
    }

    /**
     * Attempts to silently re-issue our backend JWT using the currently signed-in Firebase user.
     *
     * This is used to avoid "logged out" loops when our backend JWT is rejected (401) after an app
     * restart, but Firebase still has a valid refresh session.
     */
    suspend fun refreshBackendTokenIfFirebaseSignedIn(): Boolean {
        val firebaseUser = firebaseAuth.currentUser ?: return false

        val firebaseIdToken = firebaseUser.getIdToken(false).await().token ?: return false

        // Stable provider identifier for cross-device lookup.
        val googleProviderId = firebaseUser.providerData
            .firstOrNull { it.providerId == "google.com" }
            ?.uid

        return try {
            val response = hostedApi.get().authenticateFirebase(
                FirebaseAuthRequest(
                    firebaseToken = firebaseIdToken,
                    googleProviderId = googleProviderId
                )
            )

            saveAuth(response.token, response.userId, response.expiresAt)

            // Keep RevenueCat identity aligned with the backend user.
            subscriptionManager.get().setUserId(response.userId)
            true
        } catch (_: Exception) {
            false
        }
    }
}
