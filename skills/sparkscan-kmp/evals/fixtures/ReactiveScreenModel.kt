package com.example.app.shared

import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.barcode.spark.SparkScan
import com.kmp.datacapture.barcode.spark.SparkScanSettings
import com.kmp.datacapture.barcode.spark.SparkScanViewSettings
import com.kmp.datacapture.core.capture.DataCaptureContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Shared (commonMain) screen model with the SparkScan mode already created,
 * but no scan-result handling wired up yet (no SparkScanListener, no Flow
 * collection).
 */
class ReactiveScreenModel {

    private val _scannedBarcodes = MutableStateFlow<List<String>>(emptyList())
    val scannedBarcodes: StateFlow<List<String>> = _scannedBarcodes.asStateFlow()

    val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val settings: SparkScanSettings = SparkScanSettings.sparkScanSettings().also {
        it.enableSymbologies(setOf(Symbology.EAN13_UPCA, Symbology.CODE128))
    }

    val sparkScan: SparkScan = SparkScan(settings)

    val sparkScanViewSettings: SparkScanViewSettings = SparkScanViewSettings.sparkScanViewSettings()

    fun dispose() {
        dataCaptureContext.removeMode(sparkScan)
    }
}
