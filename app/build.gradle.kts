plugins {
    alias(libs.plugins.android.application)
    id("org.jetbrains.kotlin.android")  // Добавьте эту строку, если её нет
}

android {
    namespace = "com.example.sleepdetector"
    compileSdk = 35  // Измените с 34 на 35, если нужно

    defaultConfig {
        applicationId = "com.example.sleepdetector"
        minSdk = 26  // Важно: поднимите с 21/24 на 26 для 16KB поддержки
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        // Добавьте NDK версию для явной поддержки 16KB
        ndkVersion = "28.0.13004108"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.androidx.activity.ktx)

    // Добавьте CameraX
    implementation(libs.androidx.camera.core)
    implementation(libs.androidx.camera.camera2)
    implementation(libs.androidx.camera.lifecycle)
    implementation(libs.androidx.camera.view)

    // Добавьте MediaPipe
    implementation(libs.mediapipe.tasks.vision)

    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
}