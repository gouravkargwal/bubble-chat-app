package com.rizzbot.v2.data.local.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.rizzbot.v2.data.local.db.entity.ConversationMemoryEntity

@Dao
interface ConversationMemoryDao {
    @Query("SELECT * FROM conversation_memory ORDER BY lastUpdated DESC LIMIT 1")
    suspend fun getActiveMemory(): ConversationMemoryEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(memory: ConversationMemoryEntity): Long

    @Query("DELETE FROM conversation_memory WHERE lastUpdated < :cutoff")
    suspend fun deleteExpired(cutoff: Long)

    @Query("DELETE FROM conversation_memory")
    suspend fun clearAll()
}
