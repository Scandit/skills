# BarcodeBatch (MatrixScan Batch) Android Integration Guide

BarcodeBatch is the multi-barcode tracking mode. It simultaneously tracks all barcodes visible in the camera feed, reporting additions, position updates, and removals on every frame. Unlike BarcodeCapture (which scans one barcode at a time), BarcodeBatch continuously tracks every barcode in view — it does not stop or disable after a detection. The camera and lifecycle are managed manually, exactly like BarcodeCapture.

Examples below use Kotlin and an Activity. The same APIs work in Fragments — adapt ownership of `DataCaptureContext`, `BarcodeBatch`, and the `Camera` to the project's existing structure.

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

Ask the user which barcode symbologies they need to scan. When asking, mention that enabling only the symbologies actually needed improves tracking performance and accuracy.

Once the user responds, ask them which Activity or Fragment they'd like to integrate BarcodeBatch into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `implementation "com.scandit.datacapture:barcode:<version>"` and `implementation "com.scandit.datacapture:core:<version>"` to `app/build.gradle` (the version was already fetched and filled in above).
2. Add `<uses-permission android:name="android.permission.CAMERA" />` and the `<uses-feature>` element to `AndroidManifest.xml`.
3. Request the `CAMERA` permission at runtime before scanning starts.
4. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

## Package paths

| Class | Package |
|-------|---------|
| `BarcodeBatch`, `BarcodeBatchSettings`, `BarcodeBatchListener`, `BarcodeBatchSession` | `com.scandit.datacapture.barcode.batch.capture` |
| `BarcodeBatchBasicOverlay`, `BarcodeBatchBasicOverlayStyle`, `BarcodeBatchBasicOverlayListener` | `com.scandit.datacapture.barcode.batch.ui.overlay` |
| `BarcodeBatchAdvancedOverlay`, `BarcodeBatchAdvancedOverlayListener` | `com.scandit.datacapture.barcode.batch.ui.overlay` |
| `TrackedBarcode` | `com.scandit.datacapture.barcode.batch.data` |
| `Anchor`, `PointWithUnit`, `FloatWithUnit`, `MeasureUnit` | `com.scandit.datacapture.core.common.geometry` |
| `Feedback`, `Sound`, `Vibration` | `com.scandit.datacapture.core.feedback` |
| `Brush` | `com.scandit.datacapture.core.ui.style` |

## Step 1 — Create the DataCaptureContext

```kotlin
import com.scandit.datacapture.core.capture.DataCaptureContext

private val dataCaptureContext = DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
```

## Step 2 — Configure BarcodeBatchSettings

All symbologies are disabled by default. Enable each one explicitly; enabling only what is needed reduces tracking overhead.

```kotlin
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatchSettings
import com.scandit.datacapture.barcode.data.Symbology

val settings = BarcodeBatchSettings().apply {
    enableSymbology(Symbology.EAN13_UPCA, true)
    enableSymbology(Symbology.EAN8, true)
    enableSymbology(Symbology.CODE128, true)
}
```

### BarcodeBatchSettings Members

| Member | Description |
|--------|-------------|
| `enableSymbology(symbology, enabled)` | Enable or disable one symbology. |
| `enableSymbologies(symbologies)` | Enable a `Set<Symbology>` in one call. |
| `getSymbologySettings(symbology)` | Get per-symbology `SymbologySettings` (e.g. `activeSymbolCounts`). |

## Step 3 — Camera setup

```kotlin
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatch
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.FrameSourceState

private val camera = Camera.getDefaultCamera(BarcodeBatch.createRecommendedCameraSettings())

init {
    dataCaptureContext.setFrameSource(camera)
}
```

## Step 4 — Create BarcodeBatch

BarcodeBatch uses a factory method. The factory attaches the mode to the context.

```kotlin
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatch

private val barcodeBatch = BarcodeBatch.forDataCaptureContext(dataCaptureContext, settings)
```

### BarcodeBatch Members

