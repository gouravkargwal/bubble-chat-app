package com.rizzbot.v2.data.local.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "profile_analysis")
data class ProfileAnalysisEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val datingApp: String,
    val overallScore: Float,
    val photoFeedback: String,
    val bioSuggestions: String,
    val promptSuggestions: String,
    val redFlags: String,
    val fullAnalysis: String,
    val createdAt: Long = System.currentTimeMillis()
)
