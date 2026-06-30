package com.rizzbot.v2.domain.model

enum class ConversationDirection(
    val displayName: String,
    val promptInstruction: String
) {
    OPENER(
        displayName = "First message",
        promptInstruction = "Generate an engaging first message based on their profile. Do not say 'Hey'."
    ),
    QUICK_REPLY(
        displayName = "Quick reply",
        promptInstruction = "Reply naturally to continue the conversation based strictly on the chat history."
    ),
    CHANGE_TOPIC(
        displayName = "Change topic",
        promptInstruction = "Smoothly transition to a new, interesting, and playful topic to escape the current boring loop."
    ),
    TEASE(
        displayName = "Tease them",
        promptInstruction = "Playfully tease them, disagree with them, or challenge them based on what they just said."
    ),
    GET_NUMBER(
        displayName = "Get their number",
        promptInstruction = "Steer the conversation toward exchanging phone numbers naturally."
    ),
    ASK_OUT(
        displayName = "Ask them out",
        promptInstruction = "Smoothly suggest meeting up for a date. Be specific with a casual activity."
    ),
    REVIVE_CHAT(
        displayName = "Revive dead chat",
        promptInstruction = "Send a low-pressure, playful text to restart a dead conversation without sounding needy."
    ),
    DE_ESCALATE(
        displayName = "Cool things down",
        promptInstruction = "She seems upset or things got tense. Respond with calm, grounded emotional maturity."
    ),
    KEEP_PLAYFUL(
        displayName = "Keep it playful",
        promptInstruction = "Keep the fun energy going. React to what she actually said — mine her specific words and details, not the vibe."
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
