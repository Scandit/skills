/*
 * This file is part of the Scandit Data Capture SDK
 *
 * Copyright (C) 2026- Scandit AG. All rights reserved.
 */

package com.example.kmpapp.parser

import com.kmp.datacapture.barcode.capture.BarcodeCapture
import com.kmp.datacapture.barcode.capture.BarcodeCaptureListener
import com.kmp.datacapture.barcode.capture.BarcodeCaptureSession
import com.kmp.datacapture.barcode.data.Barcode
import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.core.data.FrameData
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Shared commonMain view model that already scans barcodes with BarcodeCapture.
 * The team now wants every scanned HIBC barcode's data string run through the
 * Parser and the parsed fields (or a friendly error) shown on screen. Keep the
 * existing BarcodeCapture wiring untouched.
 */
class ScanAndParseModel(private val dataCaptureContext: DataCaptureContext) : BarcodeCaptureListener {

    private val _lastBarcodeData = MutableStateFlow<String?>(null)
    val lastBarcodeData: StateFlow<String?> = _lastBarcodeData.asStateFlow()

    override fun onBarcodeScanned(
        barcodeCapture: BarcodeCapture,
        session: BarcodeCaptureSession,
        data: FrameData,
    ) {
        val barcode: Barcode = session.newlyRecognizedBarcode ?: return
        _lastBarcodeData.value = barcode.data
        // TODO: parse barcode.data as HIBC and surface the result.
    }

    override fun onSessionUpdated(
        barcodeCapture: BarcodeCapture,
        session: BarcodeCaptureSession,
        data: FrameData,
    ) = Unit
}
