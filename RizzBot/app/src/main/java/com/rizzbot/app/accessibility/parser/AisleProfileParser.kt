package com.rizzbot.app.accessibility.parser

import android.util.Log
import android.view.accessibility.AccessibilityNodeInfo
import com.rizzbot.app.accessibility.model.ParsedProfile
import com.rizzbot.app.accessibility.model.QAPair
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AisleProfileParser @Inject constructor() {

    companion object {
        private const val TAG = "RizzBot"

        // Hard negatives: if these exist, it's NOT a profile detail page
        private const val ID_MATCHES_RV = "com.aisle.app:id/matches_rv"
        private const val ID_HEADER_TITLE = "com.aisle.app:id/header_title"
        private const val ID_CHAT_RV = "com.aisle.app:id/chat_rv"
        private const val ID_MESSAGE_INPUT = "com.aisle.app:id/message_input"
        // Discover/swipe page shares profile_rv but has like/pass buttons
        private const val ID_PASS_BUTTON = "com.aisle.app:id/pass_button"
        private const val ID_LIKE_BUTTON = "com.aisle.app:id/like_button"
        private const val ID_DISCOVER_TEXT = "com.aisle.app:id/text_view_discover"

        // Profile page IDs from uiautomator dump
        private const val ID_PROFILE_RV = "com.aisle.app:id/profile_rv"
        private const val ID_USER_NAME_BELOW = "com.aisle.app:id/user_name_text_below"
        private const val ID_USER_NAME_TOP = "com.aisle.app:id/user_name_top"
        private const val ID_USER_AGE = "com.aisle.app:id/user_age"
        private const val ID_QUESTION = "com.aisle.app:id/question"
        private const val ID_ANSWER = "com.aisle.app:id/answer"
        private const val ID_LANGUAGE_TEXT = "com.aisle.app:id/language_text"
        private const val ID_MOTHER_TONGUE = "com.aisle.app:id/mother_tongue_text"
        private const val ID_PROFILE_GENERAL_TEXT = "com.aisle.app:id/profile_general_text"
        private const val ID_HOME_TOWN_TEXT = "com.aisle.app:id/home_town_text"
        private const val ID_INTERESTS_TITLE = "com.aisle.app:id/interests_title"
        private const val ID_INTEREST_LAYOUT = "com.aisle.app:id/general_interest_layout"
        private const val ID_TRAITS_TITLE = "com.aisle.app:id/traits_title"
        private const val ID_TRAITS_LAYOUT = "com.aisle.app:id/general_traits_layout"
        private const val ID_PILL_TEXT = "com.aisle.app:id/pill_text"
        private const val ID_GENERAL_LINEAR_LAYOUT = "com.aisle.app:id/general_linear_layout"
        private const val ID_PHILOSOPHY_CHOICE = "com.aisle.app:id/choice"
        private const val ID_SETTLE_DOWN = "com.aisle.app:id/settle_down"
    }

    /** Check if the current screen is a profile page */
    fun isProfilePage(root: AccessibilityNodeInfo): Boolean {
        // Hard negatives: these screens are NEVER a profile page
        if (isDefinitelyNotProfilePage(root)) return false

        // Primary: check by exact view ID
        val profileRv = root.findAccessibilityNodeInfosByViewId(ID_PROFILE_RV)
        if (profileRv.isNotEmpty()) {
            profileRv.forEach { it.recycle() }
            return true
        }

        // Fallback: structural detection
        return isProfilePageStructural(root)
    }

    /** Fast check for screens that are definitely NOT profile pages */
    private fun isDefinitelyNotProfilePage(root: AccessibilityNodeInfo): Boolean {
        // Discover/swipe page — has like/pass buttons (shares profile_rv with detail page!)
        val passBtn = root.findAccessibilityNodeInfosByViewId(ID_PASS_BUTTON)
        if (passBtn.isNotEmpty()) {
            passBtn.forEach { it.recycle() }
            Log.d(TAG, "ProfileParser: NOT profile (pass_button = Discover page)")
            return true
        }
        val likeBtn = root.findAccessibilityNodeInfosByViewId(ID_LIKE_BUTTON)
        if (likeBtn.isNotEmpty()) {
            likeBtn.forEach { it.recycle() }
            Log.d(TAG, "ProfileParser: NOT profile (like_button = Discover page)")
            return true
        }
        val discoverText = root.findAccessibilityNodeInfosByViewId(ID_DISCOVER_TEXT)
        if (discoverText.isNotEmpty()) {
            discoverText.forEach { it.recycle() }
            Log.d(TAG, "ProfileParser: NOT profile (text_view_discover = Discover page)")
            return true
        }
        // Matches/inbox page
        val matchesRv = root.findAccessibilityNodeInfosByViewId(ID_MATCHES_RV)
        if (matchesRv.isNotEmpty()) {
            matchesRv.forEach { it.recycle() }
            Log.d(TAG, "ProfileParser: NOT profile (matches_rv found)")
            return true
        }
        // Chat screen
        val chatRv = root.findAccessibilityNodeInfosByViewId(ID_CHAT_RV)
        if (chatRv.isNotEmpty()) {
            chatRv.forEach { it.recycle() }
            return true
        }
        val msgInput = root.findAccessibilityNodeInfosByViewId(ID_MESSAGE_INPUT)
        if (msgInput.isNotEmpty()) {
            msgInput.forEach { it.recycle() }
            return true
        }
        // Header title "Matches", "Discover", etc. = tab page, not profile
        val headers = root.findAccessibilityNodeInfosByViewId(ID_HEADER_TITLE)
        if (headers.isNotEmpty()) {
            val headerText = headers[0].text?.toString() ?: ""
            headers.forEach { it.recycle() }
            if (headerText in listOf("Matches", "Discover", "Notes", "Profile")) {
                Log.d(TAG, "ProfileParser: NOT profile (header=$headerText)")
                return true
            }
        }
        return false
    }

    private fun isProfilePageStructural(root: AccessibilityNodeInfo): Boolean {
        var hasScrollable = false
        var hasEditable = false
        var ageSignals = 0
        var distanceSignals = 0
        var textNodeCount = 0
        // Strong signals: only present on a single profile detail page, NOT on inbox/list
        var hasInterestsLabel = false
        var hasTraitsLabel = false
        var hasQASection = false

        traverseTree(root) { node ->
            if (node.isScrollable && node.childCount > 3) hasScrollable = true
            if (node.isEditable) hasEditable = true

            val text = node.text?.toString() ?: ""
            val viewId = node.viewIdResourceName ?: ""

            if (text.isNotBlank()) textNodeCount++

            // Weak signals (inbox lists have these for MULTIPLE profiles)
            if (text.matches(Regex("^(1[89]|[2-9]\\d)\\s*(,|years|yrs)?$"))) ageSignals++
            if (text.contains("km away", ignoreCase = true)) distanceSignals++

            // Strong signals: only on a single profile detail page
            if (text.equals("Interests", ignoreCase = true)) hasInterestsLabel = true
            if (text.equals("Traits", ignoreCase = true)) hasTraitsLabel = true
            if (viewId.contains("question") || viewId.contains("answer")) hasQASection = true
        }

        // Inbox pages have MULTIPLE age/distance signals (one per profile card)
        // A real profile page has exactly 1 age and at most 1 distance
        val isSingleProfile = ageSignals == 1 && distanceSignals <= 1
        val hasStrongSignal = hasInterestsLabel || hasTraitsLabel || hasQASection

        // Profile = scrollable + no input + single profile + at least one strong signal
        val isProfile = hasScrollable && !hasEditable && isSingleProfile && hasStrongSignal && textNodeCount >= 5
        if (isProfile) {
            Log.d(TAG, "ProfileParser: structural detection matched (ages=$ageSignals, distances=$distanceSignals, interests=$hasInterestsLabel, traits=$hasTraitsLabel, qa=$hasQASection, texts=$textNodeCount)")
        }
        return isProfile
    }

    private fun traverseTree(node: AccessibilityNodeInfo, action: (AccessibilityNodeInfo) -> Unit) {
        action(node)
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            traverseTree(child, action)
            child.recycle()
        }
    }

    /** Parse visible profile data from the current view tree */
    fun parseVisibleProfile(root: AccessibilityNodeInfo): ParsedProfile? {
        val name = findName(root) ?: return null
        Log.d(TAG, "ProfileParser: parsing profile for $name")

        val age = findTextById(root, ID_USER_AGE)
        val qaPrompts = findQAPairs(root)
        val languages = findAllTextsById(root, ID_LANGUAGE_TEXT)
        val motherTongue = findMotherTongue(root)
        val education = findTextById(root, ID_PILL_TEXT)
        val hometown = findHometown(root)
        val interests = findInterests(root)
        val traits = findTraits(root)
        val basics = findBasics(root)
        val distance = basics.find { it.contains("km away") }
        val philosophy = findAllTextsById(root, ID_PHILOSOPHY_CHOICE)
        val relationshipGoal = findTextById(root, ID_SETTLE_DOWN)

        val profile = ParsedProfile(
            name = name,
            age = age,
            qaPrompts = qaPrompts,
            languages = languages,
            motherTongue = motherTongue,
            education = education,
            hometown = hometown,
            distance = distance,
            basics = basics.filter { !it.contains("km away") && it != hometown },
            interests = interests,
            traits = traits,
            philosophy = philosophy,
            relationshipGoal = relationshipGoal
        )

        Log.d(TAG, "ProfileParser: parsed profile=$profile")
        return profile
    }

    /** Scroll the profile RecyclerView and collect all data */
    suspend fun scrollAndCollectFullProfile(root: AccessibilityNodeInfo): ParsedProfile? {
        val name = findName(root) ?: return null
        val profileRvNodes = root.findAccessibilityNodeInfosByViewId(ID_PROFILE_RV)
        if (profileRvNodes.isEmpty()) return parseVisibleProfile(root)

        val profileRv = profileRvNodes[0]
        val allQA = mutableSetOf<QAPair>()
        val allLanguages = mutableSetOf<String>()
        val allBasics = mutableSetOf<String>()
        val allInterests = mutableSetOf<String>()
        val allTraits = mutableSetOf<String>()
        var age: String? = null
        var motherTongue: String? = null
        var education: String? = null
        var hometown: String? = null
        val allPhilosophy = mutableSetOf<String>()
        var relationshipGoal: String? = null

        // Collect from current view first, then scroll
        var scrollAttempts = 0
        val maxScrolls = 10

        do {
            // Parse what's currently visible
            age = age ?: findTextById(root, ID_USER_AGE)
            allQA.addAll(findQAPairs(root))
            allLanguages.addAll(findAllTextsById(root, ID_LANGUAGE_TEXT))
            motherTongue = motherTongue ?: findMotherTongue(root)
            education = education ?: findTextById(root, ID_PILL_TEXT)
            hometown = hometown ?: findHometown(root)
            allInterests.addAll(findInterests(root))
            allTraits.addAll(findTraits(root))
            allBasics.addAll(findBasics(root))
            allPhilosophy.addAll(findAllTextsById(root, ID_PHILOSOPHY_CHOICE))
            relationshipGoal = relationshipGoal ?: findTextById(root, ID_SETTLE_DOWN)

            val previousSize = allQA.size + allLanguages.size + allBasics.size +
                    allInterests.size + allTraits.size + allPhilosophy.size

            // Scroll forward
            val scrolled = profileRv.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
            if (!scrolled) break

            kotlinx.coroutines.delay(300) // Let RecyclerView settle
            scrollAttempts++

            val newSize = allQA.size + allLanguages.size + allBasics.size +
                    allInterests.size + allTraits.size

            // If no new data after scroll, we've seen everything
            if (newSize == previousSize && scrollAttempts > 2) break

        } while (scrollAttempts < maxScrolls)

        profileRvNodes.forEach { it.recycle() }

        val distance = allBasics.find { it.contains("km away") }

        return ParsedProfile(
            name = name,
            age = age,
            qaPrompts = allQA.toList(),
            languages = allLanguages.toList(),
            motherTongue = motherTongue,
            education = education,
            hometown = hometown,
            distance = distance,
            basics = allBasics.filter { !it.contains("km away") && it != hometown }.toList(),
            interests = allInterests.toList(),
            traits = allTraits.toList(),
            philosophy = allPhilosophy.toList(),
            relationshipGoal = relationshipGoal
        )
    }

    private fun findName(root: AccessibilityNodeInfo): String? {
        // Try both name locations (top of page vs scrolled header)
        var name = findTextById(root, ID_USER_NAME_BELOW)
        if (name == null) {
            name = findTextById(root, ID_USER_NAME_TOP)
        }
        return name?.takeIf { it.isNotBlank() }
    }

    private fun findQAPairs(root: AccessibilityNodeInfo): List<QAPair> {
        val questions = root.findAccessibilityNodeInfosByViewId(ID_QUESTION)
        val answers = root.findAccessibilityNodeInfosByViewId(ID_ANSWER)

        val pairs = mutableListOf<QAPair>()

        // Match questions with answers
        val qTexts = questions.mapNotNull { it.text?.toString() }
        val aTexts = answers.mapNotNull { it.text?.toString() }

        questions.forEach { it.recycle() }
        answers.forEach { it.recycle() }

        // Pair them up - they should be in the same order
        for (i in 0 until minOf(qTexts.size, aTexts.size)) {
            if (qTexts[i].isNotBlank() && aTexts[i].isNotBlank()) {
                pairs.add(QAPair(qTexts[i], aTexts[i]))
            }
        }

        // If there are answers without questions (scrolled past the question)
        if (aTexts.size > qTexts.size) {
            for (i in qTexts.size until aTexts.size) {
                if (aTexts[i].isNotBlank()) {
                    pairs.add(QAPair("(prompt)", aTexts[i]))
                }
            }
        }

        return pairs
    }

    private fun findMotherTongue(root: AccessibilityNodeInfo): String? {
        // Mother tongue is a language_text that appears right after mother_tongue_text label
        val mtNodes = root.findAccessibilityNodeInfosByViewId(ID_MOTHER_TONGUE)
        if (mtNodes.isEmpty()) return null
        mtNodes.forEach { it.recycle() }

        // The mother tongue language is the first language_text in the same row
        val langNodes = root.findAccessibilityNodeInfosByViewId(ID_LANGUAGE_TEXT)
        val firstLang = langNodes.firstOrNull()?.text?.toString()
        langNodes.forEach { it.recycle() }
        return firstLang
    }

    private fun findHometown(root: AccessibilityNodeInfo): String? {
        val htNodes = root.findAccessibilityNodeInfosByViewId(ID_HOME_TOWN_TEXT)
        if (htNodes.isEmpty()) return null
        htNodes.forEach { it.recycle() }

        // Hometown value is a profile_general_text in the same container
        // We look for the general text that follows the HOME TOWN label
        val allGeneral = findAllTextsById(root, ID_PROFILE_GENERAL_TEXT)
        // Hometown is typically one of the general texts - we can't perfectly distinguish
        // but it's usually after distance. We'll handle it by checking the context
        return null // Will be picked up from basics with HOME TOWN label context
    }

    private fun findInterests(root: AccessibilityNodeInfo): List<String> {
        val interestLayout = root.findAccessibilityNodeInfosByViewId(ID_INTEREST_LAYOUT)
        if (interestLayout.isEmpty()) return emptyList()

        val layout = interestLayout[0]
        val interests = findAllTextsById(layout, ID_PROFILE_GENERAL_TEXT)
        interestLayout.forEach { it.recycle() }
        return interests
    }

    private fun findTraits(root: AccessibilityNodeInfo): List<String> {
        val traitsLayout = root.findAccessibilityNodeInfosByViewId(ID_TRAITS_LAYOUT)
        if (traitsLayout.isEmpty()) return emptyList()

        val layout = traitsLayout[0]
        val traits = findAllTextsById(layout, ID_PROFILE_GENERAL_TEXT)
        traitsLayout.forEach { it.recycle() }
        return traits
    }

    private fun findBasics(root: AccessibilityNodeInfo): List<String> {
        val basicsLayout = root.findAccessibilityNodeInfosByViewId(ID_GENERAL_LINEAR_LAYOUT)
        if (basicsLayout.isEmpty()) return emptyList()

        val layout = basicsLayout[0]
        val results = mutableListOf<String>()

        // Collect all profile_general_text within the basics layout
        val generalTexts = findAllTextsById(layout, ID_PROFILE_GENERAL_TEXT)
        results.addAll(generalTexts)

        // Also check for hometown specifically
        val htText = findTextById(layout, ID_HOME_TOWN_TEXT)
        if (htText != null) {
            // The hometown value follows - find the general text in the same ViewGroup
            // It's already captured in generalTexts
        }

        basicsLayout.forEach { it.recycle() }
        return results
    }

    private fun findTextById(node: AccessibilityNodeInfo, viewId: String): String? {
        val nodes = node.findAccessibilityNodeInfosByViewId(viewId)
        if (nodes.isNotEmpty()) {
            val text = nodes[0].text?.toString()
            nodes.forEach { it.recycle() }
            return text?.takeIf { it.isNotBlank() }
        }
        return null
    }

    private fun findAllTextsById(node: AccessibilityNodeInfo, viewId: String): List<String> {
        val nodes = node.findAccessibilityNodeInfosByViewId(viewId)
        val texts = nodes.mapNotNull { it.text?.toString()?.takeIf { t -> t.isNotBlank() } }
        nodes.forEach { it.recycle() }
        return texts
    }
}
