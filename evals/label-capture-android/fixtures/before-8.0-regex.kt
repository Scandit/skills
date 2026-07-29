package com.example.app

import com.scandit.datacapture.barcode.data.Symbology
import com.scandit.datacapture.label.capture.LabelCaptureSettings

fun buildLabelCaptureSettings(): LabelCaptureSettings {
    return LabelCaptureSettings.builder()
        .addLabel()
            .addCustomBarcode()
                .setSymbologies(Symbology.EAN13_UPCA)
            .buildFluent("barcode")
            .addExpiryDateText()
                .setDataTypePattern(Regex("EXP[:\\s]+"))
                .setPattern("\\d{2}/\\d{2}/\\d{2,4}")
            .buildFluent("expiry-date")
            .addCustomText()
                .setDataTypePatterns(listOf("LOT[:\\s]+", "Batch[:\\s]+"))
                .setPatterns("[A-Z0-9]{6,}")
                .isOptional(true)
            .buildFluent("lot-number")
        .buildFluent("perishable-product")
        .build()
}
