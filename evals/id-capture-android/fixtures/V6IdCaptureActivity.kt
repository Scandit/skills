package com.example.myapp

import android.app.AlertDialog
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.data.FrameData
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.FrameSourceState
import com.scandit.datacapture.core.ui.DataCaptureView
import com.scandit.datacapture.id.capture.*
import com.scandit.datacapture.id.data.*
import com.scandit.datacapture.id.ui.overlay.IdCaptureOverlay
import java.util.EnumSet

// v6-era ID Capture integration. Uses the supportedDocuments bitmask, supportedSides,
// and the session/frameData listener callbacks — all removed in v7+.
class IdCaptureActivity : AppCompatActivity(), IdCaptureListener {

    private val dataCaptureContext =
        DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val camera = Camera.getDefaultCamera(IdCapture.createRecommendedCameraSettings())

    private val idCapture: IdCapture

    init {
        dataCaptureContext.setFrameSource(camera)

        val settings = IdCaptureSettings().apply {
            supportedDocuments = EnumSet.of(
                IdDocumentType.ID_CARD_VIZ,
                IdDocumentType.DL_VIZ,
                IdDocumentType.PASSPORT_MRZ,
            )
            supportedSides = SupportedSides.FRONT_AND_BACK
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

    // v6 session-based callbacks — fire per recognized zone.
    override fun onIdCaptured(idCapture: IdCapture, session: IdCaptureSession, frameData: FrameData) {
        val capturedId = session.newlyCapturedId ?: return
        idCapture.isEnabled = false
        runOnUiThread {
            AlertDialog.Builder(this)
                .setTitle("Recognized")
                .setMessage(capturedId.fullName)
                .setPositiveButton("OK") { _, _ -> idCapture.isEnabled = true }
                .show()
        }
    }

    override fun onIdLocalized(idCapture: IdCapture, session: IdCaptureSession, frameData: FrameData) {}

    override fun onIdRejected(idCapture: IdCapture, session: IdCaptureSession, frameData: FrameData) {
        idCapture.isEnabled = false
        runOnUiThread {
            AlertDialog.Builder(this)
                .setTitle("Rejected")
                .setMessage("Document not supported")
                .setPositiveButton("OK") { _, _ -> idCapture.isEnabled = true }
                .show()
        }
    }

    override fun onObservationStarted(idCapture: IdCapture) {}

    override fun onObservationStopped(idCapture: IdCapture) {}
}
