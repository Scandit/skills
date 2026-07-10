# BarcodeBatch (MatrixScan Batch) KMP Integration Guide

BarcodeBatch is the multi-barcode tracking mode. It simultaneously tracks all barcodes visible in
the camera feed, reporting additions, position updates, and removals on every frame. Unlike
BarcodeCapture (which scans one barcode at a time), BarcodeBatch continuously tracks every barcode
in view — it does not stop or disable after a detection. The camera and lifecycle are managed
manually, exactly like BarcodeCapture.

This SDK is Kotlin Multiplatform: shared logic lives in `commonMain` and is consumed from both an
Android host (Activity/Compose) and an iOS host (SwiftUI/UIKit). The reference pattern below —
confirmed against Scandit's own `MatrixScanBubblesSample` — puts **all** SDK wiring (context,
camera, mode, settings, overlays, listeners) in a shared `commonMain` class (a "screen model"), and
keeps each platform host to (a) embedding the `DataCaptureView` and (b) supplying any
platform-native views the advanced overlay needs.

## Prerequisites

- Scandit KMP SDK — Maven group `com.scandit.datacapture.kmp`, version `8.6.0` (or later). Add to
  the shared module's `build.gradle.kts`:
  ```kotlin
  kotlin {
      sourceSets {
          commonMain.dependencies {
              implementation("com.scandit.datacapture.kmp:core:8.6.0")
              implementation("com.scandit.datacapture.kmp:barcode:8.6.0")
              // Compose Multiplatform UI (optional, see the Compose section below):
              implementation("com.scandit.datacapture.kmp:core-compose:8.6.0")
          }
      }
  }
  ```
- iOS distribution is via Swift Package Manager — add the `Scandit/datacapture-kmp-spm` package
  to the Xcode project (or the local `ScanditKmpPackage` the KMP Gradle plugin generates). This
  ships **one** umbrella Kotlin/Native XCFramework per app; do not attempt to link more than one
  Kotlin framework into the same iOS target.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permission:
  - Android `AndroidManifest.xml`:
    ```xml
    <uses-feature android:name="android.hardware.camera" android:required="true" />
    <uses-permission android:name="android.permission.CAMERA" />
    ```
    Request the runtime permission using the standard Android permission API before scanning
    starts.
  - iOS `Info.plist`: add `NSCameraUsageDescription`. Request access with
    `AVCaptureDevice.requestAccess(for: .video)` before navigating to the scanner screen.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that enabling only
the symbologies actually needed improves tracking performance and accuracy.

Ask whether they want the manual `DataCaptureView` embedding pattern (works with any Android/iOS
UI stack, matches the reference sample) or the Compose Multiplatform declarative pattern (Android
+ iOS both driven from `commonMain` Compose code — see the dedicated section near the end). Write
the integration code directly into the project's shared module and platform hosts; do not just
show it in chat.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `com.scandit.datacapture.kmp:core` and `com.scandit.datacapture.kmp:barcode` (and
   `core-compose` if using Compose Multiplatform) to the shared module's Gradle dependencies.
2. Add the `Scandit/datacapture-kmp-spm` Swift package to the iOS app target.
3. Add `CAMERA` permission (Android manifest) and `NSCameraUsageDescription` (iOS Info.plist), and
   request runtime/user permission before scanning starts.
4. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with the license key from
   https://ssl.scandit.com.

## Package paths

| Class | Package |
|-------|---------|
| `BarcodeBatch`, `BarcodeBatchSettings`, `BarcodeBatchListener`, `BarcodeBatchSession` | `com.kmp.datacapture.barcode.batch` |
| `BarcodeBatchBasicOverlay`, `BarcodeBatchBasicOverlayStyle`, `BarcodeBatchBasicOverlayListener` | `com.kmp.datacapture.barcode.batch` |
| `BarcodeBatchAdvancedOverlay`, `BarcodeBatchAdvancedOverlayListener` | `com.kmp.datacapture.barcode.batch` |
| `TrackedBarcode`, `BarcodeBatchLicenseInfo` | `com.kmp.datacapture.barcode.batch` |
| `Symbology` | `com.kmp.datacapture.barcode.data` |
| `DataCaptureContext` | `com.kmp.datacapture.core.capture` |
| `Camera`, `CameraSettings`, `FrameSourceState`, `VideoResolution` | `com.kmp.datacapture.core.source` |
| `DataCaptureView`, `NativeView` | `com.kmp.datacapture.core.ui` |
| `Anchor`, `PointWithUnit`, `FloatWithUnit`, `MeasureUnit`, `Quadrilateral` | `com.kmp.datacapture.core.common.geometry` |
| `Feedback`, `Sound`, `Vibration` | `com.kmp.datacapture.core.feedback` |
| `Brush` | `com.kmp.datacapture.core.ui.style` |

