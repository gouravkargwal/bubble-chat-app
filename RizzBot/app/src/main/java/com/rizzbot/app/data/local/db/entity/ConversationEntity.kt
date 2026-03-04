package com.rizzbot.app.data.local.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "conversations")
data class ConversationEntity(
    @PrimaryKey
    val personName: String,
    val firstSeenTimestamp: Long,
    val lastMessageTimestamp: Long,
    val messageCount: Int,
    val platform: String = "aisle"
)
