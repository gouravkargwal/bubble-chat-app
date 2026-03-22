package com.rizzbot.v2

/**
 * Product kill switches. Flip when backend + marketing are ready to ship a feature.
 */
object FeatureFlags {
    const val VOICE_DNA_ENABLED = false

    /** Home "Your Stats" + reply-style card (RizzProfileCard). Off until the product ships this surface. */
    const val HOME_REPLY_STYLE_SECTION_ENABLED = false
}