All BarcodeBatch types live in one flat package (`com.kmp.datacapture.barcode.batch`) — do not
invent native Android's `batch.capture` / `batch.ui.overlay` / `batch.data` sub-package split.

## Step 1 — Create the DataCaptureContext (shared code)

```kotlin
import com.kmp.datacapture.core.capture.DataCaptureContext

private val dataCaptureContext: DataCaptureContext =
    DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
```

## Step 2 — Configure BarcodeBatchSettings (shared code)

All symbologies are disabled by default. Enable each one explicitly; enabling only what is needed
reduces tracking overhead.

```kotlin
import com.kmp.datacapture.barcode.batch.BarcodeBatchSettings
import com.kmp.datacapture.barcode.data.Symbology

val settings: BarcodeBatchSettings = BarcodeBatchSettings.barcodeBatchSettings().apply {
    enableSymbology(Symbology.EAN13_UPCA, true)
    enableSymbology(Symbology.EAN8, true)
    enableSymbology(Symbology.CODE128, true)
}
```

`BarcodeBatchSettings` has no public constructor — always build it via the
`barcodeBatchSettings()` companion factory.

### BarcodeBatchSettings Members

| Member | Description |
|--------|-------------|
| `BarcodeBatchSettings.barcodeBatchSettings()` | Static factory — the only way to construct settings. |
| `enableSymbology(symbology, enabled)` | Enable or disable one symbology. |
| `enableSymbologies(symbologies)` | Enable a `Set<Symbology>` in one call. |
| `enabledSymbologies` | `Set<Symbology>` — currently enabled symbologies. |
| `getSymbologySettings(symbology)` | Get per-symbology `SymbologySettings`. |
| `expectsOnlyUniqueBarcodes` | `Boolean` — enable if tracked barcodes are expected to be unique (optimization). |
| `setArucoDictionary(dictionary)` | Sets the ArUco dictionary for ArUco/MicroPDF417 scanning. |
| `setProperty(name, value)` / `getProperty(name)` | Advanced, named properties. |

## Step 3 — Camera setup (shared code)

`BarcodeBatch.createRecommendedCameraSettings()` is a real, documented factory on KMP — use it
unless the app has a specific reason to override the defaults (e.g. a higher resolution for small
or distant barcodes).

```kotlin
import com.kmp.datacapture.barcode.batch.BarcodeBatch
import com.kmp.datacapture.core.source.Camera
import com.kmp.datacapture.core.source.FrameSourceState

private val camera: Camera? =
    Camera.getDefaultCamera(BarcodeBatch.createRecommendedCameraSettings())?.also {
        dataCaptureContext.setFrameSource(it)
    }
```

`Camera.getDefaultCamera(...)` returns `Camera?` — always null-check (`?.also { … }` /
`camera?.switchToDesiredState(...)`) since a device may expose no camera.

## Step 4 — Create BarcodeBatch (shared code)

BarcodeBatch uses a factory function. Passing a non-null context automatically adds the mode to
that context.

```kotlin
import com.kmp.datacapture.barcode.batch.BarcodeBatch

private val barcodeBatch: BarcodeBatch =
    BarcodeBatch.forContext(dataCaptureContext, settings).also {
        it.addListener(this)
    }
```

### BarcodeBatch Members

