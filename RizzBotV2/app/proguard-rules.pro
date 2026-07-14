# ── R8 full-mode overrides ──────────────────────────────────────────
# R8 full mode is more aggressive with method inlining, class merging, and enum
# optimization. These rules prevent breakage in reflection-heavy libraries.
-keepattributes *Annotation*, InnerClasses, EnclosingMethod, Signature, Exceptions

# ── Retrofit ─────────────────────────────────────────────────────────
-keep class retrofit2.** { *; }
-keepclasseswithmembers class * {
    @retrofit2.http.* <methods>;
}
# Keep service interface method signatures — R8 full mode can strip synthetic
# accessors that Retrofit resolves reflectively.
-keep,allowobfuscation interface * {
    @retrofit2.http.* <methods>;
}

# ── OkHttp ───────────────────────────────────────────────────────────
-keep class okhttp3.** { *; }
-keep interface okhttp3.** { *; }
-dontwarn okhttp3.**

# ── Kotlinx Serialization ────────────────────────────────────────────
# R8 full mode requires includedescriptorclasses to keep serializers.
-dontnote kotlinx.serialization.AnnotationsKt
-keepclassmembers class kotlinx.serialization.json.** {
    *** Companion;
}
-keepclasseswithmembers class kotlinx.serialization.json.** {
    kotlinx.serialization.KSerializer serializer(...);
}
-keep,includedescriptorclasses class com.rizzbot.v2.**$$serializer { *; }
-keepclassmembers class com.rizzbot.v2.** {
    *** Companion;
}
-keepclasseswithmembers class com.rizzbot.v2.** {
    kotlinx.serialization.KSerializer serializer(...);
}

# ── RevenueCat ───────────────────────────────────────────────────────
# RevenueCat uses reflection for its internal models and cache.
-keep class com.revenuecat.purchases.** { *; }
-dontwarn com.revenuecat.purchases.**

# ── Hilt / Dagger ────────────────────────────────────────────────────
# Hilt-generated components are already compiled via KSP, but keep the
# entry point annotations for R8 full mode.
-keep @dagger.hilt.android.AndroidEntryPoint class *
-keep @dagger.hilt.android.HiltAndroidApp class *
-keep @dagger.hilt.android.components.HiltComponent class *
-keep class dagger.hilt.** { *; }
-keep class javax.inject.** { *; }

# ── AndroidX Security / Tink ─────────────────────────────────────────
-keep class com.google.crypto.tink.** { *; }
-dontwarn com.google.crypto.tink.**

# ── Firebase ─────────────────────────────────────────────────────────
# Firebase uses @Keep internally; keep its model classes from being merged.
-keep class com.google.firebase.** { *; }
-dontwarn com.google.firebase.**
-keep class com.google.android.gms.** { *; }
-dontwarn com.google.android.gms.**

# ── Coil ─────────────────────────────────────────────────────────────
# Keep Coil's internal configuration objects used via reflection in singleton
# configuration merge.
-keep class coil.** { *; }

# ── General R8 full mode safety ──────────────────────────────────────
# Keep classes referenced from Compose (composable lambda classes are generated
# at compile time but their metadata is read reflectively by the compiler plugin).
-keep class * extends androidx.compose.runtime.Composable { *; }

# Keep Kotlin metadata on enum entries — R8 full mode optimizes enums by
# default, which breaks Enum.name / Enum.ordinal reflection.
-keepclassmembers enum * {
    public static **[] values();
    public static ** valueOf(java.lang.String);
}

# Keep Kotlin data-class componentN() methods used by destructuring.
-keepclassmembers class * {
    *** component1();
    *** component2();
    *** component3();
    *** component4();
    *** component5();
}
