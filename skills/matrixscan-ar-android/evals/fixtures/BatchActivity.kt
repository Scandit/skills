package com.example.myapp

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatch
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatchListener
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatchSession
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatchSettings
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

    private lateinit var camera: Camera
    private lateinit var barcodeBatch: BarcodeBatch
    private lateinit var dataCaptureView: DataCaptureView
    private lateinit var overlay: BarcodeBatchBasicOverlay

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        camera = Camera.getDefaultCamera()!!
        dataCaptureContext.setFrameSource(camera)

        val settings = BarcodeBatchSettings().apply {
            enableSymbology(Symbology.EAN13_UPCA, true)
            enableSymbology(Symbology.CODE128, true)
        }
        barcodeBatch = BarcodeBatch.forDataCaptureContext(dataCaptureContext, settings)
        barcodeBatch.addListener(this)

        dataCaptureView = DataCaptureView.newInstance(this, dataCaptureContext)
        setContentView(dataCaptureView)
        overlay = BarcodeBatchBasicOverlay.newInstance(barcodeBatch, dataCaptureView)
    }

    override fun onResume() {
        super.onResume()
        camera.switchToDesiredState(FrameSourceState.ON)
    }

    override fun onPause() {
        super.onPause()
        camera.switchToDesiredState(FrameSourceState.OFF)
    }

    override fun onDestroy() {
        super.onDestroy()
        barcodeBatch.removeListener(this)
    }

    override fun onSessionUpdated(
        mode: BarcodeBatch,
        session: BarcodeBatchSession,
        data: FrameData
    ) {
        // Handle tracked barcodes.
    }

    override fun onObservationStarted(mode: BarcodeBatch) {}
    override fun onObservationStopped(mode: BarcodeBatch) {}
}
