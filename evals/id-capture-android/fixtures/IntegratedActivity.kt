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
            scanner = IdCaptureScanner(FullDocumentScanner())
        }

        idCapture = IdCapture.forDataCaptureContext(dataCaptureContext, settings)
        idCapture.addListener(this)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val dataCaptureView = DataCaptureView.newInstance(this, dataCaptureContext)
        IdCaptureOverlay.newInstance(idCapture, dataCaptureView)
        setContentView(dataCaptureView)
        // Request CAMERA permission here before scanning starts.
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
        val message = descriptionFor(id)
        runOnUiThread {
            showResultDialog("Recognized Document", message)
        }
    }

    override fun onIdRejected(mode: IdCapture, id: CapturedId?, reason: RejectionReason) {
        mode.isEnabled = false
        val message = if (reason == RejectionReason.TIMEOUT) {
            "Document capture failed. Make sure the document is well lit and free of glare."
        } else {
            "Document not supported. Try scanning another document."
        }
        runOnUiThread {
            showResultDialog("Rejected", message)
        }
    }

    private fun showResultDialog(title: String, message: String) {
        AlertDialog.Builder(this)
            .setTitle(title)
            .setMessage(message)
            .setPositiveButton("OK") { _, _ -> idCapture.isEnabled = true }
            .setOnCancelListener { idCapture.isEnabled = true }
            .show()
    }

    private fun descriptionFor(capturedId: CapturedId): String {
        val parts = mutableListOf<String>()
        capturedId.fullName?.let { parts.add("Name: $it") }
        capturedId.dateOfBirth?.let { parts.add("DOB: ${it.day}/${it.month}/${it.year}") }
        capturedId.dateOfExpiry?.let { parts.add("Expiry: ${it.day}/${it.month}/${it.year}") }
        capturedId.documentNumber?.let { parts.add("Doc #: $it") }
        capturedId.nationality?.let { parts.add("Nationality: $it") }
        capturedId.document?.documentType?.let { parts.add("Type: $it") }
        return parts.joinToString("\n")
    }
}
