package com.rizzbot.app.di

import com.rizzbot.app.data.repository.ConversationRepositoryImpl
import com.rizzbot.app.data.repository.LlmRepositoryImpl
import com.rizzbot.app.data.repository.SettingsRepositoryImpl
import com.rizzbot.app.domain.repository.ConversationRepository
import com.rizzbot.app.domain.repository.LlmRepository
import com.rizzbot.app.domain.repository.SettingsRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {

    @Binds
    @Singleton
    abstract fun bindConversationRepository(
        impl: ConversationRepositoryImpl
    ): ConversationRepository

    @Binds
    @Singleton
    abstract fun bindLlmRepository(
        impl: LlmRepositoryImpl
    ): LlmRepository

    @Binds
    @Singleton
    abstract fun bindSettingsRepository(
        impl: SettingsRepositoryImpl
    ): SettingsRepository
}
