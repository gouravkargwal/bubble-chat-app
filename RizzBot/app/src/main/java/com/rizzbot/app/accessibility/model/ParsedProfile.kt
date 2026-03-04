package com.rizzbot.app.accessibility.model

data class ParsedProfile(
    val name: String,
    val age: String? = null,
    val qaPrompts: List<QAPair> = emptyList(),
    val languages: List<String> = emptyList(),
    val motherTongue: String? = null,
    val basics: List<String> = emptyList(), // Single, Aries, 5'5", Hindu, etc.
    val hometown: String? = null,
    val distance: String? = null,
    val education: String? = null,
    val interests: List<String> = emptyList(),
    val traits: List<String> = emptyList(),
    val philosophy: List<String> = emptyList(), // e.g. "Tech Savvy than Luddite"
    val relationshipGoal: String? = null // e.g. "Long-term relationship, open to settling down"
) {
    /** Build a concise text summary for the LLM prompt */
    fun toPromptString(): String {
        val parts = mutableListOf<String>()
        parts.add("[Dating app profile — all items below are from her profile, NOT about AI/tech]")
        parts.add("Name: $name")
        age?.let { parts.add("Age: $it") }

        // Basics with context (zodiac signs, height, religion, relationship status, etc.)
        if (basics.isNotEmpty()) {
            val labeled = basics.map { categorizeBasic(it) }
            parts.add("About her: ${labeled.joinToString(", ")}")
        }

        education?.let { parts.add("Education: $it") }
        hometown?.let { parts.add("Hometown: $it") }
        distance?.let { parts.add("Distance: $it") }
        motherTongue?.let { parts.add("Mother tongue: $it") }
        if (languages.isNotEmpty()) parts.add("Languages she speaks: ${languages.joinToString(", ")}")

        if (qaPrompts.isNotEmpty()) {
            parts.add("Her dating app Q&A:")
            qaPrompts.forEach { parts.add("  Q: ${it.question} → Her answer: ${it.answer}") }
        }

        if (interests.isNotEmpty()) parts.add("Her hobbies/interests: ${interests.joinToString(", ")}")
        if (traits.isNotEmpty()) parts.add("Her personality traits: ${traits.joinToString(", ")}")
        if (philosophy.isNotEmpty()) parts.add("Her life philosophy/preferences: ${philosophy.joinToString(", ")}")
        relationshipGoal?.let { parts.add("Looking for: $it") }
        return parts.joinToString("\n")
    }

    private fun categorizeBasic(item: String): String {
        val zodiacSigns = setOf(
            "aries", "taurus", "gemini", "cancer", "leo", "virgo",
            "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
        )
        val religions = setOf(
            "hindu", "muslim", "christian", "sikh", "buddhist", "jain",
            "jewish", "catholic", "protestant", "atheist", "agnostic", "spiritual"
        )
        val relationshipStatuses = setOf(
            "single", "divorced", "separated", "widowed", "married"
        )
        val lower = item.lowercase().trim()

        return when {
            zodiacSigns.any { lower.startsWith(it) } -> "$item (zodiac sign)"
            religions.any { lower.startsWith(it) } -> "$item (religion)"
            relationshipStatuses.any { lower == it } -> "$item (relationship status)"
            lower.matches(Regex("^\\d+'\\d+\"?$")) || lower.matches(Regex("^\\d+ ?(cm|ft|in).*")) -> "$item (height)"
            lower.contains("drink") || lower.contains("smoke") || lower.contains("cannabis") -> "$item (lifestyle)"
            else -> item
        }
    }
}

data class QAPair(
    val question: String,
    val answer: String
)