| Member | Description |
|--------|-------------|
| `BarcodeBatch.forContext(context, settings)` | Factory — creates the mode and attaches it to the context. |
| `isEnabled` | `Boolean` — pause/resume tracking without tearing down the camera. |
| `addListener(listener)` / `removeListener(listener)` | Register or remove a `BarcodeBatchListener`. |
| `applySettings(settings)` | Update settings at runtime. |
| `reset()` | Clear all tracked barcodes and reset the object tracker. |
| `barcodeBatchLicenseInfo` | `BarcodeBatchLicenseInfo?` — populated once the mode is attached to a licensed context. |
| `BarcodeBatch.createRecommendedCameraSettings()` | Static — returns recommended `CameraSettings`. |

## Step 5 — DataCaptureView (platform host code)

`DataCaptureView` is an `expect class` whose constructor differs per platform (Android needs a
`Context`, iOS does not), so it must be constructed in platform code, not shared `commonMain`.

Android:
```kotlin
import com.kmp.datacapture.core.ui.DataCaptureView
import com.kmp.datacapture.core.ui.toAndroidView

val dataCaptureView = DataCaptureView(context, dataCaptureContext)
// Embed dataCaptureView.toAndroidView() (an android.view.View) into the Android UI,
// e.g. setContentView(dataCaptureView.toAndroidView()) or inside a Compose AndroidView { }.
```

iOS (Swift, via the SPM package):
```swift
import shared

let dataCaptureView = DataCaptureView(dataCaptureContext: dataCaptureContext)
// Embed dataCaptureView.toUIView() (a UIView) via a UIViewRepresentable in SwiftUI,
// or add it directly to a UIKit view hierarchy.
```

## Step 6 — BarcodeBatchBasicOverlay (shared code)

`BarcodeBatchBasicOverlay` renders a highlight over each tracked barcode. On KMP, **no factory
auto-adds the overlay to the view** — always follow creation with an explicit `addOverlay` call.

```kotlin
import com.kmp.datacapture.barcode.batch.BarcodeBatchBasicOverlay

// With the view (still requires addOverlay):
val basicOverlay = BarcodeBatchBasicOverlay.withBarcodeBatchForView(barcodeBatch, dataCaptureView)
dataCaptureView.addOverlay(basicOverlay)

// Without a view up front (also requires addOverlay later):
val basicOverlay2 = BarcodeBatchBasicOverlay.withBarcodeBatch(barcodeBatch)
dataCaptureView.addOverlay(basicOverlay2)
```

`BarcodeBatchBasicOverlayStyle` has exactly two values: `FRAME` (default — a rectangular frame
with an appear animation) and `DOT` (a dot at the barcode center). **Neither KMP factory accepts a
style parameter**, and `overlay.style` is a read-only property — there is currently no documented
way to construct a `DOT`-style overlay on KMP. If a user asks for dot-style highlighting, say this
is a known gap in the current KMP API surface rather than inventing a workaround.

### BarcodeBatchBasicOverlay Members

| Member | Description |
|--------|-------------|
| `withBarcodeBatch(barcodeBatch)` | Factory — creates the overlay (not yet attached to a view). |
| `withBarcodeBatchForView(barcodeBatch, view)` | Factory — same, but the native overlay is bound to a view up front. **Still requires `view.addOverlay(overlay)`.** |
| `setListener(listener)` | Sets the listener for per-barcode brush customization and tap events. A **function call**, not a settable property. |
| `brush` | `Brush?` — uniform brush for all tracked barcodes when no listener is set. |
| `defaultBrush` | `Brush` — the brush resolved from the overlay's `style` at construction. |
| `style` | `BarcodeBatchBasicOverlayStyle` — `FRAME` or `DOT` (read-only; no setter). |
| `dotRadius` | `FloatWithUnit` — radius for `DOT` style (no effect for `FRAME`). |
| `setBrushForTrackedBarcode(brush, trackedBarcode)` | Imperatively set the brush for a specific barcode. |
| `clearTrackedBarcodeBrushes()` | Clear all custom brushes. |
| `shouldShowScanAreaGuides` | Debug: show the active scan area outline. |

### Per-barcode brush customization (requires MatrixScan AR add-on)

Implement `BarcodeBatchBasicOverlayListener` to return a different brush per barcode.
`brushForTrackedBarcode` is called synchronously on the rendering path.

