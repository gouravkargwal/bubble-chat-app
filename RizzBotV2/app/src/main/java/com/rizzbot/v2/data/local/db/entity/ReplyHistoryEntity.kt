package com.rizzbot.v2.data.local.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "reply_history")
data class ReplyHistoryEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val personContext: String?,
    val reply1: String,
    val reply2: String,
    val reply3: String,
    val reply4: String,
    val direction: String,
    val customHint: String? = null,
    val createdAt: Long = System.currentTimeMillis()
)
