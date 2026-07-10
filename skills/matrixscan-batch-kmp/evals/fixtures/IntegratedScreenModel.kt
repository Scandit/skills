package com.example.batchapp

import com.kmp.datacapture.barcode.batch.BarcodeBatch
import com.kmp.datacapture.barcode.batch.BarcodeBatchBasicOverlay
import com.kmp.datacapture.barcode.batch.BarcodeBatchListener
import com.kmp.datacapture.barcode.batch.BarcodeBatchSession
import com.kmp.datacapture.barcode.batch.BarcodeBatchSettings
import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.core.data.FrameData
import com.kmp.datacapture.core.source.Camera
import com.kmp.datacapture.core.source.FrameSourceState
import com.kmp.datacapture.core.ui.DataCaptureView

// Shared (commonMain) screen model already wired up for basic MatrixScan Batch tracking:
// context, camera, mode, settings, a basic overlay, and a listener. Platform hosts
// (Android Activity/Compose, iOS SwiftUI) call setupDataCaptureView / onStarted / onStopped
// / dispose from their own lifecycle hooks.
class ScannerScreenModel : BarcodeBatchListener {

    val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val camera: Camera? =
        Camera.getDefaultCamera(BarcodeBatch.createRecommendedCameraSettings())?.also {
            dataCaptureContext.setFrameSource(it)
        }

    private val settings: BarcodeBatchSettings =
        BarcodeBatchSettings.barcodeBatchSettings().apply {
            enableSymbology(Symbology.EAN13_UPCA, true)
            enableSymbology(Symbology.CODE128, true)
        }

    val barcodeBatch: BarcodeBatch =
        BarcodeBatch.forContext(dataCaptureContext, settings).also {
            it.addListener(this)
        }

    private var dataCaptureView: DataCaptureView? = null
    private var basicOverlay: BarcodeBatchBasicOverlay? = null

    fun setupDataCaptureView(view: DataCaptureView): DataCaptureView {
        dataCaptureView = view
        val overlay = BarcodeBatchBasicOverlay.withBarcodeBatchForView(barcodeBatch, view)
        view.addOverlay(overlay)
        basicOverlay = overlay
        return view
    }

    fun onStarted() {
        camera?.switchToDesiredState(FrameSourceState.ON)
        barcodeBatch.isEnabled = true
    }

    fun onStopped() {
        barcodeBatch.isEnabled = false
        camera?.switchToDesiredState(FrameSourceState.OFF)
    }

    override fun onSessionUpdated(
        barcodeBatch: BarcodeBatch,
        session: BarcodeBatchSession,
        frameData: FrameData,
    ) {
        // Session deltas are handled here.
    }

    override fun onObservationStarted(barcodeBatch: BarcodeBatch) {}
    override fun onObservationStopped(barcodeBatch: BarcodeBatch) {}

    fun dispose() {
        barcodeBatch.isEnabled = false
        barcodeBatch.removeListener(this)
        dataCaptureContext.removeMode(barcodeBatch)
        camera?.switchToDesiredState(FrameSourceState.OFF)
    }
}
