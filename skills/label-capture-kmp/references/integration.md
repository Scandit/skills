# Label Capture KMP Integration Guide

Label Capture (Smart Label Capture) extracts multiple fields from a single label in one scan — e.g. a barcode, an expiry date, and a total price on a grocery label. You declare the structure of the label (which fields, required/optional, barcode symbologies or text regex) and the SDK returns all matched fields per frame.

> **Label Capture reads printed text only.** Handwritten text is not supported.

On Kotlin Multiplatform, Label Capture lives in a `commonMain` **`expect`/`actual`** layer under `com.kmp.datacapture.label.*`. Almost all integration code — the `DataCaptureContext`, the `LabelCapture` mode, the label definition, the overlays, and the listener that reads results — is written **once in `commonMain`** and shared between the Android and iOS apps. Only the thin host code that embeds the native view (`toAndroidView()` on Android, `toUIView()` on iOS) and the camera-permission prompt are platform-specific.

## Starting from zero? Read the official sample first

If the user has no Label Capture code yet, the fastest path to a *correct* integration is the official KMP sample — it already has the right module structure, the right Gradle/SPM dependencies, the recommended camera settings, and both a core-view host and the Validation Flow overlay wired up end to end (shared `ScreenModel` + Android `Activity`/Compose host + iOS SwiftUI host). Before writing integration code from scratch, treat the sample as the reference for anything you're unsure about:

- **LabelCaptureSimpleSample:** `frameworks/kmp/samples/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample` — shared `LabelScannerScreenModel.kt` owns every SDK object; `androidApp/.../ScannerScreen.kt` embeds the view with Jetpack Compose; `iosApp/iosApp/LabelScannerHost.swift` embeds it with SwiftUI.

## Prerequisites

- A valid Scandit license key:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.
- Camera permission requested at runtime on each platform before the camera is switched on (Android: `android.permission.CAMERA` via `ActivityResultContracts.RequestPermission`; iOS: `AVCaptureDevice.requestAccess(for: .video)`), plus the iOS `NSCameraUsageDescription` Info.plist entry.

### Gradle setup (`commonMain`)

Add the Scandit KMP modules to the shared module's `commonMain` source set. Maven group is `com.scandit.datacapture.kmp`; use the same version for every artifact.

```kotlin
// shared/build.gradle.kts
kotlin {
    sourceSets {
        commonMain.dependencies {
            implementation("com.scandit.datacapture.kmp:core:<version>")
            implementation("com.scandit.datacapture.kmp:label:<version>")
            // Container module (AAR/xcframework, no Kotlin API of its own) shipping the
            // Smart Label Capture text-recognition model. Required at RUNTIME whenever the
            // label uses any pre-built field (barcode-semantic or text) — see the model
            // artifact rule below. Without it LabelCapture crashes when the mode loads its
            // model, on both Android and iOS.
            implementation("com.scandit.datacapture.kmp:label-text:<version>")
            // Required IN ADDITION when using createPriceCaptureDefinition — see the
            // model-artifact rule below.
            implementation("com.scandit.datacapture.kmp:price-label:<version>")
        }
    }
}
```

Replace `<version>` with the current SDK version (e.g. `8.6.0`). `com.scandit.datacapture.kmp:barcode` does **not** need to be declared explicitly — `label` re-exports it as an `api` dependency, so it resolves transitively. Declare it explicitly only if `commonMain` code also references `com.kmp.datacapture.barcode.*` symbols directly (e.g. `Symbology` for a custom barcode field, as in the examples below).

#### iOS: Swift Package Manager

iOS apps consume the KMP shared module's own umbrella XCFramework (built from the shared module) plus the native Scandit frameworks, both resolved through the published **`Scandit/datacapture-kmp-spm`** Swift package. Add the package in Xcode (*File → Add Package Dependencies*) and depend on the **`label`** variant's product — it bundles `core` + `barcode` + `label` (the label variant always pulls in `barcode`, since Label Capture reads barcodes as label fields) plus the native `label-text` recognition-model framework linked in transitively. There is no separate SPM product for `label-text` to add — it ships bundled with the `label` variant.

#### When is `label-text` required? (read this — it is a common crash)

`label-text` ships the on-device model that backs Label Capture's *semantic* field recognition. The rule is **not** "only if there's a text field." A label that uses any pre-built **barcode-semantic** field — `serialNumberBarcode`, `partNumberBarcode`, `imeiOneBarcode`, `imeiTwoBarcode` — needs the model artifact too, even though those are "barcode" fields. Without it, the app **crashes at launch** when the label definition is built, on both Android and iOS.

- **Include `label-text`** whenever the label uses *any* pre-built field — every text field builder (`expiryDateText`, `packingDateText`, `dateText`, `totalPriceText`, `unitPriceText`, `weightText`) **and** every pre-built barcode field (`serialNumberBarcode`, `partNumberBarcode`, `imeiOneBarcode`, `imeiTwoBarcode`) — or any pre-built whole-label definition (see below). The official sample bundles it unconditionally for exactly this reason.
- **You can omit it only** for a label whose fields are *exclusively* `customBarcode` (a raw symbology read with no semantic extraction). If in doubt, include it.

