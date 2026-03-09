package com.rizzbot.v2.di

import com.rizzbot.v2.data.repository.HostedRepositoryImpl
import com.rizzbot.v2.data.repository.SettingsRepositoryImpl
import com.rizzbot.v2.domain.repository.HostedRepository
import com.rizzbot.v2.domain.repository.SettingsRepository
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
    abstract fun bindSettingsRepository(impl: SettingsRepositoryImpl): SettingsRepository

    @Binds
    @Singleton
    abstract fun bindHostedRepository(impl: HostedRepositoryImpl): HostedRepository
}