```kotlin
import com.kmp.datacapture.barcode.batch.BarcodeBatchBasicOverlayListener
import com.kmp.datacapture.barcode.batch.TrackedBarcode
import com.kmp.datacapture.core.ui.style.Brush

class ScannerScreenModel : BarcodeBatchBasicOverlayListener {

    override fun brushForTrackedBarcode(
        overlay: BarcodeBatchBasicOverlay,
        trackedBarcode: TrackedBarcode,
    ): Brush? {
        // Return null to use the overlay's default brush.
        return when (trackedBarcode.barcode.symbology) {
            Symbology.EAN13_UPCA -> Brush(/* fillColor, strokeColor, strokeWidth */)
            else -> null
        }
    }

    override fun onTrackedBarcodeTapped(
        overlay: BarcodeBatchBasicOverlay,
        trackedBarcode: TrackedBarcode,
    ) {
        // React to the user tapping a barcode highlight.
    }
}
```

Assign the listener after creating the overlay, **via the setter function**, not a property:

```kotlin
overlay.setListener(this)
```

> **MatrixScan AR add-on required** for `brushForTrackedBarcode`, `setBrushForTrackedBarcode`, and
> `setListener` in general. A uniform default brush (no listener set) does not require the
> add-on.

> **Tap callback**: on KMP the callback is `onTrackedBarcodeTapped(overlay, trackedBarcode)` —
> matching native Android's name, not the JS/iOS `didTapTrackedBarcode` name. A barcode whose
> `brushForTrackedBarcode` returned `null` (or whose brush was cleared) is not tappable.

## Step 7 — BarcodeBatchListener (shared code)

Implement `BarcodeBatchListener` to receive per-frame session updates.

```kotlin
import com.kmp.datacapture.barcode.batch.BarcodeBatch
import com.kmp.datacapture.barcode.batch.BarcodeBatchListener
import com.kmp.datacapture.barcode.batch.BarcodeBatchSession
import com.kmp.datacapture.core.data.FrameData

class ScannerScreenModel : BarcodeBatchListener {

    override fun onSessionUpdated(
        barcodeBatch: BarcodeBatch,
        session: BarcodeBatchSession,
        frameData: FrameData,
    ) {
        val added = session.addedTrackedBarcodes.map { it.barcode.data }
        // Dispatch to the main thread / a StateFlow before touching UI state,
        // mirroring the reference sample's `observerScope.launch { ... }` pattern.
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
| `onSessionUpdated(barcodeBatch, session, frameData)` | Called every processed frame. |
| `onObservationStarted(barcodeBatch)` | Listener was registered. Has a default empty body. |
| `onObservationStopped(barcodeBatch)` | Listener was removed. Has a default empty body. |

### BarcodeBatchSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `trackedBarcodes` | `Map<Int, TrackedBarcode>` | All currently tracked barcodes, keyed by tracking ID. |
| `addedTrackedBarcodes` | `List<TrackedBarcode>` | Barcodes newly tracked in this frame. |
| `updatedTrackedBarcodes` | `List<TrackedBarcode>` | Barcodes whose position changed in this frame. |
| `removedTrackedBarcodes` | `List<Int>` | Tracking IDs of barcodes that left the view. |
| `unscannedTrackedBarcodes` | `List<TrackedBarcode>` | Barcodes tracked previously but absent from the current frame's tracked set. |
| `frameSequenceID` | `Int` | Identifier of the current frame sequence. |
| `reset()` | — | Clear all tracked state (call only from within `onSessionUpdated`). |

### Reacting to added, updated, and removed barcodes

Each frame, the session reports deltas. `addedTrackedBarcodes` and `updatedTrackedBarcodes` are
`List<TrackedBarcode>`; `removedTrackedBarcodes` is a `List<Int>` of **tracking identifiers**
only (the barcodes are already gone, so only their `identifier` is available). Use
`removedTrackedBarcodes` to drop entries from the app's own UI/state keyed by tracking ID.

```kotlin
override fun onSessionUpdated(
    barcodeBatch: BarcodeBatch,
    session: BarcodeBatchSession,
    frameData: FrameData,
) {
    val removed: List<Int> = session.removedTrackedBarcodes
    if (removed.isNotEmpty()) {
        // Hop to the UI-owning scope before touching app state, e.g.:
        // scope.launch { removed.forEach { id -> myCache.remove(id) } }
    }
}
```

### TrackedBarcode Properties

| Property | Type | Description |
|----------|------|-------------|
| `barcode` | `Barcode` | The decoded barcode. Access `.data`, `.symbology`, etc. |
| `identifier` | `Int` | Unique tracking ID. Reused after the barcode leaves the frame. |
| `location` | `Quadrilateral` | Barcode position in image-space coordinates. |
| `getAnchorPosition(anchor)` | `Point` | The point on `location` for the given `Anchor`. |

## Step 8 — Lifecycle management

Drive the camera and `isEnabled` flag from each platform's lifecycle hooks (Android
`Activity`/Compose `Lifecycle.Event`, iOS `onAppear`/`onDisappear`). Expose lifecycle intents from
the shared screen model so both platforms call the same shared code:

```kotlin
fun onStarted() {
    camera?.switchToDesiredState(FrameSourceState.ON)
    barcodeBatch.isEnabled = true
}

