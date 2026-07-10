/*
 * Android (androidMain) Compose scanner screen skeleton, no Scandit wiring
 * yet. Used for evals that ask for the Compose Multiplatform DataCaptureView
 * pattern (core-compose) rather than the imperative shared-ScreenModel one.
 */
package com.example.scanner

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

@Composable
fun ScannerScreen() {
    Scaffold { padding ->
        Box(modifier = Modifier.fillMaxSize()) {
            // TODO: render the Scandit BarcodeCapture camera preview here
            // using the core-compose DataCaptureView composable.
        }
    }
}
