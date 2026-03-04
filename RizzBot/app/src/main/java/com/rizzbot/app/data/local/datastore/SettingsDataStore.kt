package com.rizzbot.app.data.local.datastore

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "rizzbot_settings")

@Singleton
class SettingsDataStore @Inject constructor(
    @ApplicationContext private val context: Context
) {

    val apiKey: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[API_KEY] ?: ""
    }

    val isServiceEnabled: Flow<Boolean> = context.dataStore.data.map { prefs ->
        prefs[SERVICE_ENABLED] ?: false
    }

    val tonePreference: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[TONE] ?: "FLIRTY"
    }

    val hasCompletedOnboarding: Flow<Boolean> = context.dataStore.data.map { prefs ->
        prefs[ONBOARDING_COMPLETE] ?: false
    }

    suspend fun setApiKey(key: String) {
        context.dataStore.edit { it[API_KEY] = key }
    }

    suspend fun setServiceEnabled(enabled: Boolean) {
        context.dataStore.edit { it[SERVICE_ENABLED] = enabled }
    }

    suspend fun setTonePreference(tone: String) {
        context.dataStore.edit { it[TONE] = tone }
    }

    suspend fun setOnboardingComplete() {
        context.dataStore.edit { it[ONBOARDING_COMPLETE] = true }
    }

    companion object {
        val API_KEY = stringPreferencesKey("api_key")
        val SERVICE_ENABLED = booleanPreferencesKey("service_enabled")
        val TONE = stringPreferencesKey("tone_preference")
        val ONBOARDING_COMPLETE = booleanPreferencesKey("onboarding_complete")
    }
}