| Member | Description |
|--------|-------------|
| `BarcodeBatch.forDataCaptureContext(context, settings)` | Factory — creates the mode and attaches it to the context. |
| `isEnabled` | `Boolean` — pause/resume tracking without tearing down the camera. |
| `addListener(listener)` / `removeListener(listener)` | Register or remove a `BarcodeBatchListener`. |
| `applySettings(settings)` | Update settings at runtime. |
| `reset()` | Clear all tracked barcodes and reset the object tracker. |
| `BarcodeBatch.createRecommendedCameraSettings()` | Static — returns recommended `CameraSettings`. |

## Step 5 — DataCaptureView

```kotlin
import com.scandit.datacapture.core.ui.DataCaptureView

// In onCreate():
val dataCaptureView = DataCaptureView.newInstance(this, dataCaptureContext)
setContentView(dataCaptureView)
```

In a Fragment, add the view to a container:
```kotlin
val dataCaptureView = DataCaptureView.newInstance(requireContext(), dataCaptureContext)
binding.scannerContainer.addView(dataCaptureView, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
```

## Step 6 — BarcodeBatchBasicOverlay

`BarcodeBatchBasicOverlay` renders a highlight frame or dot over each tracked barcode. `newInstance` auto-adds the overlay to the view.

```kotlin
import com.scandit.datacapture.barcode.batch.ui.overlay.BarcodeBatchBasicOverlay
import com.scandit.datacapture.barcode.batch.ui.overlay.BarcodeBatchBasicOverlayStyle

// Default style (FRAME):
val overlay = BarcodeBatchBasicOverlay.newInstance(barcodeBatch, dataCaptureView)

// Or choose a style explicitly:
val overlay = BarcodeBatchBasicOverlay.newInstance(barcodeBatch, dataCaptureView, BarcodeBatchBasicOverlayStyle.DOT)
```

`BarcodeBatchBasicOverlayStyle` has exactly two values: `BarcodeBatchBasicOverlayStyle.FRAME` (default — a rectangular frame with an appear animation) and `BarcodeBatchBasicOverlayStyle.DOT` (a dot at the barcode center). The style is chosen via the three-argument `newInstance(mode, view, style)` overload at creation time. The `style` property is **read-only** — to change styles you create a new overlay; you do not assign `overlay.style`.

### BarcodeBatchBasicOverlay Members

| Member | Description |
|--------|-------------|
| `newInstance(mode, view)` | Factory — creates the overlay and adds it to the view. Default FRAME style. |
| `newInstance(mode, view, style)` | Factory — same, with explicit style. |
| `listener` | `BarcodeBatchBasicOverlayListener?` — for per-barcode brush customization. |
| `brush` | `Brush?` — uniform brush for all tracked barcodes when no listener is set. |
| `style` | `BarcodeBatchBasicOverlayStyle` — `FRAME` or `DOT` (read-only). |
| `setBrushForTrackedBarcode(trackedBarcode, brush)` | Imperatively set the brush for a specific barcode. |
| `clearTrackedBarcodeBrushes()` | Clear all custom brushes. |
| `shouldShowScanAreaGuides` | Debug: show the active scan area outline. |

### Per-barcode brush customization (requires MatrixScan AR add-on)

Implement `BarcodeBatchBasicOverlayListener` to return a different brush per barcode. `brushForTrackedBarcode` is called from the rendering thread.

```kotlin
import com.scandit.datacapture.barcode.batch.ui.overlay.BarcodeBatchBasicOverlayListener
import com.scandit.datacapture.core.ui.style.Brush

class ScannerActivity : AppCompatActivity(), BarcodeBatchBasicOverlayListener {

    override fun brushForTrackedBarcode(
        overlay: BarcodeBatchBasicOverlay,
        trackedBarcode: TrackedBarcode
    ): Brush? {
        // Return null to use the overlay's default brush.
        // Return a fully transparent brush to hide the barcode.
        return when (trackedBarcode.barcode.symbology) {
            Symbology.EAN13_UPCA -> Brush(Color.argb(100, 0, 200, 68), Color.rgb(0, 200, 68), 2f)
            else -> null
        }
    }

    override fun onTrackedBarcodeTapped(
        overlay: BarcodeBatchBasicOverlay,
        trackedBarcode: TrackedBarcode
    ) {
        // React to the user tapping a barcode highlight.
    }
}
```

