package com.rizzbot.v2.data.local.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.rizzbot.v2.data.local.db.entity.ReplyHistoryEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ReplyHistoryDao {
    @Query("SELECT * FROM reply_history ORDER BY createdAt DESC LIMIT 20")
    fun getAll(): Flow<List<ReplyHistoryEntity>>

    @Insert
    suspend fun insert(entry: ReplyHistoryEntity)

    @Query("DELETE FROM reply_history WHERE id = :id")
    suspend fun deleteById(id: Long)

    @Query("DELETE FROM reply_history WHERE createdAt < :cutoff")
    suspend fun deleteExpired(cutoff: Long)

    @Query("SELECT COUNT(*) FROM reply_history")
    suspend fun count(): Int
}
