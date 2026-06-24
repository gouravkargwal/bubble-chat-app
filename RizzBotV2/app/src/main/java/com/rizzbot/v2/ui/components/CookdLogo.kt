package com.rizzbot.v2.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingWhite

/**
 * Single source of truth for the Cookd logo — a white circle with a bold black "C".
 *
 * @param size Diameter of the white circle. Default 100dp.
 * @param textStyle Typography style for the "C". Default [MaterialTheme.typography.displayLarge].
 *        Callers with small circles should pass a smaller style (e.g. [MaterialTheme.typography.headlineLarge]).
 */
@Composable
fun CookdLogo(
    modifier: Modifier = Modifier,
    size: Dp = 100.dp,
    textStyle: TextStyle = MaterialTheme.typography.displayLarge,
) {
    Box(
        modifier = modifier
            .size(size)
            .clip(CircleShape)
            .background(NothingWhite),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = "C",
            color = NothingBlack,
            style = textStyle,
            fontWeight = FontWeight.ExtraBold,
        )
    }
}
