package com.rizzbot.app.accessibility

import com.rizzbot.app.accessibility.model.ParsedProfile
import com.rizzbot.app.data.local.db.dao.ProfileDao
import com.rizzbot.app.data.local.db.entity.ProfileEntity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ProfileCacheManager @Inject constructor(
    private val profileDao: ProfileDao
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val profileCache = mutableMapOf<String, ParsedProfile>()

    init {
        // Pre-load from Room on startup
        scope.launch {
            profileDao.observeAllProfiles().collect { entities ->
                synchronized(profileCache) {
                    profileCache.clear()
                    entities.forEach { entity ->
                        profileCache[entity.name.lowercase()] = entity.toDomain()
                    }
                }
            }
        }
    }

    fun cacheProfile(profile: ParsedProfile) {
        synchronized(profileCache) {
            profileCache[profile.name.lowercase()] = profile
        }
        scope.launch {
            profileDao.upsertProfile(ProfileEntity.fromDomain(profile))
        }
    }

    fun getProfile(personName: String): ParsedProfile? {
        return synchronized(profileCache) {
            profileCache[personName.lowercase()]
        }
    }

    fun isProfileSynced(personName: String): Boolean {
        return synchronized(profileCache) {
            profileCache.containsKey(personName.lowercase())
        }
    }

    fun observeAllSyncedNames(): Flow<Set<String>> {
        return profileDao.observeAllProfileNames().map { it.map { name -> name.lowercase() }.toSet() }
    }

    fun observeAllProfiles(): Flow<List<ParsedProfile>> {
        return profileDao.observeAllProfiles().map { entities ->
            entities.map { it.toDomain() }
        }
    }

    fun observeProfile(personName: String): Flow<ParsedProfile?> {
        return profileDao.observeProfile(personName).map { it?.toDomain() }
    }

    suspend fun deleteProfile(personName: String) {
        synchronized(profileCache) {
            profileCache.remove(personName.lowercase())
        }
        profileDao.deleteProfile(personName)
    }

    fun clear() {
        synchronized(profileCache) {
            profileCache.clear()
        }
        scope.launch {
            // No deleteAll in DAO yet, but cache clear is sufficient
        }
    }
}
