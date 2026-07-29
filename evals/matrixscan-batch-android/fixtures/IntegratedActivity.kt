package com.example.myapp

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatch
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatchListener
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatchSession
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatchSettings
import com.scandit.datacapture.barcode.batch.data.TrackedBarcode
import com.scandit.datacapture.barcode.batch.ui.overlay.BarcodeBatchBasicOverlay
import com.scandit.datacapture.barcode.data.Symbology
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.data.FrameData
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.FrameSourceState
import com.scandit.datacapture.core.ui.DataCaptureView

class MainActivity : AppCompatActivity(), BarcodeBatchListener {

    private val dataCaptureContext =
        DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val camera = Camera.getDefaultCamera(BarcodeBatch.createRecommendedCameraSettings())

    private val barcodeBatch: BarcodeBatch

    init {
        dataCaptureContext.setFrameSource(camera)

        val settings = BarcodeBatchSettings().apply {
            enableSymbology(Symbology.EAN13_UPCA, true)
            enableSymbology(Symbology.CODE128, true)
        }

        barcodeBatch = BarcodeBatch.forDataCaptureContext(dataCaptureContext, settings)
        barcodeBatch.addListener(this)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val dataCaptureView = DataCaptureView.newInstance(this, dataCaptureContext)
        BarcodeBatchBasicOverlay.newInstance(barcodeBatch, dataCaptureView)
        setContentView(dataCaptureView)
    }

    override fun onResume() {
        super.onResume()
        barcodeBatch.isEnabled = true
        camera?.switchToDesiredState(FrameSourceState.ON)
    }

    override fun onPause() {
        barcodeBatch.isEnabled = false
        camera?.switchToDesiredState(FrameSourceState.OFF)
        super.onPause()
    }

    override fun onDestroy() {
        barcodeBatch.removeListener(this)
        dataCaptureContext.removeCurrentMode()
        super.onDestroy()
    }

    override fun onSessionUpdated(
        mode: BarcodeBatch,
        session: BarcodeBatchSession,
        data: FrameData
    ) {
        val added = session.addedTrackedBarcodes.map { it.barcode.data }
        runOnUiThread {
            for (barcodeData in added) {
            }
        }
    }

    override fun onObservationStarted(barcodeBatch: BarcodeBatch) {}
    override fun onObservationStopped(barcodeBatch: BarcodeBatch) {}
}
