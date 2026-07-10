/*
 * Sample-app screen model with a working MatrixScan Pick integration already wired up.
 */
package com.example.picking

import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.barcode.pick.BarcodePick
import com.kmp.datacapture.barcode.pick.BarcodePickActionCallback
import com.kmp.datacapture.barcode.pick.BarcodePickActionListener
import com.kmp.datacapture.barcode.pick.BarcodePickAsyncMapperProductProvider
import com.kmp.datacapture.barcode.pick.BarcodePickAsyncMapperProductProviderCallback
import com.kmp.datacapture.barcode.pick.BarcodePickListener
import com.kmp.datacapture.barcode.pick.BarcodePickProduct
import com.kmp.datacapture.barcode.pick.BarcodePickProductProviderCallback
import com.kmp.datacapture.barcode.pick.BarcodePickProductProviderCallbackItem
import com.kmp.datacapture.barcode.pick.BarcodePickScanningListener
import com.kmp.datacapture.barcode.pick.BarcodePickScanningSession
import com.kmp.datacapture.barcode.pick.BarcodePickSession
import com.kmp.datacapture.barcode.pick.BarcodePickSettings
import com.kmp.datacapture.barcode.pick.BarcodePickView
import com.kmp.datacapture.barcode.pick.BarcodePickViewSettings
import com.kmp.datacapture.barcode.pick.BarcodePickViewUiListener
import com.kmp.datacapture.core.capture.DataCaptureContext

data class ProductDatabaseEntry(val identifier: String, val items: Set<String>)

interface BarcodePickViewHandle {
    fun start()
    fun pause()
    fun stop()
}

class PickingScreenModel :
    BarcodePickActionListener,
    BarcodePickListener,
    BarcodePickScanningListener,
    BarcodePickViewUiListener {

    private val productDatabase: List<ProductDatabaseEntry> = listOf(
        ProductDatabaseEntry("product_1", setOf("9783598215438", "9783598215414")),
        ProductDatabaseEntry("product_2", setOf("9783598215471", "9783598215481")),
        ProductDatabaseEntry("product_3", setOf("9783598215498")),
    )

    private val productsToPick: Set<BarcodePickProduct> = setOf(
        BarcodePickProduct("product_1", 2),
        BarcodePickProduct("product_2", 3),
    )

    private val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val barcodePickSettings: BarcodePickSettings = BarcodePickSettings.barcodePickSettings().also {
        it.enableSymbology(Symbology.EAN13_UPCA, true)
        it.enableSymbology(Symbology.EAN8, true)
        it.enableSymbology(Symbology.UPCE, true)
        it.enableSymbology(Symbology.CODE128, true)
        it.enableSymbology(Symbology.CODE39, true)
    }

    private val productProvider = BarcodePickAsyncMapperProductProvider(
        productsToPick,
        object : BarcodePickAsyncMapperProductProviderCallback {
            override fun mapItems(itemsData: Set<String>, callback: BarcodePickProductProviderCallback) {
                val mapped = itemsData.map { item ->
                    val entry = productDatabase.firstOrNull { item in it.items }
                    BarcodePickProductProviderCallbackItem(item, entry?.identifier)
                }.toSet()
                callback.onData(mapped)
            }
        },
    )

    val barcodePick: BarcodePick =
        BarcodePick.forContext(dataCaptureContext, barcodePickSettings, productProvider).also {
            it.addListener(this)
            it.addScanningListener(this)
        }

    val barcodePickViewSettings: BarcodePickViewSettings = BarcodePickViewSettings.barcodePickViewSettings()

    private var viewHandle: BarcodePickViewHandle? = null

    fun registerBarcodePickView(handle: BarcodePickViewHandle) {
        viewHandle = handle
    }

    fun unregisterBarcodePickView() {
        viewHandle = null
    }

    fun onResumed() = viewHandle?.start()
    fun onPaused() = viewHandle?.pause()

    fun dispose() {
        barcodePick.removeListener(this)
        barcodePick.removeScanningListener(this)
        viewHandle?.stop()
        viewHandle = null
    }

    override fun onPick(itemData: String, callback: BarcodePickActionCallback) {
        callback.onFinish(true)
    }

    override fun onUnpick(itemData: String, callback: BarcodePickActionCallback) {
        callback.onFinish(true)
    }

    override fun onSessionUpdated(barcodePick: BarcodePick, session: BarcodePickSession) {
        // no-op
    }

    override fun onScanningSessionUpdated(barcodePick: BarcodePick, session: BarcodePickScanningSession) {
        // no-op
    }

    override fun onScanningSessionCompleted(barcodePick: BarcodePick, session: BarcodePickScanningSession) {
        // no-op
    }

    override fun onFinishButtonTapped(view: BarcodePickView) {
        // TODO: navigate to result screen
    }
}
