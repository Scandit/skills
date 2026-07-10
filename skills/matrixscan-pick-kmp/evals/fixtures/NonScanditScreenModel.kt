/*
 * Sample-app screen model scaffold — no Scandit APIs wired up yet.
 */
package com.example.picking

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

sealed interface PickingUiState {
    data object Idle : PickingUiState
}

class PickingScreenModel {

    private val _state = MutableStateFlow<PickingUiState>(PickingUiState.Idle)
    val state: StateFlow<PickingUiState> = _state.asStateFlow()

    fun onScreenShown() {
        // TODO: wire up scanning
    }

    fun onScreenHidden() {
        // TODO: tear down scanning
    }
}
