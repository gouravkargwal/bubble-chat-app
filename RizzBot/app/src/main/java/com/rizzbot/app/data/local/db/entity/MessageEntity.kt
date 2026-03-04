package com.rizzbot.app.data.local.db.entity

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "messages",
    foreignKeys = [ForeignKey(
        entity = ConversationEntity::class,
        parentColumns = ["personName"],
        childColumns = ["personName"],
        onDelete = ForeignKey.CASCADE
    )],
    indices = [Index("personName", "timestamp")]
)
data class MessageEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val personName: String,
    val text: String,
    val isIncoming: Boolean,
    val timestamp: Long,
    val wasSuggestionUsed: Boolean = false
)
