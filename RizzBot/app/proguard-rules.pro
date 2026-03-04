# Retrofit
-keepattributes Signature
-keepattributes *Annotation*
-keep class com.rizzbot.app.data.remote.dto.** { *; }
-keepclassmembers class com.rizzbot.app.data.remote.dto.** { *; }

# Room
-keep class com.rizzbot.app.data.local.db.entity.** { *; }

# Kotlinx Serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKt
-keepclassmembers class kotlinx.serialization.json.** {
    *** Companion;
}
-keepclasseswithmembers class kotlinx.serialization.json.** {
    kotlinx.serialization.KSerializer serializer(...);
}
-keep,includedescriptorclasses class com.rizzbot.app.**$$serializer { *; }
-keepclassmembers class com.rizzbot.app.** {
    *** Companion;
}
-keepclasseswithmembers class com.rizzbot.app.** {
    kotlinx.serialization.KSerializer serializer(...);
}

# Coroutines
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}

# OkHttp
-dontwarn okhttp3.**
-dontwarn okio.**
