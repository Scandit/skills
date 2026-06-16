# BarcodeCapture Android Integration Guide

BarcodeCapture is the low-level single-barcode scanning mode. On Android you wire it up by hand: a `DataCaptureContext`, a `Camera` as the frame source, the `BarcodeCapture` mode with a `BarcodeCaptureListener`, a `DataCaptureView` for the camera preview, and a `BarcodeCaptureOverlay` for the highlight. Unlike SparkScan, there is no pre-built UI — the camera preview and highlight rectangle are the only visuals.

Examples below use Kotlin and an Activity. The same APIs work identically with Java and in Fragments — adapt ownership of `DataCaptureContext`, `BarcodeCapture`, and the `Camera` to the project's existing structure.

## Prerequisites

- Scandit Data Capture SDK for Android — add via Gradle. Before writing the dependency, fetch the latest published version from `https://central.sonatype.com/artifact/com.scandit.datacapture/barcode` and extract the latest version number from the page. Then add both dependencies to `app/build.gradle`:
  ```gradle
  dependencies {
      implementation "com.scandit.datacapture:barcode:<latest-version>"
      implementation "com.scandit.datacapture:core:<latest-version>"
  }
  ```
  Or in `app/build.gradle.kts`:
  ```kotlin
  dependencies {
      implementation("com.scandit.datacapture:barcode:<latest-version>")
      implementation("com.scandit.datacapture:core:<latest-version>")
  }
  ```
  The SDK is distributed via Maven Central.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permission in `AndroidManifest.xml`:
  ```xml
  <uses-feature
      android:name="android.hardware.camera"
      android:required="true" />
  <uses-permission android:name="android.permission.CAMERA" />
  ```
  Request the permission at runtime using the standard Android permission API before scanning starts.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which Activity or Fragment they'd like to integrate BarcodeCapture into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `implementation "com.scandit.datacapture:barcode:<version>"` and `implementation "com.scandit.datacapture:core:<version>"` to `app/build.gradle` (the version was already fetched and filled in above).
2. Add `<uses-permission android:name="android.permission.CAMERA" />` and the `<uses-feature>` element to `AndroidManifest.xml`.
3. Request the `CAMERA` permission at runtime before scanning starts.
4. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

## Step 1 — Create the DataCaptureContext

The `DataCaptureContext` is the central hub of the SDK. Construct it once and reuse the same reference for the lifetime of the scanning surface.

```kotlin
import com.scandit.datacapture.core.capture.DataCaptureContext

private val dataCaptureContext = DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
```

## Step 2 — Configure BarcodeCaptureSettings

Choose which barcode symbologies to scan. By default, all symbologies are disabled — enable each one explicitly. Only enable what you need; each extra symbology adds processing time.

```kotlin
import com.scandit.datacapture.barcode.capture.BarcodeCaptureSettings
import com.scandit.datacapture.barcode.data.Symbology

val settings = BarcodeCaptureSettings().apply {
    enableSymbology(Symbology.EAN13_UPCA, true)
    enableSymbology(Symbology.EAN8, true)
    enableSymbology(Symbology.UPCE, true)
    enableSymbology(Symbology.CODE39, true)
    enableSymbology(Symbology.CODE128, true)
}

// Optional: adjust active symbol counts for variable-length symbologies
val code39Settings = settings.getSymbologySettings(Symbology.CODE39)
code39Settings.activeSymbolCounts = setOf(7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20)
```

You can also enable a set of symbologies at once:
```kotlin
settings.enableSymbologies(setOf(Symbology.EAN13_UPCA, Symbology.CODE128))
```

### BarcodeCaptureSettings Members

| Member | Type | Description |
|--------|------|-------------|
| `enableSymbology(symbology, enabled)` | method | Enable or disable one symbology. |
| `enableSymbologies(symbologies)` | method | Enable a `Set<Symbology>` in one call. |
| `getSymbologySettings(symbology)` | method | Get per-symbology `SymbologySettings` (e.g. `activeSymbolCounts`). |
| `codeDuplicateFilter` | `TimeInterval` | Time window to suppress duplicate scans of the same code (e.g. `TimeInterval.millis(500)`). `TimeInterval.zero()` reports every detection; `TimeInterval.millis(-1)` reports each code only once until scanning stops. |

