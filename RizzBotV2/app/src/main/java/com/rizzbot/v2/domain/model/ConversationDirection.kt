package com.rizzbot.v2.domain.model

enum class ConversationDirection(
    val displayName: String,
    val emoji: String,
    val promptInstruction: String
) {
    OPENER(
        displayName = "First message",
        emoji = "👋",
        promptInstruction = "Generate an engaging first message based on their profile. Do not say 'Hey'."
    ),
    QUICK_REPLY(
        displayName = "Quick reply",
        emoji = "⚡",
        promptInstruction = "Reply naturally to continue the conversation based strictly on the chat history."
    ),
    CHANGE_TOPIC(
        displayName = "Change topic",
        emoji = "🔄",
        promptInstruction = "Smoothly transition to a new, interesting, and playful topic to escape the current boring loop."
    ),
    TEASE(
        displayName = "Tease them",
        emoji = "😏",
        promptInstruction = "Playfully tease them, disagree with them, or challenge them based on what they just said."
    ),
    GET_NUMBER(
        displayName = "Get their number",
        emoji = "📱",
        promptInstruction = "Steer the conversation toward exchanging phone numbers naturally."
    ),
    ASK_OUT(
        displayName = "Ask them out",
        emoji = "🥂",
        promptInstruction = "Smoothly suggest meeting up for a date. Be specific with a casual activity."
    ),
    REVIVE_CHAT(
        displayName = "Revive dead chat",
        emoji = "👻",
        promptInstruction = "Send a low-pressure, playful text to restart a dead conversation without sounding needy."
    );
}

data class DirectionWithHint(
    val direction: ConversationDirection = ConversationDirection.QUICK_REPLY,
    val customHint: String? = null
) {
    val promptText: String
        get() = if (customHint != null) {
            "User hint: $customHint"
        } else {
            "Direction: ${direction.displayName}. ${direction.promptInstruction}"
        }
}
