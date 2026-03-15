package com.rizzbot.v2.data.auth

import android.accounts.AccountManager
import android.content.Context
import android.util.Log
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.GoogleAuthProvider
import com.rizzbot.v2.BuildConfig
import dagger.hilt.android.qualifiers.ApplicationContext
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
        if (webClientId.isBlank()) {
            return GoogleSignInResult.Error("Google Sign-In is not configured yet.")
        }

        return try {
            // First try authorized accounts for faster sign-in
            val idToken = try {
                getGoogleIdToken(activityContext, webClientId, filterByAuthorized = true)
            } catch (e: NoCredentialException) {
                // No previously authorized account — show full account picker
                try {
                    getGoogleIdToken(activityContext, webClientId, filterByAuthorized = false)
                } catch (e2: NoCredentialException) {
                    // This means no accounts are available or OAuth client is misconfigured
                    Log.e("GoogleSignIn", "NoCredentialException: ${e2.message}", e2)
                    // Check if device has Google accounts
                    val hasAccounts = AccountManager.get(context)
                        .getAccountsByType("com.google")
                        .isNotEmpty()
                    
                    if (!hasAccounts) {
                        return GoogleSignInResult.Error("No Google account found on this device. Please add one in Settings.")
                    } else {
                        // Device has accounts but Credential Manager can't access them
                        // This usually means OAuth client is not properly configured for this package
                        val packageName = context.packageName
                        Log.e("GoogleSignIn", "Device has Google accounts but sign-in failed. Package: $packageName, WebClientId: $webClientId")
                        return GoogleSignInResult.Error(
                            "Google Sign-In is not properly configured for this app. " +
                            "Please ensure the Android OAuth client is set up in Firebase Console for package: $packageName"
                        )
                    }
                }
            }

            if (idToken == null) {
                return GoogleSignInResult.Error("Could not retrieve your Google account. Please try again.")
            }

            // Sign in to Firebase with the Google credential
            val firebaseCredential = GoogleAuthProvider.getCredential(idToken, null)
            val authResult = firebaseAuth.signInWithCredential(firebaseCredential).await()
            val firebaseIdToken = authResult.user?.getIdToken(false)?.await()?.token
                ?: return GoogleSignInResult.Error("Something went wrong. Please try again.")

            // Send Firebase token to our backend to upgrade the account
            when (val authResult = authManager.authenticateFirebase(firebaseIdToken)) {
                is AuthManager.AuthResult.Success -> {
                    GoogleSignInResult.Success(firebaseIdToken, authResult.isNewUser)
                }
                is AuthManager.AuthResult.Error -> {
                    GoogleSignInResult.Error(authResult.message)
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
        val googleIdOption = GetGoogleIdOption.Builder()
            .setFilterByAuthorizedAccounts(filterByAuthorized)
            .setServerClientId(webClientId)
            .build()

        val request = GetCredentialRequest.Builder()
            .addCredentialOption(googleIdOption)
            .build()

        val result = credentialManager.getCredential(activityContext, request)
        val credential = result.credential

        if (credential is CustomCredential &&
            credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
        ) {
            return GoogleIdTokenCredential.createFrom(credential.data).idToken
        }
        return null
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
        firebaseAuth.signOut()
        authManager.clearAuth()
    }
}
