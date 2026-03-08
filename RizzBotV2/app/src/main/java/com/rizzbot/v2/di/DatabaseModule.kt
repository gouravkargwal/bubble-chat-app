package com.rizzbot.v2.di

import android.content.Context
import androidx.room.Room
import com.rizzbot.v2.data.local.db.RizzBotDatabase
import com.rizzbot.v2.data.local.db.dao.ConversationMemoryDao
import com.rizzbot.v2.data.local.db.dao.PersonProfileDao
import com.rizzbot.v2.data.local.db.dao.ProfileAnalysisDao
import com.rizzbot.v2.data.local.db.dao.ReplyHistoryDao
import com.rizzbot.v2.data.local.db.dao.ReplyRatingDao
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
            "rizzbot_v2_db"
        ).fallbackToDestructiveMigration()
            .build()
    }

    @Provides
    fun provideConversationMemoryDao(db: RizzBotDatabase): ConversationMemoryDao =
        db.conversationMemoryDao()

    @Provides
    fun provideReplyHistoryDao(db: RizzBotDatabase): ReplyHistoryDao =
        db.replyHistoryDao()

    @Provides
    fun provideReplyRatingDao(db: RizzBotDatabase): ReplyRatingDao =
        db.replyRatingDao()

    @Provides
    fun provideProfileAnalysisDao(db: RizzBotDatabase): ProfileAnalysisDao =
        db.profileAnalysisDao()

    @Provides
    fun providePersonProfileDao(db: RizzBotDatabase): PersonProfileDao =
        db.personProfileDao()
}
