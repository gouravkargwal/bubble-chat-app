package com.rizzbot.app.di

import android.content.Context
import androidx.room.Room
import com.rizzbot.app.data.local.db.RizzBotDatabase
import com.rizzbot.app.data.local.db.dao.ConversationDao
import com.rizzbot.app.data.local.db.dao.MessageDao
import com.rizzbot.app.data.local.db.dao.ProfileDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): RizzBotDatabase {
        return Room.databaseBuilder(
            context,
            RizzBotDatabase::class.java,
            "rizzbot_database"
        ).fallbackToDestructiveMigration().build()
    }

    @Provides
    fun provideConversationDao(db: RizzBotDatabase): ConversationDao = db.conversationDao()

    @Provides
    fun provideMessageDao(db: RizzBotDatabase): MessageDao = db.messageDao()

    @Provides
    fun provideProfileDao(db: RizzBotDatabase): ProfileDao = db.profileDao()
}
