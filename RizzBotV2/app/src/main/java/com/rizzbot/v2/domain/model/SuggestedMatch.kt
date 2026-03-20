package com.rizzbot.v2.domain.model

data class SuggestedMatch(
    val personName: String,
    val conversationId: String,
    val lastActive: String,
    val contextPreview: SuggestedMatchContextPreview
)

data class SuggestedMatchContextPreview(
    val herLastMessage: String,
    val yourLastReply: String,
    val aiMemoryNote: String
)

