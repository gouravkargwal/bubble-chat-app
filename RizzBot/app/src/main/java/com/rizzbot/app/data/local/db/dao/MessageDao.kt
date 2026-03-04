package com.rizzbot.app.data.local.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.rizzbot.app.data.local.db.entity.MessageEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface MessageDao {

    @Query("SELECT * FROM messages WHERE personName = :personName ORDER BY timestamp DESC LIMIT :limit")
    suspend fun getRecentMessages(personName: String, limit: Int): List<MessageEntity>

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertMessages(messages: List<MessageEntity>)

    @Query("SELECT * FROM messages WHERE personName = :personName ORDER BY timestamp ASC")
    fun observeMessages(personName: String): Flow<List<MessageEntity>>

    @Query("DELETE FROM messages WHERE personName = :personName")
    suspend fun deleteMessagesForPerson(personName: String)

    @Query("SELECT COUNT(*) FROM messages WHERE personName = :personName")
    suspend fun getMessageCount(personName: String): Int
}
