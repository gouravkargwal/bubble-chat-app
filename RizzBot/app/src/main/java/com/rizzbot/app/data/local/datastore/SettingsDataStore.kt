package com.rizzbot.app.data.local.datastore

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
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

    val selectedProvider: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[SELECTED_PROVIDER] ?: "GROQ"
    }

    val selectedModel: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[SELECTED_MODEL] ?: "llama-3.3-70b-versatile"
    }

    val repliesGenerated: Flow<Int> = context.dataStore.data.map { prefs ->
        prefs[REPLIES_GENERATED] ?: 0
    }

    val hasSeenGuide: Flow<Boolean> = context.dataStore.data.map { prefs ->
        prefs[HAS_SEEN_GUIDE] ?: false
    }

    suspend fun setGuideComplete() {
        context.dataStore.edit { it[HAS_SEEN_GUIDE] = true }
    }

    suspend fun incrementRepliesGenerated() {
        context.dataStore.edit { prefs ->
            val current = prefs[REPLIES_GENERATED] ?: 0
            prefs[REPLIES_GENERATED] = current + 1
        }
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

    suspend fun setSelectedProvider(provider: String) {
        context.dataStore.edit { it[SELECTED_PROVIDER] = provider }
    }

    suspend fun setSelectedModel(model: String) {
        context.dataStore.edit { it[SELECTED_MODEL] = model }
    }

    companion object {
        val API_KEY = stringPreferencesKey("api_key")
        val SERVICE_ENABLED = booleanPreferencesKey("service_enabled")
        val TONE = stringPreferencesKey("tone_preference")
        val ONBOARDING_COMPLETE = booleanPreferencesKey("onboarding_complete")
        val SELECTED_PROVIDER = stringPreferencesKey("selected_provider")
        val SELECTED_MODEL = stringPreferencesKey("selected_model")
        val REPLIES_GENERATED = intPreferencesKey("replies_generated")
        val HAS_SEEN_GUIDE = booleanPreferencesKey("has_seen_guide")
    }
}