Assign the listener after creating the overlay:
```kotlin
overlay.listener = this
```

> **MatrixScan AR add-on required** for `brushForTrackedBarcode` and `setBrushForTrackedBarcode`. A uniform default brush (no listener) does not require the add-on.

> **Tap callback naming**: On Android the tap callback is `onTrackedBarcodeTapped(overlay, trackedBarcode)` — called on the **main thread**. Do not use `didTapTrackedBarcode` (that is the iOS/JS name). A barcode whose `brushForTrackedBarcode` returned `null` (or whose brush was cleared) is not tappable. The tap callback is independent of the overlay's `BarcodeBatchBasicOverlayStyle` (`FRAME` or `DOT`) — both styles support it.

## Step 7 — BarcodeBatchListener

Implement `BarcodeBatchListener` to receive per-frame session updates. `onSessionUpdated` is called on a **recognition thread** — do not hold session references outside the callback.

```kotlin
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatchListener
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatchSession
import com.scandit.datacapture.barcode.batch.data.TrackedBarcode
import com.scandit.datacapture.core.data.FrameData

class ScannerActivity : AppCompatActivity(), BarcodeBatchListener {

    override fun onSessionUpdated(
        mode: BarcodeBatch,
        session: BarcodeBatchSession,
        data: FrameData
    ) {
        // Called on a recognition thread — copy data, then dispatch UI work.
        val added = session.addedTrackedBarcodes.map { it.barcode.data }
        runOnUiThread {
            for (barcodeData in added) {
                // handle barcodeData
            }
        }
    }

    override fun onObservationStarted(barcodeBatch: BarcodeBatch) {}
    override fun onObservationStopped(barcodeBatch: BarcodeBatch) {}
}
```

Register the listener after constructing `BarcodeBatch`:
```kotlin
barcodeBatch.addListener(this)
```

### BarcodeBatchListener Interface

| Callback | Description |
|----------|-------------|
| `onSessionUpdated(mode, session, data)` | Called every processed frame. Recognition thread — copy data and dispatch UI work. |
| `onObservationStarted(barcodeBatch)` | Listener was registered. |
| `onObservationStopped(barcodeBatch)` | Listener was removed. |

### BarcodeBatchSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `trackedBarcodes` | `Map<Int, TrackedBarcode>` | All currently tracked barcodes, keyed by tracking ID. |
| `addedTrackedBarcodes` | `List<TrackedBarcode>` | Barcodes newly tracked in this frame. |
| `updatedTrackedBarcodes` | `List<TrackedBarcode>` | Barcodes whose position changed in this frame. |
| `removedTrackedBarcodes` | `List<Int>` | Tracking IDs of barcodes that left the view. |
| `frameSequenceId` | `Long` | Identifier of the current frame sequence. |
| `reset()` | — | Clear all tracked state (call only from within `onSessionUpdated`). |

> **Important**: Do not hold references to the session or its collections outside `onSessionUpdated`. Copy any data you need before the callback returns.

### Reacting to added, updated, and removed barcodes

Each frame, the session reports three deltas. `addedTrackedBarcodes` and `updatedTrackedBarcodes` are `List<TrackedBarcode>`; `removedTrackedBarcodes` is a `List<Int>` of **tracking identifiers** only (the barcodes are already gone, so only their `identifier` is available). Use `removedTrackedBarcodes` to drop entries from your own UI/state keyed by tracking ID.

