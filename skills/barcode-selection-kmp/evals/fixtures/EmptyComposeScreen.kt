/*
 * Android (androidMain) Compose selection screen skeleton, no Scandit wiring
 * yet. Used for evals that ask for the Compose Multiplatform DataCaptureView
 * pattern (core-compose) rather than the imperative shared-ScreenModel one.
 */
package com.example.selection

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

@Composable
fun SelectionScreen() {
    Scaffold { padding ->
        Box(modifier = Modifier.fillMaxSize()) {
            // TODO: render the Scandit BarcodeSelection camera preview here
            // using the core-compose DataCaptureView composable.
        }
    }
}
