package com.rizzbot.app.domain.usecase

import android.util.Log
import com.rizzbot.app.accessibility.model.ParsedMessage
import com.rizzbot.app.domain.model.SuggestionResult
import com.rizzbot.app.domain.model.TonePreference
import com.rizzbot.app.domain.repository.LlmRepository
import javax.inject.Inject

class GenerateReplyUseCase @Inject constructor(
    private val llmRepository: LlmRepository,
    private val saveMessageUseCase: SaveMessageUseCase,
    private val getConversationHistoryUseCase: GetConversationHistoryUseCase,
    private val buildSystemPromptUseCase: BuildSystemPromptUseCase
) {
    suspend operator fun invoke(
        personName: String,
        currentScreenMessages: List<ParsedMessage>,
        toneOverride: TonePreference? = null,
        profileInfo: String? = null
    ): SuggestionResult {
        return try {
            val isConversationStarter = currentScreenMessages.isEmpty()
            Log.d("RizzBot", "GenerateReply: person=$personName, msgs=${currentScreenMessages.size}, starter=$isConversationStarter, profile=$profileInfo")

            if (!isConversationStarter) {
                Log.d("RizzBot", "GenerateReply: saving messages for $personName")
                saveMessageUseCase(personName, currentScreenMessages)
            }

            val systemPrompt = buildSystemPromptUseCase(toneOverride)

            val userPrompt = if (isConversationStarter) {
                buildConversationStarterPrompt(personName, profileInfo)
            } else {
                Log.d("RizzBot", "GenerateReply: loading conversation history")
                val history = getConversationHistoryUseCase(personName)
                Log.d("RizzBot", "GenerateReply: history has ${history.size} messages")

                val conversationContext = history.joinToString("\n") { msg ->
                    val prefix = if (msg.isIncoming) "Them" else "You"
                    "$prefix: ${msg.text}"
                }

                val isThinConversation = history.size <= 3

                if (isThinConversation && !profileInfo.isNullOrBlank()) {
                    // Thin conversation WITH profile: use profile to create personal connection
                    """
$personName's profile:
$profileInfo

Conversation (early stage — just started):
$conversationContext

This chat JUST started. You have an advantage — you know things about them from their profile. Use it.

Your reply should:
- Feel like you're genuinely interested in THEM specifically, not just anyone
- Pick ONE thing from their profile and weave it in naturally (don't list everything you know — that's creepy)
- Create an "open loop" — say something that makes them curious or want to explain/share more
- If they just said "Hi" or something generic, don't mirror the boring energy. Elevate it — bring something fun to the table
- Be warm but not overeager. You're interested, not desperate.

Think: "What would make HER specifically want to reply to THIS message?"

IMPORTANT: Reply in the same language and script used in the conversation.
                    """.trimIndent()
                } else if (isThinConversation) {
                    // Thin conversation WITHOUT profile: create intrigue from nothing
                    """
Conversation with $personName (early stage — just started):

$conversationContext

This chat JUST started and you have no profile info. You need to create chemistry from scratch.

Your reply should:
- NOT mirror boring energy. If they said "Hi", don't say "Hi, how are you?" — that's a dead-end
- Ask something fun, unexpected, or slightly challenging that reveals personality. E.g., "would you rather" style, playful assumptions, or an intriguing "I have a feeling you're the type who..."
- Make them WANT to respond. Create curiosity about YOU while showing curiosity about THEM
- Keep it light and fun. You're building a vibe, not conducting an interview

Think: "If I were her, would I be excited to reply to this?"

IMPORTANT: Reply in the same language and script used in the conversation.
                    """.trimIndent()
                } else {
                    // Normal conversation flow — keep the momentum
                    val profileContext = if (!profileInfo.isNullOrBlank()) {
                        "\n\nHer profile (use naturally, don't force it): $profileInfo"
                    } else ""

                    """
Conversation with $personName:$profileContext

$conversationContext

Read the vibe. What's the energy? Match it, then elevate it slightly.

Your reply should:
- Respond to what they ACTUALLY said (don't ignore their message)
- Add something new — a twist, a tease, a question, a callback to something earlier
- If things are going well, keep the momentum. If it's getting flat, inject something unexpected
- Leave a hook — end with something that makes it easy AND fun for them to reply

Think: "What reply would make her smile and type back immediately?"

IMPORTANT: Reply in the same language and script used in the conversation.
                    """.trimIndent()
                }
            }

            Log.d("RizzBot", "GenerateReply: calling LLM with tone=${toneOverride?.label ?: "default"}")
            val rawReply = llmRepository.generateReply(systemPrompt, userPrompt)
            val replies = parseReplies(rawReply)
            Log.d("RizzBot", "GenerateReply: SUCCESS ${replies.size} replies, first=${replies.firstOrNull()?.take(50)}...")
            SuggestionResult.Success(replies)
        } catch (e: Exception) {
            Log.e("RizzBot", "GenerateReply: FAILED - ${e.message}", e)
            SuggestionResult.Error(e.message ?: "Failed to generate reply")
        }
    }

    private fun parseReplies(raw: String): List<String> {
        // Split by "---" separator, filter blanks, trim each
        val parts = raw.split("---")
            .map { it.trim() }
            .filter { it.isNotBlank() }
        // If LLM didn't use separator, return as single reply
        return parts.ifEmpty { listOf(raw.trim()) }
    }

    private fun buildConversationStarterPrompt(personName: String, profileInfo: String?): String {
        val profileContext = if (!profileInfo.isNullOrBlank()) {
            """
$personName's profile:
$profileInfo

You're about to send the FIRST message to $personName. You have their profile — use it as your weapon.

Pick ONE specific thing from their profile and use it to craft an opener that:
- Shows you actually read their profile (not "hey beautiful")
- Creates instant curiosity or makes them smile
- Makes it EASY for them to reply (ask something or make a playful assumption they'll want to correct/confirm)
- Feels like something a charming, confident person would actually text

Good patterns: playful assumption about them, fun "would you rather" tied to their interests, a witty observation about something in their profile, a mini challenge.

Bad patterns: "I noticed you like X, I like X too!" (boring), complimenting looks (generic), "hey how's your day" (dead).
            """.trimIndent()
        } else {
            """
You're about to send the FIRST message to $personName on a dating app. No profile info available.

Craft an opener that:
- Stands out in a sea of "hey" and "hi beautiful" messages
- Creates curiosity — make them WANT to know more about you
- Is easy to reply to — give them something to react to or answer
- Shows personality and confidence without being tryhard

Good patterns: fun hypothetical, playful observation, unexpected question, bold but charming assumption.
            """.trimIndent()
        }

        return """
$profileContext

If their profile suggests a regional language (Hindi, Hinglish), use that language. Otherwise use English.
        """.trimIndent()
    }
}
