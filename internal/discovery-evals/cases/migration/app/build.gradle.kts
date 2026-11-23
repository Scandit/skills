plugins { id("com.android.application") }

android { namespace = "com.example.myapp" }

dependencies {
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.scandit.datacapture:core:7.6.0")
    implementation("com.scandit.datacapture:barcode:7.6.0")
}
