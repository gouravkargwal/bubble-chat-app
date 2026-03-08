package com.rizzbot.v2.domain.repository

interface MemoryRepository {
    suspend fun getActiveMemory(): String?
    suspend fun getActivePersonName(): String?
    suspend fun saveMemory(personName: String?, summary: String)
    suspend fun clearMemory()
    suspend fun clearExpiredMemories()
}
