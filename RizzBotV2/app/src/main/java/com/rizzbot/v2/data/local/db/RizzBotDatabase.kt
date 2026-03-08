package com.rizzbot.v2.data.local.db

import androidx.room.Database
import androidx.room.RoomDatabase
import com.rizzbot.v2.data.local.db.dao.ConversationMemoryDao
import com.rizzbot.v2.data.local.db.dao.PersonProfileDao
import com.rizzbot.v2.data.local.db.dao.ProfileAnalysisDao
import com.rizzbot.v2.data.local.db.dao.ReplyHistoryDao
import com.rizzbot.v2.data.local.db.dao.ReplyRatingDao
import com.rizzbot.v2.data.local.db.entity.ConversationMemoryEntity
import com.rizzbot.v2.data.local.db.entity.PersonProfileEntity
import com.rizzbot.v2.data.local.db.entity.ProfileAnalysisEntity
import com.rizzbot.v2.data.local.db.entity.ReplyHistoryEntity
import com.rizzbot.v2.data.local.db.entity.ReplyRatingEntity

@Database(
    entities = [
        ConversationMemoryEntity::class,
        ReplyHistoryEntity::class,
        ReplyRatingEntity::class,
        ProfileAnalysisEntity::class,
        PersonProfileEntity::class
    ],
    version = 3,
    exportSchema = false
)
abstract class RizzBotDatabase : RoomDatabase() {
    abstract fun conversationMemoryDao(): ConversationMemoryDao
    abstract fun replyHistoryDao(): ReplyHistoryDao
    abstract fun replyRatingDao(): ReplyRatingDao
    abstract fun profileAnalysisDao(): ProfileAnalysisDao
    abstract fun personProfileDao(): PersonProfileDao
}