```kotlin
override fun onSessionUpdated(
    mode: BarcodeBatch,
    session: BarcodeBatchSession,
    data: FrameData
) {
    // Copy the deltas out of the session before leaving the recognition thread.
    val added = session.addedTrackedBarcodes.map { it.identifier to it.barcode.data }
    val removedIds = session.removedTrackedBarcodes.toList() // List<Int> of tracking IDs

    runOnUiThread {
        for ((id, value) in added) {
            // add `value` to your own collection keyed by `id`
        }
        for (id in removedIds) {
            // remove the entry previously stored under this tracking `id`
        }
    }
}
```

### TrackedBarcode Properties

| Property | Type | Description |
|----------|------|-------------|
| `barcode` | `Barcode` | The decoded barcode. Access `.data`, `.symbology`, etc. |
| `identifier` | `Int` | Unique tracking ID. Reused after the barcode leaves the frame. |
| `location` | `Quadrilateral` | Barcode position in image-space coordinates. |

## Step 8 — Lifecycle management

Drive the camera and `isEnabled` flag from `onResume` and `onPause`.

```kotlin
override fun onResume() {
    super.onResume()
    barcodeBatch.isEnabled = true
    camera?.switchToDesiredState(FrameSourceState.ON)
}

override fun onPause() {
    barcodeBatch.isEnabled = false
    camera?.switchToDesiredState(FrameSourceState.OFF)
    super.onPause()
}

override fun onDestroy() {
    barcodeBatch.removeListener(this)
    dataCaptureContext.removeCurrentMode()
    super.onDestroy()
}
```

## Optional: emitting feedback (sound / vibration)

Unlike `BarcodeCapture`, `BarcodeBatch` does **not** emit any sound or vibration on its own — there is no `feedback` property on `BarcodeBatch` or its settings. If you want a beep/vibration when a new barcode is tracked, emit it yourself from `onSessionUpdated` using a `Feedback` instance.

Create one `Feedback` once and reuse it (creating one per frame is wasteful). `Feedback.defaultFeedback()` gives the default sound + vibration; `emit()` plays it.

```kotlin
import com.scandit.datacapture.core.feedback.Feedback

private val feedback = Feedback.defaultFeedback()

override fun onSessionUpdated(
    mode: BarcodeBatch,
    session: BarcodeBatchSession,
    data: FrameData
) {
    // Only give feedback when something new was actually tracked this frame.
    if (session.addedTrackedBarcodes.isNotEmpty()) {
        feedback.emit()
    }
    // ... copy data and dispatch UI work as usual
}
```

To customize, build a `Feedback` from a `Sound` and/or `Vibration`:
```kotlin
import com.scandit.datacapture.core.feedback.Feedback
import com.scandit.datacapture.core.feedback.Sound
import com.scandit.datacapture.core.feedback.Vibration

private val feedback = Feedback(Vibration.defaultVibration(), Sound.defaultSound())
```

`emit()` is influenced by the device's ring mode and volume settings. `Feedback.emit()` is safe to call from the recognition thread.

## Complete minimal example

