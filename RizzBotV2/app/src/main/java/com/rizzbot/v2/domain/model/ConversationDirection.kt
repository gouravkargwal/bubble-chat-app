package com.rizzbot.v2.domain.model

enum class ConversationDirection(
    val displayName: String,
    val emoji: String,
    val promptInstruction: String
) {
    QUICK_REPLY(
        displayName = "Quick reply",
        emoji = "⚡",
        promptInstruction = "Reply naturally and engagingly to continue the conversation."
    ),
    GET_NUMBER(
        displayName = "Get their number",
        emoji = "🔥",
        promptInstruction = "Steer the conversation toward exchanging phone numbers naturally. Don't be too direct."
    ),
    ASK_OUT(
        displayName = "Ask them out",
        emoji = "☕",
        promptInstruction = "Smoothly suggest meeting up for a date. Be specific with a casual activity suggestion."
    ),
    KEEP_PLAYFUL(
        displayName = "Keep it playful",
        emoji = "😂",
        promptInstruction = "Keep the conversation fun, flirty, and light-hearted. Use humor."
    ),
    GO_DEEPER(
        displayName = "Go deeper",
        emoji = "💬",
        promptInstruction = "Take the conversation to a more meaningful level. Ask thoughtful questions."
    ),
    CHANGE_TOPIC(
        displayName = "Change topic",
        emoji = "🔄",
        promptInstruction = "Smoothly transition to a new, interesting topic. Don't make the transition feel forced."
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
