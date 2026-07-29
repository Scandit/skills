package com.example.app

import android.os.Bundle
import android.view.ViewGroup
import android.widget.FrameLayout
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.barcode.data.Symbology
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.FrameSourceState
import com.scandit.datacapture.core.ui.DataCaptureView
import com.scandit.datacapture.label.capture.LabelCapture
import com.scandit.datacapture.label.capture.LabelCaptureSettings
import com.scandit.datacapture.label.data.LabelField
import com.scandit.datacapture.label.ui.overlay.validation.LabelCaptureValidationFlowListener
import com.scandit.datacapture.label.ui.overlay.validation.LabelCaptureValidationFlowOverlay
import com.scandit.datacapture.label.ui.overlay.validation.LabelCaptureValidationFlowSettings

class ScanActivity : AppCompatActivity() {

    private lateinit var dataCaptureContext: DataCaptureContext
    private lateinit var labelCapture: LabelCapture
    private lateinit var camera: Camera
    private lateinit var validationFlowOverlay: LabelCaptureValidationFlowOverlay

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_scan)

        dataCaptureContext = DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

        val settings = LabelCaptureSettings.builder()
            .addLabel()
                .addCustomBarcode()
                    .setSymbologies(Symbology.EAN13_UPCA)
                .buildFluent("barcode")
                .addExpiryDateText()
                .buildFluent("expiry-date")
            .buildFluent("perishable-product")
            .build()

        labelCapture = LabelCapture.forDataCaptureContext(dataCaptureContext, settings)

        val dataCaptureView = DataCaptureView.newInstance(this, dataCaptureContext)
        val container = findViewById<FrameLayout>(R.id.data_capture_container)
        container.addView(
            dataCaptureView,
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT,
        )

        val validationFlowSettings = LabelCaptureValidationFlowSettings.newInstance()
        validationFlowSettings.setPlaceholderTextForLabelDefinition("expiry-date", "MM/DD/YYYY")

        validationFlowOverlay = LabelCaptureValidationFlowOverlay.newInstance(
            this,
            labelCapture,
            dataCaptureView,
        )
        validationFlowOverlay.applySettings(validationFlowSettings)
        validationFlowOverlay.listener = object : LabelCaptureValidationFlowListener {
            override fun onValidationFlowLabelCaptured(fields: List<LabelField>) {
                val barcodeData = fields.find { it.name == "barcode" }?.barcode?.data
                val expiryDate = fields.find { it.name == "expiry-date" }?.asDate()
                runOnUiThread {
                    // Handle results
                }
            }
        }

        camera = Camera.getDefaultCamera(LabelCapture.createRecommendedCameraSettings())
            ?: throw IllegalStateException("Failed to init camera!")
        dataCaptureContext.setFrameSource(camera)
    }

    override fun onResume() {
        super.onResume()
        camera.switchToDesiredState(FrameSourceState.ON)
        validationFlowOverlay.onResume()
    }

    override fun onPause() {
        super.onPause()
        camera.switchToDesiredState(FrameSourceState.OFF)
        validationFlowOverlay.onPause()
    }
}
