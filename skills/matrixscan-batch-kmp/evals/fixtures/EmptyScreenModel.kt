package com.example.batchapp

// Shared (commonMain) screen model for the scanner screen. Nothing is wired up yet —
// MatrixScan Batch (BarcodeBatch) needs to be added here.
class ScannerScreenModel {

    fun onStarted() {
        // TODO: turn the camera on and enable tracking.
    }

    fun onStopped() {
        // TODO: turn the camera off and disable tracking.
    }

    fun dispose() {
        // TODO: tear down the SDK objects.
    }
}
