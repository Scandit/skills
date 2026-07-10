/*
 * Shared (commonMain) screen model skeleton for a KMP barcode-selection
 * screen. Platform hosts (Android Compose, iOS SwiftUI) collect [state] and
 * forward lifecycle events through [onEvent]. No Scandit SDK code has been
 * wired up yet — this is the starting point before BarcodeSelection is added.
 */
package com.example.selection

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class SelectionScreenModel {

    private val _state = MutableStateFlow(SelectionUiState())
    val state: StateFlow<SelectionUiState> = _state.asStateFlow()

    fun onEvent(event: SelectionEvent) {
        // TODO: wire up Scandit BarcodeSelection start/stop here.
    }

    fun dispose() {
        // TODO: tear down Scandit SDK resources here.
    }
}

data class SelectionUiState(
    val lastSelectionData: String = "",
    val lastSelectionCount: Int = 0,
)

enum class SelectionEvent { STARTED, STOPPED }
