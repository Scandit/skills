# Label Capture Android — Advanced Overlays & Adaptive Recognition

This file covers the overlay customisation paths beyond the minimal Basic Overlay, plus the cloud-based Adaptive Recognition Engine (ARE) features. For the basic integration read `references/integration.md` first; for the guided checklist experience read `references/validation-flow.md`.

## The three overlays

Smart Label Capture ships three overlays. When advising the user, enumerate **all three** even if they only named two — the most common omission is forgetting the Advanced Overlay exists.

| Overlay | When to use |
| --- | --- |
| **Basic Overlay** (`LabelCaptureBasicOverlay`) | Fully automated scanning with live highlights drawn on the camera feed. No confirmation step, no manual-entry fallback. The Minimal Integration in `integration.md` is the Basic Overlay scaffold. |
| **Validation Flow** (`LabelCaptureValidationFlowOverlay`) | The recommended default for production: a guided checklist of captured/missing fields with a manual-entry fallback when OCR misses a field. See `references/validation-flow.md`. |
| **Advanced Overlay** (`LabelCaptureAdvancedOverlay`) | A fully custom AR experience — the app draws its own Android `View`s anchored to detected labels/fields with full control over position and style. Significant implementation cost; only reach for it when the Validation Flow and Basic Overlay aren't visually flexible enough. |

## Basic Overlay customisation (brushes)

The Basic Overlay draws a box around the whole captured label and a box around each captured field. You can override the brushes in two ways.

**Globally**, when you don't need to vary the appearance by field name or content, set the brushes directly on the overlay instance:

```kotlin
overlay.setLabelBrush(Brush(Color.TRANSPARENT, Color.TRANSPARENT, 0f))
overlay.setCapturedFieldBrush(Brush(Color.GREEN, Color.GREEN, 1f))
```

**Per-field / per-label**, implement `LabelCaptureBasicOverlayListener`. `brushForField()` is called for each captured field and `brushForLabel()` for the whole label; return `null` to keep the default brush, or a `Brush` to override it:

```kotlin
import android.graphics.Color
import com.scandit.datacapture.core.ui.style.Brush
import com.scandit.datacapture.label.data.CapturedLabel
import com.scandit.datacapture.label.data.LabelField
import com.scandit.datacapture.label.ui.overlay.LabelCaptureBasicOverlay
import com.scandit.datacapture.label.ui.overlay.LabelCaptureBasicOverlayListener

overlay.listener = object : LabelCaptureBasicOverlayListener {
    override fun brushForField(
        overlay: LabelCaptureBasicOverlay,
        field: LabelField,
        label: CapturedLabel,
    ): Brush? = when (field.name) {
        "barcode" -> Brush(Color.CYAN, Color.CYAN, 1f)
        "expiry-date" -> Brush(Color.GREEN, Color.GREEN, 1f)
        else -> null   // null = keep the default brush
    }

    override fun brushForLabel(
        overlay: LabelCaptureBasicOverlay,
        label: CapturedLabel,
    ): Brush? = null   // null = keep the default label brush; return a Brush to override

    override fun onLabelTapped(
        overlay: LabelCaptureBasicOverlay,
        label: CapturedLabel,
    ) {
        // Handle the user tapping a captured label, e.g. open a detail screen.
    }
}
```

`Brush(fillColor, strokeColor, strokeWidth)` comes from `com.scandit.datacapture.core.ui.style.Brush`. A fully transparent brush (`Brush(Color.TRANSPARENT, Color.TRANSPARENT, 0f)`) hides that element.

## Advanced Overlay (custom AR views)

**When to use it — and the cost.** The Advanced Overlay is the most work of the three overlays: you build, position, and style your own Android `View`s rather than letting the SDK draw highlights (Basic Overlay) or a guided checklist with manual-entry fallback (Validation Flow). Reach for it **only** when you need full custom AR control that the Basic Overlay's brushes and the Validation Flow can't give you. If you just want recoloured field/label highlights, use the Basic Overlay brushes above; if you want a guided capture-and-confirm UX, use the Validation Flow (`references/validation-flow.md`) — both are far less code.

