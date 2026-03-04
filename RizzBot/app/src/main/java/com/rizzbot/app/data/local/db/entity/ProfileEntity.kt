package com.rizzbot.app.data.local.db.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.rizzbot.app.accessibility.model.ParsedProfile
import com.rizzbot.app.accessibility.model.QAPair
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

@Entity(tableName = "profiles")
data class ProfileEntity(
    @PrimaryKey
    val name: String,
    val age: String? = null,
    val qaPromptsJson: String = "[]",
    val languagesJson: String = "[]",
    val motherTongue: String? = null,
    val basicsJson: String = "[]",
    val hometown: String? = null,
    val distance: String? = null,
    val education: String? = null,
    val interestsJson: String = "[]",
    val traitsJson: String = "[]",
    val philosophyJson: String = "[]",
    val relationshipGoal: String? = null,
    val syncedAt: Long = System.currentTimeMillis()
) {
    fun toDomain(): ParsedProfile {
        val json = Json { ignoreUnknownKeys = true }
        return ParsedProfile(
            name = name,
            age = age,
            qaPrompts = try { json.decodeFromString<List<QAPairDto>>(qaPromptsJson).map { QAPair(it.q, it.a) } } catch (_: Exception) { emptyList() },
            languages = try { json.decodeFromString<List<String>>(languagesJson) } catch (_: Exception) { emptyList() },
            motherTongue = motherTongue,
            basics = try { json.decodeFromString<List<String>>(basicsJson) } catch (_: Exception) { emptyList() },
            hometown = hometown,
            distance = distance,
            education = education,
            interests = try { json.decodeFromString<List<String>>(interestsJson) } catch (_: Exception) { emptyList() },
            traits = try { json.decodeFromString<List<String>>(traitsJson) } catch (_: Exception) { emptyList() },
            philosophy = try { json.decodeFromString<List<String>>(philosophyJson) } catch (_: Exception) { emptyList() },
            relationshipGoal = relationshipGoal
        )
    }

    companion object {
        fun fromDomain(profile: ParsedProfile): ProfileEntity {
            val json = Json { ignoreUnknownKeys = true }
            return ProfileEntity(
                name = profile.name,
                age = profile.age,
                qaPromptsJson = json.encodeToString(profile.qaPrompts.map { QAPairDto(it.question, it.answer) }),
                languagesJson = json.encodeToString(profile.languages),
                motherTongue = profile.motherTongue,
                basicsJson = json.encodeToString(profile.basics),
                hometown = profile.hometown,
                distance = profile.distance,
                education = profile.education,
                interestsJson = json.encodeToString(profile.interests),
                traitsJson = json.encodeToString(profile.traits),
                philosophyJson = json.encodeToString(profile.philosophy),
                relationshipGoal = profile.relationshipGoal
            )
        }
    }
}

@Serializable
private data class QAPairDto(val q: String, val a: String)