```kotlin
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatch
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatchListener
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatchSession
import com.scandit.datacapture.barcode.batch.capture.BarcodeBatchSettings
import com.scandit.datacapture.barcode.batch.data.TrackedBarcode
import com.scandit.datacapture.barcode.batch.ui.overlay.BarcodeBatchBasicOverlay
import com.scandit.datacapture.barcode.data.Symbology
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.data.FrameData
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.FrameSourceState
import com.scandit.datacapture.core.ui.DataCaptureView

class BatchScanActivity : AppCompatActivity(), BarcodeBatchListener {

    private val dataCaptureContext =
        DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val camera = Camera.getDefaultCamera(BarcodeBatch.createRecommendedCameraSettings())

    private val barcodeBatch: BarcodeBatch

    init {
        dataCaptureContext.setFrameSource(camera)

        val settings = BarcodeBatchSettings().apply {
            enableSymbology(Symbology.EAN13_UPCA, true)
            enableSymbology(Symbology.CODE128, true)
        }

        barcodeBatch = BarcodeBatch.forDataCaptureContext(dataCaptureContext, settings)
        barcodeBatch.addListener(this)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Request CAMERA permission here before scanning starts.
        val dataCaptureView = DataCaptureView.newInstance(this, dataCaptureContext)
        BarcodeBatchBasicOverlay.newInstance(barcodeBatch, dataCaptureView)
        setContentView(dataCaptureView)
    }

    override fun onResume() {
        super.onResume()
        barcodeBatch.isEnabled = true
        camera?.switchToDesiredState(FrameSourceState.ON)
    }

    override fun onPause() {
        barcodeBatch.isEnabled = false
        camera?.switchToDesiredState(FrameSourceState.OFF)
        super.onPause()
    }

    override fun onDestroy() {
        barcodeBatch.removeListener(this)
        dataCaptureContext.removeCurrentMode()
        super.onDestroy()
    }

    override fun onSessionUpdated(
        mode: BarcodeBatch,
        session: BarcodeBatchSession,
        data: FrameData
    ) {
        val added = session.addedTrackedBarcodes.map { it.barcode.data }
        runOnUiThread {
            for (barcodeData in added) {
                // handle barcodeData
            }
        }
    }

    override fun onObservationStarted(barcodeBatch: BarcodeBatch) {}
    override fun onObservationStopped(barcodeBatch: BarcodeBatch) {}
}
```

## Optional: BarcodeBatchAdvancedOverlay (requires MatrixScan AR add-on)

`BarcodeBatchAdvancedOverlay` anchors a custom Android `View` to each tracked barcode in real time. `newInstance` auto-adds the overlay to the view.

```kotlin
import com.scandit.datacapture.barcode.batch.ui.overlay.BarcodeBatchAdvancedOverlay
import com.scandit.datacapture.barcode.batch.ui.overlay.BarcodeBatchAdvancedOverlayListener

class ScannerActivity : AppCompatActivity(), BarcodeBatchAdvancedOverlayListener {

    private lateinit var advancedOverlay: BarcodeBatchAdvancedOverlay

    // In onCreate(), after creating dataCaptureView:
    fun setupAdvancedOverlay(dataCaptureView: DataCaptureView) {
        advancedOverlay = BarcodeBatchAdvancedOverlay.newInstance(barcodeBatch, dataCaptureView)
        advancedOverlay.listener = this
    }

    // Called on the main thread for each newly tracked barcode.
    // Return an Android View to anchor to this barcode, or null to show nothing.
    override fun viewForTrackedBarcode(
        overlay: BarcodeBatchAdvancedOverlay,
        trackedBarcode: TrackedBarcode
    ): View? {
        val label = TextView(this).apply {
            text = trackedBarcode.barcode.data
            setBackgroundColor(Color.WHITE)
            setPadding(8, 4, 8, 4)
        }
        return label
    }

    override fun anchorForTrackedBarcode(
        overlay: BarcodeBatchAdvancedOverlay,
        trackedBarcode: TrackedBarcode
    ): Anchor {
        return Anchor.TOP_CENTER
    }

    override fun offsetForTrackedBarcode(
        overlay: BarcodeBatchAdvancedOverlay,
        trackedBarcode: TrackedBarcode,
        view: View
    ): PointWithUnit {
        // Center the view above the barcode. FRACTION offsets are relative to the view size.
        return PointWithUnit(
            FloatWithUnit(0f, MeasureUnit.FRACTION),
            FloatWithUnit(-1f, MeasureUnit.FRACTION)
        )
    }
}
```

To update the view for a specific barcode imperatively (e.g. after a data lookup):
```kotlin
advancedOverlay.setViewForTrackedBarcode(trackedBarcode, updatedView)
advancedOverlay.setAnchorForTrackedBarcode(trackedBarcode, Anchor.TOP_CENTER)
advancedOverlay.setOffsetForTrackedBarcode(trackedBarcode, offset)
advancedOverlay.clearTrackedBarcodeViews() // remove all views
```

### BarcodeBatchAdvancedOverlay Members

