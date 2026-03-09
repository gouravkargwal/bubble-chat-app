package com.rizzbot.v2.data.auth

import android.content.Context
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
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
    data class Success(val firebaseIdToken: String) : GoogleSignInResult()
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
            return GoogleSignInResult.Error("Google Sign-In not configured. Set GOOGLE_WEB_CLIENT_ID in gradle.properties.")
        }

        return try {
            val googleIdOption = GetGoogleIdOption.Builder()
                .setFilterByAuthorizedAccounts(false)
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
                val googleIdTokenCredential = GoogleIdTokenCredential.createFrom(credential.data)
                val idToken = googleIdTokenCredential.idToken

                // Sign in to Firebase with the Google credential
                val firebaseCredential = GoogleAuthProvider.getCredential(idToken, null)
                val authResult = firebaseAuth.signInWithCredential(firebaseCredential).await()
                val firebaseIdToken = authResult.user?.getIdToken(false)?.await()?.token
                    ?: return GoogleSignInResult.Error("Failed to get Firebase token")

                // Send Firebase token to our backend to upgrade the account
                val success = authManager.authenticateFirebase(firebaseIdToken)
                if (success) {
                    GoogleSignInResult.Success(firebaseIdToken)
                } else {
                    GoogleSignInResult.Error("Backend authentication failed")
                }
            } else {
                GoogleSignInResult.Error("Unexpected credential type")
            }
        } catch (e: Exception) {
            GoogleSignInResult.Error(e.message ?: "Sign-in failed")
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
        firebaseAuth.signOut()
        authManager.clearAuth()
    }
}
