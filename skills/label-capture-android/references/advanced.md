# Label Capture Android — Advanced Overlays & Adaptive Recognition

This file covers the overlay customisation paths beyond the minimal Basic Overlay, plus the cloud-based Adaptive Recognition Engine (ARE) features. For the basic integration read `references/integration.md` first; for the guided checklist experience read `references/validation-flow.md`.

## The three overlays

Smart Label Capture ships three overlays. When advising the user, enumerate **all three** even if they only named two — the most common omission is forgetting the Advanced Overlay exists.

| Overlay | When to use |
| --- | --- |
| **Basic Overlay** (`LabelCaptureBasicOverlay`) | Fully automated scanning with live highlights drawn on the camera feed. No confirmation step, no manual-entry fallback. The Minimal Integration in `integration.md` is the Basic Overlay scaffold. |
| **Validation Flow** (`LabelCaptureValidationFlowOverlay`) | The recommended default for production: a guided checklist of captured/missing fields with a manual-entry fallback when OCR misses a field. See `references/validation-flow.md`. |
| **Advanced Overlay** (`LabelCaptureAdvancedOverlay`) | A fully custom AR experience — the app draws its own Android `View`s anchored to detected labels/fields with full control over position and style. Significant implementation cost; only reach for it when the Validation Flow and Basic Overlay aren't visually flexible enough. |

### Overlays compose

You can attach several overlays to the *same* `DataCaptureView`:

- **Basic + Advanced** is the classic pairing — basic for field coloring, advanced for a floating status view.
- **Validation Flow + Basic** is also a documented pairing: the VF overlay draws its checklist UI but no field highlighting, so the official `LabelCaptureSimpleSample` attaches a `LabelCaptureBasicOverlay` (with a brush listener) *alongside* the VF overlay to outline fields.

One rule survives in a Validation Flow setup: **the VF overlay stays the capture-lifecycle owner — do not add your own `LabelCaptureListener` next to it** (results come through `onValidationFlowLabelCaptured`). That has a knock-on for the Advanced Overlay: the imperative push pattern below is driven from `onSessionUpdated`, which you don't have under VF. So with VF, the Advanced Overlay can only be driven through its *listener* callbacks — fine for views that don't need sibling-field state (e.g. a checkmark gated on the field's own `state`), but a view whose appearance depends on other fields of the label can't be built per-field under VF. If you need that, use the Basic + Advanced (non-VF) path.

## Basic Overlay customisation (brushes)

The Basic Overlay draws a box around the whole captured label and a box around each captured field. You can override the brushes in two ways.

**Globally**, when you don't need to vary the appearance by field name or content, assign the brush properties directly on the overlay instance (these are Kotlin properties — `overlay.labelBrush = ...`, not `setLabelBrush(...)` method calls, which don't compile from Kotlin):