For custom AR — your own Android `View`s anchored to labels and fields — use `LabelCaptureAdvancedOverlay` and implement `LabelCaptureAdvancedOverlayListener`. The listener has two families of callbacks: one set for the whole label, one set for individual fields. Return a `View?` (`null` = no AR view), an `Anchor`, and a `PointWithUnit` offset for each.

```kotlin
import android.view.View
import android.widget.TextView
import com.scandit.datacapture.core.common.geometry.Anchor
import com.scandit.datacapture.core.common.geometry.MeasureUnit
import com.scandit.datacapture.core.common.geometry.PointWithUnit
import com.scandit.datacapture.label.data.CapturedLabel
import com.scandit.datacapture.label.data.LabelField
import com.scandit.datacapture.label.data.LabelFieldType
import com.scandit.datacapture.label.ui.overlay.LabelCaptureAdvancedOverlay
import com.scandit.datacapture.label.ui.overlay.LabelCaptureAdvancedOverlayListener

val advancedOverlay = LabelCaptureAdvancedOverlay.newInstance(labelCapture, dataCaptureView)

advancedOverlay.listener = object : LabelCaptureAdvancedOverlayListener {
    // Called when a whole label is detected. Return null to add AR only to specific fields.
    override fun viewForCapturedLabel(
        overlay: LabelCaptureAdvancedOverlay,
        capturedLabel: CapturedLabel,
    ): View? = null

    override fun anchorForCapturedLabel(
        overlay: LabelCaptureAdvancedOverlay,
        capturedLabel: CapturedLabel,
    ): Anchor = Anchor.CENTER

    override fun offsetForCapturedLabel(
        overlay: LabelCaptureAdvancedOverlay,
        capturedLabel: CapturedLabel,
        view: View,
    ): PointWithUnit = PointWithUnit(0f, 0f, MeasureUnit.PIXEL)

    // Called per detected field. Return a View to draw it anchored to that field.
    override fun viewForCapturedLabelField(
        overlay: LabelCaptureAdvancedOverlay,
        labelField: LabelField,
    ): View? {
        if (labelField.name.contains("expiry", ignoreCase = true) &&
            labelField.type == LabelFieldType.TEXT
        ) {
            return TextView(context).apply {
                text = "Item expires soon!"
            }
        }
        return null
    }

    override fun anchorForCapturedLabelField(
        overlay: LabelCaptureAdvancedOverlay,
        labelField: LabelField,
    ): Anchor = Anchor.BOTTOM_CENTER

    override fun offsetForCapturedLabelField(
        overlay: LabelCaptureAdvancedOverlay,
        labelField: LabelField,
        view: View,
    ): PointWithUnit = PointWithUnit(0f, 22f, MeasureUnit.DIP)
}
```

`Anchor`, `MeasureUnit`, and `PointWithUnit` come from `com.scandit.datacapture.core.common.geometry`; `LabelFieldType` from `com.scandit.datacapture.label.data`. The Basic and Advanced overlays can be used at the same time on one `DataCaptureView`.

## Seven-segment display labels

For LCD/LED meter or display readouts (seven-segment digits), use the pre-built whole-label factory — do not hand-write a digit regex:

```kotlin
import com.scandit.datacapture.label.capture.LabelDefinition

val settings = LabelCaptureSettings.builder()
    .addLabel(LabelDefinition.createSevenSegmentDisplayLabelDefinition("display"))
    .build()
```

This is one of the pre-built whole-label definitions on `LabelDefinition` (alongside `createPriceCaptureDefinition` and `createVinLabelDefinition`); it returns a complete, tuned definition you pass straight into `addLabel(...)`. Because it is a pre-built definition, bundle the `label-text-models` Gradle artifact (see `references/integration.md`).

