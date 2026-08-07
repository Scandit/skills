/*
 * Shared (commonMain) screen model with BarcodeSelection already integrated
 * using Tap-to-Select, matching the canonical BarcodeSelectionSimpleSample
 * structure. Used as the starting point for evals that modify an existing
 * integration (selection type, strategy, feedback, freeze/unfreeze, teardown,
 * etc.) rather than building one from scratch.
 */
package com.example.selection

import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.barcode.selection.BarcodeSelection
import com.kmp.datacapture.barcode.selection.BarcodeSelectionBasicOverlay
import com.kmp.datacapture.barcode.selection.BarcodeSelectionListener
import com.kmp.datacapture.barcode.selection.BarcodeSelectionSession
import com.kmp.datacapture.barcode.selection.BarcodeSelectionSettings
import com.kmp.datacapture.barcode.selection.BarcodeSelectionTapSelection
import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.core.data.FrameData
import com.kmp.datacapture.core.source.Camera
import com.kmp.datacapture.core.source.FrameSourceState
import com.kmp.datacapture.core.ui.DataCaptureView
import com.kmp.datacapture.core.ui.LogoStyle
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

internal const val LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --"

class SelectionScreenModel : BarcodeSelectionListener {

    private val _state = MutableStateFlow(SelectionUiState())
    val state: StateFlow<SelectionUiState> = _state.asStateFlow()

    val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize(LICENSE_KEY)

    private val camera: Camera? =
        Camera.getDefaultCamera(BarcodeSelection.createRecommendedCameraSettings())?.also {
            dataCaptureContext.setFrameSource(it)
        }

    private val settings: BarcodeSelectionSettings =
        BarcodeSelectionSettings.barcodeSelectionSettings().also {
            it.selectionType = BarcodeSelectionTapSelection.tapSelection()
            it.enableSymbology(Symbology.EAN13_UPCA, true)
            it.enableSymbology(Symbology.CODE128, true)
            it.enableSymbology(Symbology.QR, true)
        }

    val barcodeSelection: BarcodeSelection =
        BarcodeSelection.forContext(dataCaptureContext, settings).also {
            it.addListener(this)
        }

    fun setupDataCaptureView(view: DataCaptureView): DataCaptureView {
        view.logoStyle = LogoStyle.MINIMAL
        view.addOverlay(BarcodeSelectionBasicOverlay.withBarcodeSelectionForView(barcodeSelection, view))
        return view
    }

    fun onEvent(event: SelectionEvent) {
        when (event) {
            SelectionEvent.STARTED -> {
                camera?.switchToDesiredState(FrameSourceState.ON)
                barcodeSelection.isEnabled = true
            }
            SelectionEvent.STOPPED -> {
                barcodeSelection.isEnabled = false
                camera?.switchToDesiredState(FrameSourceState.OFF)
            }
        }
    }

    override fun onSelectionUpdated(
        barcodeSelection: BarcodeSelection,
        session: BarcodeSelectionSession,
        frameData: FrameData?,
    ) {
        val barcode = session.newlySelectedBarcodes.firstOrNull() ?: return
        _state.value = _state.value.copy(
            lastSelectionData = barcode.data ?: "",
            lastSelectionCount = session.getCount(barcode),
        )
    }

    override fun onSessionUpdated(
        barcodeSelection: BarcodeSelection,
        session: BarcodeSelectionSession,
        frameData: FrameData?,
    ) = Unit

    // NOTE: no dispose() function yet — some evals ask for proper teardown to be added.
}

data class SelectionUiState(
    val lastSelectionData: String = "",
    val lastSelectionCount: Int = 0,
)

enum class SelectionEvent { STARTED, STOPPED }
