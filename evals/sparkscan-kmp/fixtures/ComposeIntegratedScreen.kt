package com.example.app.shared

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.barcode.spark.SparkScanSettings
import com.kmp.datacapture.barcode.compose.SparkScanView

/**
 * Compose Multiplatform screen with the default SparkScan composable already
 * wired up (all UI chrome left at its default visibility).
 */
@Composable
fun WarehouseScanScreen(onBarcodeScanned: (String) -> Unit) {
    SparkScanView(
        settings = SparkScanSettings.sparkScanSettings().also {
            it.enableSymbologies(setOf(Symbology.EAN13_UPCA, Symbology.CODE128))
        },
        modifier = Modifier.fillMaxSize(),
        onScan = { barcodes -> barcodes.firstOrNull()?.data?.let(onBarcodeScanned) },
    )
}
