# Label Capture Android — Validation Flow

The Validation Flow provides a guided scanning experience with an always-present checklist of captured and missing fields. Users can scan from multiple angles, and can type in values manually when a field cannot be scanned.

> **PriceCapture and VIN pre-made labels are not VF-compatible.** `LabelDefinition.createPriceCaptureDefinition(name)` and `LabelDefinition.createVinLabelDefinition(name)` are **explicitly documented as incompatible with the Validation Flow** — using them inside VF "may result in incorrect data being captured." For price labels or VIN scanning, either build a custom definition out of custom barcode and text fields to use with VF, or keep the pre-made label but use the basic overlay path instead.

## Key classes

| Class | Purpose |
| --- | --- |
| `LabelCaptureValidationFlowOverlay` | The overlay itself; created with `newInstance(context, labelCapture, view)` |
| `LabelCaptureValidationFlowListener` | Callback interface; implement `onValidationFlowLabelCaptured(fields: List<LabelField>)` |
| `LabelCaptureValidationFlowSettings` | Customisation settings; created with `newInstance()`, applied with `overlay.applySettings(settings)` |

## Imports

```kotlin
import com.scandit.datacapture.label.data.LabelField
import com.scandit.datacapture.label.ui.overlay.validation.LabelCaptureValidationFlowListener
import com.scandit.datacapture.label.ui.overlay.validation.LabelCaptureValidationFlowOverlay
import com.scandit.datacapture.label.ui.overlay.validation.LabelCaptureValidationFlowSettings
```

## Setup

In `onCreate`, after creating `dataCaptureView`, replace `LabelCaptureBasicOverlay` with the following:

```kotlin
val validationFlowSettings = LabelCaptureValidationFlowSettings.newInstance()
// Optional: set per-field placeholder text for manual entry
validationFlowSettings.setPlaceholderTextForLabelDefinition("expiry-date", "MM/DD/YYYY")

val validationFlowOverlay = LabelCaptureValidationFlowOverlay.newInstance(
    this,
    labelCapture,
    dataCaptureView,
)
validationFlowOverlay.applySettings(validationFlowSettings)
validationFlowOverlay.listener = object : LabelCaptureValidationFlowListener {
    override fun onValidationFlowLabelCaptured(fields: List<LabelField>) {
        val barcodeData = fields.find { it.name == "barcode" }?.barcode?.data
        val expiryDate = fields.find { it.name == "expiry-date" }?.asDate()
        // All required fields are confirmed — process results on the main thread
    }
}
```

Do NOT also add a `LabelCaptureListener` — the Validation Flow overlay manages capture lifecycle internally.

**You can keep a `LabelCaptureBasicOverlay` alongside the Validation Flow overlay for field highlighting.** The VF overlay draws its checklist/manual-entry UI but no field outlines; the official `LabelCaptureSimpleSample` attaches both to the same `DataCaptureView` — the basic overlay with a brush listener for the visuals, the VF overlay for the flow. The basic overlay is then purely visual: results still come only through `onValidationFlowLabelCaptured`. (An advanced overlay can also be added, but only driven via its listener callbacks — the imperative push needs a `LabelCaptureListener`, which VF setups must not add; see `advanced.md`.)

## Lifecycle

The overlay must be paused and resumed alongside the host Fragment or Activity:

```kotlin
override fun onPause() {
    super.onPause()
    camera.switchToDesiredState(FrameSourceState.OFF)
    validationFlowOverlay.onPause()
}

override fun onResume() {
    super.onResume()
    camera.switchToDesiredState(FrameSourceState.ON)
    validationFlowOverlay.onResume()
}
```

## Customisation

All text strings in the Validation Flow UI can be replaced via `LabelCaptureValidationFlowSettings`:

```kotlin
validationFlowSettings.restartButtonText = "Restart"
validationFlowSettings.pauseButtonText = "Pause"
validationFlowSettings.finishButtonText = "Finish"
validationFlowSettings.standbyHintText = "No label detected, camera paused"
validationFlowSettings.validationHintText = "data fields collected"   // shown as "X/Y data fields collected"
validationFlowSettings.validationErrorText = "Incorrect format."
validationFlowSettings.scanningText = "Scan in progress"
validationFlowSettings.adaptiveScanningText = "Processing"
```

Call `overlay.applySettings(validationFlowSettings)` after setting all properties.

## Where to go next

- [Advanced Configurations](https://docs.scandit.com/sdks/android/label-capture/advanced/) — Validation Flow, Advanced Overlay, and Adaptive Recognition
- [LabelCaptureSimpleSample](https://github.com/Scandit/datacapture-android-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample) — sample app using `LabelCaptureValidationFlowOverlay`
