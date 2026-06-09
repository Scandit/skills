# Label Capture Android Integration Guide

Label Capture (Smart Label Capture) extracts multiple fields from a single label in one scan — e.g. a barcode, an expiry date, and a total price on a grocery label. You declare the structure of the label (which fields, required/optional, barcode symbologies or text regex) and the SDK returns all matched fields per frame.

> **Label Capture reads printed text only.** Handwritten text is not supported.

## Starting from zero? Read the official sample first

If the user has no Label Capture code yet, the fastest path to a *correct* integration is the official Android sample — it already has the right project structure, the right Gradle dependencies, the recommended camera settings, and both overlay types wired up. Before writing integration code from scratch, fetch and read the sample so your code matches a known-good shape rather than your memory:

- **LabelCaptureSimpleSample:** <https://github.com/Scandit/datacapture-android-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample>

The sample's `build.gradle` shows the canonical dependency set, and `data/LabelCaptureProvider.kt` shows how the label definition and overlays are built (including a commented-out IMEI / serial-number definition for smart-device boxes). If the user already has a project to add Label Capture to, read their existing files and follow the steps below, but still treat the sample as the reference for anything you're unsure about.

## Prerequisites

- Android Studio with Kotlin support.
- A valid Scandit license key:
  - Sign in at <https://ssl.scandit.com> to generate one.
  - No account yet? Sign up at <https://ssl.scandit.com/dashboard/sign-up?p=test>.

### Gradle setup

```kotlin
dependencies {
    implementation("com.scandit.datacapture:core:<version>")
    implementation("com.scandit.datacapture:barcode:<version>")
    implementation("com.scandit.datacapture:label:<version>")
    // See the rule below for when label-text-models is required.
    implementation("com.scandit.datacapture:label-text-models:<version>")
}
```

Replace `<version>` with the current SDK version (e.g. `8.3.1`). All artifacts must use the same version. Read `app/build.gradle` or `app/build.gradle.kts` to find the version already in use.

#### When is `label-text-models` required? (read this — it is a common crash)

`label-text-models` ships the on-device models that back Label Capture's *semantic* field recognition. The rule is **not** "only if there's a text field." A label that uses any pre-built **barcode-semantic** field — `addSerialNumberBarcode()`, `addPartNumberBarcode()`, `addImeiOneBarcode()`, `addImeiTwoBarcode()` — needs the model artifact too, even though those are "barcode" fields. Without it, the app **crashes at launch** when the label definition is built.

Practical rule, and the safe default:

- **Include `label-text-models`** whenever the label uses *any* pre-built field — every `add*Text()` field **and** every pre-built barcode field (serial number, part number, IMEI 1/2) — or any pre-built whole-label definition (see below). The official sample bundles it unconditionally for exactly this reason.
- **You can omit it only** for a label whose fields are *exclusively* `addCustomBarcode()` (a raw symbology read with no semantic extraction). If in doubt, include it — a barcode-only label still works with the artifact present; a semantic label crashes without it.

### Camera permission

Add to `AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.CAMERA" />
```

Request the `CAMERA` permission at runtime before starting the camera (use `ActivityResultContracts.RequestPermission` or the legacy `requestPermissions` approach).

## Prefer pre-built over custom — do not hallucinate regex

Label Capture has a tuned builder for most things people scan. When the user's request matches one, use it: the pre-built field carries default `valueRegexes` and `anchorRegexes` validated against real labels in the supported languages, so it will out-perform anything you hand-write — and reaching for a custom field with a guessed regex is the most common way these integrations go wrong. Only use `addCustomBarcode()` / `addCustomText()` when nothing pre-built covers the field.

### Step 0 — Is the *whole label* a pre-built definition?

Before composing fields one by one, check whether the entire label is one Scandit already ships as a factory on `LabelDefinition`. These return a complete, tuned definition that you pass straight into `addLabel(...)` — no manual field assembly, no guessed regex:

| User says… | Use this factory |
|---|---|
| "retail **price label**", "shelf label", "price tag" (price + barcode + unit/total price) | `LabelDefinition.createPriceCaptureDefinition("price-label")` |
| "**VIN**", "vehicle identification number" label | `LabelDefinition.createVinLabelDefinition("vehicle-vin")` |
| "**seven-segment** display", LCD/LED meter readout | `LabelDefinition.createSevenSegmentDisplayLabelDefinition("display")` |