## Adaptive Recognition Engine (ARE) — cloud fallback (BETA)

> **BETA.** The Adaptive Recognition API is still in beta and may change in future SDK versions. It requires a license key with the ARE feature flag enabled. To enable it on a production subscription the customer must contact **support@scandit.com**. Always surface the beta status and the contact-support requirement to the user — do not present ARE as a generally-available feature.

ARE is Scandit's cloud-based OCR fallback. When Smart Label Capture's on-device model fails to capture a field, the SDK can automatically trigger the larger cloud model to recognise complex or unforeseen data, reducing how often the user has to type a value manually.

Enable it by adding a single `adaptiveRecognition(...)` line to your label definition, set to `AdaptiveRecognitionMode.AUTO`:

```kotlin
import com.scandit.datacapture.barcode.data.Symbology
import com.scandit.datacapture.label.capture.labelCaptureSettings
import com.scandit.datacapture.label.data.AdaptiveRecognitionMode
import com.scandit.datacapture.label.data.LabelDateComponentFormat
import com.scandit.datacapture.label.data.LabelDateFormat

val settings = labelCaptureSettings {
    label("perishable-product") {
        customBarcode("barcode") {
            setSymbologies(Symbology.EAN13_UPCA, Symbology.CODE128)
        }
        expiryDateText("expiry-date") {
            setLabelDateFormat(
                LabelDateFormat(
                    componentFormat = LabelDateComponentFormat.MDY,
                    acceptPartialDates = false,
                )
            )
        }
        adaptiveRecognition(adaptiveRecognitionMode = AdaptiveRecognitionMode.AUTO)
    }
}
```

ARE works in combination with the Validation Flow — the cloud fallback fills fields the on-device model missed before the user reaches the manual-entry step. See `AdaptiveRecognitionMode` in the API reference for the available options.

## Receipt Scanning (BETA)

> **BETA.** Receipt Scanning requires the Adaptive Recognition Engine, which is still in beta. To enable it on a subscription the customer must contact **support@scandit.com**. Surface the beta status and contact-support requirement to the user.

Receipt Scanning uses ARE to extract structured data from receipts in the cloud — store information, payment details, and individual line items. It uses a **different integration pattern** from the standard label overlays:

- Use `LabelCaptureAdaptiveRecognitionOverlay.newInstance(labelCapture, dataCaptureView)` instead of the standard overlay.
- Implement `LabelCaptureAdaptiveRecognitionListener` and its `onRecognized` callback.

The `onRecognized` callback returns a `ReceiptScanningResult`, whose fields include `storeName`, `storeAddress`, `storeCity`, `date`, `time`, `paymentPreTaxTotal`, `paymentTax`, `paymentTotal`, `loyaltyNumber`, and `lineItems` (each line item carries `name`, `unitPrice`, `discount`, `quantity`, and `totalPrice`).

```kotlin
import com.scandit.datacapture.label.ui.overlay.adaptive.LabelCaptureAdaptiveRecognitionListener
import com.scandit.datacapture.label.ui.overlay.adaptive.LabelCaptureAdaptiveRecognitionOverlay

val adaptiveOverlay = LabelCaptureAdaptiveRecognitionOverlay.newInstance(
    labelCapture,
    dataCaptureView,
)
adaptiveOverlay.listener = object : LabelCaptureAdaptiveRecognitionListener {
    override fun onRecognized(result: ReceiptScanningResult) {
        val store = result.storeName
        val total = result.paymentTotal
        for (item in result.lineItems) {
            // item.name, item.unitPrice, item.quantity, item.totalPrice
        }
    }
}
```

## Where to go next

- [Advanced Configurations](https://docs.scandit.com/sdks/android/label-capture/advanced/) — overlay customisation, adaptive recognition, receipt scanning.
- [Label Definitions](https://docs.scandit.com/sdks/android/label-capture/label-definitions/) — pre-built whole-label definitions and field types.
