package com.example.myapp

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.barcode.capture.*
import com.scandit.datacapture.barcode.data.Symbology
import com.scandit.datacapture.barcode.ui.overlay.BarcodeCaptureOverlay
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.data.FrameData
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.CameraSettings
import com.scandit.datacapture.core.source.FrameSourceState
import com.scandit.datacapture.core.source.VideoResolution
import com.scandit.datacapture.core.ui.DataCaptureView

class MainActivity : AppCompatActivity(), BarcodeCaptureListener {

    private val dataCaptureContext =
        DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val camera: Camera?

    private val barcodeCapture: BarcodeCapture

    init {
        // v6-style camera setup: manual CameraSettings with VideoResolution.AUTO
        val cameraSettings = CameraSettings()
        cameraSettings.preferredResolution = VideoResolution.AUTO
        camera = Camera.getDefaultCamera()
        camera?.applySettings(cameraSettings)
        dataCaptureContext.setFrameSource(camera)

        val settings = BarcodeCaptureSettings().apply {
            enableSymbology(Symbology.EAN13_UPCA, true)
            enableSymbology(Symbology.CODE128, true)
        }

        barcodeCapture = BarcodeCapture.forDataCaptureContext(dataCaptureContext, settings)
        barcodeCapture.addListener(this)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val dataCaptureView = DataCaptureView.newInstance(this, dataCaptureContext)
        BarcodeCaptureOverlay.newInstance(barcodeCapture, dataCaptureView)
        setContentView(dataCaptureView)
    }

    override fun onResume() {
        super.onResume()
        barcodeCapture.isEnabled = true
        camera?.switchToDesiredState(FrameSourceState.ON)
    }

    override fun onPause() {
        barcodeCapture.isEnabled = false
        camera?.switchToDesiredState(FrameSourceState.OFF)
        super.onPause()
    }

    override fun onDestroy() {
        barcodeCapture.removeListener(this)
        dataCaptureContext.removeCurrentMode()
        super.onDestroy()
    }

    override fun onBarcodeScanned(
        barcodeCapture: BarcodeCapture,
        session: BarcodeCaptureSession,
        data: FrameData
    ) {
        val barcode = session.newlyRecognizedBarcode ?: return
        barcodeCapture.isEnabled = false
        runOnUiThread {
            // handle barcode.data and barcode.symbology
        }
    }

    override fun onSessionUpdated(barcodeCapture: BarcodeCapture, session: BarcodeCaptureSession, data: FrameData) {}
    override fun onObservationStarted(barcodeCapture: BarcodeCapture) {}
    override fun onObservationStopped(barcodeCapture: BarcodeCapture) {}
}
