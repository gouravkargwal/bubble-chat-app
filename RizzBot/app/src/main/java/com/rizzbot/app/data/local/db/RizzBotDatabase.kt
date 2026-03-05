package com.rizzbot.app.data.local.db

import androidx.room.Database
import androidx.room.RoomDatabase
import com.rizzbot.app.data.local.db.dao.ConversationDao
import com.rizzbot.app.data.local.db.dao.MessageDao
import com.rizzbot.app.data.local.db.dao.ProfileDao
import com.rizzbot.app.data.local.db.entity.ConversationEntity
import com.rizzbot.app.data.local.db.entity.MessageEntity
import com.rizzbot.app.data.local.db.entity.ProfileEntity

@Database(
    entities = [ConversationEntity::class, MessageEntity::class, ProfileEntity::class],
    version = 5,
    exportSchema = false
)
abstract class RizzBotDatabase : RoomDatabase() {
    abstract fun conversationDao(): ConversationDao
    abstract fun messageDao(): MessageDao
    abstract fun profileDao(): ProfileDao
}
