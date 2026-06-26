package com.rizzbot.v2.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.rizzbot.v2.R
import com.rizzbot.v2.ui.theme.NothingBlack
import com.rizzbot.v2.ui.theme.NothingBorder
import com.rizzbot.v2.ui.theme.NothingDimens
import com.rizzbot.v2.ui.theme.NothingTextSecondary
import com.rizzbot.v2.ui.theme.NothingWhite
import com.rizzbot.v2.ui.components.CookdLogo

@Composable
fun BrandedBootScreen() {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(NothingBlack),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 36.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            // Push content to true vertical center, accounting for the indicator below
            Spacer(modifier = Modifier.weight(1f))

            CookdLogo(size = 80.dp)
            Spacer(modifier = Modifier.height(28.dp))
            Text(
                text = stringResource(R.string.app_name),
                style = MaterialTheme.typography.displaySmall,
                color = NothingWhite,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
            Box(
                modifier = Modifier
                    .width(40.dp)
                    .height(3.dp)
                    .clip(CircleShape)
                    .background(NothingBorder),
            )
            Spacer(modifier = Modifier.height(NothingDimens.elementGap))
            Text(
                text = stringResource(R.string.boot_tagline),
                style = MaterialTheme.typography.bodyLarge,
                color = NothingTextSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )

            // Reserve space below content so the indicator sits at the bottom
            // without competing with the centered content block
            Spacer(modifier = Modifier.weight(1f))

            CircularProgressIndicator(
                modifier = Modifier.size(40.dp),
                color = NothingWhite,
                trackColor = NothingBorder,
                strokeWidth = 3.dp,
            )
            Spacer(modifier = Modifier.height(52.dp))
        }
    }
}
