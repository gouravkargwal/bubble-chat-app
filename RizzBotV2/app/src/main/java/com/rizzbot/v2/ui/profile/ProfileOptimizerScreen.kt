package com.rizzbot.v2.ui.profile

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Cached
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage
import com.rizzbot.v2.util.HapticHelper
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private val DarkBg = Color(0xFF050510)
private val CardBg = Color(0xFF111122)
private val Accent = Color(0xFFFFD700)
private val AccentSoft = Accent.copy(alpha = 0.16f)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileOptimizerScreen(
    onBack: () -> Unit,
    viewModel: ProfileOptimizerViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val clipboardManager = LocalClipboardManager.current
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    // Keep existing idle CTA; we can also auto-trigger if you want:
    // LaunchedEffect(Unit) { viewModel.generateBlueprint() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Profile Optimizer",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.White
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = DarkBg,
                    titleContentColor = Color.White
                )
            )
        },
        containerColor = DarkBg,
        snackbarHost = { SnackbarHost(snackbarHostState) },
        floatingActionButton = {
            if (state is OptimizerState.Success) {
                FloatingActionButton(
                    onClick = { viewModel.generateBlueprint() },
                    containerColor = Accent,
                    modifier = Modifier.navigationBarsPadding()
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        modifier = Modifier.padding(horizontal = 12.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Cached,
                            contentDescription = "Recalibrate",
                            tint = Color.Black
                        )
                        Text(
                            text = "Recalibrate",
                            color = Color.Black,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        colors = listOf(DarkBg, Color(0xFF050515))
                    )
                )
        ) {
            when (val s = state) {
                is OptimizerState.Idle -> {
                    IdleOptimizerCard(
                        onGenerate = { viewModel.generateBlueprint() }
                    )
                }

                is OptimizerState.Loading -> {
                    LoadingState()
                }

                is OptimizerState.Success -> {
                    SuccessState(
                        blueprint = s.blueprint,
                        onCopy = { text ->
                            clipboardManager.setText(AnnotatedString(text))
                            // Use a light success haptic if available
                            HapticHelper(context).successTap()
                            scope.launch {
                                snackbarHostState.showSnackbar("Copied to clipboard")
                            }
                        },
                        onRecalibrate = { viewModel.generateBlueprint() }
                    )
                }

                is OptimizerState.Error -> {
                    ErrorState(
                        message = s.message,
                        onRetry = { viewModel.generateBlueprint() },
                        onBackToIdle = { viewModel.reset() }
                    )
                }
            }
        }
    }
}

@Composable
private fun IdleOptimizerCard(
    onGenerate: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(20.dp),
        contentAlignment = Alignment.Center
    ) {
        Card(
            colors = CardDefaults.cardColors(containerColor = CardBg),
            shape = RoundedCornerShape(24.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier
                    .padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .height(44.dp)
                            .clip(RoundedCornerShape(16.dp))
                            .background(AccentSoft),
                        contentAlignment = Alignment.Center
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 14.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.AutoAwesome,
                                contentDescription = null,
                                tint = Accent
                            )
                            Text(
                                text = "High-Status Auto Builder",
                                color = Accent,
                                fontSize = 13.sp,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }
                }

            Text(
                text = "Let Cookd auto-assemble a cross-app profile from your best audited photos.",
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold
                )

            Text(
                text = "We'll pick 6 photos, craft hooks, and explain the strategy like a creative director.",
                    color = Color(0xFFB0B0D0),
                    fontSize = 13.sp,
                    lineHeight = 18.sp
                )

                Spacer(modifier = Modifier.height(6.dp))

                Button(
                    onClick = onGenerate,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Accent)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = "✨ Auto-Build My Profile",
                            color = Color.Black,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                }

                Text(
                    text = "Uses only photos you've already audited. No new uploads needed.",
                    color = Color(0xFF8080A0),
                    fontSize = 11.sp
                )
            }
        }
    }
}