fun onStopped() {
    barcodeBatch.isEnabled = false
    camera?.switchToDesiredState(FrameSourceState.OFF)
}

fun dispose() {
    barcodeBatch.isEnabled = false
    barcodeBatch.removeListener(this)
    dataCaptureContext.removeMode(barcodeBatch)
    camera?.switchToDesiredState(FrameSourceState.OFF)
}
```

Teardown uses `dataCaptureContext.removeMode(barcodeBatch)` — not `removeCurrentMode()` (that
removes whatever mode is currently attached, which is fragile if more than one mode is ever added).

## Optional: emitting feedback (sound / vibration)

Unlike some other Scandit modes, `BarcodeBatch` does **not** emit any sound or vibration on its
own — there is no `feedback` property on `BarcodeBatch` or its settings. If a beep/vibration is
wanted when a new barcode is tracked, emit it manually from `onSessionUpdated` using a `Feedback`
instance.

`Feedback` has no public constructor on KMP — build it via `Feedback.defaultFeedback()` and create
it once, reusing the same instance (constructing one per frame is wasteful):

```kotlin
import com.kmp.datacapture.core.feedback.Feedback

private val feedback: Feedback = Feedback.defaultFeedback()

override fun onSessionUpdated(
    barcodeBatch: BarcodeBatch,
    session: BarcodeBatchSession,
    frameData: FrameData,
) {
    if (session.addedTrackedBarcodes.isNotEmpty()) {
        feedback.emit()
    }
}
```

To customize, override the `sound` / `vibration` properties after construction:
```kotlin
import com.kmp.datacapture.core.feedback.Sound
import com.kmp.datacapture.core.feedback.Vibration

private val feedback: Feedback = Feedback.defaultFeedback().apply {
    sound = Sound.defaultSound()
    vibration = Vibration.defaultVibration()
}
```

`emit()` is safe to call from a background/recognition thread.

## Optional: BarcodeBatchAdvancedOverlay (requires MatrixScan AR add-on)

`BarcodeBatchAdvancedOverlay` anchors a custom native view to each tracked barcode in real time —
this is the "AR bubble" pattern from Scandit's `MatrixScanBubblesSample`. Unlike
`BarcodeBatchBasicOverlay`, there is only **one** factory (no `ForView` variant), so
`addOverlay` is always required, and the listener is a real settable **property**.

```kotlin
import com.kmp.datacapture.barcode.batch.BarcodeBatchAdvancedOverlay
import com.kmp.datacapture.barcode.batch.BarcodeBatchAdvancedOverlayListener
import com.kmp.datacapture.core.ui.NativeView

private var advancedOverlay: BarcodeBatchAdvancedOverlay? = null

// Platform-supplied factory: builds (or recycles) the native view for a tracked barcode.
// commonMain cannot construct an android.view.View / UIView directly, so the platform host
// passes this lambda in.
private var bubbleViewFactory: ((TrackedBarcode, String) -> NativeView?)? = null

