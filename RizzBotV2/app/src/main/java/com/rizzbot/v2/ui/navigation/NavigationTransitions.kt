package com.rizzbot.v2.ui.navigation

import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.slideOutVertically

/**
 * Full-screen navigation: one easing curve and matched durations so enter/exit stay in sync.
 * Avoid stacking slide + scale + fade with different timings (that reads as jittery / “not smooth”).
 */
private const val NAV_MS = 300
private const val LEGAL_MS = 300
private const val PAYWALL_MS = 300

private val Ease = FastOutSlowInEasing

/** Push: new screen from the right; previous moves slightly left (parallax). */
fun defaultEnterTransition(): EnterTransition =
    slideInHorizontally(
        animationSpec = tween(NAV_MS, easing = Ease),
        initialOffsetX = { fullWidth -> fullWidth },
    ) +
        fadeIn(
            animationSpec = tween(NAV_MS, easing = Ease),
            initialAlpha = 0.94f,
        )

fun defaultExitTransition(): ExitTransition =
    slideOutHorizontally(
        animationSpec = tween(NAV_MS, easing = Ease),
        targetOffsetX = { fullWidth -> -(fullWidth * 0.28f).toInt() },
    ) +
        fadeOut(
            animationSpec = tween(NAV_MS, easing = Ease),
            targetAlpha = 0.94f,
        )

/** Pop: underneath returns from the left; current leaves to the right. */
fun defaultPopEnterTransition(): EnterTransition =
    slideInHorizontally(
        animationSpec = tween(NAV_MS, easing = Ease),
        initialOffsetX = { fullWidth -> -(fullWidth * 0.28f).toInt() },
    ) +
        fadeIn(
            animationSpec = tween(NAV_MS, easing = Ease),
            initialAlpha = 0.94f,
        )

fun defaultPopExitTransition(): ExitTransition =
    slideOutHorizontally(
        animationSpec = tween(NAV_MS, easing = Ease),
        targetOffsetX = { fullWidth -> fullWidth },
    ) +
        fadeOut(
            animationSpec = tween(NAV_MS, easing = Ease),
        )

/** Legal sheets: vertical slide + fade only (no scale — avoids vertical “bounce”). */
fun legalEnterTransition(): EnterTransition =
    fadeIn(tween(LEGAL_MS, easing = Ease)) +
        slideInVertically(
            animationSpec = tween(LEGAL_MS, easing = Ease),
            initialOffsetY = { fullHeight -> (fullHeight * 0.06f).toInt() },
        )

fun legalExitTransition(): ExitTransition =
    fadeOut(tween(LEGAL_MS, easing = Ease)) +
        slideOutVertically(
            animationSpec = tween(LEGAL_MS, easing = Ease),
            targetOffsetY = { fullHeight -> (fullHeight * 0.05f).toInt() },
        )

fun legalPopEnterTransition(): EnterTransition =
    fadeIn(tween(LEGAL_MS, easing = Ease)) +
        slideInVertically(
            animationSpec = tween(LEGAL_MS, easing = Ease),
            initialOffsetY = { fullHeight -> -(fullHeight * 0.05f).toInt() },
        )

fun legalPopExitTransition(): ExitTransition =
    fadeOut(tween(LEGAL_MS, easing = Ease)) +
        slideOutVertically(
            animationSpec = tween(LEGAL_MS, easing = Ease),
            targetOffsetY = { fullHeight -> fullHeight },
        )

/** Paywall: subtle zoom + fade; single duration and easing. */
fun paywallEnterTransition(): EnterTransition =
    fadeIn(tween(PAYWALL_MS, easing = Ease), initialAlpha = 0f) +
        scaleIn(
            initialScale = 0.94f,
            animationSpec = tween(PAYWALL_MS, easing = Ease),
        )

fun paywallExitTransition(): ExitTransition =
    fadeOut(tween(PAYWALL_MS, easing = Ease)) +
        scaleOut(
            targetScale = 0.96f,
            animationSpec = tween(PAYWALL_MS, easing = Ease),
        )

fun paywallPopEnterTransition(): EnterTransition =
    fadeIn(tween(PAYWALL_MS, easing = Ease)) +
        scaleIn(
            initialScale = 0.96f,
            animationSpec = tween(PAYWALL_MS, easing = Ease),
        )

fun paywallPopExitTransition(): ExitTransition =
    fadeOut(tween(PAYWALL_MS, easing = Ease)) +
        scaleOut(
            targetScale = 0.94f,
            animationSpec = tween(PAYWALL_MS, easing = Ease),
        )
