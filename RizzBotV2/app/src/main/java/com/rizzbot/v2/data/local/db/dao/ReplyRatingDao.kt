package com.rizzbot.v2.data.local.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.rizzbot.v2.data.local.db.entity.ReplyRatingEntity

@Dao
interface ReplyRatingDao {
    @Insert
    suspend fun insert(rating: ReplyRatingEntity)

    @Query("SELECT COUNT(*) FROM reply_rating")
    suspend fun totalCount(): Int

    @Query("SELECT vibeIndex, COUNT(*) as cnt FROM reply_rating WHERE isPositive = 1 GROUP BY vibeIndex")
    suspend fun getPositiveCountsByVibe(): List<VibeStat>

    @Query("SELECT COUNT(*) FROM reply_rating WHERE isPositive = 1 AND LENGTH(replyText) < 50")
    suspend fun shortPositiveCount(): Int

    @Query("SELECT COUNT(*) FROM reply_rating WHERE isPositive = 1 AND LENGTH(replyText) >= 50 AND LENGTH(replyText) < 120")
    suspend fun mediumPositiveCount(): Int

    @Query("SELECT COUNT(*) FROM reply_rating WHERE isPositive = 1 AND LENGTH(replyText) >= 120")
    suspend fun longPositiveCount(): Int
}

data class VibeStat(
    val vibeIndex: Int,
    val cnt: Int
)