## Step 3 — Camera setup

`Camera.getDefaultCamera(cameraSettings)` returns the back camera pre-configured with the recommended settings. Attach it to the context via `setFrameSource`.

```kotlin
import com.scandit.datacapture.barcode.capture.BarcodeCapture
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.FrameSourceState

private val camera = Camera.getDefaultCamera(BarcodeCapture.createRecommendedCameraSettings())

init {
    dataCaptureContext.setFrameSource(camera)
}
```

Switch the camera on / off:

```kotlin
camera?.switchToDesiredState(FrameSourceState.ON)   // start preview / scanning
camera?.switchToDesiredState(FrameSourceState.OFF)  // release the camera
```

## Step 4 — Create the BarcodeCapture mode

```kotlin
import com.scandit.datacapture.barcode.capture.BarcodeCapture

private val barcodeCapture = BarcodeCapture.forDataCaptureContext(dataCaptureContext, settings)
```

Re-applying settings at runtime is done via `barcodeCapture.applySettings(newSettings)`.

### BarcodeCapture Members

| Member | Description |
|--------|-------------|
| `BarcodeCapture.forDataCaptureContext(context, settings)` | Factory — creates the mode and attaches it to the context. |
| `isEnabled` | Pause / resume scanning without tearing down the camera. |
| `feedback` | `BarcodeCaptureFeedback` — sound / vibration on success. |
| `applySettings(settings)` | Update settings at runtime. |
| `addListener(listener)` / `removeListener(listener)` | Register or remove a `BarcodeCaptureListener`. |
| `BarcodeCapture.createRecommendedCameraSettings()` | Static — returns the recommended `CameraSettings` for BarcodeCapture. |

## Step 5 — DataCaptureView and BarcodeCaptureOverlay

`DataCaptureView.newInstance(context, dataCaptureContext)` creates the camera preview. In an Activity, pass it directly to `setContentView`. `BarcodeCaptureOverlay.newInstance(barcodeCapture, dataCaptureView)` adds the highlight overlay to the view.

```kotlin
import com.scandit.datacapture.core.ui.DataCaptureView
import com.scandit.datacapture.barcode.ui.overlay.BarcodeCaptureOverlay

// In onCreate():
val dataCaptureView = DataCaptureView.newInstance(this, dataCaptureContext)
val overlay = BarcodeCaptureOverlay.newInstance(barcodeCapture, dataCaptureView)
setContentView(dataCaptureView)
```

In a Fragment, add the view to a container in your layout:
```kotlin
val dataCaptureView = DataCaptureView.newInstance(requireContext(), dataCaptureContext)
BarcodeCaptureOverlay.newInstance(barcodeCapture, dataCaptureView)
binding.scannerContainer.addView(dataCaptureView, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
```

### BarcodeCaptureOverlay Members

| Member | Description |
|--------|-------------|
| `BarcodeCaptureOverlay.newInstance(mode, view)` | Factory — creates the overlay and adds it to the view. |
| `brush` | `Brush` — fill / stroke for recognized-barcode highlights. |
| `viewfinder` | `Viewfinder?` — optional viewfinder drawn on the preview. |

## Step 6 — Implement BarcodeCaptureListener

Implement `BarcodeCaptureListener` on the Activity or a dedicated controller class.