```kotlin
overlay.labelBrush = Brush(Color.TRANSPARENT, Color.TRANSPARENT, 0f)   // whole-label box
overlay.capturedFieldBrush = Brush(Color.GREEN, Color.GREEN, 1f)       // fields recognized this frame
overlay.predictedFieldBrush = Brush(Color.GRAY, Color.GRAY, 1f)        // fields inferred/tracked, not yet read
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

`Brush(fillColor, strokeColor, strokeWidth)` comes from `com.scandit.datacapture.core.ui.style.Brush`. A fully transparent brush (`Brush(Color.TRANSPARENT, Color.TRANSPARENT, 0f)`) hides that element. A transparent *fill* with a colored stroke (`Brush(Color.TRANSPARENT, color, 2f)`) draws an outline only — usually what you want for state feedback on a field the user still needs to read.

The `label` parameter of `brushForField(overlay, field, label)` is the whole `CapturedLabel`, so the brush can depend on *sibling* fields — e.g. color the price field green/red based on whether the barcode↔price pair validates against your database. Read fields by `field.type` (`LabelFieldType.BARCODE` / `LabelFieldType.TEXT`) rather than hardcoded names when the definition is a pre-built factory.

**Imperatively**, `setBrushForField(brush, field, label)` and `setBrushForLabel(brush, label)` push a brush directly from your own code. Use these only when the listener model doesn't fit — the listener is the idiomatic path for state-driven coloring.

## Advanced Overlay (custom AR views)

**When to use it — and the cost.** The Advanced Overlay is the most work of the three overlays: you build, position, and style your own Android `View`s rather than letting the SDK draw highlights (Basic Overlay) or a guided checklist with manual-entry fallback (Validation Flow). Reach for it **only** when you need full custom AR control that the Basic Overlay's brushes and the Validation Flow can't give you. If you just want recoloured field/label highlights, use the Basic Overlay brushes above; if you want a guided capture-and-confirm UX, use the Validation Flow (`references/validation-flow.md`) — both are far less code.

### Anchor and offset — how placement works

- **Anchor** (`Anchor.TOP_CENTER`, `CENTER`, `BOTTOM_CENTER`, …) picks the point *on the label/field* the view attaches to.
- The view is **centered on that anchor point** — not placed beside it. A badge anchored `TOP_CENTER` with no offset straddles the top edge, half above and half below.
- **Offset** is a `PointWithUnit(x, y, MeasureUnit.DIP)` shift from the anchor. `+Y` is **downward**, so to lift a view *above* the anchor pass a **negative** Y; to hang it fully *below* a `BOTTOM_CENTER` anchor, push down by half the view's height.

### The listener path

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

### The trap: the per-field listener callback has NO label context

The two callback families are not equally capable:

- **Per-label:** `viewForCapturedLabel(overlay, capturedLabel)` receives the whole `CapturedLabel` — you can read every field and compute state. The listener is fine here.
- **Per-field:** `viewForCapturedLabelField(overlay, labelField)` receives **only the `LabelField`**, with no way back to its parent label or `trackingId`.

That second signature is the trap. The example above is safe because the view depends only on the field's own name/type. But if the view's appearance depends on *sibling* fields — e.g. a status marker pinned to the price field whose color depends on the barcode↔price validation — you **cannot** build it from the per-field listener: the callback can't see the other fields. Trying to recover the label state through a global side-store keyed on field values is fragile (it collides on duplicate values) — don't.

### The fix: drive the overlay imperatively from `onSessionUpdated`

Push views from your `LabelCaptureListener.onSessionUpdated`, where you hold the whole `CapturedLabel`. There you can both compute the state (reading any field) *and* still anchor on a specific field:

```kotlin
// Re-push only when a label's state changes; key by trackingId.
private val pinnedStates = HashMap<Int, ValidationState>()
private val pinOffset = PointWithUnit(0f, -BADGE_HALF_HEIGHT_DP, MeasureUnit.DIP) // lift above the field