#### Pre-built whole-label definitions need their OWN model artifact too (another launch-time crash)

`label-text` is necessary but **not sufficient** for the pre-built whole-label factories on `LabelDefinition`. Each factory is backed by its own ML model set shipped in a *separate* artifact:

| Factory | Model artifact(s) required (in addition to `label-text`) |
|---|---|
| `LabelDefinition.createPriceCaptureDefinition(name)` | `com.scandit.datacapture.kmp:price-label:<version>` |
| `LabelDefinition.createVinLabelDefinition(name)` | none beyond `label-text` |
| `LabelDefinition.createSevenSegmentDisplayLabelDefinition(name)` | none beyond `label-text` |

Miss `price-label` and the app compiles and launches, but price recognition silently never fires.

## Prefer pre-built over custom — do not hallucinate regex

Label Capture has a tuned builder for most things people scan. When the user's request matches one, use it: the pre-built field carries default value/anchor regexes validated against real labels, and it will out-perform anything you hand-write. Only use `customBarcode` / `customText` when nothing pre-built covers the field.

### Step 0 — Is the *whole label* a pre-built definition?

Before composing fields one by one, check whether the entire label is one Scandit already ships as a factory on `LabelDefinition` (`com.kmp.datacapture.label.definition.LabelDefinition`). These return a complete, tuned definition passed straight into `LabelCaptureSettingsBuilder().addLabel(...)` — no manual field assembly, no guessed regex:

| User says… | Use this factory | Emits | Extra model artifact |
|---|---|---|---|
| "retail **price label**", "shelf label", "price tag" (price + barcode) | `LabelDefinition.createPriceCaptureDefinition("price-label")` | 2 fields: one `BARCODE` (product SKU), one `TEXT` (price) | **`com.scandit.datacapture.kmp:price-label`** (required) |
| "**VIN**", "vehicle identification number" label | `LabelDefinition.createVinLabelDefinition("vehicle-vin")` | VIN field(s) | none beyond `label-text` |
| "**seven-segment** display", LCD/LED meter readout | `LabelDefinition.createSevenSegmentDisplayLabelDefinition("display")` | display readout field | none beyond `label-text` |

```kotlin
import com.kmp.datacapture.label.capture.LabelCaptureSettingsBuilder
import com.kmp.datacapture.label.definition.LabelDefinition

val settings = LabelCaptureSettingsBuilder()
    .addLabel(LabelDefinition.createPriceCaptureDefinition("price-label"))
    .build()
```

**Reading fields from a pre-built definition — prefer field *type* over field *name*.** A factory definition ships with its own fixed set of fields whose names are decided by the SDK, not by you. Read by `field.type` (`LabelFieldType.BARCODE` / `LabelFieldType.TEXT`):

```kotlin
val capturedLabel = session.capturedLabels.firstOrNull() ?: return
val barcode = capturedLabel.fields.firstOrNull { it.type == LabelFieldType.BARCODE }?.barcode?.data
val price = capturedLabel.fields.firstOrNull { it.type == LabelFieldType.TEXT }?.text
```

There is **no typed/numeric accessor** for the price — it comes back only as the `TEXT` field's `.text` string; parse it yourself (handle decimal comma / currency symbols).

If no whole-label factory fits, build the label from fields — preferring pre-built fields per the catalogue below.

## Interactive Label Definition

Before writing any code, walk the user through their label. Ask one question at a time. Until the user has described their label, don't include any integration code in your reply — not even a "preview" snippet.

**Question A — What's on your label?** Map each item to its pre-built builder first. The full set of field builders, each available in two forms — a fluent `add*()` that returns a builder (terminate with `.build(name)`), and a Kotlin-DSL member `*(name) { ... }` that both configures and registers the field in one call:

| Field type | Builder (fluent) | DSL member | Notes |
|---|---|---|---|
| Custom barcode | `addCustomBarcode()` | `customBarcode(name) { }` | Any barcode, user chooses symbologies. Use only when no pre-built barcode field fits. |
| Serial number | `addSerialNumberBarcode()` | `serialNumberBarcode(name) { }` | Pre-built (preset symbologies + regex). Requires `label-text`. |
| Part number | `addPartNumberBarcode()` | `partNumberBarcode(name) { }` | Pre-built. Requires `label-text`. |
| IMEI 1 | `addImeiOneBarcode()` | `imeiOneBarcode(name) { }` | Pre-built (smartphone/electronics boxes). Requires `label-text`. |
| IMEI 2 | `addImeiTwoBarcode()` | `imeiTwoBarcode(name) { }` | Pre-built. Requires `label-text`. |
| Expiry date | `addExpiryDateText()` | `expiryDateText(name) { }` | Pre-built (optional date format). |
| Packing / production date | `addPackingDateText()` | `packingDateText(name) { }` | Pre-built. |
| Generic date | `addDateText()` | `dateText(name) { }` | Pre-built (a date but not specifically expiry or packing). |
| Total price | `addTotalPriceText()` | `totalPriceText(name) { }` | Pre-built. |
| Unit price | `addUnitPriceText()` | `unitPriceText(name) { }` | Pre-built. |
| Weight | `addWeightText()` | `weightText(name) { }` | Pre-built. |
| Custom text | `addCustomText()` | `customText(name) { }` | Last resort — any text; user provides a value regex. |

