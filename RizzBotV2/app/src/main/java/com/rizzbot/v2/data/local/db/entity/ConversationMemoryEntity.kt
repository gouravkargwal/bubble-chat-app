package com.rizzbot.v2.data.local.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "conversation_memory")
data class ConversationMemoryEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val personName: String?,
    val summary: String,
    val createdAt: Long = System.currentTimeMillis(),
    val lastUpdated: Long = System.currentTimeMillis()
)