override fun onSessionUpdated(
    mode: LabelCapture,
    session: LabelCaptureSession,
    data: FrameData,
) {
    val present = HashSet<Int>()
    session.capturedLabels.forEach { label ->
        val priceField = label.fields.firstOrNull { it.type == LabelFieldType.TEXT } ?: return@forEach
        val state = computeState(label) ?: return@forEach   // reads barcode + price off the whole label

        present.add(label.trackingId)
        if (pinnedStates[label.trackingId] != state) {        // avoid re-pushing an identical view every frame
            pinnedStates[label.trackingId] = state
            advancedOverlay.setViewForCapturedLabelField(priceField, label, StatusBadgeView(context, state))
            advancedOverlay.setAnchorForCapturedLabelField(priceField, label, Anchor.TOP_CENTER)
            advancedOverlay.setOffsetForCapturedLabelField(priceField, label, pinOffset)
        }
    }
    pinnedStates.keys.retainAll(present) // labels gone from frame: the overlay drops their views for you
}
```

Note the argument order of the imperative setters: **field first, then label, then the value** — `setViewForCapturedLabelField(field, label, view)`, `setAnchorForCapturedLabelField(field, label, anchor)`, `setOffsetForCapturedLabelField(field, label, offset)`. The per-label variants drop the field argument: `setViewForCapturedLabel(label, view)`, etc. `clearCapturedLabelViews()` removes everything.

Because you push from a `LabelCaptureListener`, this pattern is unavailable in a Validation Flow setup (see "Overlays compose" above). When combining a basic-overlay brush listener with this imperative push, keep both on the same handler object if they share state — that keeps the field color and the floating badge in sync.

All signatures in this section are compile-verified against `com.scandit.datacapture:label` 8.4.0.

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
>
> **Availability.** The `adaptiveRecognition(...)` builder method is **not present in public SDK releases up to and including 8.4.0** (verified against the published AAR). Before generating ARE code, check the project's SDK version — on 8.4.0 or older this snippet will not compile, and the honest answer is that the feature isn't available to them yet.

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
>
> **Availability.** The public Receipt Scanning classes (`LabelCaptureAdaptiveRecognitionOverlay`, `LabelCaptureAdaptiveRecognitionListener`, `ReceiptScanningResult`) are **not present in public SDK releases up to and including 8.4.0** (verified against the published AAR — only internal native counterparts exist there). Check the project's SDK version before generating this code; on 8.4.0 or older it will not compile.

Receipt Scanning uses ARE to extract structured data from receipts in the cloud — store information, payment details, and individual line items. It uses a **different integration pattern** from the standard label overlays:

- Use `LabelCaptureAdaptiveRecognitionOverlay.newInstance(context, labelCapture, dataCaptureView)` instead of the standard overlay — note the `Context` first argument, unlike the other overlays' `newInstance`.
- Implement `LabelCaptureAdaptiveRecognitionListener`. Its `onRecognized(result: AdaptiveRecognitionResult)` callback receives the **sealed base type** `AdaptiveRecognitionResult` — narrow it to `ReceiptScanningResult` before reading receipt fields (overriding `onRecognized` with a `ReceiptScanningResult` parameter does not compile — "overrides nothing"). The listener also offers optional `onFailure()` and `onProcessingFrame(frameData)` callbacks.

`ReceiptScanningResult` carries `storeName`/`storeCity`/`storeAddress` (`String?`), `date`/`time` (`String?`), `paymentPreTaxTotal`/`paymentTax`/`paymentTotal` (`Float?`), `loyaltyNumber` (`Int?`), and `lineItems` (each line item: `name`, `unitPrice`, `discount`, `quantity`, `totalPrice`).

```kotlin
import com.scandit.datacapture.label.ui.overlay.adaptiverecognition.AdaptiveRecognitionResult
import com.scandit.datacapture.label.ui.overlay.adaptiverecognition.LabelCaptureAdaptiveRecognitionListener
import com.scandit.datacapture.label.ui.overlay.adaptiverecognition.LabelCaptureAdaptiveRecognitionOverlay
import com.scandit.datacapture.label.ui.overlay.adaptiverecognition.ReceiptScanningResult

val adaptiveOverlay = LabelCaptureAdaptiveRecognitionOverlay.newInstance(
    context,
    labelCapture,
    dataCaptureView,
)
adaptiveOverlay.listener = object : LabelCaptureAdaptiveRecognitionListener {
    override fun onRecognized(result: AdaptiveRecognitionResult) {
        val receipt = result as? ReceiptScanningResult ?: return
        val store = receipt.storeName
        val total = receipt.paymentTotal
        for (item in receipt.lineItems) {
            // item.name, item.unitPrice, item.quantity, item.totalPrice
        }
    }
}
```

The package is `com.scandit.datacapture.label.ui.overlay.adaptiverecognition` (one word) — **not** `...ui.overlay.adaptive`, which doesn't exist and fails to compile.

## Where to go next

- [Advanced Configurations](https://docs.scandit.com/sdks/android/label-capture/advanced/) — overlay customisation, adaptive recognition, receipt scanning.
- [Label Definitions](https://docs.scandit.com/sdks/android/label-capture/label-definitions/) — pre-built whole-label definitions and field types.
