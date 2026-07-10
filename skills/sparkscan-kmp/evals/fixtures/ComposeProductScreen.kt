package com.example.app.shared

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

/**
 * Plain Compose Multiplatform screen (no scanning yet). Shared verbatim
 * between the Android and iOS Compose Multiplatform UI.
 */
@Composable
fun ProductListScreen() {
    Column(modifier = Modifier.fillMaxSize()) {
        Text("Scan a product barcode")
    }
}