fun setupAdvancedOverlay(
    view: DataCaptureView,
    bubbleViewFactory: (TrackedBarcode, String) -> NativeView?,
) {
    this.bubbleViewFactory = bubbleViewFactory
    val overlay = BarcodeBatchAdvancedOverlay.withBarcodeBatch(barcodeBatch)
    overlay.listener = this // a settable property on BarcodeBatchAdvancedOverlay
    view.addOverlay(overlay)
    advancedOverlay = overlay
}

// --- BarcodeBatchAdvancedOverlayListener ---

override fun viewForTrackedBarcode(
    overlay: BarcodeBatchAdvancedOverlay,
    trackedBarcode: TrackedBarcode,
): NativeView? {
    val code = trackedBarcode.barcode.data ?: ""
    return bubbleViewFactory?.invoke(trackedBarcode, code)
}

override fun anchorForTrackedBarcode(
    overlay: BarcodeBatchAdvancedOverlay,
    trackedBarcode: TrackedBarcode,
): Anchor = Anchor.TOP_CENTER

override fun offsetForTrackedBarcode(
    overlay: BarcodeBatchAdvancedOverlay,
    trackedBarcode: TrackedBarcode,
): PointWithUnit = PointWithUnit(
    FloatWithUnit(0f, MeasureUnit.FRACTION),
    FloatWithUnit(-1f, MeasureUnit.FRACTION),
)
```

Android host builds and returns the native view (`android.view.View`, which resolves directly to
`NativeView` — no cast needed):
```kotlin
bubbleViewFactory = { trackedBarcode, code ->
    TextView(context).apply { text = code } // android.view.View == NativeView on Android
}
```

iOS host (Swift) builds and returns a `UIView`:
```swift
bubbleViewFactory: { trackedBarcode, code in
    let label = UILabel()
    label.text = code
    return label // UIView == NativeView on iOS
}
```

To update the view for a specific barcode imperatively (e.g. after a data lookup):
```kotlin
advancedOverlay?.setViewForTrackedBarcode(trackedBarcode, updatedView)
advancedOverlay?.setAnchorForTrackedBarcode(trackedBarcode, Anchor.TOP_CENTER)
advancedOverlay?.setOffsetForTrackedBarcode(trackedBarcode, offset)
advancedOverlay?.clearTrackedBarcodeViews() // remove all views
```

### BarcodeBatchAdvancedOverlay Members

| Member | Description |
|--------|-------------|
| `withBarcodeBatch(barcodeBatch)` | Factory — the only advanced-overlay factory. Requires `view.addOverlay(overlay)` afterward. |
| `listener` | `BarcodeBatchAdvancedOverlayListener?` — a settable **property** (unlike the basic overlay's `setListener()` function). |
| `setViewForTrackedBarcode(trackedBarcode, view)` | Set or update the native view for a barcode. Pass `null` to remove. |
| `setAnchorForTrackedBarcode(trackedBarcode, anchor)` | Override the anchor for a barcode. |
| `setOffsetForTrackedBarcode(trackedBarcode, offset)` | Override the offset for a barcode. |
| `clearTrackedBarcodeViews()` | Remove all anchored views. |
| `shouldShowScanAreaGuides` | Debug: show the active scan area. |

### BarcodeBatchAdvancedOverlayListener Interface

| Callback | Description |
|----------|-------------|
| `viewForTrackedBarcode(overlay, trackedBarcode): NativeView?` | Return the native view to anchor to this barcode, or `null` for none. |
| `anchorForTrackedBarcode(overlay, trackedBarcode): Anchor` | Return an `Anchor` (e.g. `Anchor.TOP_CENTER`) for the view position relative to the barcode. |
| `offsetForTrackedBarcode(overlay, trackedBarcode): PointWithUnit` | Return a `PointWithUnit` offset to fine-tune the view position. `MeasureUnit.FRACTION` makes it relative to the view's own dimensions. |

There is no `didTapViewForTrackedBarcode` callback on KMP — that tap callback only exists on
web/cordova/react-native/flutter/capacitor.

The geometry types live in `com.kmp.datacapture.core.common.geometry`:
```kotlin
import com.kmp.datacapture.core.common.geometry.Anchor
import com.kmp.datacapture.core.common.geometry.FloatWithUnit
import com.kmp.datacapture.core.common.geometry.MeasureUnit
import com.kmp.datacapture.core.common.geometry.PointWithUnit
```

> **Positioning note**: `PointWithUnit(x: FloatWithUnit, y: FloatWithUnit)` — not `DoubleWithUnit`
> (that is the Flutter/Dart name). A `y` of `FloatWithUnit(-1f, MeasureUnit.FRACTION)` shifts the
> view up by its own full height, placing it directly above the barcode when combined with
> `Anchor.TOP_CENTER`.

## Compose Multiplatform

There is no BarcodeBatch-specific Compose wrapper (unlike SparkScan/BarcodeAr/BarcodePick, which
have dedicated `*View` composables). Instead, use the module-agnostic `core-compose`
`DataCaptureView` composable and pass the overlays as a list:

```kotlin
import com.kmp.datacapture.core.compose.DataCaptureView
import com.kmp.datacapture.core.compose.rememberCamera
import com.kmp.datacapture.core.compose.rememberDataCaptureContext