**Question B — For each selected field:**
- Is it **required** or **optional**? Call `.isOptional(true)` in the fluent form, or the same `isOptional(true)` builder call inside the DSL block; required is the default.
- For `customBarcode`: which **symbologies**? `.setSymbologies(Symbology.X, Symbology.Y, ...)` (vararg) from `com.kmp.datacapture.barcode.data.Symbology` — the same enum values as the single-platform Android SDK (underscore form, e.g. `Symbology.EAN13_UPCA`, `Symbology.GS1_DATABAR_EXPANDED`, `Symbology.CODE128`).
- For `customText`: what **value regex**? `.setValueRegexes("pattern1", "pattern2")` (vararg) or `.setValueRegex("pattern")` / `.setValueRegex(Regex(...))` for a single one.
- For date fields: does the user need a specific date format? Ask for the component order (MDY/DMY/YMD) and whether partial dates are accepted.

**Question C — Which file should the integration code go in?** For a KMP project this is almost always a `commonMain` file (the shared `ScreenModel`/presenter). Write the code directly into that file.

## Minimal Integration

Once the user has answered Questions A, B, and C, generate the shared integration code, plus the thin platform hosts. This mirrors `LabelScannerScreenModel.kt` in the official sample: a `commonMain` class owns every SDK object and exposes a `StateFlow`-based UI state; the Android and iOS hosts each embed the native view and forward lifecycle events.

### Shared (`commonMain`)

```kotlin
package com.example.labelscanner

import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.core.source.Camera
import com.kmp.datacapture.core.source.FrameSourceState
import com.kmp.datacapture.core.ui.DataCaptureView
import com.kmp.datacapture.label.capture.LabelCapture
import com.kmp.datacapture.label.capture.LabelCaptureListener
import com.kmp.datacapture.label.capture.LabelCaptureSession
import com.kmp.datacapture.label.capture.labelCaptureSettings
import com.kmp.datacapture.label.ui.overlay.LabelCaptureBasicOverlay
import com.kmp.datacapture.core.data.FrameData

class LabelScannerScreenModel {

    val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val camera: Camera? =
        Camera.getDefaultCamera(LabelCapture.createRecommendedCameraSettings())?.also {
            dataCaptureContext.setFrameSource(it)
        }

    private val settings = labelCaptureSettings {
        label("perishable-product") {
            customBarcode("barcode") {
                setSymbologies(Symbology.EAN13_UPCA, Symbology.CODE128)
            }
            expiryDateText("expiry-date")
            totalPriceText("total-price") {
                isOptional(true)
            }
        }
    }

    private val labelCapture: LabelCapture = LabelCapture.forContext(dataCaptureContext, settings)

    fun setupDataCaptureView(view: DataCaptureView): DataCaptureView {
        val overlay = LabelCaptureBasicOverlay.withLabelCaptureForView(labelCapture, view)
        labelCapture.addListener(object : LabelCaptureListener {
            override fun onSessionUpdated(
                labelCapture: LabelCapture,
                session: LabelCaptureSession,
                frameData: FrameData,
            ) {
                val capturedLabel = session.capturedLabels.firstOrNull() ?: return
                val barcodeData = capturedLabel.fields.find { it.name == "barcode" }?.barcode?.data
                val expiryDate = capturedLabel.fields.find { it.name == "expiry-date" }?.asDate()

                labelCapture.isEnabled = false
                // Surface barcodeData / expiryDate to the UI on the main thread.
            }
        })
        return view
    }

    fun onStarted() {
        labelCapture.isEnabled = true
        camera?.switchToDesiredState(FrameSourceState.ON)
    }

    fun onStopped() {
        camera?.switchToDesiredState(FrameSourceState.OFF)
    }

    fun dispose() {
        labelCapture.isEnabled = false
        dataCaptureContext.removeMode(labelCapture)
        camera?.switchToDesiredState(FrameSourceState.OFF)
    }
}
```

Notes:

- Import ONLY the field builders the user actually selected.
- `DataCaptureContext.initialize(licenseKey)` is the KMP entry point (there is also `DataCaptureContext.forLicenseKey(licenseKey)` and `DataCaptureContext.sharedInstance` for the Compose path — see **Compose Multiplatform**). Do not use `DataCaptureContext.forDataCaptureContext(...)` — that symbol does not exist.
- `LabelCapture.forContext(dataCaptureContext, settings)` is the only mode constructor on KMP. There is no `LabelCapture.forDataCaptureContext(...)` (that is the Android-only name) and no async `applySettings` overload with a completion handler — `labelCapture.applySettings(settings)` is synchronous void on KMP.
- `onSessionUpdated` fires on every processed frame; `onLabelsScanned` fires only on frames where at least one label was scanned (or use the `LabelCapture.scannedLabels: Flow<List<CapturedLabel>>` extension to consume results as a cold `Flow` instead of a listener).
- Set `labelCapture.isEnabled = false` after a successful capture to prevent duplicate results; re-enable when ready to scan again.
- Bundle `label-text` if the label uses any pre-built field — see the Gradle rule above.