```kotlin
import com.scandit.datacapture.label.capture.LabelDefinition   // verified against SDK 8.4.0

val settings = LabelCaptureSettings.builder()
    .addLabel(LabelDefinition.createPriceCaptureDefinition("price-label"))
    .build()
```

`LabelDefinition` lives in `com.scandit.datacapture.label.capture` (the same package as `LabelCaptureSettings`) — not `com.scandit.datacapture.label` and not `...label.data`. Both wrong guesses fail to compile, so use the verified import above. Reach for `createPriceCaptureDefinition` for a price/shelf label rather than hand-assembling `addTotalPriceText()` — the factory is purpose-built for that scenario, the single fields are not.

**Reading fields from a pre-built definition — don't guess the field names.** A factory definition ships with its own fixed set of fields, and their names are decided by the SDK, not by you (the label name you pass in is just the label's name, not the field names). Hardcoding a guessed name like `"SKU"` or `"priceText"` silently returns `null` if you guess wrong. Instead, iterate the captured fields and read them generically:

```kotlin
val capturedLabel = session.capturedLabels.firstOrNull() ?: return
for (field in capturedLabel.fields) {
    val value = field.barcode?.data ?: field.text   // barcode fields expose .barcode?.data; text fields, .text
    // field.name tells you which field this is — log them once to learn the exact names
}
```

