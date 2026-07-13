package com.rizzbot.v2.ui.components

import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.rizzbot.v2.ui.theme.NothingDimens

/**
 * Convenience skeleton that combines [RedeemCodeSkeleton] and [PlanCardSkeleton]
 * — exactly the two sections shown on the Settings screen while data loads.
 */
@Composable
fun SettingsSkeleton() {
    RedeemCodeSkeleton()
    Spacer(modifier = Modifier.height(NothingDimens.sectionSpacing))
    PlanCardSkeleton()
}