### Android host

```kotlin
import android.view.View
import android.view.ViewGroup
import com.kmp.datacapture.core.ui.toAndroidView

class ScanActivity : ComponentActivity() {
    private val screenModel = LabelScannerScreenModel()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val dataCaptureView = screenModel.setupDataCaptureView(
            DataCaptureView(this, screenModel.dataCaptureContext),
        )
        val nativeView: View = dataCaptureView.toAndroidView()
        (nativeView.parent as? ViewGroup)?.removeView(nativeView)
        setContentView(nativeView)
    }

    override fun onResume() {
        super.onResume()
        screenModel.onStarted()
    }

    override fun onPause() {
        super.onPause()
        screenModel.onStopped()
    }

    override fun onDestroy() {
        super.onDestroy()
        screenModel.dispose()
    }
}
```

`toAndroidView()` is an Android-only extension on `com.kmp.datacapture.core.ui.DataCaptureView` (`androidMain`), returning the underlying `android.view.View`; it is not visible from `commonMain` or iOS code.

### iOS host (SwiftUI)

```swift
import SwiftUI
import shared

private extension DataCaptureView {
    var hostView: UIView { toUIView() }
}

struct LabelScannerHost: View {
    @StateObject private var screenModelHolder = ScreenModelHolder()

    var body: some View {
        DataCaptureViewRepresentable {
            let dcView = screenModelHolder.model.setupDataCaptureView(
                view: DataCaptureView(dataCaptureContext: screenModelHolder.model.dataCaptureContext)
            )
            return dcView.hostView
        }
        .onAppear { screenModelHolder.model.onStarted() }
        .onDisappear { screenModelHolder.model.onStopped() }
    }
}
```

`DataCaptureView(dataCaptureContext:)` takes no host/context parameter on iOS (unlike Android, which needs an Android `Context`); `toUIView()` is a member on iOS returning the underlying `UIView`.

## Label definitions & fields

Every field builder shares a common base (`LabelFieldDefinitionBuilder`): `.isOptional(Boolean)`, `.setValueRegex(es)`, `.setHiddenProperty(ies)`, `.setNumberOfMandatoryInstances(Int?)`. Barcode-based builders (`BarcodeFieldBuilder`) additionally get `.setSymbology(Symbology)` / `.setSymbologies(vararg Symbology)`.

### `anchorRegex` vs `valueRegex`

- **`valueRegex`** — validates the *content* of the field (e.g. `\d{2}/\d{2}/\d{4}` for a date). Set with `.setValueRegex(es)` (`String` or `Regex` overloads).
- **`anchorRegex`** — identifies the *context* of the field (a keyword/phrase near the value, e.g. `EXP`, `Best Before`). Set with `.setAnchorRegex(es)` on `CustomBarcodeBuilder`, `CustomTextBuilder`, `DateTextBuilder`, `PackingDateTextBuilder`, `ExpiryDateTextBuilder`, `TotalPriceTextBuilder`, `UnitPriceTextBuilder`, and `WeightTextBuilder`.

**Pre-built fields ship with default value and anchor regexes.** Call `.resetAnchorRegexes()` on a text/custom-barcode builder to drop the default anchor keywords and rely solely on the value regex — useful when the label has no consistent keyword near the value.

**Keep regexes simple** — standard character classes/quantifiers/groups are supported; lookahead/lookbehind assertions are not and cause the pattern to silently fail to match.

### Constraining a field's location

`CustomBarcodeBuilder` and `CustomTextBuilder` additionally support `.setLocation(LabelFieldLocation)` (or the `(left, top, right, bottom)` / `Rect` overloads) to restrict where on the label a field is searched for. `LabelFieldLocation` (`com.kmp.datacapture.label.capture.LabelFieldLocation`) has factory functions for the label's corners/edges/center: `.topLeft()`, `.topRight()`, `.bottomLeft()`, `.bottomRight()`, `.top()`, `.right()`, `.bottom()`, `.left()`, `.center()`, `.wholeLabel()`.

### Date fields

`DateTextBuilder`, `ExpiryDateTextBuilder`, and `PackingDateTextBuilder` each take `.setLabelDateFormat(LabelDateFormat(componentFormat, acceptPartialDates))`:

```kotlin
import com.kmp.datacapture.label.definition.LabelDateComponentFormat
import com.kmp.datacapture.label.definition.LabelDateFormat

expiryDateText("expiry-date") {
    setLabelDateFormat(LabelDateFormat(LabelDateComponentFormat.MDY, acceptPartialDates = false))
}
```

`LabelDateComponentFormat` is `DMY` / `MDY` / `YMD`.

### The Kotlin DSL vs the fluent builder

Both are equivalent; the DSL is sugar over the fluent builder and does not add any new native binding:

