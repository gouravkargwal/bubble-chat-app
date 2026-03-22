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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Article
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
import com.rizzbot.v2.ui.theme.DarkBg
import com.rizzbot.v2.util.HapticHelper
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private val CardBg = Color(0xFF111122)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileOptimizerScreen(
    onBack: () -> Unit,
    onViewStrategy: () -> Unit = {},
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
                        text = "Auto-Build Profile",
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
                actions = {
                    IconButton(onClick = onViewStrategy) {
                        Icon(
                            imageVector = Icons.Filled.Article,
                            contentDescription = "Saved profile blueprints",
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
                    containerColor = MaterialTheme.colorScheme.primary,
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
                            HapticHelper(context).successTap()
                            scope.launch {
                                snackbarHostState.showSnackbar("Copied to clipboard")
                            }
                        },
                        onRecalibrate = { viewModel.generateBlueprint() },
                        onViewStrategy = onViewStrategy
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
                    .padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(20.dp)
            ) {
                // Header with icon
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .size(48.dp)
                            .clip(RoundedCornerShape(14.dp))
                            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.16f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.AutoAwesome,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(26.dp)
                        )
                    }
                    Column {
                        Text(
                            text = "Auto-Build Profile",
                            color = Color.White,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "AI-powered profile builder",
                            color = Color(0xFFB0B0D0),
                            fontSize = 13.sp
                        )
                    }
                }

                Spacer(modifier = Modifier.height(4.dp))

                // Main description
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(
                        text = "What it does:",
                        color = Color.White,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = "Cookd analyzes your audited photos and automatically creates a complete dating profile blueprint. We'll select your best 6 photos, order them strategically, craft compelling captions, and provide universal hooks that work across Tinder, Bumble, and Hinge.",
                        color = Color(0xFFB0B0D0),
                        fontSize = 14.sp,
                        lineHeight = 20.sp
                    )
                    
                    Spacer(modifier = Modifier.height(4.dp))
                    
                    Text(
                        text = "How it works:",
                        color = Color.White,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        FeatureBullet("Uses only photos you've already audited")
                        FeatureBullet("AI analyzes photo quality, angles, and appeal")
                        FeatureBullet("Creates a strategic photo order for maximum impact")
                        FeatureBullet("Generates captions and hooks tailored to your style")
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                Button(
                    onClick = onGenerate,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                    contentPadding = PaddingValues(vertical = 16.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.AutoAwesome,
                            contentDescription = null,
                            tint = Color.Black,
                            modifier = Modifier.size(18.dp)
                        )
                        Text(
                            text = "Generate My Profile Blueprint",
                            color = Color.Black,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
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
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.16f)),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator(
                    color = MaterialTheme.colorScheme.primary,
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
    onRecalibrate: () -> Unit,
    onViewStrategy: () -> Unit = {}
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
            Spacer(modifier = Modifier.height(12.dp))
            Button(
                onClick = onViewStrategy,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1A1A33)),
                contentPadding = PaddingValues(vertical = 14.dp)
            ) {
                Text(
                    text = "View Blueprints & History",
                    color = MaterialTheme.colorScheme.primary,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }
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
                    tint = MaterialTheme.colorScheme.primary
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Recalibrate with a new blueprint",
                    color = MaterialTheme.colorScheme.primary,
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
                    model = slot.imageUrl,
                    contentDescription = null,
                    modifier = Modifier.fillMaxSize()
                )

                BadgedBox(
                    badge = {
                        Badge(
                            containerColor = Color.Black.copy(alpha = 0.85f),
                            contentColor = MaterialTheme.colorScheme.primary
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

            if (slot.hingePrompt.isNotBlank()) {
                PlatformPromptCard(
                    label = "Hinge Prompt",
                    labelColor = Color(0xFFFF6B6B),
                    text = slot.hingePrompt,
                    onCopy = { onCopy(slot.hingePrompt) }
                )
            }
            if (slot.aislePrompt.isNotBlank()) {
                PlatformPromptCard(
                    label = "Aisle Prompt",
                    labelColor = Color(0xFF6BDDFF),
                    text = slot.aislePrompt,
                    onCopy = { onCopy(slot.aislePrompt) }
                )
            }
        }
    }
}

@Composable
private fun PlatformPromptCard(
    label: String,
    labelColor: Color,
    text: String,
    onCopy: () -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF0D0D22)),
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = label,
                    color = labelColor,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
                IconButton(
                    onClick = onCopy,
                    modifier = Modifier.size(28.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.ContentCopy,
                        contentDescription = "Copy",
                        tint = labelColor.copy(alpha = 0.8f),
                        modifier = Modifier.size(16.dp)
                    )
                }
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = text,
                color = Color(0xFFD0D0F0),
                fontSize = 13.sp,
                lineHeight = 19.sp
            )
        }
    }
}

@Composable
private fun FeatureBullet(text: String) {
    Row(
        verticalAlignment = Alignment.Top,
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Box(
            modifier = Modifier
                .size(6.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primary)
                .padding(top = 6.dp)
        )
        Text(
            text = text,
            color = Color(0xFFB0B0D0),
            fontSize = 13.sp,
            lineHeight = 18.sp
        )
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
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
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

