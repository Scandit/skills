package com.example.myapp.shared

import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.core.ui.DataCaptureView

class IdScannerScreenModel {

    val dataCaptureContext: DataCaptureContext by lazy {
        DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
    }

    fun setupDataCaptureView(view: DataCaptureView): DataCaptureView {
        return view
    }

    fun dispose() {
        // Tear down modes and camera here.
    }
}
