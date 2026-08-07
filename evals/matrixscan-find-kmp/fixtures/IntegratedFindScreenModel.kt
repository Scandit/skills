/*
 * Sample shared (commonMain) KMP screen model, with a minimal MatrixScan Find
 * integration already in place: a DataCaptureContext, a BarcodeFind mode with
 * default settings, and a no-op listener. Extend it for item list, transformer,
 * and feedback changes.
 */

package com.example.kmpapp.shared

import com.kmp.datacapture.barcode.find.BarcodeFind
import com.kmp.datacapture.barcode.find.BarcodeFindItem
import com.kmp.datacapture.barcode.find.BarcodeFindListener
import com.kmp.datacapture.barcode.find.BarcodeFindSettings
import com.kmp.datacapture.barcode.find.BarcodeFindViewSettings
import com.kmp.datacapture.core.capture.DataCaptureContext

class FindScreenModel : BarcodeFindListener {

    val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val settings: BarcodeFindSettings = BarcodeFindSettings.barcodeFindSettings()

    val barcodeFind: BarcodeFind =
        BarcodeFind.forContext(dataCaptureContext, settings).also { mode ->
            mode.addListener(this)
        }

    val viewSettings: BarcodeFindViewSettings = BarcodeFindViewSettings.barcodeFindViewSettings()

    override fun onSearchStarted() {
        // no-op
    }

    override fun onSearchPaused(foundItems: Set<BarcodeFindItem>) {
        // no-op
    }

    override fun onSearchStopped(foundItems: Set<BarcodeFindItem>) {
        // no-op
    }

    fun dispose() {
        barcodeFind.removeListener(this)
        dataCaptureContext.removeMode(barcodeFind)
    }
}
