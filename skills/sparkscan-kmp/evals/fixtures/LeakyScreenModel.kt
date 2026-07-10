package com.example.app.shared

import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.barcode.spark.SparkScan
import com.kmp.datacapture.barcode.spark.SparkScanListener
import com.kmp.datacapture.barcode.spark.SparkScanSession
import com.kmp.datacapture.barcode.spark.SparkScanSettings
import com.kmp.datacapture.barcode.spark.SparkScanViewSettings
import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.core.data.FrameData
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Shared (commonMain) screen model with a working SparkScan integration, but
 * no teardown: nothing removes the listener or detaches the mode from the
 * DataCaptureContext when the screen goes away.
 */
class LeakyScreenModel : SparkScanListener {

    private val _scannedBarcodes = MutableStateFlow<List<String>>(emptyList())
    val scannedBarcodes: StateFlow<List<String>> = _scannedBarcodes.asStateFlow()

    val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val settings: SparkScanSettings = SparkScanSettings.sparkScanSettings().also {
        it.enableSymbologies(setOf(Symbology.EAN13_UPCA, Symbology.CODE128))
    }

    val sparkScan: SparkScan = SparkScan(settings).also {
        it.addListener(this)
    }

    val sparkScanViewSettings: SparkScanViewSettings = SparkScanViewSettings.sparkScanViewSettings()

    override fun onBarcodeScanned(
        sparkScan: SparkScan,
        session: SparkScanSession,
        frameData: FrameData,
    ) {
        val barcode = session.newlyRecognizedBarcode ?: return
        val data = barcode.data ?: return
        _scannedBarcodes.value = _scannedBarcodes.value + data
    }

    override fun onSessionUpdated(
        sparkScan: SparkScan,
        session: SparkScanSession,
        frameData: FrameData,
    ) = Unit
}