@Composable
private fun LoadingState() {
    val phrases = listOf(
        "Analyzing your best angles...",
        "Reordering your lineup like a creative director...",
        "Designing a Tinder/Bumble/Hinge-proof blueprint...",
        "Balancing status, warmth, and fun...",
        "Locking in a first-photo glow-up..."
    )
    val index = remember { mutableStateOf(0) }

    LaunchedEffect(Unit) {
        while (true) {
            delay(1600)
            index.value = (index.value + 1) % phrases.size
        }
    }

    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            val transition = rememberInfiniteTransition(label = "loadingPulse")
            val scale by transition.animateFloat(
                initialValue = 0.9f,
                targetValue = 1.1f,
                animationSpec = infiniteRepeatable(
                    animation = tween(durationMillis = 1000, easing = LinearEasing),
                    repeatMode = RepeatMode.Reverse
                ),
                label = "scaleAnim"
            )

            Box(
                modifier = Modifier
                    .height(80.dp)
                    .clip(CircleShape)
                    .background(AccentSoft),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator(
                    color = Accent,
                    strokeWidth = 3.dp
                )
            }
            AnimatedContent(targetState = index.value, label = "loadingText") { idx ->
                Text(
                    text = phrases[idx],
                    color = Color.White,
                    fontSize = 14.sp
                )
            }
            Text(
                text = "This usually takes ~5–10 seconds.",
                color = Color(0xFF9090B0),
                fontSize = 12.sp
            )
        }
    }
}

@Composable
private fun SuccessState(
    blueprint: ProfileBlueprint,
    onCopy: (String) -> Unit,
    onRecalibrate: () -> Unit
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        contentPadding = PaddingValues(bottom = 88.dp, top = 12.dp)
    ) {
        item {
            Text(
                text = "Profile Blueprint",
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = blueprint.overallTheme,
                color = Color(0xFFB0B0D0),
                fontSize = 14.sp
            )
        }

        items(
            items = blueprint.slots.sortedBy { it.slotNumber },
            key = { it.slotNumber }
        ) { slot ->
            SlotCard(slot = slot, onCopy = onCopy)
        }

        item {
            Spacer(modifier = Modifier.height(8.dp))
            TextButton(
                onClick = onRecalibrate,
                modifier = Modifier.fillMaxWidth()
            ) {
                Icon(
                    imageVector = Icons.Default.Cached,
                    contentDescription = null,
                    tint = Accent
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Recalibrate with a new blueprint",
                    color = Accent,
                    fontSize = 13.sp
                )
            }
        }
    }
}

@Composable
private fun SlotCard(
    slot: OptimizedSlot,
    onCopy: (String) -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = CardBg),
        shape = RoundedCornerShape(20.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 6.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(260.dp)
                    .clip(RoundedCornerShape(18.dp))
            ) {
                AsyncImage(
                    model = slot.photoUrl,
                    contentDescription = null,
                    modifier = Modifier.fillMaxSize()
                )

                BadgedBox(
                    badge = {
                        Badge(
                            containerColor = Color.Black.copy(alpha = 0.85f),
                            contentColor = Accent
                        ) {
                            Text(
                                text = "Slot ${slot.slotNumber}: ${slot.role}",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.SemiBold,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                        }
                    },
                    modifier = Modifier
                        .align(Alignment.TopStart)
                        .padding(10.dp)
                ) {
                    // No anchor content
                }
            }

            Text(
                text = slot.caption,
                color = Color.White,
                fontSize = 15.sp,
                fontWeight = FontWeight.SemiBold
            )

            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFF17172A)),
                shape = RoundedCornerShape(14.dp),
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Contextual Hook",
                            color = Color(0xFFB0B0D0),
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Medium
                        )
                        IconButton(onClick = {
                            onCopy(slot.contextualHook)
                        }) {
                            Icon(
                                imageVector = Icons.Default.ContentCopy,
                                contentDescription = "Copy prompt",
                                tint = Color(0xFFDDDDFF)
                            )
                        }
                    }
                    Text(
                        text = slot.contextualHook,
                        color = Color(0xFFE0FFE8),
                        fontSize = 14.sp,
                        lineHeight = 20.sp
                    )
                }
            }

            Text(
                text = slot.coachReasoning,
                color = Color(0xFF9FA8DA),
                fontSize = 12.sp,
                lineHeight = 18.sp
            )
        }
    }
}

@Composable
private fun ErrorState(
    message: String,
    onRetry: () -> Unit,
    onBackToIdle: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(20.dp),
        contentAlignment = Alignment.Center
    ) {
        Card(
            colors = CardDefaults.cardColors(containerColor = CardBg),
            shape = RoundedCornerShape(20.dp)
        ) {
            Column(
                modifier = Modifier
                    .padding(18.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "Couldn't generate a blueprint",
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = message,
                    color = Color(0xFFEF9A9A),
                    fontSize = 13.sp
                )
                Spacer(modifier = Modifier.height(8.dp))
                Row(
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Button(
                        onClick = onRetry,
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.buttonColors(containerColor = Accent)
                    ) {
                        Text(
                            text = "Try Again",
                            color = Color.Black,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                    TextButton(
                        onClick = onBackToIdle,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text(
                            text = "Back",
                            color = Color(0xFFB0B0D0),
                            fontSize = 13.sp
                        )
                    }
                }
            }
        }
    }
}

