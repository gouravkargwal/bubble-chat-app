package com.rizzbot.v2.data.local.datastore

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "cookd_settings")

@Singleton
class SettingsDataStore @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private object Keys {
        val SERVICE_ENABLED = booleanPreferencesKey("service_enabled")
        val ONBOARDING_COMPLETED = booleanPreferencesKey("onboarding_completed")
        val TOTAL_REPLIES_GENERATED = intPreferencesKey("total_replies_generated")
        val TOTAL_REPLIES_COPIED = intPreferencesKey("total_replies_copied")
        val FIRST_CAPTURE_DONE = booleanPreferencesKey("first_capture_done")
        val LAST_CAPTURE_TIMESTAMP = longPreferencesKey("last_capture_timestamp")
    }

    val serviceEnabled: Flow<Boolean> = context.dataStore.data.map { it[Keys.SERVICE_ENABLED] ?: false }
    val onboardingCompleted: Flow<Boolean> = context.dataStore.data.map { it[Keys.ONBOARDING_COMPLETED] ?: false }
    val totalRepliesGenerated: Flow<Int> = context.dataStore.data.map { it[Keys.TOTAL_REPLIES_GENERATED] ?: 0 }
    val totalRepliesCopied: Flow<Int> = context.dataStore.data.map { it[Keys.TOTAL_REPLIES_COPIED] ?: 0 }
    val firstCaptureDone: Flow<Boolean> = context.dataStore.data.map { it[Keys.FIRST_CAPTURE_DONE] ?: false }
    val lastCaptureTimestamp: Flow<Long> = context.dataStore.data.map { it[Keys.LAST_CAPTURE_TIMESTAMP] ?: 0L }

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
}
