package com.rizzbot.app.ui.guide

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Rocket
import androidx.compose.material.icons.filled.TouchApp
import androidx.compose.ui.graphics.vector.ImageVector

data class GuideStep(
    val icon: ImageVector,
    val title: String,
    val description: String
)

val GUIDE_STEPS = listOf(
    GuideStep(
        icon = Icons.Default.Chat,
        title = "Open Aisle & Start Chatting",
        description = "RizzBot activates automatically when you open Aisle. Just go to any chat conversation and we'll be ready."
    ),
    GuideStep(
        icon = Icons.Default.TouchApp,
        title = "Tap the Rizz Button",
        description = "A floating Rizz button appears on chat screens. Tap it to get AI-powered reply suggestions based on your conversation."
    ),
    GuideStep(
        icon = Icons.Default.AutoAwesome,
        title = "Pick Your Style",
        description = "Choose a tone — Flirty, Witty, Smooth, or Bold — and get 2 tailored reply variations. Copy or paste directly into the chat."
    ),
    GuideStep(
        icon = Icons.Default.Person,
        title = "Sync Profiles",
        description = "Visit a match's profile in Aisle and tap \"Sync Profile\". RizzBot uses their bio and interests for more personalized replies."
    ),
    GuideStep(
        icon = Icons.Default.Rocket,
        title = "You're All Set!",
        description = "RizzBot works in the background whenever you're on Aisle. Change your tone, switch AI providers, or view history anytime from Settings."
    )
)