```kotlin
// Fluent
val settings = LabelCaptureSettingsBuilder()
    .addLabel(
        LabelDefinitionBuilder()
            .addCustomBarcode().setSymbologies(Symbology.EAN13_UPCA).build("barcode")
            .let { /* … */ }
    )
    .build()

// DSL — prefer this form
val settings = labelCaptureSettings {
    label("perishable-product") {
        customBarcode("barcode") { setSymbologies(Symbology.EAN13_UPCA) }
        expiryDateText("expiry-date")
    }
}
```

### Constructing `LabelCaptureSettings` directly from definitions

`LabelCaptureSettings(definitions: List<LabelDefinition>)` is also a public constructor when you already have one or more built `LabelDefinition` instances (e.g. a mix of custom-built and pre-built factory definitions):

```kotlin
val settings = LabelCaptureSettings(listOf(retailLabel, LabelDefinition.createVinLabelDefinition("vehicle-vin")))
```

## Handling results

- **`LabelCaptureListener`** (`com.kmp.datacapture.label.capture`): `onLabelsScanned(labelCapture, session, frameData)` fires only on frames with at least one scanned label; `onSessionUpdated(labelCapture, session, frameData)` fires on every processed frame (the list may be empty). `onObservationStarted` / `onObservationStopped` are optional lifecycle hooks. Register with `labelCapture.addListener(...)`, remove with `labelCapture.removeListener(...)`.
- **`LabelCapture.scannedLabels`** — a cold `Flow<List<CapturedLabel>>` extension property that wraps a `LabelCaptureListener` for Flow-based consumption; each collector gets its own listener. Share with `.shareIn(scope, SharingStarted.WhileSubscribed())` if multiple coroutines need the same stream.
- **`LabelCaptureSession`**: `capturedLabels: List<CapturedLabel>`, `lastProcessedFrameId: Int`, `frameSequenceID: Int`.
- **`CapturedLabel`**: `name`, `fields: List<LabelField>`, `isComplete: Boolean`, `location: Quadrilateral`, `trackingId: Int`, `deltaTimeToPrediction: Double`.
- **`LabelField`**: `name`, `type: LabelFieldType` (`BARCODE` / `TEXT` / `UNKNOWN`), `state: LabelFieldState` (`CAPTURED` / `PREDICTED` / `UNKNOWN`), `barcode: Barcode?`, `text: String?`, `location: Quadrilateral`, `isRequired: Boolean`, `valueType: LabelFieldValueType?` (populated on **iOS only** — always `null` on Android; do not rely on it cross-platform), and `fun asDate(): LabelDateResult?`.
- **`LabelDateResult`**: `day: Int?`, `month: Int?`, `year: Int?`, plus string fallbacks `dayString`/`monthString`/`yearString` for when the numeric components aren't available.
- Read a captured value by field type: `field.barcode?.data` for barcode fields, `field.text` for text fields, `field.asDate()` for date fields. There is no `asText()` — the text value is the `.text` property.
- `onSessionUpdated`/`onLabelsScanned` may run off the main thread on either platform — dispatch UI updates accordingly.

## Overlays

Every overlay factory has two forms: `withLabelCapture(labelCapture)` (viewless — add later via `view.addOverlay(overlay)`) and `withLabelCaptureForView(labelCapture, view)` (binds to the view immediately). All overlay types implement `com.kmp.datacapture.core.ui.DataCaptureOverlay`.

### Basic Overlay

```kotlin
import com.kmp.datacapture.label.ui.overlay.LabelCaptureBasicOverlay
import com.kmp.datacapture.label.ui.overlay.LabelCaptureBasicOverlayListener

val overlay = LabelCaptureBasicOverlay.withLabelCaptureForView(labelCapture, view)
overlay.listener = object : LabelCaptureBasicOverlayListener {
    override fun brushForField(overlay: LabelCaptureBasicOverlay, field: LabelField, label: CapturedLabel): Brush? =
        if (field.name == "barcode") Brush(fillColor = Color.fromRgba(0, 255, 255, 64), strokeColor = Color.fromRgba(0, 255, 255, 255), strokeWidth = 2f) else null

    override fun brushForLabel(overlay: LabelCaptureBasicOverlay, label: CapturedLabel): Brush? = null
}
```

- `Brush(fillColor: Color, strokeColor: Color, strokeWidth: Float)` — `com.kmp.datacapture.core.ui.style.Brush`. There's also a no-arg `Brush()` and `Brush.transparent()`.
- Returning `null` from `brushForField`/`brushForLabel` keeps the default brush. `overlay.labelBrush`, `overlay.capturedFieldBrush`, `overlay.predictedFieldBrush` are settable `var`s used when the listener isn't set (or returns `null`); `LabelCaptureBasicOverlay.defaultLabelBrush()` / `defaultCapturedFieldBrush()` / `defaultPredictedFieldBrush()` are the static defaults.
- `overlay.setBrushForField(brush, field, label)` / `overlay.setBrushForLabel(brush, label)` set a one-off brush for a specific field/label instance, taking precedence over the listener.
- `overlay.shouldShowScanAreaGuides` (debug only) and `overlay.viewfinder: Viewfinder?` are also available.
- `onLabelTapped(overlay, label)` on the listener fires when a label is tapped, if supported by the host.

