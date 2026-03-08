package com.rizzbot.v2.data.local.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "person_profile")
data class PersonProfileEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val age: String? = null,
    val bio: String? = null,
    val interests: String? = null,
    val personalityTraits: String? = null,
    val datingApp: String? = null,
    val fullExtraction: String,
    val createdAt: Long = System.currentTimeMillis()
)