```kotlin
import com.scandit.datacapture.barcode.capture.BarcodeCaptureListener
import com.scandit.datacapture.barcode.capture.BarcodeCaptureSession
import com.scandit.datacapture.core.data.FrameData

class BarcodeScanActivity : AppCompatActivity(), BarcodeCaptureListener {

    override fun onBarcodeScanned(
        barcodeCapture: BarcodeCapture,
        session: BarcodeCaptureSession,
        data: FrameData
    ) {
        val barcode = session.newlyRecognizedBarcode ?: return

        // Disable while we handle the scan, so duplicates don't fire.
        barcodeCapture.isEnabled = false

        // onBarcodeScanned is called on a background thread — dispatch UI work.
        runOnUiThread {
            // Handle the barcode: barcode.data, barcode.symbology
        }
    }

    override fun onSessionUpdated(
        barcodeCapture: BarcodeCapture,
        session: BarcodeCaptureSession,
        data: FrameData
    ) {
        // Called every frame; keep this fast.
    }

    override fun onObservationStarted(barcodeCapture: BarcodeCapture) {}
    override fun onObservationStopped(barcodeCapture: BarcodeCapture) {}
}
```

### BarcodeCaptureListener Interface

| Callback | Description |
|----------|-------------|
| `onBarcodeScanned(barcodeCapture, session, data)` | A barcode was recognized. Read it from `session.newlyRecognizedBarcode`. Called on a background thread. |
| `onSessionUpdated(barcodeCapture, session, data)` | Called for every processed frame. Keep work minimal. |
| `onObservationStarted(barcodeCapture)` | Listener was added. |
| `onObservationStopped(barcodeCapture)` | Listener was removed. |

### BarcodeCaptureSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `newlyRecognizedBarcode` | `Barcode?` | The barcode just scanned. |
| `newlyLocalizedBarcodes` | `List<LocalizedOnlyBarcode>` | Codes that were located but not decoded. |
| `frameSequenceId` | `Long` | Identifier of the current frame sequence. |

## Step 7 — Lifecycle management

Drive the camera from `onResume` and `onPause`. The camera must not be active while the app is in the background.

```kotlin
override fun onResume() {
    super.onResume()
    // Re-enable after returning from background.
    barcodeCapture.isEnabled = true
    camera?.switchToDesiredState(FrameSourceState.ON)
}

override fun onPause() {
    barcodeCapture.isEnabled = false
    camera?.switchToDesiredState(FrameSourceState.OFF)
    super.onPause()
}

override fun onDestroy() {
    barcodeCapture.removeListener(this)
    dataCaptureContext.removeCurrentMode()
    super.onDestroy()
}
```

## Complete minimal example

```kotlin
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.barcode.capture.*
import com.scandit.datacapture.barcode.data.Symbology
import com.scandit.datacapture.barcode.ui.overlay.BarcodeCaptureOverlay
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.data.FrameData
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.FrameSourceState
import com.scandit.datacapture.core.ui.DataCaptureView

class BarcodeScanActivity : AppCompatActivity(), BarcodeCaptureListener {

    private val dataCaptureContext =
        DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val camera = Camera.getDefaultCamera(BarcodeCapture.createRecommendedCameraSettings())

    private val barcodeCapture: BarcodeCapture

    init {
        dataCaptureContext.setFrameSource(camera)

        val settings = BarcodeCaptureSettings().apply {
            enableSymbology(Symbology.EAN13_UPCA, true)
            enableSymbology(Symbology.CODE128, true)
        }

        barcodeCapture = BarcodeCapture.forDataCaptureContext(dataCaptureContext, settings)
        barcodeCapture.addListener(this)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val dataCaptureView = DataCaptureView.newInstance(this, dataCaptureContext)
        BarcodeCaptureOverlay.newInstance(barcodeCapture, dataCaptureView)
        setContentView(dataCaptureView)
        // Request CAMERA permission here before scanning starts
    }

    override fun onResume() {
        super.onResume()
        barcodeCapture.isEnabled = true
        camera?.switchToDesiredState(FrameSourceState.ON)
    }

    override fun onPause() {
        barcodeCapture.isEnabled = false
        camera?.switchToDesiredState(FrameSourceState.OFF)
        super.onPause()
    }

    override fun onDestroy() {
        barcodeCapture.removeListener(this)
        dataCaptureContext.removeCurrentMode()
        super.onDestroy()
    }

    override fun onBarcodeScanned(
        barcodeCapture: BarcodeCapture,
        session: BarcodeCaptureSession,
        data: FrameData
    ) {
        val barcode = session.newlyRecognizedBarcode ?: return
        barcodeCapture.isEnabled = false
        runOnUiThread {
            // handle barcode.data and barcode.symbology
        }
    }

    override fun onSessionUpdated(barcodeCapture: BarcodeCapture, session: BarcodeCaptureSession, data: FrameData) {}
    override fun onObservationStarted(barcodeCapture: BarcodeCapture) {}
    override fun onObservationStopped(barcodeCapture: BarcodeCapture) {}
}
```

