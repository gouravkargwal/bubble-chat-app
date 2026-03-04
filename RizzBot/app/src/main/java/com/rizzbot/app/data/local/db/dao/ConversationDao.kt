package com.rizzbot.app.data.local.db.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Query
import androidx.room.Upsert
import com.rizzbot.app.data.local.db.entity.ConversationEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ConversationDao {

    @Query("SELECT * FROM conversations ORDER BY lastMessageTimestamp DESC")
    fun observeAllConversations(): Flow<List<ConversationEntity>>

    @Upsert
    suspend fun upsertConversation(conversation: ConversationEntity)

    @Query("SELECT * FROM conversations WHERE personName = :name")
    suspend fun getConversation(name: String): ConversationEntity?

    @Delete
    suspend fun deleteConversation(conversation: ConversationEntity)

    @Query("DELETE FROM conversations")
    suspend fun deleteAll()
}
