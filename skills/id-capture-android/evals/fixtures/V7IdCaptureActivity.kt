package com.example.myapp

import android.app.AlertDialog
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.FrameSourceState
import com.scandit.datacapture.core.ui.DataCaptureView
import com.scandit.datacapture.id.capture.*
import com.scandit.datacapture.id.data.*
import com.scandit.datacapture.id.ui.overlay.IdCaptureOverlay

// v7-era ID Capture integration. Uses the v7 document-based callbacks (already modern),
// but assigns the scanner via the v7 `scannerType` property — replaced by `scanner =
// IdCaptureScanner(...)` in v8.
class IdCaptureActivity : AppCompatActivity(), IdCaptureListener {

    private val dataCaptureContext =
        DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val camera = Camera.getDefaultCamera(IdCapture.createRecommendedCameraSettings())

    private val idCapture: IdCapture

    init {
        dataCaptureContext.setFrameSource(camera)

        val settings = IdCaptureSettings().apply {
            acceptedDocuments = listOf(
                IdCard(IdCaptureRegion.ANY),
                DriverLicense(IdCaptureRegion.ANY),
                Passport(IdCaptureRegion.ANY),
            )
            scannerType = FullDocumentScanner()
        }

        idCapture = IdCapture.forDataCaptureContext(dataCaptureContext, settings)
        idCapture.addListener(this)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val dataCaptureView = DataCaptureView.newInstance(this, dataCaptureContext)
        IdCaptureOverlay.newInstance(idCapture, dataCaptureView)
        setContentView(dataCaptureView)
    }

    override fun onResume() {
        super.onResume()
        idCapture.isEnabled = true
        camera?.switchToDesiredState(FrameSourceState.ON)
    }

    override fun onPause() {
        idCapture.isEnabled = false
        camera?.switchToDesiredState(FrameSourceState.OFF)
        super.onPause()
    }

    override fun onDestroy() {
        idCapture.removeListener(this)
        dataCaptureContext.removeCurrentMode()
        super.onDestroy()
    }

    override fun onIdCaptured(mode: IdCapture, id: CapturedId) {
        mode.isEnabled = false
        runOnUiThread {
            AlertDialog.Builder(this)
                .setTitle("Recognized")
                .setMessage(id.fullName)
                .setPositiveButton("OK") { _, _ -> mode.isEnabled = true }
                .show()
        }
    }

    override fun onIdRejected(mode: IdCapture, id: CapturedId?, reason: RejectionReason) {
        mode.isEnabled = false
        runOnUiThread {
            AlertDialog.Builder(this)
                .setTitle("Rejected")
                .setMessage("Document not supported")
                .setPositiveButton("OK") { _, _ -> idCapture.isEnabled = true }
                .show()
        }
    }
}
