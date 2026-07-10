/*
 * Shared (commonMain) screen model skeleton for a KMP scanner screen.
 * Platform hosts (Android Compose, iOS SwiftUI) collect [state] and forward
 * lifecycle events through [onEvent]. No Scandit SDK code has been wired up
 * yet — this is the starting point before BarcodeCapture is added.
 */
package com.example.scanner

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class ScannerScreenModel {

    private val _state = MutableStateFlow<ScannerUiState>(ScannerUiState.Scanning)
    val state: StateFlow<ScannerUiState> = _state.asStateFlow()

    fun onEvent(event: ScannerEvent) {
        // TODO: wire up Scandit BarcodeCapture start/stop here.
    }

    fun dispose() {
        // TODO: tear down Scandit SDK resources here.
    }
}

sealed interface ScannerUiState {
    data object Scanning : ScannerUiState
    data class Scanned(val data: String, val symbologyName: String) : ScannerUiState
}

enum class ScannerEvent {
    STARTED,
    STOPPED,
    DISMISS_RESULT,
}