## Optional configuration

### Async work after a scan (coroutines)

When the scan result requires a network or database call, disable scanning immediately on the scanner thread, then use `lifecycleScope.launch` to do the async work on the main coroutine scope. Re-enable in a `finally` block so scanning always resumes even if the lookup fails.

```kotlin
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

override fun onBarcodeScanned(
    barcodeCapture: BarcodeCapture,
    session: BarcodeCaptureSession,
    data: FrameData
) {
    val barcodeData = session.newlyRecognizedBarcode?.data ?: return
    barcodeCapture.isEnabled = false  // prevent duplicate scans while lookup is in flight

    lifecycleScope.launch {           // safe to call from any thread; runs on Main
        try {
            val result = withContext(Dispatchers.IO) {
                // your network or database call here
            }
            // update UI with result — already on Main
        } finally {
            barcodeCapture.isEnabled = true
        }
    }
}
```

`lifecycleScope` is automatically cancelled when the Activity is destroyed — no manual cleanup needed. Add `implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")` to `build.gradle` if it is not already present.

### BarcodeCaptureFeedback

By default, BarcodeCapture beeps and vibrates on success. To customize feedback, replace `barcodeCapture.feedback`:

```kotlin
import com.scandit.datacapture.barcode.capture.BarcodeCaptureFeedback

// Suppress all feedback (silent mode):
barcodeCapture.feedback = BarcodeCaptureFeedback()

// Restore defaults:
barcodeCapture.feedback = BarcodeCaptureFeedback.defaultFeedback()
```

For per-result feedback (e.g. success sound only, no vibration), fetch the Advanced Configurations page — the exact `Feedback` constructor arguments need to be verified against the docs.

### Viewfinder

Attach a viewfinder to the overlay to draw a guide on the preview. Assign it to the `viewfinder` property of the `BarcodeCaptureOverlay`:

```kotlin
import com.scandit.datacapture.core.ui.viewfinder.RectangularViewfinder
import com.scandit.datacapture.core.ui.viewfinder.RectangularViewfinderStyle

overlay.viewfinder = RectangularViewfinder(RectangularViewfinderStyle.SQUARE)
```

**Aimer viewfinder** — a small crosshair/aimer with an embedded Scandit logo. Recommended when pairing with `RadiusLocationSelection`. `AimerViewfinder` has no constructor arguments; tune it via `frameColor` and `dotColor`.

```kotlin
import com.scandit.datacapture.core.ui.viewfinder.AimerViewfinder

overlay.viewfinder = AimerViewfinder()
```

**Laserline viewfinder** — a horizontal laser line with a Scandit logo underneath, centered on the view's point of interest. `LaserlineViewfinder` has no constructor arguments; tune it via `width`, `enabledColor`, and `disabledColor`.

```kotlin
import com.scandit.datacapture.core.ui.viewfinder.LaserlineViewfinder

overlay.viewfinder = LaserlineViewfinder()
```

| Viewfinder | Constructor | Tunable properties |
|------------|-------------|--------------------|
| `RectangularViewfinder` | `RectangularViewfinder(RectangularViewfinderStyle.SQUARE)` | style, color, dimming |
| `AimerViewfinder` | `AimerViewfinder()` | `frameColor`, `dotColor` |
| `LaserlineViewfinder` | `LaserlineViewfinder()` | `width`, `enabledColor`, `disabledColor` |

### CodeDuplicateFilter

Suppress duplicate scans of the same code within a time window. `-1` reports each code only once until scanning is stopped; `0` reports every detection. The value is a `TimeInterval`.

