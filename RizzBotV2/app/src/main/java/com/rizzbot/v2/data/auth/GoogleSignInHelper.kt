package com.rizzbot.v2.data.auth

import android.accounts.AccountManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import java.security.MessageDigest
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.GoogleAuthProvider
import com.revenuecat.purchases.Purchases
import com.revenuecat.purchases.CustomerInfo
import com.revenuecat.purchases.PurchasesError
import com.revenuecat.purchases.interfaces.LogInCallback
import com.revenuecat.purchases.interfaces.ReceiveCustomerInfoCallback
import com.rizzbot.v2.BuildConfig
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.launch
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.tasks.await
import javax.inject.Inject
import javax.inject.Singleton

sealed class GoogleSignInResult {
    data class Success(val firebaseIdToken: String, val isNewUser: Boolean) : GoogleSignInResult()
    data class Error(val message: String) : GoogleSignInResult()
}

@Singleton
class GoogleSignInHelper @Inject constructor(
    @ApplicationContext private val context: Context,
    private val authManager: AuthManager
) {
    private val credentialManager = CredentialManager.create(context)
    private val firebaseAuth = FirebaseAuth.getInstance()

    suspend fun signIn(activityContext: Context): GoogleSignInResult {
        val webClientId = BuildConfig.GOOGLE_WEB_CLIENT_ID
        val packageName = context.packageName
        
        // Log configuration details for debugging
        Log.d("GoogleSignIn", "=== Google Sign-In Configuration ===")
        Log.d("GoogleSignIn", "Package Name: $packageName")
        Log.d("GoogleSignIn", "Web Client ID: $webClientId")
        Log.d("GoogleSignIn", "BuildConfig.BACKEND_URL: ${BuildConfig.BACKEND_URL}")
        Log.d("GoogleSignIn", "=====================================")
        
        if (webClientId.isBlank()) {
            Log.e("GoogleSignIn", "Web Client ID is blank or not configured")
            return GoogleSignInResult.Error("Google Sign-In is not configured yet.")
        }

        return try {
            // First try authorized accounts for faster sign-in
            Log.d("GoogleSignIn", "Attempting sign-in with authorized accounts first...")
            val idToken = try {
                getGoogleIdToken(activityContext, webClientId, filterByAuthorized = true)
            } catch (e: NoCredentialException) {
                // No previously authorized account — show full account picker
                Log.d("GoogleSignIn", "No authorized account found, trying full account picker...")
                try {
                    getGoogleIdToken(activityContext, webClientId, filterByAuthorized = false)
                } catch (e2: NoCredentialException) {
                    // This means no accounts are available or OAuth client is misconfigured
                    Log.e("GoogleSignIn", "NoCredentialException: ${e2.message}", e2)
                    // Check if device has Google accounts
                    val hasAccounts = AccountManager.get(context)
                        .getAccountsByType("com.google")
                        .isNotEmpty()
                    
                    Log.d("GoogleSignIn", "Device has Google accounts: $hasAccounts")
                    
                    if (!hasAccounts) {
                        return GoogleSignInResult.Error("No Google account found on this device. Please add one in Settings.")
                    } else {
                        // Device has accounts but Credential Manager can't access them
                        // This usually means OAuth client is not properly configured for this package
                        Log.e("GoogleSignIn", "Device has Google accounts but sign-in failed. Package: $packageName, WebClientId: $webClientId")
                        return GoogleSignInResult.Error(
                            "Google Sign-In is not properly configured for this app. " +
                            "Please ensure the Android OAuth client is set up in Firebase Console for package: $packageName"
                        )
                    }
                }
            }

            if (idToken == null) {
                Log.e("GoogleSignIn", "Failed to retrieve Google ID token")
                return GoogleSignInResult.Error("Could not retrieve your Google account. Please try again.")
            }

            Log.d("GoogleSignIn", "Successfully retrieved Google ID token, signing in to Firebase...")
            // Sign in to Firebase with the Google credential
            val firebaseCredential = GoogleAuthProvider.getCredential(idToken, null)
            val authResult = firebaseAuth.signInWithCredential(firebaseCredential).await()
            val firebaseUser = authResult.user
            val firebaseIdToken = firebaseUser?.getIdToken(false)?.await()?.token
                ?: return GoogleSignInResult.Error("Something went wrong. Please try again.")
            
            val firebaseUserId = firebaseUser?.uid
            Log.d("GoogleSignIn", "Firebase sign-in successful, user ID: $firebaseUserId")

            // Extract stable Google provider ID from providerData (NOT the Firebase UID).
            val googleProviderId = firebaseUser
                ?.providerData
                ?.firstOrNull { it.providerId == "google.com" }
                ?.uid
            Log.d("GoogleSignIn", "Google provider ID (stable): $googleProviderId")

            // Send Firebase token (and stable Google provider ID) to our backend to upgrade the account
            when (val backendAuthResult = authManager.authenticateFirebase(firebaseIdToken, googleProviderId)) {
                is AuthManager.AuthResult.Success -> {
                    // Get the backend user ID (preferred) or fall back to Firebase UID
                    val userId = authManager.getUserId() ?: firebaseUserId ?: ""
                    
                    if (userId.isNotEmpty()) {
                        // Sync user identity with RevenueCat (non-blocking)
                        syncRevenueCatUser(userId)
                    } else {
                        Log.w("GoogleSignIn", "No user ID available for RevenueCat sync")
                    }
                    
                    GoogleSignInResult.Success(firebaseIdToken, backendAuthResult.isNewUser)
                }
                is AuthManager.AuthResult.Error -> {
                    GoogleSignInResult.Error(backendAuthResult.message)
                }
            }
        } catch (e: GetCredentialCancellationException) {
            GoogleSignInResult.Error("Sign-in was cancelled.")
        } catch (e: Exception) {
            Log.e("GoogleSignIn", "Sign-in failed", e)
            GoogleSignInResult.Error("Something went wrong. Please try again.")
        }
    }

    private suspend fun getGoogleIdToken(
        activityContext: Context,
        webClientId: String,
        filterByAuthorized: Boolean
    ): String? {
        Log.d("GoogleSignIn", "getGoogleIdToken called - filterByAuthorized: $filterByAuthorized, webClientId: $webClientId")
        
        val googleIdOption = GetGoogleIdOption.Builder()
            .setFilterByAuthorizedAccounts(filterByAuthorized)
            .setServerClientId(webClientId)
            .build()

        val request = GetCredentialRequest.Builder()
            .addCredentialOption(googleIdOption)
            .build()

        logAppSigningSha1(activityContext)
        Log.d("GoogleSignIn", "Requesting credential from CredentialManager...")
        val result = credentialManager.getCredential(activityContext, request)
        val credential = result.credential

        if (credential is CustomCredential &&
            credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
        ) {
            val idToken = GoogleIdTokenCredential.createFrom(credential.data).idToken
            Log.d("GoogleSignIn", "Successfully retrieved Google ID token")
            return idToken
        }
        
        Log.w("GoogleSignIn", "Credential is not a Google ID token credential. Type: ${credential::class.simpleName}")
        return null
    }

    private fun logAppSigningSha1(ctx: Context) {
        try {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.P) return
            val pkgInfo = ctx.packageManager.getPackageInfo(ctx.packageName, PackageManager.GET_SIGNING_CERTIFICATES)
            val signingInfo = pkgInfo.signingInfo ?: return
            val signers = signingInfo.apkContentsSigners
            val sha1s = signers.map { cert ->
                val md = MessageDigest.getInstance("SHA1")
                val digest = md.digest(cert.toByteArray())
                digest.joinToString(":") { b -> "%02x".format(b) }
            }
            Log.d("GoogleSignIn", "App signing SHA-1(s): ${sha1s.joinToString()}")
        } catch (t: Throwable) {
            Log.e("GoogleSignIn", "Failed to log app signing SHA-1", t)
        }
    }

    fun isSignedIn(): Boolean {
        return firebaseAuth.currentUser != null
    }

    fun getCurrentUserEmail(): String? {
        return firebaseAuth.currentUser?.email
    }

    fun getCurrentUserName(): String? {
        return firebaseAuth.currentUser?.displayName
    }

    fun signOut() {
        Log.d("GoogleSignIn", "Signing out user...")

        // Log out from RevenueCat to clear subscription cache
        try {
            Purchases.sharedInstance.logOut(
                object : ReceiveCustomerInfoCallback {
                    override fun onReceived(customerInfo: CustomerInfo) {
                        Log.d(
                            "GoogleSignIn",
                            "RevenueCat logout successful. Active entitlements after logout: ${customerInfo.entitlements.active.keys}"
                        )
                    }

                    override fun onError(error: PurchasesError) {
                        Log.e(
                            "GoogleSignIn",
                            "RevenueCat logout failed: ${error.message} (Code: ${error.code})"
                        )
                    }
                }
            )
        } catch (e: Exception) {
            Log.e("GoogleSignIn", "Exception during RevenueCat logout: ${e.message}", e)
        }

        firebaseAuth.signOut()
        authManager.clearAuth()

        Log.d("GoogleSignIn", "Sign out completed")
    }
    
    /**
     * Sync user identity with RevenueCat after successful authentication.
     * This is called asynchronously and doesn't block the main UI flow.
     */
    private fun syncRevenueCatUser(userId: String) {
        // Launch in IO dispatcher to avoid blocking UI
        CoroutineScope(Dispatchers.IO).launch {
            try {
                Log.d("GoogleSignIn", "Syncing RevenueCat user ID: $userId")
                
                Purchases.sharedInstance.logIn(
                    userId,
                    object : LogInCallback {
                        override fun onReceived(customerInfo: CustomerInfo, created: Boolean) {
                            Log.d(
                                "GoogleSignIn",
                                "RevenueCat logIn successful. User ID: $userId, Created: $created, " +
                                "Active Entitlements: ${customerInfo.entitlements.active.keys}"
                            )
                        }

                        override fun onError(error: PurchasesError) {
                            Log.e(
                                "GoogleSignIn",
                                "RevenueCat logIn failed for user ID: $userId. Error: ${error.message} (Code: ${error.code})"
                            )
                        }
                    }
                )
            } catch (e: Exception) {
                Log.e("GoogleSignIn", "Exception during RevenueCat sync: ${e.message}", e)
            }
        }
    }
}
