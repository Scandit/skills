package com.example.myapp

import android.content.Context
import android.os.Bundle
import android.widget.FrameLayout
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.barcode.ar.capture.BarcodeAr
import com.scandit.datacapture.barcode.ar.capture.BarcodeArListener
import com.scandit.datacapture.barcode.ar.capture.BarcodeArSession
import com.scandit.datacapture.barcode.ar.capture.BarcodeArSettings
import com.scandit.datacapture.barcode.ar.ui.BarcodeArView
import com.scandit.datacapture.barcode.ar.ui.BarcodeArViewSettings
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArAnnotationProvider
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArInfoAnnotation
import com.scandit.datacapture.barcode.ar.ui.annotations.BarcodeArInfoAnnotationBodyComponent
import com.scandit.datacapture.barcode.ar.ui.highlight.BarcodeArHighlightProvider
import com.scandit.datacapture.barcode.ar.ui.highlight.BarcodeArRectangleHighlight
import com.scandit.datacapture.barcode.batch.data.TrackedBarcode
import com.scandit.datacapture.barcode.data.Barcode
import com.scandit.datacapture.barcode.data.Symbology
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.data.FrameData

class MainActivity : AppCompatActivity(), BarcodeArListener {

    private val dataCaptureContext =
        DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val barcodeAr: BarcodeAr
    private lateinit var barcodeArView: BarcodeArView

    init {
        val settings = BarcodeArSettings().apply {
            enableSymbology(Symbology.EAN13_UPCA, true)
            enableSymbology(Symbology.CODE128, true)
        }
        barcodeAr = BarcodeAr(dataCaptureContext, settings)
        barcodeAr.addListener(this)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = FrameLayout(this)
        setContentView(container)
        val viewSettings = BarcodeArViewSettings()
        barcodeArView = BarcodeArView(container, barcodeAr, dataCaptureContext, viewSettings)
        barcodeArView.highlightProvider = HighlightProvider()
        barcodeArView.annotationProvider = AnnotationProvider()
        barcodeArView.start()
    }

    override fun onResume() {
        super.onResume()
        barcodeArView.onResume()
    }

    override fun onPause() {
        super.onPause()
        barcodeArView.onPause()
    }

    override fun onDestroy() {
        super.onDestroy()
        barcodeAr.removeListener(this)
        barcodeArView.onDestroy()
    }

    override fun onSessionUpdated(
        barcodeAr: BarcodeAr,
        session: BarcodeArSession,
        frameData: FrameData
    ) {
        val added: List<TrackedBarcode> = session.addedTrackedBarcodes
        runOnUiThread {
            for (tracked in added) {
            }
        }
    }

    override fun onObservationStarted(barcodeAr: BarcodeAr) {}
    override fun onObservationStopped(barcodeAr: BarcodeAr) {}

    private inner class AnnotationProvider : BarcodeArAnnotationProvider {
        override fun annotationForBarcode(
            context: Context,
            barcode: Barcode,
            callback: BarcodeArAnnotationProvider.Callback
        ) {
            val annotation = BarcodeArInfoAnnotation(context, barcode).apply {
                body = listOf(
                    BarcodeArInfoAnnotationBodyComponent().apply {
                        text = barcode.data ?: ""
                    }
                )
            }
            callback.onData(annotation)
        }
    }

    private inner class HighlightProvider : BarcodeArHighlightProvider {
        override fun highlightForBarcode(
            context: Context,
            barcode: Barcode,
            callback: BarcodeArHighlightProvider.Callback
        ) {
            callback.onData(BarcodeArRectangleHighlight(context, barcode))
        }
    }
}