```kotlin
import com.scandit.datacapture.core.time.TimeInterval

settings.codeDuplicateFilter = TimeInterval.millis(500)  // suppress duplicates within 500 ms
```

Set this before calling `BarcodeCapture.forDataCaptureContext(dataCaptureContext, settings)`. To change at runtime, use `barcodeCapture.applySettings(newSettings)`.

### LocationSelection

To restrict scanning to a sub-area of the preview, assign an `ILocationSelection` to `settings.locationSelection`. Only barcodes inside the selected area are reported. Set it on the `BarcodeCaptureSettings` before constructing the mode (or re-apply via `barcodeCapture.applySettings(newSettings)`).

`RectangularLocationSelection` is created with a static factory — there is no public constructor. Use `withSize(SizeWithUnit)`, `withWidthAndAspectRatio(...)`, or `withHeightAndAspectRatio(...)`. Sizes use `DoubleWithUnit` with `MeasureUnit.FRACTION` for view-relative dimensions (or `MeasureUnit.DIP` / `MeasureUnit.PIXEL` for absolute).

```kotlin
import com.scandit.datacapture.core.area.RectangularLocationSelection
import com.scandit.datacapture.core.area.RadiusLocationSelection
import com.scandit.datacapture.core.geometry.MeasureUnit
import com.scandit.datacapture.core.geometry.DoubleWithUnit
import com.scandit.datacapture.core.geometry.SizeWithUnit

// A rectangle 90% of the view width by 30% of the view height, centered on the point of interest.
settings.locationSelection = RectangularLocationSelection.withSize(
    SizeWithUnit(
        DoubleWithUnit(0.9, MeasureUnit.FRACTION),
        DoubleWithUnit(0.3, MeasureUnit.FRACTION)
    )
)
```

