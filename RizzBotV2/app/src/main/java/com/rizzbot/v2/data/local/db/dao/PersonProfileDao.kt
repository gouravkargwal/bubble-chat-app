package com.rizzbot.v2.data.local.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.rizzbot.v2.data.local.db.entity.PersonProfileEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface PersonProfileDao {
    @Query("SELECT * FROM person_profile ORDER BY createdAt DESC")
    fun getAll(): Flow<List<PersonProfileEntity>>

    @Query("SELECT * FROM person_profile WHERE id = :id")
    suspend fun getById(id: Long): PersonProfileEntity?

    @Query("SELECT * FROM person_profile ORDER BY createdAt DESC LIMIT 1")
    suspend fun getLatest(): PersonProfileEntity?

    @Insert
    suspend fun insert(profile: PersonProfileEntity): Long

    @Query("DELETE FROM person_profile WHERE id = :id")
    suspend fun deleteById(id: Long)
}
