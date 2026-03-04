package com.rizzbot.app.data.local.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.rizzbot.app.data.local.db.entity.ProfileEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ProfileDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertProfile(profile: ProfileEntity)

    @Query("SELECT * FROM profiles WHERE name = :name LIMIT 1")
    suspend fun getProfile(name: String): ProfileEntity?

    @Query("SELECT * FROM profiles WHERE name = :name LIMIT 1")
    fun observeProfile(name: String): Flow<ProfileEntity?>

    @Query("SELECT * FROM profiles ORDER BY syncedAt DESC")
    fun observeAllProfiles(): Flow<List<ProfileEntity>>

    @Query("SELECT name FROM profiles")
    fun observeAllProfileNames(): Flow<List<String>>

    @Query("DELETE FROM profiles WHERE name = :name")
    suspend fun deleteProfile(name: String)
}