`RadiusLocationSelection` selects codes touching a circle of the given radius, centered on the point of interest. It takes a single `DoubleWithUnit` radius (fractional radius is relative to the view's width):

```kotlin
settings.locationSelection = RadiusLocationSelection(DoubleWithUnit(0.2, MeasureUnit.FRACTION))
```

### Symbology extensions

Some symbologies support extensions that toggle symbology-specific behavior (e.g. Code 39 full ASCII, UPC-A leading-zero handling). Get the per-symbology `SymbologySettings` and call `setExtensionEnabled(extension, enabled)`:

```kotlin
settings.getSymbologySettings(Symbology.CODE39).setExtensionEnabled("full_ascii", true)
```

The set of currently enabled extensions is exposed read-only via `enabledExtensions`. See [Symbology Properties](https://docs.scandit.com/symbology-properties) for the list of supported extension names per symbology.

### Symbology checksums

Optional checksums are configured per symbology through `SymbologySettings.checksums`, an `EnumSet<Checksum>`. A code is accepted if any of the listed checksums matches in addition to any mandatory checksum. Checksum enum values are SCREAMING_SNAKE in Kotlin (e.g. `Checksum.MOD_43`, `Checksum.MOD_10`, `Checksum.MOD_11`).

```kotlin
import com.scandit.datacapture.barcode.data.Checksum
import java.util.EnumSet

settings.getSymbologySettings(Symbology.CODE39).checksums = EnumSet.of(Checksum.MOD_43)
```

### Active symbol counts

Variable-length 1D symbologies (Code 39, Code 128, ITF, etc.) only decode a default length range. To scan shorter or longer codes, set `SymbologySettings.activeSymbolCounts` to the desired `Set<Int>`. The setting is ignored for fixed-size symbologies (EAN/UPC) and 2D codes.

```kotlin
settings.getSymbologySettings(Symbology.CODE39).activeSymbolCounts =
    setOf(7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20)
```

### Color-inverted codes

By default only dark-on-bright codes are decoded. To also scan bright-on-dark (color-inverted) codes for a symbology, set `SymbologySettings.isColorInvertedEnabled = true`. The symbology must also be enabled (`isEnabled = true` / `enableSymbology(...)`).

```kotlin
settings.getSymbologySettings(Symbology.CODE128).isColorInvertedEnabled = true
```

### Reject / filter scanned barcodes

BarcodeCapture has no built-in reject API — implement rejection inside `onBarcodeScanned` by inspecting the barcode and choosing whether to act on it. To give visual feedback that a code was rejected (no highlight), set the overlay `brush` to a transparent brush; to highlight an accepted code, leave the default brush. A common pattern is to filter by `barcode.data`:

```kotlin
override fun onBarcodeScanned(
    barcodeCapture: BarcodeCapture,
    session: BarcodeCaptureSession,
    data: FrameData
) {
    val barcode = session.newlyRecognizedBarcode ?: return
    val code = barcode.data ?: return
    if (!code.startsWith("ACME-")) {
        // Reject: don't highlight, keep scanning.
        overlay.brush = Brush.TRANSPARENT
        return
    }
    overlay.brush = BarcodeCaptureOverlay.defaultBrush()
    barcodeCapture.isEnabled = false
    runOnUiThread { /* handle accepted code */ }
}
```

### Overlay brush

The `BarcodeCaptureOverlay.brush` property controls how a recognized barcode is highlighted. It is read-write — assign a Kotlin property, do not call a setter. Construct a `Brush(fillColor, strokeColor, strokeWidth)` from ARGB `android.graphics.Color` values. Use `Brush.TRANSPARENT` to draw nothing, or `BarcodeCaptureOverlay.defaultBrush()` to restore the default Scandit-blue highlight.

```kotlin
import android.graphics.Color
import com.scandit.datacapture.core.ui.style.Brush

// Green fill (alpha 50), solid green stroke, 2dp stroke width:
overlay.brush = Brush(Color.argb(128, 0, 200, 68), Color.rgb(0, 200, 68), 2f)

// Hide the highlight entirely:
overlay.brush = Brush.TRANSPARENT
```

### Composite codes

Composite codes (a linear/1D component plus a 2D companion such as a GS1 DataBar with a PDF417) require **both** the component symbologies **and** the composite types to be enabled on the `BarcodeCaptureSettings`:

1. Enable the symbologies for the composite types with `enableSymbologies(compositeTypes)` (Kotlin overload taking an `EnumSet<CompositeType>`).
2. Enable the composite types themselves via the `enabledCompositeTypes` property.

Composite type values are `CompositeType.A`, `CompositeType.B`, and `CompositeType.C`.

```kotlin
import com.scandit.datacapture.barcode.data.CompositeType
import java.util.EnumSet

val compositeTypes = EnumSet.of(CompositeType.A, CompositeType.B, CompositeType.C)
settings.enableSymbologies(compositeTypes)
settings.enabledCompositeTypes = compositeTypes
```

## Key Rules

1. **One context per scanning surface** — construct `DataCaptureContext.forLicenseKey(key)` once and reuse it.
2. **Factory wires the mode** — `BarcodeCapture.forDataCaptureContext(context, settings)` both creates the mode and attaches it to the context.
3. **Listener thread** — `onBarcodeScanned` runs on a background thread; always dispatch UI work via `runOnUiThread {}`.
4. **Disable inside onBarcodeScanned** — set `barcodeCapture.isEnabled = false` before doing any non-trivial work to avoid duplicate scans.
5. **Camera lifecycle** — turn the camera off in `onPause()`, back on in `onResume()`. Call `dataCaptureContext.removeCurrentMode()` in `onDestroy()`.
6. **Overlay is explicit** — `BarcodeCaptureOverlay.newInstance(barcodeCapture, view)` adds the overlay to the view in one step. There is no implicit overlay.
7. **Runtime permission** — add `CAMERA` to the manifest and request it at runtime before the first scan.
8. **Symbologies** — enable only what's needed. Variable-length 1D symbologies (Code39, Code128, ITF) may need `activeSymbolCounts` adjusted.
9. **Settings before construction** — configure `BarcodeCaptureSettings` before passing to `forDataCaptureContext`. To change at runtime, use `barcodeCapture.applySettings(newSettings)`.