If the user needs to branch on specific fields, confirm the exact field names for that factory from the [Label Definitions](https://docs.scandit.com/sdks/android/label-capture/label-definitions/) page or the sample before hardcoding them.

If no whole-label factory fits, build the label from fields — preferring pre-built fields per the catalogue below.

## Interactive Label Definition

Before writing any code, walk the user through their label. Ask one question at a time.

**Question A — What's on your label?** Present this checklist and ask the user to pick everything that applies. As they answer, map each item to its **pre-built** builder first.

*Barcode fields:*

- `addCustomBarcode()` — any barcode, user chooses symbologies (use only when none of the below fit)
- `addSerialNumberBarcode()` — serial number (preset symbologies + regex)
- `addPartNumberBarcode()` — part number
- `addImeiOneBarcode()` — IMEI 1 (typically smartphone / electronics boxes)
- `addImeiTwoBarcode()` — IMEI 2

*Text fields (preset recognisers):*

- `addExpiryDateText()` — expiry date (with optional date format)
- `addPackingDateText()` — packing / production date
- `addDateText()` — generic date (when it's a date but not specifically expiry or packing)
- `addTotalPriceText()` — total price
- `addUnitPriceText()` — unit price
- `addWeightText()` — weight

*Text fields (custom — last resort):*

- `addCustomText()` — any text; user provides a value regex. Use only when no preset recogniser matches the field.

**Question B — For each selected field:**
- Is it **required** or **optional**? (required = label is not considered captured until this field matches; optional = captured when/if it matches). Call `.isOptional(true)` for optional fields; required is the default.
- For `addCustomBarcode()`: which **symbologies**? Enabling only the symbologies actually needed improves scanning performance and accuracy. Android symbology names use underscores: `Symbology.EAN13_UPCA`, `Symbology.CODE128`, `Symbology.GS1_DATABAR_EXPANDED`, etc.
- For `addCustomText()`: what **value regex** should the text match?
- For `addExpiryDateText()` (and other date fields): does the user need a specific date format? If so, ask for the component order (MDY, DMY, YMD, etc.) and whether partial dates are accepted.

**Question C — Which file should the integration code go in?** Then write the code directly into that file. Do not just show it in chat.

## anchorRegex vs valueRegex

Every text field definition has two kinds of regex:

- **`valueRegex`** — validates the *content* of the field: the actual data to extract (e.g. `\d{2}/\d{2}/\d{4}` for a date).
- **`anchorRegex`** — identifies the *context* of the field: the keyword/phrase near the value (e.g. `EXP`, `Best Before`, `Poids`). The SDK uses it to disambiguate when several fields on the label could match the same value pattern (e.g. a packing date and an expiry date that look identical).

**Pre-built fields ship with default value and anchor regexes** tuned for their type — that is exactly why you should prefer them. You can override with `.setValueRegex(...)` / `.setValueRegexes(...)` and `.setAnchorRegex(...)` / `.setAnchorRegexes(...)`, but only do so when the user's labels genuinely differ from the defaults.

**Resetting anchors** — call `.resetAnchorRegexes()` on a pre-built field to drop its default anchor keywords and rely solely on the value regex. Useful when the label has no consistent keyword near the value.

**Keep regexes simple.** The SDK regex engine supports standard character classes (`\d`, `[A-Z]`), quantifiers (`{2}`, `+`, `*`), and groups. Lookahead/lookbehind assertions are not supported and cause the pattern to fail to match.

## Constraint: cannot run alongside Barcode Capture

A `DataCaptureContext` can only have **one active mode at a time** — attaching both a `LabelCapture` and a `BarcodeCapture` mode to the same context makes it stop processing frames and report an error, so the two cannot run *simultaneously*.

The right fix depends on what the user actually wants:

- **"Read a barcode as well as the label fields"** — do **not** add a second mode. Add the barcode as a field inside the label definition (`addCustomBarcode()`, or a pre-built barcode field such as `addSerialNumberBarcode()`). Label Capture already reads barcodes, so a label field is the supported way to get standalone-barcode data alongside the other fields. This covers almost every case.
- **"Two genuinely separate scanning steps on the same screen"** (e.g. a "scan label" mode and a distinct "scan loose packages" mode the user toggles between) — keep one context/camera/view and switch the *active* mode with `dataCaptureContext.setMode(mode)` (it replaces the previously active mode), swapping the overlay to match. The camera stays on, so switching is seamless — but it is time-slicing, never concurrent recognition.

Lead with the first option; only reach for `setMode()` switching when the user truly needs two distinct modes rather than two kinds of data off one label.

## Minimal Integration (Android / Kotlin)

Once the user has answered Questions A, B, and C, generate the integration code. Substitute the placeholder field and label names based on the user's answers. (If the whole label is a pre-built definition, replace the `LabelCaptureSettings.builder()...build()` block with the single `addLabel(LabelDefinition.create…)` form shown earlier.)

```kotlin
import android.os.Bundle
import android.view.ViewGroup
import android.widget.FrameLayout
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.barcode.data.Symbology
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.data.FrameData
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.FrameSourceState
import com.scandit.datacapture.core.ui.DataCaptureView
import com.scandit.datacapture.label.capture.LabelCapture
import com.scandit.datacapture.label.capture.LabelCaptureListener
import com.scandit.datacapture.label.capture.LabelCaptureSession
import com.scandit.datacapture.label.capture.LabelCaptureSettings
import com.scandit.datacapture.label.ui.overlay.LabelCaptureBasicOverlay

class ScanActivity : AppCompatActivity() {

    private lateinit var dataCaptureContext: DataCaptureContext
    private lateinit var labelCapture: LabelCapture
    private lateinit var camera: Camera

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_scan)

        dataCaptureContext = DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

        val settings = LabelCaptureSettings.builder()
            .addLabel()
                .addCustomBarcode()
                    .setSymbologies(Symbology.EAN13_UPCA, Symbology.CODE128)
                .buildFluent("barcode")
                .addExpiryDateText()
                .buildFluent("expiry-date")
            .buildFluent("perishable-product")
            .build()

        labelCapture = LabelCapture.forDataCaptureContext(dataCaptureContext, settings)

        labelCapture.addListener(object : LabelCaptureListener {
            override fun onSessionUpdated(
                mode: LabelCapture,
                session: LabelCaptureSession,
                data: FrameData,
            ) {
                val capturedLabel = session.capturedLabels.firstOrNull() ?: return
                val barcodeData = capturedLabel.fields
                    .find { it.name == "barcode" }?.barcode?.data
                val expiryDate = capturedLabel.fields
                    .find { it.name == "expiry-date" }?.asDate()

                mode.isEnabled = false
                // Process barcodeData and expiryDate on the main thread
            }
        })

        val dataCaptureView = DataCaptureView.newInstance(this, dataCaptureContext)
        val container = findViewById<FrameLayout>(R.id.data_capture_container)
        container.addView(
            dataCaptureView,
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT,
        )
        LabelCaptureBasicOverlay.newInstance(labelCapture, dataCaptureView)

        camera = Camera.getDefaultCamera(LabelCapture.createRecommendedCameraSettings())
            ?: throw IllegalStateException("Failed to init camera!")
        dataCaptureContext.setFrameSource(camera)
    }

    override fun onResume() {
        super.onResume()
        camera.switchToDesiredState(FrameSourceState.ON)
    }

    override fun onPause() {
        super.onPause()
        camera.switchToDesiredState(FrameSourceState.OFF)
    }
}
```

Notes when generating this code:

- Import ONLY the field builders the user actually selected. Do not import unused ones.
- The builder method on `LabelCaptureSettings.builder().addLabel()` mirrors the field type: `addCustomBarcode()`, `addSerialNumberBarcode()`, `addPartNumberBarcode()`, `addImeiOneBarcode()`, `addImeiTwoBarcode()`, `addExpiryDateText()`, `addPackingDateText()`, `addDateText()`, `addTotalPriceText()`, `addUnitPriceText()`, `addWeightText()`, `addCustomText()`. Each is chained and terminated with `.buildFluent("<field-name>")`.
- Android symbology enum values use underscores: `Symbology.EAN13_UPCA`, `Symbology.CODE128`, `Symbology.GS1_DATABAR_EXPANDED`, `Symbology.QR`, `Symbology.DATA_MATRIX`, etc. Do NOT use camelCase forms.
- For `addCustomBarcode()`, use `.setSymbologies(Symbology.X, Symbology.Y, ...)` (vararg). For a single symbology, `.setSymbologies(Symbology.X)` is fine.
- For `addCustomText()`, use `.setValueRegexes("<pattern>")` (vararg). For multiple patterns, `.setValueRegexes("pattern1", "pattern2")`. Do NOT use `.setPatterns` or `.setPattern` — those names were renamed and no longer exist in v8+.
- For `addExpiryDateText()`, optionally call `.setLabelDateFormat(LabelDateFormat(LabelDateComponentFormat.MDY, false))` to control date parsing. Import `LabelDateFormat` and `LabelDateComponentFormat` from `com.scandit.datacapture.label.data`.
- Bundle `label-text-models` if the label uses any pre-built field (text OR barcode-semantic like serial/IMEI/part-number) — see the Gradle rule above. Only a label that uses exclusively `addCustomBarcode()` can omit it.
- Read captured values by field type: `field.barcode?.data` for barcode fields, `field.text` for text fields, and `field.asDate()` (returns a `LabelDateResult`, not a `java.util.Date`) for date fields. There is **no** `asText()` method — the text value is the `.text` property.
- `onSessionUpdated` is called on a background thread. Dispatch any UI updates to the main thread (e.g. with `runOnUiThread { }` or a coroutine).
- Set `mode.isEnabled = false` after a successful capture to prevent duplicate results.
- Re-enable the mode (e.g. `labelCapture.isEnabled = true`) when the user is ready to scan again.
- In a Fragment-based setup replace `AppCompatActivity` lifecycle hooks with Fragment lifecycle hooks; the camera and overlay setup logic is identical.

## Setup Checklist

After writing the integration code, show this checklist:

1. Add the Gradle dependencies to `app/build.gradle.kts` (see Prerequisites). Use the same version for all. Include `label-text-models` unless the label uses only `addCustomBarcode()`.
2. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from <https://ssl.scandit.com>.
3. Add the `CAMERA` permission to `AndroidManifest.xml` and request it at runtime before starting the camera.
4. Add a `FrameLayout` (or other container) with the id `data_capture_container` to your layout XML.

## Optional: Validation Flow

If the user wants a guided scanning experience with a live checklist of captured/missing fields, and the ability to manually enter values for missed fields without rescanning, enable the Validation Flow. Skip this section if the user is fine with the minimal scan-and-handle path above.

Replace `LabelCaptureBasicOverlay` with `LabelCaptureValidationFlowOverlay`, and implement `LabelCaptureValidationFlowListener` instead of `LabelCaptureListener`.

```kotlin
import com.scandit.datacapture.label.data.LabelField
import com.scandit.datacapture.label.ui.overlay.validation.LabelCaptureValidationFlowListener
import com.scandit.datacapture.label.ui.overlay.validation.LabelCaptureValidationFlowOverlay
import com.scandit.datacapture.label.ui.overlay.validation.LabelCaptureValidationFlowSettings

// In onCreate, after creating dataCaptureView:
val validationFlowSettings = LabelCaptureValidationFlowSettings.newInstance()
// Optional: set placeholder text shown in the manual-entry field for each label field
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

Add lifecycle delegation so the Validation Flow overlay can manage its own UI state:

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

You can also customize button labels and toast messages via `LabelCaptureValidationFlowSettings` properties:

```kotlin
validationFlowSettings.restartButtonText = "Restart"
validationFlowSettings.pauseButtonText = "Pause"
validationFlowSettings.finishButtonText = "Finish"
validationFlowSettings.standbyHintText = "No label detected, camera paused"
validationFlowSettings.validationHintText = "data fields collected"
validationFlowSettings.validationErrorText = "Incorrect format."
validationFlowSettings.scanningText = "Scan in progress"
validationFlowSettings.adaptiveScanningText = "Processing"
```

## Troubleshooting common failures

When the user reports a problem, map the symptom to its cause before suggesting code changes. The most common failures are environmental, not API misuse.

- **App crashes on launch when the label definition is built** — the label uses a pre-built field (any `add*Text()` field, or a barcode-semantic field such as `addSerialNumberBarcode()` / `addImeiOneBarcode()` / `addImeiTwoBarcode()` / `addPartNumberBarcode()`), or a pre-built whole-label definition, but the `com.scandit.datacapture:label-text-models` Gradle artifact is missing. These fields load an on-device model at runtime. Add the dependency at the same version as the other Scandit artifacts. See the Gradle rule above — this is the single most common Label Capture crash.

- **Black / blank camera preview, no error** — almost always the `CAMERA` runtime permission was never granted, or the camera was never switched on. Check that (1) `<uses-permission android:name="android.permission.CAMERA" />` is in `AndroidManifest.xml`, (2) the runtime permission is requested and granted **before** the camera is started, and (3) `camera.switchToDesiredState(FrameSourceState.ON)` runs in `onResume` after permission is granted. Also confirm `dataCaptureContext.setFrameSource(camera)` was called and that `Camera.getDefaultCamera(...)` did not return `null`.

- **Camera preview shows but nothing is ever captured** — verify the `DataCaptureView` was actually added to the view hierarchy and an overlay (`LabelCaptureBasicOverlay.newInstance(...)` or a Validation Flow overlay) was attached, that `labelCapture.isEnabled` is `true`, and that the mode was not left disabled after a previous capture (re-enable with `labelCapture.isEnabled = true`). Remember `onSessionUpdated` runs on a background thread — if your handler throws or blocks, it can look like nothing happens.

- **A field never matches** — the field's `valueRegex` or `anchorRegex` doesn't match the real label. Prefer the pre-built field for that data (its regexes are tuned) over a hand-written one. If the label has no keyword near the value, call `.resetAnchorRegexes()` on the field to drop the default anchor keywords and rely on the value regex alone. Keep regexes simple — lookahead/lookbehind are not supported and silently fail to match.

- **Handwritten text is never read** — this is expected. Label Capture reads **printed text only**; the on-device OCR and the Adaptive Recognition Engine do not recognise handwriting. Use the Validation Flow's manual-entry fallback so the user can type the value when it cannot be scanned (see `references/validation-flow.md`).

- **Context errors out when Barcode Capture is also active** — a `DataCaptureContext` runs only one active mode at a time. Model the extra barcode as a field inside the label definition instead of adding a second mode. See the "cannot run alongside Barcode Capture" section above.

For OCR accuracy problems on worn or low-contrast printed labels, the cloud-based Adaptive Recognition Engine (BETA) can be enabled as a fallback — see `references/advanced.md`.

## Where to Go Next

After the core integration is running, point the user at the right resource for follow-ups:

- [Label Definitions](https://docs.scandit.com/sdks/android/label-capture/label-definitions/) — full catalogue of pre-built text/barcode field types, the pre-built whole-label definitions, and how to tune their regex anchors and value patterns.
- [Advanced Configurations](https://docs.scandit.com/sdks/android/label-capture/advanced/) — Validation Flow customisation, adaptive recognition, custom overlays.
- [LabelCaptureSimpleSample](https://github.com/Scandit/datacapture-android-samples/tree/master/03_Advanced_Batch_Scanning_Samples/05_Smart_Label_Capture/LabelCaptureSimpleSample) — working reference sample (includes a commented-out IMEI / serial-number label definition).