@Composable
fun BatchScanScreen() {
    val context = rememberDataCaptureContext("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
    rememberCamera(context) // wires the default camera to context and drives its lifecycle

    val settings = remember {
        BarcodeBatchSettings.barcodeBatchSettings().apply {
            enableSymbology(Symbology.EAN13_UPCA, true)
        }
    }
    val barcodeBatch = remember(context) { BarcodeBatch.forContext(context, settings) }

    // Overlay instances must be `remember`-ed: the composable diffs the overlays list by
    // reference/content equality on every recomposition, and an overlay class without
    // structural equality will otherwise be removed and re-added on every recomposition,
    // causing flicker.
    val overlay = remember(barcodeBatch) { BarcodeBatchBasicOverlay.withBarcodeBatch(barcodeBatch) }

    DataCaptureView(
        context = context,
        overlays = listOf(overlay),
    )
}
```

`rememberDataCaptureContext` and `rememberCamera` tie context/camera lifecycle to the composition
automatically (camera on last when entering composition, off first on dispose) — there is no need
to call `switchToDesiredState` manually in Compose code. Still add/remove the `BarcodeBatchListener`
and call `barcodeBatch.reset()` / `removeListener` in a `DisposableEffect` keyed on `barcodeBatch`.

## Lifecycle & Teardown summary

| Step | Manual (Android/iOS host) | Compose Multiplatform |
|---|---|---|
| Start camera | `camera?.switchToDesiredState(FrameSourceState.ON)` in `onResume`/`onAppear` | Handled by `rememberCamera` |
| Stop camera | `camera?.switchToDesiredState(FrameSourceState.OFF)` in `onPause`/`onDisappear` | Handled by `rememberCamera`'s `onDispose` |
| Pause/resume tracking | `barcodeBatch.isEnabled = true/false` | Same — toggle explicitly if needed |
| Remove listener | `barcodeBatch.removeListener(this)` | `DisposableEffect { onDispose { barcodeBatch.removeListener(listener) } }` |
| Detach mode | `dataCaptureContext.removeMode(barcodeBatch)` | Same, in the same `onDispose` |

## Known KMP gaps / pitfalls

1. **No DOT-style factory.** `BarcodeBatchBasicOverlayStyle.DOT` cannot currently be selected via
   any documented KMP factory — `withBarcodeBatch`/`withBarcodeBatchForView` take no style
   argument and `style` is read-only. Tell the user this rather than fabricating an API.
2. **`setListener` vs `.listener =`.** `BarcodeBatchBasicOverlay.setListener(listener)` is a
   function call; `BarcodeBatchAdvancedOverlay.listener = listener` is a property assignment.
   Mixing these up is a common mistake when porting code from native Android (where the basic
   overlay's listener is also a settable property).
3. **`removedTrackedBarcodes` is `List<Int>`**, not `List<TrackedBarcode>` — only tracking
   identifiers survive removal.
4. **`Feedback` has no public constructor** — always start from `Feedback.defaultFeedback()`.
5. **`DataCaptureView` must be constructed in platform code** — Android's constructor takes a
   `Context`, iOS's does not; `commonMain` code receives the already-constructed view.
6. **`Camera.getDefaultCamera(...)` is nullable** — always null-check.
