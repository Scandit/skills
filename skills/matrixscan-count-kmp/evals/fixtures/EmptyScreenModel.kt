/*
 * Starter file for a KMP shared screen model. No Scandit code yet.
 */

package com.example.kmpapp.count

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class CountScreenModel {

    private val _scannedCount = MutableStateFlow(0)
    val scannedCount: StateFlow<Int> = _scannedCount.asStateFlow()

    fun dispose() {
        // TODO: tear down resources
    }
}
