package com.example.myapp.shared

import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.core.source.Camera
import com.kmp.datacapture.core.source.FrameSourceState
import com.kmp.datacapture.core.ui.DataCaptureView
import com.kmp.datacapture.core.ui.LogoStyle
import com.kmp.datacapture.id.capture.IdCapture
import com.kmp.datacapture.id.capture.IdCaptureFeedback
import com.kmp.datacapture.id.capture.IdCaptureListener
import com.kmp.datacapture.id.capture.IdCaptureSettings
import com.kmp.datacapture.id.capture.IdCaptureSettings.Companion.idCaptureSettings
import com.kmp.datacapture.id.data.CapturedId
import com.kmp.datacapture.id.data.DriverLicense
import com.kmp.datacapture.id.data.IdCard
import com.kmp.datacapture.id.data.IdCaptureRegion
import com.kmp.datacapture.id.data.Passport
import com.kmp.datacapture.id.scanner.FullDocumentScanner
import com.kmp.datacapture.id.scanner.RejectionReason
import com.kmp.datacapture.id.capture.IdCaptureOverlay

class IdScannerScreenModel : IdCaptureListener {

    val dataCaptureContext: DataCaptureContext by lazy {
        DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
    }

    private val camera: Camera? =
        Camera.getDefaultCamera(IdCapture.createRecommendedCameraSettings())?.also {
            dataCaptureContext.setFrameSource(it)
        }

    private val settings: IdCaptureSettings =
        IdCaptureSettings.idCaptureSettings().apply {
            scannerType = FullDocumentScanner()
            acceptedDocuments = listOf(
                IdCard(IdCaptureRegion.ANY),
                DriverLicense(IdCaptureRegion.ANY),
                Passport(IdCaptureRegion.ANY),
            )
        }

    val idCapture: IdCapture =
        IdCapture.forContext(dataCaptureContext, settings).also {
            it.addListener(this)
            it.feedback = IdCaptureFeedback.defaultFeedback()
        }

    fun setupDataCaptureView(view: DataCaptureView): DataCaptureView {
        view.logoStyle = LogoStyle.MINIMAL
        view.addOverlay(IdCaptureOverlay.withIdCaptureForView(idCapture, view))
        return view
    }

    fun onStarted() {
        camera?.switchToDesiredState(FrameSourceState.ON)
        idCapture.isEnabled = true
    }

    fun onStopped() {
        idCapture.isEnabled = false
        camera?.switchToDesiredState(FrameSourceState.OFF)
    }

    override fun onIdCaptured(mode: IdCapture, id: CapturedId) {
        mode.isEnabled = false
        val message = listOfNotNull(id.fullName, id.documentNumber).joinToString("\n")
        // publish `message` to shared UI state
    }

    override fun onIdRejected(mode: IdCapture, id: CapturedId?, reason: RejectionReason) {
        mode.isEnabled = false
        val message = if (reason == RejectionReason.TIMEOUT) {
            "Capture timed out. Try again."
        } else {
            "Document not supported."
        }
        // publish `message` to shared UI state
    }

    fun dispose() {
        idCapture.isEnabled = false
        idCapture.removeListener(this)
        dataCaptureContext.removeMode(idCapture)
        camera?.switchToDesiredState(FrameSourceState.OFF)
    }
}