### Advanced Overlay (floating AR views)

```kotlin
import com.kmp.datacapture.core.common.geometry.Anchor
import com.kmp.datacapture.core.common.geometry.FloatWithUnit
import com.kmp.datacapture.core.common.geometry.MeasureUnit
import com.kmp.datacapture.core.common.geometry.PointWithUnit
import com.kmp.datacapture.label.ui.overlay.LabelCaptureAdvancedOverlay
import com.kmp.datacapture.label.ui.overlay.LabelCaptureAdvancedOverlayListener

val overlay = LabelCaptureAdvancedOverlay.withLabelCaptureForView(labelCapture, view)
```

**The per-field listener callback carries no label context** — `viewForCapturedLabelField(overlay, labelField)` receives only the `LabelField`, not its parent `CapturedLabel`. If the view you want to float depends on sibling fields (e.g. a status icon whose color depends on both the price and the barcode), don't try to build it from that callback; instead push it imperatively from `onSessionUpdated`:

```kotlin
overlay.setViewForCapturedLabelField(field, capturedLabel, nativeView)
overlay.setAnchorForCapturedLabelField(field, capturedLabel, Anchor.TOP_CENTER)
overlay.setOffsetForCapturedLabelField(field, capturedLabel, PointWithUnit(FloatWithUnit(0f, MeasureUnit.PIXEL), FloatWithUnit(-8f, MeasureUnit.PIXEL)))
```

The **per-label** callback (`viewForCapturedLabel(overlay, capturedLabel)`) *does* receive the whole `CapturedLabel`, so sibling-field state is available there — the no-context trap applies only to the per-field callback. `NativeView` is `android.view.View` on Android / `UIView` on iOS — construct it in platform code and pass it through the shared API. `overlay.clearCapturedLabelViews()` clears everything.

Anchor placement: the view is centered on the anchor point, and a positive Y offset moves it downward (e.g. `Anchor.BOTTOM_CENTER` + a positive-Y `PointWithUnit` pushes a summary card fully below the label).

### Validation Flow Overlay

Guided scanning with a live checklist of captured/missing fields and manual-entry fallback for fields that can't be scanned. **Works with a single label definition only.**

```kotlin
import com.kmp.datacapture.label.ui.overlay.LabelCaptureValidationFlowOverlay
import com.kmp.datacapture.label.ui.overlay.LabelCaptureValidationFlowListener
import com.kmp.datacapture.label.ui.overlay.LabelCaptureValidationFlowSettings

val validationFlowOverlay = LabelCaptureValidationFlowOverlay.withLabelCaptureForView(labelCapture, view)

val validationFlowSettings = LabelCaptureValidationFlowSettings.labelCaptureValidationFlowSettings()
validationFlowSettings.setPlaceholderTextForLabelDefinition("expiry-date", "MM/DD/YYYY")
validationFlowOverlay.applySettings(validationFlowSettings)

validationFlowOverlay.listener = object : LabelCaptureValidationFlowListener {
    override fun onValidationFlowLabelCaptured(overlay: LabelCaptureValidationFlowOverlay, fields: List<LabelField>) {
        // The SDK has already paused the camera and disabled the mode at this point.
        val barcodeData = fields.find { it.name == "barcode" }?.barcode?.data
        val expiryDate = fields.find { it.name == "expiry-date" }?.asDate()
    }
}
```

