/*
 * Shared (commonMain) screen model with BarcodeCapture already integrated,
 * matching the canonical BarcodeCaptureSimpleSample structure. Used as the
 * starting point for evals that modify an existing integration (settings,
 * feedback, viewfinder, teardown, etc.) rather than building one from scratch.
 */
package com.example.scanner

import com.kmp.datacapture.barcode.capture.BarcodeCapture
import com.kmp.datacapture.barcode.capture.BarcodeCaptureListener
import com.kmp.datacapture.barcode.capture.BarcodeCaptureOverlay
import com.kmp.datacapture.barcode.capture.BarcodeCaptureSession
import com.kmp.datacapture.barcode.capture.BarcodeCaptureSettings
import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.core.data.FrameData
import com.kmp.datacapture.core.source.Camera
import com.kmp.datacapture.core.source.FrameSourceState
import com.kmp.datacapture.core.ui.DataCaptureView
import com.kmp.datacapture.core.ui.LogoStyle
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

internal const val LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --"

class ScannerScreenModel : BarcodeCaptureListener {

    private val _state = MutableStateFlow<ScannerUiState>(ScannerUiState.Scanning)
    val state: StateFlow<ScannerUiState> = _state.asStateFlow()

    val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize(LICENSE_KEY)

    private val camera: Camera? =
        Camera.getDefaultCamera(BarcodeCapture.createRecommendedCameraSettings())?.also {
            dataCaptureContext.setFrameSource(it)
        }

    private val settings: BarcodeCaptureSettings =
        BarcodeCaptureSettings.barcodeCaptureSettings().also {
            it.enableSymbology(Symbology.EAN13_UPCA, true)
            it.enableSymbology(Symbology.CODE128, true)
            it.enableSymbology(Symbology.QR, true)
        }

    val barcodeCapture: BarcodeCapture =
        BarcodeCapture.forContext(dataCaptureContext, settings).also {
            it.addListener(this)
        }

    fun setupDataCaptureView(view: DataCaptureView): DataCaptureView {
        view.logoStyle = LogoStyle.MINIMAL
        val overlay = BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view)
        view.addOverlay(overlay)
        return view
    }

    fun onEvent(event: ScannerEvent) {
        when (event) {
            ScannerEvent.STARTED -> {
                camera?.switchToDesiredState(FrameSourceState.ON)
                barcodeCapture.isEnabled = true
            }
            ScannerEvent.STOPPED -> {
                barcodeCapture.isEnabled = false
                camera?.switchToDesiredState(FrameSourceState.OFF)
            }
            ScannerEvent.DISMISS_RESULT -> {
                if (_state.value !is ScannerUiState.Scanning) {
                    _state.value = ScannerUiState.Scanning
                    barcodeCapture.isEnabled = true
                }
            }
        }
    }

    override fun onBarcodeScanned(
        barcodeCapture: BarcodeCapture,
        session: BarcodeCaptureSession,
        data: FrameData,
    ) {
        val barcode = session.newlyRecognizedBarcode ?: return
        barcodeCapture.isEnabled = false
        _state.value = ScannerUiState.Scanned(
            data = barcode.data ?: "",
            symbologyName = barcode.symbology.name,
        )
    }

    override fun onSessionUpdated(
        barcodeCapture: BarcodeCapture,
        session: BarcodeCaptureSession,
        data: FrameData,
    ) = Unit

    // NOTE: no dispose() function yet — some evals ask for proper teardown to be added.
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
