package com.rizzbot.v2.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ReplyOption(
    val text: String,
    @SerialName("strategy_label") val strategyLabel: String,
    @SerialName("is_recommended") val isRecommended: Boolean,
    @SerialName("coach_reasoning") val coachReasoning: String
)

