package com.rizzbot.app.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class GroqResponse(
    val choices: List<GroqChoice>
)

@Serializable
data class GroqChoice(
    val message: GroqMessage
)