| Member | Description |
|--------|-------------|
| `newInstance(mode, view)` | Factory — creates the overlay and adds it to the view. |
| `listener` | `BarcodeBatchAdvancedOverlayListener?` |
| `setViewForTrackedBarcode(trackedBarcode, view)` | Set or update the Android View for a barcode. Pass `null` to remove. |
| `setAnchorForTrackedBarcode(trackedBarcode, anchor)` | Override the anchor for a barcode. |
| `setOffsetForTrackedBarcode(trackedBarcode, offset)` | Override the offset for a barcode. |
| `clearTrackedBarcodeViews()` | Remove all anchored views. |
| `shouldShowScanAreaGuides` | Debug: show the active scan area. |

### BarcodeBatchAdvancedOverlayListener Interface

| Callback | Description |
|----------|-------------|
| `viewForTrackedBarcode(overlay, trackedBarcode): View?` | Return the Android `View` to anchor to this barcode, or `null` for none. Called on the main thread. |
| `anchorForTrackedBarcode(overlay, trackedBarcode): Anchor` | Return an `Anchor` value (e.g. `Anchor.TOP_CENTER`) for the view position relative to the barcode. Called on the main thread. |
| `offsetForTrackedBarcode(overlay, trackedBarcode, view): PointWithUnit` | Return a `PointWithUnit` offset to fine-tune the view position. The offset is relative to the anchor; `MeasureUnit.FRACTION` makes it relative to the view's own dimensions. Called on the main thread. |

The geometry types live in `com.scandit.datacapture.core.common.geometry`:
```kotlin
import com.scandit.datacapture.core.common.geometry.Anchor
import com.scandit.datacapture.core.common.geometry.FloatWithUnit
import com.scandit.datacapture.core.common.geometry.MeasureUnit
import com.scandit.datacapture.core.common.geometry.PointWithUnit
```

> **Positioning note**: On Android the offset value type is `FloatWithUnit(value: Float, unit: MeasureUnit)` — not `DoubleWithUnit` (that is the Flutter/Dart name). Construct the point as `PointWithUnit(FloatWithUnit(x, unit), FloatWithUnit(y, unit))`. A `y` of `FloatWithUnit(-1f, MeasureUnit.FRACTION)` shifts the view up by its full height, placing it directly above the barcode when combined with `Anchor.TOP_CENTER`.

> For the tap callback and any additional listener methods, fetch the [Adding AR Overlays](https://docs.scandit.com/sdks/android/matrixscan-batch/advanced/) page.

## Key Rules

1. **Factory, not constructor** — `BarcodeBatch.forDataCaptureContext(context, settings)` is a factory method, not a direct constructor.
2. **Manual camera** — create `Camera.getDefaultCamera(BarcodeBatch.createRecommendedCameraSettings())`, call `setFrameSource`, and drive the camera from `onResume`/`onPause`.
3. **Recognition thread** — `onSessionUpdated` runs on a background thread. Copy the data you need, then dispatch UI work via `runOnUiThread {}`.
4. **Don't hold session references** — the session and its collections are only safe within `onSessionUpdated`. Copy data before the callback returns.
5. **Overlay auto-adds** — `BarcodeBatchBasicOverlay.newInstance(mode, view)` and `BarcodeBatchAdvancedOverlay.newInstance(mode, view)` both add themselves to the `DataCaptureView` automatically.
6. **AR add-on required** — per-barcode brush customization (`brushForTrackedBarcode`) and `BarcodeBatchAdvancedOverlay` both require the MatrixScan AR add-on license.
7. **isEnabled for pause/resume** — toggle `barcodeBatch.isEnabled` to pause and resume tracking without removing the mode.
8. **Cleanup** — call `barcodeBatch.removeListener(this)` and `dataCaptureContext.removeCurrentMode()` in `onDestroy`.
9. **Symbologies** — all disabled by default; enable only what is needed.
10. **Runtime permission** — add `CAMERA` to the manifest and request it at runtime before the first scan.
