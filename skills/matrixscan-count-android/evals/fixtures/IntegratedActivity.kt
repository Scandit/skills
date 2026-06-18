package com.example.myapp

import android.os.Bundle
import android.widget.FrameLayout
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.barcode.count.capture.BarcodeCount
import com.scandit.datacapture.barcode.count.capture.BarcodeCountListener
import com.scandit.datacapture.barcode.count.capture.BarcodeCountSession
import com.scandit.datacapture.barcode.count.capture.BarcodeCountSessionSnapshot
import com.scandit.datacapture.barcode.count.capture.BarcodeCountSettings
import com.scandit.datacapture.barcode.count.ui.view.BarcodeCountView
import com.scandit.datacapture.barcode.count.ui.view.BarcodeCountViewUiListener
import com.scandit.datacapture.barcode.data.Barcode
import com.scandit.datacapture.barcode.data.Symbology
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.data.FrameData
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.FrameSourceState

class CountActivity : AppCompatActivity(), BarcodeCountListener, BarcodeCountViewUiListener {

    private val dataCaptureContext =
        DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private var camera: Camera? = null
    private lateinit var barcodeCount: BarcodeCount
    private lateinit var barcodeCountView: BarcodeCountView

    private var allRecognizedBarcodes: List<Barcode> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setupRecognition()
    }

    private fun setupRecognition() {
        val cameraSettings = BarcodeCount.createRecommendedCameraSettings()
        camera = Camera.getDefaultCamera(cameraSettings)
        dataCaptureContext.setFrameSource(camera)

        val settings = BarcodeCountSettings()
        settings.enableSymbologies(
            setOf(
                Symbology.EAN13_UPCA,
                Symbology.EAN8,
                Symbology.UPCE,
                Symbology.CODE128,
                Symbology.CODE39
            )
        )

        barcodeCount = BarcodeCount.forDataCaptureContext(dataCaptureContext, settings)
        barcodeCount.addListener(this)

        val container = FrameLayout(this)
        setContentView(container)
        barcodeCountView = BarcodeCountView.newInstance(this, dataCaptureContext, barcodeCount)
        container.addView(barcodeCountView)
        barcodeCountView.uiListener = this
    }

    override fun onResume() {
        super.onResume()
        camera?.switchToDesiredState(FrameSourceState.ON)
    }

    override fun onPause() {
        super.onPause()
        camera?.switchToDesiredState(FrameSourceState.OFF)
    }

    override fun onDestroy() {
        super.onDestroy()
        barcodeCount.removeListener(this)
    }

    override fun onScan(
        barcodeCount: BarcodeCount,
        session: BarcodeCountSession,
        data: FrameData
    ) {
        val recognizedBarcodes = session.recognizedBarcodes
        runOnUiThread {
            allRecognizedBarcodes = recognizedBarcodes
        }
    }

    override fun onListButtonTapped(view: BarcodeCountView, snapshot: BarcodeCountSessionSnapshot?) {
        // Present the current progress, e.g. from snapshot?.recognizedBarcodes.
    }

    override fun onExitButtonTapped(view: BarcodeCountView, snapshot: BarcodeCountSessionSnapshot?) {
        // Present a summary, e.g. from snapshot?.recognizedBarcodes.
    }
}
