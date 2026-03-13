package com.rizzbot.v2.ui.profile

import com.rizzbot.v2.data.remote.dto.OptimizedSlotDto
import com.rizzbot.v2.data.remote.dto.ProfileBlueprintDto

data class OptimizedSlot(
    val photoUrl: String,
    val slotNumber: Int,
    val role: String,
    val caption: String,
    val hingePromptQuestion: String,
    val hingePromptAnswer: String,
    val coachReasoning: String
)

data class ProfileBlueprint(
    val overallTheme: String,
    val slots: List<OptimizedSlot>
)

fun ProfileBlueprintDto.toUi(): ProfileBlueprint =
    ProfileBlueprint(
        overallTheme = overallTheme,
        slots = slots.map { it.toUi() }
    )

fun OptimizedSlotDto.toUi(): OptimizedSlot =
    OptimizedSlot(
        photoUrl = photoUrl,
        slotNumber = slotNumber,
        role = role,
        caption = caption,
        hingePromptQuestion = hingePromptQuestion,
        hingePromptAnswer = hingePromptAnswer,
        coachReasoning = coachReasoning
    )

