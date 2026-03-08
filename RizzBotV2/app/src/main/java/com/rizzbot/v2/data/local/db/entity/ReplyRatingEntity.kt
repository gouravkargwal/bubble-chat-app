package com.rizzbot.v2.data.local.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "reply_rating")
data class ReplyRatingEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val direction: String,
    val vibeIndex: Int,
    val isPositive: Boolean,
    val replyText: String,
    val createdAt: Long = System.currentTimeMillis()
)
