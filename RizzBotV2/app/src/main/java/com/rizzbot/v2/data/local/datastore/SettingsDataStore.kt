package com.rizzbot.v2.data.local.datastore

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
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
        // Removed: TOTAL_REPLIES_GENERATED, TOTAL_REPLIES_COPIED (now sourced from backend)
        val FIRST_CAPTURE_DONE = booleanPreferencesKey("first_capture_done")
        val LAST_CAPTURE_TIMESTAMP = longPreferencesKey("last_capture_timestamp")
        val HIGH_VALUE_COPY_COUNT = intPreferencesKey("high_value_copy_count")
        val ROAST_LANGUAGE = stringPreferencesKey("roast_language")
    }

    val serviceEnabled: Flow<Boolean> = context.dataStore.data.map { it[Keys.SERVICE_ENABLED] ?: false }
    val onboardingCompleted: Flow<Boolean> = context.dataStore.data.map { it[Keys.ONBOARDING_COMPLETED] ?: false }
    val firstCaptureDone: Flow<Boolean> = context.dataStore.data.map { it[Keys.FIRST_CAPTURE_DONE] ?: false }
    val lastCaptureTimestamp: Flow<Long> = context.dataStore.data.map { it[Keys.LAST_CAPTURE_TIMESTAMP] ?: 0L }
    val highValueCopyCount: Flow<Int> = context.dataStore.data.map { it[Keys.HIGH_VALUE_COPY_COUNT] ?: 0 }
    val roastLanguage: Flow<String> = context.dataStore.data.map { it[Keys.ROAST_LANGUAGE] ?: "English" }

    suspend fun setServiceEnabled(enabled: Boolean) = context.dataStore.edit { it[Keys.SERVICE_ENABLED] = enabled }
    suspend fun setOnboardingCompleted(completed: Boolean) = context.dataStore.edit { it[Keys.ONBOARDING_COMPLETED] = completed }
    suspend fun setFirstCaptureDone() = context.dataStore.edit { it[Keys.FIRST_CAPTURE_DONE] = true }
    suspend fun setLastCaptureTimestamp(timestamp: Long) = context.dataStore.edit { it[Keys.LAST_CAPTURE_TIMESTAMP] = timestamp }
    suspend fun setRoastLanguage(language: String) = context.dataStore.edit { it[Keys.ROAST_LANGUAGE] = language }
    suspend fun incrementHighValueCopyCount(): Int {
        var newValue = 0
        context.dataStore.edit { prefs ->
            val current = prefs[Keys.HIGH_VALUE_COPY_COUNT] ?: 0
            newValue = current + 1
            prefs[Keys.HIGH_VALUE_COPY_COUNT] = newValue
        }
        return newValue
    }
}
