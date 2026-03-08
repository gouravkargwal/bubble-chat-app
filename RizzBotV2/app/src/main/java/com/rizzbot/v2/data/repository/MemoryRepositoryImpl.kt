package com.rizzbot.v2.data.repository

import com.rizzbot.v2.data.local.db.dao.ConversationMemoryDao
import com.rizzbot.v2.data.local.db.entity.ConversationMemoryEntity
import com.rizzbot.v2.domain.repository.MemoryRepository
import com.rizzbot.v2.util.Constants
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MemoryRepositoryImpl @Inject constructor(
    private val memoryDao: ConversationMemoryDao
) : MemoryRepository {

    override suspend fun getActiveMemory(): String? {
        clearExpiredMemories()
        return memoryDao.getActiveMemory()?.summary
    }

    override suspend fun getActivePersonName(): String? {
        return memoryDao.getActiveMemory()?.personName
    }

    override suspend fun saveMemory(personName: String?, summary: String) {
        val existing = memoryDao.getActiveMemory()

        // If person changed, clear old memory
        if (existing != null && personName != null && existing.personName != null && existing.personName != personName) {
            memoryDao.clearAll()
        }

        val entity = ConversationMemoryEntity(
            id = existing?.id ?: 0,
            personName = personName,
            summary = summary
        )
        memoryDao.upsert(entity)
    }

    override suspend fun clearMemory() {
        memoryDao.clearAll()
    }

    override suspend fun clearExpiredMemories() {
        val cutoff = System.currentTimeMillis() - (Constants.MEMORY_EXPIRY_HOURS * 60 * 60 * 1000)
        memoryDao.deleteExpired(cutoff)
    }
}
