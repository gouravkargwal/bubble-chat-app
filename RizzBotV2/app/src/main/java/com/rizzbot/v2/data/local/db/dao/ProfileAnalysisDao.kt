package com.rizzbot.v2.data.local.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.rizzbot.v2.data.local.db.entity.ProfileAnalysisEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ProfileAnalysisDao {
    @Query("SELECT * FROM profile_analysis ORDER BY createdAt DESC")
    fun getAll(): Flow<List<ProfileAnalysisEntity>>

    @Query("SELECT * FROM profile_analysis ORDER BY createdAt DESC LIMIT 1")
    suspend fun getLatest(): ProfileAnalysisEntity?

    @Insert
    suspend fun insert(analysis: ProfileAnalysisEntity): Long

    @Query("DELETE FROM profile_analysis WHERE id = :id")
    suspend fun deleteById(id: Long)

    @Query("SELECT COUNT(*) FROM profile_analysis WHERE createdAt > :since")
    suspend fun countSince(since: Long): Int
}
