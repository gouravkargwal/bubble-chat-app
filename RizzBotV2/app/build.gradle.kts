plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.hilt.android)
    alias(libs.plugins.ksp)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.google.services)
    alias(libs.plugins.firebase.crashlytics.plugin)
}

import java.util.Properties

val keystorePropertiesFile = rootProject.file("keystore.properties")
val keystoreProperties = Properties()
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(keystorePropertiesFile.inputStream())
}

// Load local.properties for RevenueCat API key
val localPropertiesFile = rootProject.file("local.properties")
val localProperties = Properties()
if (localPropertiesFile.exists()) {
    localProperties.load(localPropertiesFile.inputStream())
}

android {
    namespace = "com.rizzbot.v2"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.cookd.mobile"
        minSdk = 26
        targetSdk = 35
        versionCode = 27
        versionName = "2.0.1"

        // Set via gradle.properties or Firebase Console → Authentication → Google
        buildConfigField("String", "GOOGLE_WEB_CLIENT_ID", "\"${project.findProperty("GOOGLE_WEB_CLIENT_ID") ?: ""}\"")
    }

    flavorDimensions += "environment"

    productFlavors {
        create("staging") {
            dimension = "environment"
            applicationIdSuffix = ".stg"
            resValue("string", "app_name", "Cookd (Staging)")
            // Same as production so shares point at the public listing; change if you publish a separate Play app id for staging.
            resValue(
                "string",
                "app_public_link",
                "https://play.google.com/store/apps/details?id=com.cookd.mobile"
            )
            buildConfigField("String", "BACKEND_URL", "\"https://nonconscientious-annette-saddeningly.ngrok-free.dev/\"")
            buildConfigField("String", "GOOGLE_WEB_CLIENT_ID", "\"226210127602-dc2jh362c0a2bcc2trdbd1da6qqnogvc.apps.googleusercontent.com\"")
            buildConfigField("String", "REVENUE_CAT_PUBLIC_KEY", "\"goog_qbaXLjSzKcIbBbYlEjNfLQzSoWn\"")
        }

        create("production") {
            dimension = "environment"
            // Production uses default app_name from strings.xml: "Cookd"
            resValue(
                "string",
                "app_public_link",
                "https://play.google.com/store/apps/details?id=com.cookd.mobile"
            )
            buildConfigField("String", "BACKEND_URL", "\"https://cookd.digidairy.site/\"")
            // Set in local.properties: GOOGLE_WEB_CLIENT_ID_PROD, REVENUE_CAT_PUBLIC_KEY_PROD (from production Firebase + RevenueCat)
            buildConfigField("String", "GOOGLE_WEB_CLIENT_ID", "\"${localProperties.getProperty("GOOGLE_WEB_CLIENT_ID_PROD") ?: ""}\"")
            buildConfigField("String", "REVENUE_CAT_PUBLIC_KEY", "\"${localProperties.getProperty("REVENUE_CAT_PUBLIC_KEY_PROD") ?: "REPLACE_WITH_PRODUCTION_KEY"}\"")
        }
    }

    signingConfigs {
        if (keystorePropertiesFile.exists() && keystoreProperties.containsKey("storeFile")) {
            create("release") {
                storeFile = file("../${keystoreProperties["storeFile"]}")
                storePassword = keystoreProperties["storePassword"] as? String
                keyAlias = keystoreProperties["keyAlias"] as? String
                keyPassword = keystoreProperties["keyPassword"] as? String
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            // Only apply signing config if keystore exists
            if (keystorePropertiesFile.exists() && keystoreProperties.containsKey("storeFile")) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    // Core
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)

    // Compose
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.ui.graphics)
    implementation(libs.compose.ui.tooling.preview)
    implementation(libs.compose.material3)
    implementation(libs.compose.material.icons)
    implementation(libs.compose.animation)
    implementation("androidx.compose.animation:animation-graphics:1.7.6")
    debugImplementation(libs.compose.ui.tooling)

    // Images
    implementation(libs.coil.compose)
    implementation(libs.exifinterface)

    // Lifecycle
    implementation(libs.lifecycle.runtime.ktx)
    implementation(libs.lifecycle.viewmodel.compose)
    implementation(libs.lifecycle.runtime.compose)

    // Navigation
    implementation(libs.navigation.compose)

    // Hilt
    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)
    implementation(libs.hilt.navigation.compose)

    // Network
    implementation(libs.retrofit)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    implementation(libs.retrofit.kotlinx.serialization)

    // Serialization
    implementation(libs.kotlinx.serialization.json)

    // DataStore
    implementation(libs.datastore.preferences)

    // Coroutines
    implementation(libs.coroutines.core)
    implementation(libs.coroutines.android)

    // Security
    implementation(libs.security.crypto)

    // Splash Screen
    implementation(libs.splash.screen)

    // In-App Update & Review
    implementation(libs.play.app.update)
    implementation(libs.play.app.update.ktx)
    implementation("com.google.android.play:review:2.0.1")

    // Firebase
    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.crashlytics)
    implementation(libs.firebase.analytics)
    implementation(libs.firebase.auth)

    // Google Sign-In (Credential Manager)
    implementation(libs.credentials)
    implementation(libs.credentials.play.services)
    implementation(libs.googleid)
    implementation("com.google.android.gms:play-services-auth:21.1.1")

    // RevenueCat
    // NOTE: Keep these versions in sync with a version that exists on Maven Central
    implementation("com.revenuecat.purchases:purchases:8.10.1")
}
