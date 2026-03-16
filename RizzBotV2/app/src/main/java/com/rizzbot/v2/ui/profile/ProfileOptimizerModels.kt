package com.rizzbot.v2.ui.profile

import com.rizzbot.v2.data.remote.dto.OptimizedSlotDto
import com.rizzbot.v2.data.remote.dto.ProfileBlueprintDto
import com.rizzbot.v2.data.remote.dto.UniversalPromptDto

data class OptimizedSlot(
    val id: String,
    val photoId: String,
    val imageUrl: String,
    val slotNumber: Int,
    val role: String,
    val caption: String,
    val universalHook: String,
    val hingePrompt: String,
    val aislePrompt: String
)

data class UniversalPrompt(
    val category: String,
    val suggestedText: String
)

data class ProfileBlueprint(
    val id: String,
    val userId: String,
    val overallTheme: String,
    val bio: String,
    val createdAt: String,
    val universalPrompts: List<UniversalPrompt>?,
    val slots: List<OptimizedSlot>
)

fun ProfileBlueprintDto.toUi(): ProfileBlueprint =
    ProfileBlueprint(
        id = id,
        userId = userId,
        overallTheme = overallTheme,
        bio = bio,
        createdAt = createdAt,
        universalPrompts = universalPrompts?.map { it.toUi() },
        slots = slots.map { it.toUi() }
    )

fun OptimizedSlotDto.toUi(): OptimizedSlot =
    OptimizedSlot(
        id = id,
        photoId = photoId,
        imageUrl = imageUrl,
        slotNumber = slotNumber,
        role = role,
        caption = caption,
        universalHook = universalHook,
        hingePrompt = hingePrompt,
        aislePrompt = aislePrompt
    )

fun UniversalPromptDto.toUi(): UniversalPrompt =
    UniversalPrompt(
        category = category,
        suggestedText = suggestedText
    )