- Do not also add a plain `LabelCaptureListener` alongside the Validation Flow overlay to read results — the overlay owns the capture lifecycle; results come only through `onValidationFlowLabelCaptured`.
- `validationFlowOverlay.onResume()` / `.onPause()` forward the host's resume/pause lifecycle — call them from the Android host's `onResume`/`onPause` (the sample's pattern). They are **no-ops on iOS**, which manages its own lifecycle internally.
- `validationFlowOverlay.applyCurrentSettings()` re-applies the most recently applied settings, useful after deserialization; also a no-op on iOS (which applies settings immediately).
- `shouldHandleKeyboardInsetsInternally: Boolean` — relevant for Android 15 edge-to-edge; has no effect on iOS.
- Optional listener callbacks: `onManualInputSubmitted(overlay, field, oldValue, newValue)` and `onValidationFlowResultUpdate(overlay, type, fields, frameData)` (`type` is `LabelResultUpdateType.Sync` for synchronous capture, or a matching `AsyncStarted`/`AsyncFinished(id)` pair for asynchronous capture).
- **Combining with the Basic Overlay:** the Validation Flow overlay draws no field highlighting itself. Attach a `LabelCaptureBasicOverlay` alongside it on the same `DataCaptureView` (as the official sample does — see the `transparentBrush` label-brush trick to hide the whole-label box while still coloring individual fields) for brand-color outlines; keep the VF overlay as the sole result-reporting path.
- `LabelCaptureValidationFlowSettings` text properties: `standbyHintText`, `validationHintText`, `validationErrorText`, `finishButtonText`, `restartButtonText`, `pauseButtonText`, `scanningText`, `adaptiveScanningText`, `missingFieldsHintText` / `requiredFieldErrorText` / `manualInputButtonText` (all three deprecated since 8.2 and no longer used).

### Adaptive Recognition Overlay (BETA)

> The Adaptive Recognition API is still in **BETA** and may change in future SDK versions. It requires a license key with the Adaptive Recognition Engine (ARE) feature flag; enabling it for production requires contacting **support@scandit.com**.

The **Adaptive Recognition Engine** is a cloud-hosted fallback model that Label Capture automatically triggers whenever the on-device model fails to capture data, making recognition more robust on worn/low-contrast labels or unstructured layouts (e.g. full receipts).

There are two ways to opt in:

1. **Per-field-definition fallback** — set `.adaptiveRecognition(AdaptiveRecognitionMode.AUTO)` on `LabelDefinitionBuilder` (or the settable `labelDefinition.adaptiveRecognitionMode` property after the definition is built). This augments the existing Basic/Advanced/Validation-Flow overlay flow — no separate overlay needed.
2. **Structured Adaptive Recognition overlay** — for scenarios like receipt scanning where the whole capture flow (not just one field) is driven by the cloud model:

```kotlin
import com.kmp.datacapture.label.adaptive.AdaptiveRecognitionResultType
import com.kmp.datacapture.label.adaptive.LabelCaptureAdaptiveRecognitionOverlay
import com.kmp.datacapture.label.adaptive.LabelCaptureAdaptiveRecognitionListener
import com.kmp.datacapture.label.adaptive.LabelCaptureAdaptiveRecognitionSettings
import com.kmp.datacapture.label.adaptive.ReceiptScanningResult

val settings = LabelCaptureAdaptiveRecognitionSettings.labelCaptureAdaptiveRecognitionSettings().apply {
    resultType = AdaptiveRecognitionResultType.RECEIPT
}
val overlay = LabelCaptureAdaptiveRecognitionOverlay.withLabelCaptureAndSettings(labelCapture, settings)
overlay.listener = object : LabelCaptureAdaptiveRecognitionListener {
    override fun onResultReceived(overlay: LabelCaptureAdaptiveRecognitionOverlay, result: AdaptiveRecognitionResult) {
        val receipt = result as? ReceiptScanningResult ?: return
        val storeName = receipt.storeName
        val total = receipt.paymentTotal
        val lineItems = receipt.lineItems // List<ReceiptScanningLineItem>
    }
    override fun onFailure(overlay: LabelCaptureAdaptiveRecognitionOverlay) {}
}
```

`onResultReceived`'s `result` parameter is the sealed base type `AdaptiveRecognitionResult` (only `resultType: AdaptiveRecognitionResultType` and `toNative()`) — narrow it with `as?`/`as` to `ReceiptScanningResult`, do not type the override parameter itself as `ReceiptScanningResult` (that does not compile — the interface signature is fixed). `ReceiptScanningResult` fields: `storeName`, `storeCity`, `storeAddress`, `date`, `time`, `paymentPreTaxTotal`, `paymentTax`, `paymentTotal`, `loyaltyNumber`, `lineItems: List<ReceiptScanningLineItem>` (each with `name`, `unitPrice`, `discount`, `quantity`, `totalPrice`). `AdaptiveRecognitionResultType` currently has only `RECEIPT`.

`overlay.onResume()` / `.onPause()` forward the host's lifecycle (Android is inert until `onResume()` starts scanning; no-op on iOS).

## Compose Multiplatform

The `com.scandit.datacapture.kmp:label-compose` module exposes Label Capture as a `@Composable` function, built on `core-compose`. Add both to `commonMain`:

```kotlin
commonMain.dependencies {
    implementation("com.scandit.datacapture.kmp:core-compose:<version>")
    implementation("com.scandit.datacapture.kmp:label-compose:<version>")
}
```

The high-level composable picks its overlay declaratively via `LabelOverlayStyle` (`Basic` / `Advanced` / `ValidationFlow` / `AdaptiveRecognition`):

```kotlin
import com.kmp.datacapture.label.capture.labelCaptureSettings
import com.kmp.datacapture.label.compose.LabelCaptureView
import com.kmp.datacapture.label.compose.LabelOverlayStyle

@Composable
fun LabelScannerScreen() {
    LabelCaptureView(
        settings = labelCaptureSettings {
            label("perishable-product") {
                customBarcode("barcode") { setSymbologies(Symbology.EAN13_UPCA) }
                expiryDateText("expiry-date")
            }
        },
        modifier = Modifier.fillMaxSize(),
        overlayStyle = LabelOverlayStyle.Basic,
        onCapture = { capturedLabels -> /* handle captured labels */ },
    )
}
```

`onCapture` is invoked with `List<CapturedLabel>` for each frame where at least one label was scanned (the `onLabelsScanned` semantics, not `onSessionUpdated`); `overlayStyle = LabelOverlayStyle.AdaptiveRecognition` additionally requires a non-null `adaptiveSettings: LabelCaptureAdaptiveRecognitionSettings` parameter or the composable throws `IllegalArgumentException`. Camera-on is the final mount step and camera-off runs first on dispose; the mode, its listener, and the overlay are all torn down automatically on dispose.

For finer control, the module also exposes the building blocks the high-level composable is built from — use these when you need custom overlay content layered on top, or a different overlay lifecycle than the all-in-one composable provides:

- `rememberLabelCapture(context, settings)` — creates and remembers a `LabelCapture` mode, removed from the context on dispose.
- `rememberLabelCaptureBasicOverlay(labelCapture, view)`, `rememberLabelCaptureAdvancedOverlay(labelCapture, view)`, `rememberLabelCaptureValidationFlowOverlay(labelCapture, view)`, `rememberLabelCaptureAdaptiveRecognitionOverlay(labelCapture, settings)` — one remembered overlay instance per style; `view` is the base-module `DataCaptureView` to bind to (nullable — omit for a viewless overlay you add later).
- `rememberCamera(context, position)` — remembers a `Camera` at the given `CameraPosition` (default `WORLD_FACING`), configured with `LabelCapture.createRecommendedCameraSettings()`, and ties its on/off lifecycle to the composition.

`DataCaptureContext.sharedInstance` is the typical `context` default for Compose call sites that don't manage their own context.

## Lifecycle & Teardown

- **Android**: forward `onResume`/`onPause` (or the equivalent Compose `DisposableEffect`/`LifecycleEventObserver`) to turn the camera on/off (`camera.switchToDesiredState(FrameSourceState.ON/OFF)`) and to re-arm/disarm `labelCapture.isEnabled`. If a Validation Flow overlay is attached, also forward to `validationFlowOverlay.onResume()`/`.onPause()`.
- **iOS**: `onAppear`/`onDisappear` (SwiftUI) map to the same `onStarted()`/`onStopped()` calls on the shared model — the Validation Flow's `onResume()`/`onPause()` are no-ops there, since the native overlay manages its own lifecycle.
- **Composition leave vs. Activity pause are two different events** — on Android, navigating back within the same Activity does not fire `onPause`. Always tear down explicitly in `onDispose`/`deinit` (or the shared model's `dispose()`) in addition to the pause/resume forwarding, or repeated visits will leak modes onto the shared `DataCaptureContext` and slow scanning down over time.
- `dispose()` on the shared model should, in order: disable the mode, tear down any Validation Flow overlay (`onPause()`), remove the mode from the context (`dataCaptureContext.removeMode(labelCapture)`), and switch the camera off. See `LabelScannerScreenModel.dispose()` in the official sample.
- SwiftUI re-runs the containing `View`'s `init()` on every body recomputation — hold the shared `ScreenModel` in a `@StateObject`, not a plain stored property, or a fresh model gets constructed on every recomposition while any `@StateObject` observer stays attached to the original.

## Pitfalls

- **App crashes on launch when the label definition is built** — the label uses a pre-built field (any text-field builder, or a barcode-semantic field like `serialNumberBarcode`/`imeiOneBarcode`), or a pre-built whole-label definition, but `com.scandit.datacapture.kmp:label-text` is missing from `commonMain.dependencies` (or, on iOS, the SPM `label` product wasn't added). This is the single most common Label Capture crash, on both platforms.
- **Price capture "builds and launches but never scans"** — `createPriceCaptureDefinition` needs `com.scandit.datacapture.kmp:price-label` *in addition to* `label-text`. Missing it is a silent runtime failure, not a compile error.
- **Black / blank camera preview, no error** — the runtime camera permission was never granted, or the camera was never switched on. Confirm the platform permission flow ran before `camera.switchToDesiredState(FrameSourceState.ON)`, that `dataCaptureContext.setFrameSource(camera)` was called, and that `Camera.getDefaultCamera(...)` did not return `null`.
- **Camera preview shows but nothing is ever captured** — confirm the `DataCaptureView` was actually embedded (`toAndroidView()`/`toUIView()` called and added to the view hierarchy) and an overlay was attached, `labelCapture.isEnabled` is `true`, and the mode wasn't left disabled after a previous capture.
- **A field never matches** — the `valueRegex`/`anchorRegex` doesn't match the real label; prefer the pre-built field (its regexes are tuned), or call `.resetAnchorRegexes()` if there's no consistent keyword near the value. Lookahead/lookbehind in a regex silently fails to match.
- **Handwritten text is never read** — expected; Label Capture reads printed text only. Point the user at the Validation Flow's manual-entry fallback.
- **Compose: overlay rebuilt every frame / camera flicker** — key `remember`/`rememberLabelCapture*` calls on the mode and view, not on a freshly-allocated `settings` instance passed in from a recomposition; the high-level `LabelCaptureView` composable already keys correctly, but hand-rolled compositions using the `remember*` building blocks must do the same.
- **Reusing single-platform Android/iOS snippets verbatim** — `LabelCapture.forDataCaptureContext(...)`, an Android `LabelCaptureBasicOverlay.newInstance(...)`, or a Swift `LabelCaptureValidationFlowOverlay(labelCapture:view:)` initializer do not exist on the KMP `expect`/`actual` surface. Use `LabelCapture.forContext(...)` and the `withLabelCapture(ForView)(...)` factories documented above instead.
