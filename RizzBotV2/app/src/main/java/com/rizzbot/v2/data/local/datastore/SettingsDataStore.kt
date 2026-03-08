package com.rizzbot.v2.data.local.datastore

import android.content.Context
import android.content.SharedPreferences
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "rizzbot_v2_settings")

@Singleton
class SettingsDataStore @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private object Keys {
        val PROVIDER = stringPreferencesKey("provider")
        val MODEL_ID = stringPreferencesKey("model_id")
        val API_KEY = stringPreferencesKey("api_key") // kept for migration only
        val SERVICE_ENABLED = booleanPreferencesKey("service_enabled")
        val ONBOARDING_COMPLETED = booleanPreferencesKey("onboarding_completed")
        val TOTAL_REPLIES_GENERATED = intPreferencesKey("total_replies_generated")
        val TOTAL_REPLIES_COPIED = intPreferencesKey("total_replies_copied")
        val FIRST_CAPTURE_DONE = booleanPreferencesKey("first_capture_done")
        val LAST_CAPTURE_TIMESTAMP = longPreferencesKey("last_capture_timestamp")
    }

    private companion object {
        const val ENCRYPTED_API_KEY = "encrypted_api_key"
        const val MIGRATION_DONE = "api_key_migration_done"
    }

    private val encryptedPrefs: SharedPreferences by lazy {
        val masterKeyAlias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)
        EncryptedSharedPreferences.create(
            "rizzbot_v2_secure_prefs",
            masterKeyAlias,
            context,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    val provider: Flow<String?> = context.dataStore.data.map { it[Keys.PROVIDER] }
    val modelId: Flow<String?> = context.dataStore.data.map { it[Keys.MODEL_ID] }
    val apiKey: Flow<String?> = context.dataStore.data.map {
        migrateApiKeyIfNeeded()
        val key = encryptedPrefs.getString(ENCRYPTED_API_KEY, null)
        key?.ifEmpty { null }
    }
    val serviceEnabled: Flow<Boolean> = context.dataStore.data.map { it[Keys.SERVICE_ENABLED] ?: false }
    val onboardingCompleted: Flow<Boolean> = context.dataStore.data.map { it[Keys.ONBOARDING_COMPLETED] ?: false }
    val totalRepliesGenerated: Flow<Int> = context.dataStore.data.map { it[Keys.TOTAL_REPLIES_GENERATED] ?: 0 }
    val totalRepliesCopied: Flow<Int> = context.dataStore.data.map { it[Keys.TOTAL_REPLIES_COPIED] ?: 0 }
    val firstCaptureDone: Flow<Boolean> = context.dataStore.data.map { it[Keys.FIRST_CAPTURE_DONE] ?: false }
    val lastCaptureTimestamp: Flow<Long> = context.dataStore.data.map { it[Keys.LAST_CAPTURE_TIMESTAMP] ?: 0L }

    suspend fun setProvider(provider: String) = context.dataStore.edit { it[Keys.PROVIDER] = provider }
    suspend fun setModelId(modelId: String) = context.dataStore.edit { it[Keys.MODEL_ID] = modelId }

    suspend fun setApiKey(apiKey: String) {
        encryptedPrefs.edit().putString(ENCRYPTED_API_KEY, apiKey).apply()
        context.dataStore.edit { it.remove(Keys.API_KEY) }
    }

    suspend fun setServiceEnabled(enabled: Boolean) = context.dataStore.edit { it[Keys.SERVICE_ENABLED] = enabled }
    suspend fun setOnboardingCompleted(completed: Boolean) = context.dataStore.edit { it[Keys.ONBOARDING_COMPLETED] = completed }
    suspend fun incrementRepliesGenerated() = context.dataStore.edit { prefs ->
        prefs[Keys.TOTAL_REPLIES_GENERATED] = (prefs[Keys.TOTAL_REPLIES_GENERATED] ?: 0) + 1
    }
    suspend fun incrementRepliesCopied() = context.dataStore.edit { prefs ->
        prefs[Keys.TOTAL_REPLIES_COPIED] = (prefs[Keys.TOTAL_REPLIES_COPIED] ?: 0) + 1
    }
    suspend fun setFirstCaptureDone() = context.dataStore.edit { it[Keys.FIRST_CAPTURE_DONE] = true }
    suspend fun setLastCaptureTimestamp(timestamp: Long) = context.dataStore.edit { it[Keys.LAST_CAPTURE_TIMESTAMP] = timestamp }

    private suspend fun migrateApiKeyIfNeeded() {
        if (encryptedPrefs.getBoolean(MIGRATION_DONE, false)) return
        val plainKey = context.dataStore.data.first()[Keys.API_KEY]
        if (!plainKey.isNullOrEmpty()) {
            encryptedPrefs.edit()
                .putString(ENCRYPTED_API_KEY, plainKey)
                .putBoolean(MIGRATION_DONE, true)
                .apply()
            context.dataStore.edit { it.remove(Keys.API_KEY) }
        } else {
            encryptedPrefs.edit().putBoolean(MIGRATION_DONE, true).apply()
        }
    }
}
