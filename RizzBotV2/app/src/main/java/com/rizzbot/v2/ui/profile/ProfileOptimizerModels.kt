package com.rizzbot.v2.ui.profile

import com.rizzbot.v2.data.remote.dto.OptimizedSlotDto
import com.rizzbot.v2.data.remote.dto.ProfileBlueprintDto
import com.rizzbot.v2.data.remote.dto.UniversalPromptDto

data class OptimizedSlot(
    val photoUrl: String,
    val slotNumber: Int,
    val role: String,
    val caption: String,
    val contextualHook: String,
    val coachReasoning: String
)

data class UniversalPrompt(
    val category: String,
    val suggestedText: String
)

data class ProfileBlueprint(
    val overallTheme: String,
    val tinderBio: String,
    val bumbleBio: String,
    val universalPrompts: List<UniversalPrompt>,
    val slots: List<OptimizedSlot>
)

fun ProfileBlueprintDto.toUi(): ProfileBlueprint =
    ProfileBlueprint(
        overallTheme = overallTheme,
        tinderBio = tinderBio,
        bumbleBio = bumbleBio,
        universalPrompts = universalPrompts.map { it.toUi() },
        slots = slots.map { it.toUi() }
    )

fun OptimizedSlotDto.toUi(): OptimizedSlot =
    OptimizedSlot(
        photoUrl = photoUrl,
        slotNumber = slotNumber,
        role = role,
        caption = caption,
        contextualHook = contextualHook,
        coachReasoning = coachReasoning
    )

fun UniversalPromptDto.toUi(): UniversalPrompt =
    UniversalPrompt(
        category = category,
        suggestedText = suggestedText
    )
