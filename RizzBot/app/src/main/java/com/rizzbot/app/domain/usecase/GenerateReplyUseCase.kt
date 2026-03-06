package com.rizzbot.app.domain.usecase

import android.util.Log
import com.rizzbot.app.accessibility.model.ParsedMessage
import com.rizzbot.app.domain.model.ChatMessage
import com.rizzbot.app.domain.model.SuggestionResult
import com.rizzbot.app.domain.repository.LlmRepository
import java.util.concurrent.TimeUnit
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
        profileInfo: String? = null,
        isFullRead: Boolean = false,
        userHint: String? = null
    ): SuggestionResult {
        return try {
            val isConversationStarter = currentScreenMessages.isEmpty()
            Log.d("RizzBot", "GenerateReply: person=$personName, msgs=${currentScreenMessages.size}, starter=$isConversationStarter, profile=${!profileInfo.isNullOrBlank()}, fullRead=$isFullRead")

            if (!isConversationStarter) {
                if (isFullRead) {
                    Log.d("RizzBot", "GenerateReply: replacing all messages for $personName (full read)")
                    saveMessageUseCase.replaceAll(personName, currentScreenMessages)
                } else {
                    Log.d("RizzBot", "GenerateReply: saving messages for $personName")
                    saveMessageUseCase(personName, currentScreenMessages)
                }
            }

            val systemPrompt = buildSystemPromptUseCase()

            val hintSection = if (!userHint.isNullOrBlank()) {
                "\nUSER DIRECTION: Focus on: \"$userHint\". Incorporate this into all 4 replies while keeping each vibe distinct.\n"
            } else ""

            val userPrompt = if (isConversationStarter) {
                buildConversationStarterPrompt(personName, profileInfo) + hintSection
            } else {
                Log.d("RizzBot", "GenerateReply: loading conversation history")
                val history = getConversationHistoryUseCase(personName)
                Log.d("RizzBot", "GenerateReply: history has ${history.size} messages")

                val now = System.currentTimeMillis()
                val conversationContext = formatConversationWithTime(history, now)
                val timeGapNote = detectTimeGap(history, now)

                val isThinConversation = history.size <= 3
                val lastMessage = history.lastOrNull()?.text ?: ""

                val basePrompt = if (isThinConversation && !profileInfo.isNullOrBlank()) {
                    buildThinConvoWithProfilePrompt(personName, profileInfo, conversationContext, lastMessage, timeGapNote)
                } else if (isThinConversation) {
                    buildThinConvoNoProfilePrompt(personName, conversationContext, lastMessage, timeGapNote)
                } else {
                    buildNormalConvoPrompt(personName, profileInfo, conversationContext, lastMessage, timeGapNote)
                }
                basePrompt + hintSection
            }

            Log.d("RizzBot", "GenerateReply: calling LLM (4 vibes)")
            val rawReply = llmRepository.generateReply(systemPrompt, userPrompt)
            val replies = parseReplies(rawReply)
            Log.d("RizzBot", "GenerateReply: SUCCESS ${replies.size} replies, first=${replies.firstOrNull()?.take(50)}...")
            SuggestionResult.Success(replies)
        } catch (e: Exception) {
            Log.e("RizzBot", "GenerateReply: FAILED - ${e.message}", e)
            SuggestionResult.Error(e.message ?: "Failed to generate reply")
        }
    }

    suspend fun invokeNewTopic(
        personName: String,
        profileInfo: String? = null,
        userHint: String? = null
    ): SuggestionResult {
        return try {
            Log.d("RizzBot", "GenerateNewTopic: person=$personName, profile=${!profileInfo.isNullOrBlank()}")

            val systemPrompt = buildSystemPromptUseCase()
            val history = getConversationHistoryUseCase(personName)
            val now = System.currentTimeMillis()

            val hintSection = if (!userHint.isNullOrBlank()) {
                "\nUSER DIRECTION: Focus on: \"$userHint\". Incorporate this into all 4 replies while keeping each vibe distinct.\n"
            } else ""
            val userPrompt = buildNewTopicPrompt(personName, profileInfo, history, now) + hintSection

            Log.d("RizzBot", "GenerateNewTopic: calling LLM")
            val rawReply = llmRepository.generateReply(systemPrompt, userPrompt)
            val replies = parseReplies(rawReply)
            Log.d("RizzBot", "GenerateNewTopic: SUCCESS ${replies.size} replies")
            SuggestionResult.Success(replies)
        } catch (e: Exception) {
            Log.e("RizzBot", "GenerateNewTopic: FAILED - ${e.message}", e)
            SuggestionResult.Error(e.message ?: "Failed to generate new topics")
        }
    }

    private fun parseReplies(raw: String): List<String> {
        val parts = raw.split("---")
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .map { part ->
                // Strip labels like "Flirty:", "1.", "**Bold**:", etc.
                part.replace(Regex("^\\s*(?:Flirty|Witty|Smooth|Bold|Option|Reply|Vibe)\\s*\\d?\\s*[:\\-]+\\s*", RegexOption.IGNORE_CASE), "")
                    .replace(Regex("^\\s*\\d+[.):]+\\s*"), "")
                    .replace(Regex("^\\s*\\*\\*[^*]+\\*\\*\\s*[:\\-]*\\s*"), "")
                    .trim()
            }
            .filter { it.isNotBlank() }

        Log.d("RizzBot", "parseReplies: parsed ${parts.size} replies from ${raw.length} chars")
        return parts.ifEmpty { listOf(raw.trim()) }
    }

    private fun formatConversationWithTime(history: List<ChatMessage>, now: Long): String {
        val sb = StringBuilder()
        var lastTimestamp = 0L

        for (msg in history) {
            val gap = if (lastTimestamp > 0) msg.timestamp - lastTimestamp else 0
            // Insert time gap marker for gaps > 1 hour
            if (gap > TimeUnit.HOURS.toMillis(1)) {
                sb.appendLine("--- ${formatDuration(gap)} gap ---")
            }
            val prefix = if (msg.isIncoming) "Them" else "You"
            val relTime = formatRelativeTime(now - msg.timestamp)
            sb.appendLine("$prefix ($relTime): ${msg.text}")
            lastTimestamp = msg.timestamp
        }
        return sb.toString().trim()
    }

    private fun detectTimeGap(history: List<ChatMessage>, now: Long): String {
        if (history.size < 2) return ""
        val lastMsg = history.last()
        val secondLast = history[history.size - 2]

        // Gap between the last two messages
        val gapMs = lastMsg.timestamp - secondLast.timestamp
        // Time since last message
        val sinceLast = now - lastMsg.timestamp

        val notes = mutableListOf<String>()

        if (gapMs > TimeUnit.HOURS.toMillis(6)) {
            val gapStr = formatDuration(gapMs)
            val whoSentLast = if (lastMsg.isIncoming) "They" else "You"
            val whoSentBefore = if (secondLast.isIncoming) "they" else "you"
            notes.add("$whoSentLast replied after $gapStr (${whoSentBefore} sent the previous message).")
        }

        if (sinceLast > TimeUnit.HOURS.toMillis(2)) {
            notes.add("Their last message was ${formatDuration(sinceLast)} ago.")
        }

        return if (notes.isNotEmpty()) {
            "\nTIMING CONTEXT: ${notes.joinToString(" ")}\n"
        } else ""
    }

    private fun formatRelativeTime(ms: Long): String {
        val mins = TimeUnit.MILLISECONDS.toMinutes(ms)
        val hours = TimeUnit.MILLISECONDS.toHours(ms)
        val days = TimeUnit.MILLISECONDS.toDays(ms)
        return when {
            mins < 2 -> "just now"
            mins < 60 -> "${mins}m ago"
            hours < 24 -> "${hours}h ago"
            days == 1L -> "yesterday"
            else -> "${days}d ago"
        }
    }

    private fun formatDuration(ms: Long): String {
        val mins = TimeUnit.MILLISECONDS.toMinutes(ms)
        val hours = TimeUnit.MILLISECONDS.toHours(ms)
        val days = TimeUnit.MILLISECONDS.toDays(ms)
        return when {
            mins < 60 -> "${mins} minutes"
            hours < 24 -> "${hours} hours"
            days == 1L -> "1 day"
            else -> "$days days"
        }
    }

    private fun buildConversationStarterPrompt(personName: String, profileInfo: String?): String {
        return if (!profileInfo.isNullOrBlank()) {
            """
TASK: First message to $personName. Cold open — make it count.

PROFILE:
$profileInfo

Pick 4 DIFFERENT specific details from their profile. For each, build a fun question, assumption, or scenario around it.
NEVER say "I noticed you like X" or "I see you're into X" — weave the detail in naturally as if you already know it.
Try connecting two profile details together in at least one reply for depth.
Each reply must reference a DIFFERENT profile detail. Be specific, not generic.
            """.trimIndent()
        } else {
            """
TASK: First message to $personName. No profile info available.

Be memorable in under 20 words. Use: fun dilemmas, bold assumptions, mini scenarios, or playful frames. Each reply uses a different approach. Must require zero context to reply to.
Don't sound like every other guy in their DMs. Surprise them.
            """.trimIndent()
        }
    }

    private fun buildThinConvoWithProfilePrompt(
        personName: String,
        profileInfo: String,
        conversationContext: String,
        lastMessage: String,
        timeGapNote: String = ""
    ): String {
        return """
TASK: Reply to $personName. Early conversation (1-3 messages). You have their profile — USE specific details.

PROFILE:
$profileInfo
$timeGapNote
CHAT:
$conversationContext

LAST MESSAGE: "$lastMessage"

Respond to what they said FIRST, then weave in a specific profile detail as a hook.
If their message is low-effort ("hi", "hey", "haha"), DON'T match their energy — bring something interesting from their profile instead.
Each reply uses a DIFFERENT profile detail. Don't reference a detail the conversation already covered.
Match their language. Don't repeat their words back to them.
        """.trimIndent()
    }

    private fun buildThinConvoNoProfilePrompt(
        personName: String,
        conversationContext: String,
        lastMessage: String,
        timeGapNote: String = ""
    ): String {
        return """
TASK: Reply to $personName. Early conversation (1-3 messages). No profile info available.
$timeGapNote
CHAT:
$conversationContext

LAST MESSAGE: "$lastMessage"

Respond to what they said, then add personality — humor, curiosity, or a fun assumption about them.
End with a hook (playful question, bold assumption, mini challenge). Never interview them with boring questions.
If they sent low-effort ("hi", "hey", "haha"), bring WAY more energy — make them want to match yours.
Don't repeat what they said. Build forward. Each reply should feel like a different person wrote it.
Match their language.
        """.trimIndent()
    }

    private fun buildNormalConvoPrompt(
        personName: String,
        profileInfo: String?,
        conversationContext: String,
        lastMessage: String,
        timeGapNote: String = ""
    ): String {
        val profileContext = if (!profileInfo.isNullOrBlank()) {
            "\nPROFILE:\n$profileInfo\n"
        } else ""

        return """
TASK: Continue conversation with $personName. Rapport is building — keep momentum.
$profileContext$timeGapNote
CHAT:
$conversationContext

LAST MESSAGE: "$lastMessage"

CONVERSATION HEALTH CHECK:
- If the last 3+ messages are about the same topic → at least ONE reply MUST change the subject entirely
- If they're giving shorter replies → don't push harder on the same thing, pivot to something fresh
- If the vibe is dying → go bold or funny, don't play it safe

Respond to what they said first. Then advance — new angle, go deeper, or escalate.
Match their energy: if flirty lean in, if energy is dropping pivot to an unused profile detail, if they're testing you then play along confidently.
End each reply with a hook. Each of the 4 replies takes a COMPLETELY different angle.
Don't repeat topics or questions already covered in the chat. Move the conversation FORWARD.
Match their language.
        """.trimIndent()
    }

    private fun buildNewTopicPrompt(
        personName: String,
        profileInfo: String?,
        history: List<ChatMessage>,
        now: Long
    ): String {
        val conversationSummary = if (history.isNotEmpty()) {
            val topics = history.map { it.text }.joinToString(" | ")
            "ALREADY DISCUSSED (don't repeat): $topics"
        } else {
            "No conversation yet — this will be your opening message."
        }

        val profileSection = if (!profileInfo.isNullOrBlank()) {
            "PROFILE:\n$profileInfo"
        } else ""

        return """
TASK: 4 fresh topic pivots for $personName. New energy — nothing they've already talked about.

$profileSection

$conversationSummary

Use 4 different strategies:
(1) Untapped profile detail with a fun spin — don't just mention it, build a scenario around it
(2) Creative hypothetical tied to their interests — "would you rather" or "what if" that reveals personality
(3) Shared experience seed — "I feel like we'd..." or "okay but imagine us at..." that creates a shared future image
(4) Playful debate on something they'd actually care about based on their profile/interests

Each must be specific and surprising, not generic. Keep it 1-3 sentences, conversational. Match their language.
        """.trimIndent()
    }
}
