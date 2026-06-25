package com.rizzbot.v2.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.path
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingWhite

/**
 * Single source of truth for the Cookd logo — a bold geometric "C".
 *
 * @param size Diameter of the circle. Default 100dp.
 * @param backgroundColor Fill color behind the "C" path. Default NothingWhite for standard use.
 *        Pass Color.Transparent when placing on a dark overlay bubble to avoid nested circles.
 * @param iconTint Color of the "C" path. Default NothingBlack.
 */
@Composable
fun CookdLogo(
    modifier: Modifier = Modifier,
    size: Dp = 100.dp,
    backgroundColor: androidx.compose.ui.graphics.Color = NothingWhite,
    iconTint: androidx.compose.ui.graphics.Color = NothingBlack,
) {
    val cookdCVector = remember { VectorCookdC }

    Box(
        modifier = modifier
            .size(size)
            .clip(CircleShape)
            .then(
                if (backgroundColor != androidx.compose.ui.graphics.Color.Transparent) {
                    Modifier.background(backgroundColor)
                } else Modifier
            ),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            imageVector = cookdCVector,
            contentDescription = "Cookd Logo",
            tint = iconTint,
            modifier = Modifier.size(size)
        )
    }
}

/**
 * Hardcoded ImageVector utilizing the exact 108x108 viewport coordinate mapping 
 * of the perfectly centered, custom-scaled geometric "C" asset.
 */
private val VectorCookdC: ImageVector
    get() = ImageVector.Builder(
        name = "VectorCookdC",
        defaultWidth = 108.dp,
        defaultHeight = 108.dp,
        viewportWidth = 108f,
        viewportHeight = 108f
    ).path(fill = SolidColor(NothingBlack)) {
        moveTo(63.73f, 45.51f)
        arcTo(
            horizontalEllipseRadius = 12f,
            verticalEllipseRadius = 12f,
            theta = 0f,
            isMoreThanHalf = true,
            isPositiveArc = false,
            x1 = 63.73f,
            y1 = 62.49f
        )
        lineTo(61.31f, 60.07f)
        arcTo(
            horizontalEllipseRadius = 8.6f,
            verticalEllipseRadius = 8.6f,
            theta = 0f,
            isMoreThanHalf = true,
            isPositiveArc = true,
            x1 = 61.31f,
            y1 = 47.93f
        )
        close()
    }.build()