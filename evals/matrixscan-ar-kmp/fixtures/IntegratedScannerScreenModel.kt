package com.example.myapp

import com.kmp.datacapture.barcode.ar.BarcodeAr
import com.kmp.datacapture.barcode.ar.BarcodeArHighlight
import com.kmp.datacapture.barcode.ar.BarcodeArHighlightProvider
import com.kmp.datacapture.barcode.ar.BarcodeArListener
import com.kmp.datacapture.barcode.ar.BarcodeArRectangleHighlight
import com.kmp.datacapture.barcode.ar.BarcodeArSession
import com.kmp.datacapture.barcode.ar.BarcodeArSettings
import com.kmp.datacapture.barcode.ar.BarcodeArView
import com.kmp.datacapture.barcode.data.Barcode
import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.core.data.FrameData

// Shared (commonMain) screen model. Owns all Scandit SDK wiring; the Android/iOS hosts only
// construct the platform-native BarcodeArView and forward lifecycle events to this class.
class ScannerScreenModel : BarcodeArHighlightProvider, BarcodeArListener {

    val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val settings: BarcodeArSettings = BarcodeArSettings.barcodeArSettings().apply {
        enableSymbology(Symbology.EAN13_UPCA, true)
        enableSymbology(Symbology.CODE128, true)
    }

    val barcodeAr: BarcodeAr = BarcodeAr.forContext(dataCaptureContext, settings).also {
        it.addListener(this)
    }

    private var view: BarcodeArView? = null

    /** Registers an already-constructed [BarcodeArView] (built platform-side), wires the
     * highlight provider, and starts scanning. */
    fun registerView(view: BarcodeArView): BarcodeArView {
        this.view = view
        view.highlightProvider = this
        view.start()
        return view
    }

    fun onResume() { view?.start() }
    fun onPause() { view?.pause() }

    fun dispose() {
        view?.stop()
        view = null
        barcodeAr.removeListener(this)
    }

    override fun highlightForBarcode(barcode: Barcode, callback: (BarcodeArHighlight?) -> Unit) {
        callback(BarcodeArRectangleHighlight(barcode))
    }

    override fun onSessionUpdated(
        barcodeAr: BarcodeAr,
        session: BarcodeArSession,
        frameData: FrameData
    ) {
        val added = session.addedTrackedBarcodes
        for (tracked in added) {
            // tracked.barcode.data, tracked.barcode.symbology
        }
    }
}
