/*
 * A KMP shared screen model with MatrixScan Count (BarcodeCount) already
 * integrated: DataCaptureContext, BarcodeCountSettings, BarcodeCount, camera,
 * and a BarcodeCountListener aggregating scanned barcodes into a StateFlow.
 */

package com.example.kmpapp.count

import com.kmp.datacapture.barcode.count.BarcodeCount
import com.kmp.datacapture.barcode.count.BarcodeCountListener
import com.kmp.datacapture.barcode.count.BarcodeCountSession
import com.kmp.datacapture.barcode.count.BarcodeCountSettings
import com.kmp.datacapture.barcode.data.Barcode
import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.core.data.FrameData
import com.kmp.datacapture.core.source.Camera
import com.kmp.datacapture.core.source.FrameSourceState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

private const val LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --"

class CountScreenModel : BarcodeCountListener {

    val dataCaptureContext: DataCaptureContext = DataCaptureContext.forLicenseKey(LICENSE_KEY)

    val settings: BarcodeCountSettings = BarcodeCountSettings.barcodeCountSettings().also {
        it.enableSymbologies(
            setOf(
                Symbology.EAN13_UPCA,
                Symbology.EAN8,
                Symbology.CODE128,
            ),
        )
    }

    val barcodeCount: BarcodeCount = BarcodeCount.forContext(dataCaptureContext, settings)

    private val camera: Camera? =
        Camera.getDefaultCamera(BarcodeCount.createRecommendedCameraSettings())?.also {
            dataCaptureContext.setFrameSource(it)
        }

    private val _scannedBarcodes = MutableStateFlow<List<Barcode>>(emptyList())
    val scannedBarcodes: StateFlow<List<Barcode>> = _scannedBarcodes.asStateFlow()

    init {
        barcodeCount.addListener(this)
    }

    fun resumeFrameSource() {
        barcodeCount.isEnabled = true
        camera?.switchToDesiredState(FrameSourceState.ON)
    }

    fun pauseFrameSource() {
        camera?.switchToDesiredState(FrameSourceState.OFF)
    }

    override fun onScan(barcodeCount: BarcodeCount, session: BarcodeCountSession, frameData: FrameData) {
        _scannedBarcodes.value = _scannedBarcodes.value + session.recognizedBarcodes
    }

    fun resetSession() {
        barcodeCount.reset()
        _scannedBarcodes.value = emptyList()
    }

    fun dispose() {
        camera?.switchToDesiredState(FrameSourceState.OFF)
        barcodeCount.removeListener(this)
        dataCaptureContext.removeMode(barcodeCount)
    }
}
