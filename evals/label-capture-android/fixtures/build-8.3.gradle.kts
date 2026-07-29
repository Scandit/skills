plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    compileSdk = 34
    namespace = "com.example.app"

    defaultConfig {
        applicationId = "com.example.app"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }
}

dependencies {
    implementation("com.scandit.datacapture:core:8.3.1")
    implementation("com.scandit.datacapture:barcode:8.3.1")
    implementation("com.scandit.datacapture:label:8.3.1")
    implementation("com.scandit.datacapture:label-text-models:8.3.1")
}
