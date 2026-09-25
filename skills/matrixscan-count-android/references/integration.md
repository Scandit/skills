# MatrixScan Count Android Integration Guide

MatrixScan Count is a pre-built bulk-counting workflow built on top of the Scandit SDK. It scans many
barcodes at once, counts them, and renders a built-in augmented-reality counting UI (highlights over
each recognized barcode plus a guidance overlay, a shutter, and List / Exit buttons) so a user can
sweep the camera across a shelf or pile and tally everything. The integration has two primary
elements: the **`BarcodeCount`** data capture mode and the **`BarcodeCountView`** pre-built UI.

This guide follows the official
[MatrixScan Count Get Started (Android)](https://docs.scandit.com/sdks/android/matrixscan-count/get-started/)
flow. Its general steps are:

1. Create a Data Capture Context
2. Configure the Barcode Count mode
3. Obtain the camera instance and set the frame source
4. Register the listener to be informed when a scan phase completes
5. Set the capture view and AR overlays
6. Configure the camera for the scanning view (lifecycle)
7. Store and retrieve the scanned barcodes
8. List and Exit callbacks

> **The camera is yours to manage.** **`BarcodeCountView` does NOT own or manage the camera.** You
> create the `Camera`, apply `BarcodeCount.createRecommendedCameraSettings()`, set it as the context's
> frame source, and switch it on/off yourself in the Activity/Fragment lifecycle (steps 3 and 6). This
> is unlike `BarcodeArView` (MatrixScan AR), which manages the camera internally.

Examples below use Kotlin and an Activity. The same APIs work in Fragments — adapt ownership of the
`DataCaptureContext`, `BarcodeCount`, and the view to the project's existing structure.

## Prerequisites

- Scandit Data Capture SDK for Android — add via Gradle. Before writing the dependency, fetch the
  latest published version from `https://central.sonatype.com/artifact/com.scandit.datacapture/barcode`
  and extract the latest version number from the page. Then add both dependencies to `app/build.gradle`:
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
  The SDK is distributed via Maven Central. It requires **`minSdk` 24 or higher** (the manifest merge
  fails with a lower `minSdk`).
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
  Request the permission at runtime using the standard Android permission API before scanning starts —
  the manifest declaration alone is not sufficient.

## Package paths

Import each class from exactly these packages — they are easy to get wrong (e.g. `TrackedBarcode`
lives under `batch.data`, not `batch`; `Feedback` is under `core.common.feedback`, not `core.feedback`).

| Class | Package |
|-------|---------|
| `BarcodeCount`, `BarcodeCountListener`, `BarcodeCountSession`, `BarcodeCountSessionSnapshot`, `BarcodeCountSettings`, `BarcodeClusterEditor` | `com.scandit.datacapture.barcode.count.capture` |
| `BarcodeCountCaptureList`, `BarcodeCountCaptureListListener`, `BarcodeCountCaptureListSession`, `TargetBarcode` | `com.scandit.datacapture.barcode.count.capture.list` |
| `BarcodeCountFeedback` | `com.scandit.datacapture.barcode.count.feedback` |
| `BarcodeCountView`, `BarcodeCountViewListener`, `BarcodeCountViewUiListener`, `BarcodeCountViewStyle`, `BarcodeCountNotInListActionSettings`, `BarcodeCountStatus` | `com.scandit.datacapture.barcode.count.ui.view` |
| `BarcodeCountStatusProvider`, `BarcodeCountStatusProviderCallback`, `BarcodeCountStatusItem`, `BarcodeCountStatusResultSuccess`, `BarcodeCountStatusResultError`, `BarcodeCountStatusResultAbort` | `com.scandit.datacapture.barcode.count.ui.view.status` |
| `BarcodeCountIcon`, `DefaultBarcodeCountIcons` | `com.scandit.datacapture.barcode.count.ui.icon` |
| `Barcode`, `Symbology`, `Cluster` | `com.scandit.datacapture.barcode.data` |
| `TrackedBarcode` | `com.scandit.datacapture.barcode.batch.data` |
| `SymbologySettings` | `com.scandit.datacapture.barcode.capture` |
| `BarcodeFilterSettings` | `com.scandit.datacapture.barcode.filter.capture` |
| `BarcodeFilterHighlightSettings` | `com.scandit.datacapture.barcode.filter.ui.overlay` |
| `DataCaptureContext` | `com.scandit.datacapture.core.capture` |
| `Camera`, `CameraSettings`, `FrameSourceState` | `com.scandit.datacapture.core.source` |
| `FrameData`, `ClusteringMode`, `ClusterExpectationStatus` | `com.scandit.datacapture.core.data` |
| `Feedback` | `com.scandit.datacapture.core.common.feedback` |
| `Brush` | `com.scandit.datacapture.core.ui.style` |
| `ScanditIcon`, `ScanditIconBuilder`, `ScanditIconType`, `ScanditIconShape` | `com.scandit.datacapture.core.ui.icon` |

## Minimal Integration (Kotlin)

Ask the user which barcode symbologies they need to scan. When asking about symbologies, mention that
it's important to only enable the ones they actually need — fewer enabled symbologies improves
scanning performance and accuracy.

Then ask which Activity or Fragment they'd like to integrate MatrixScan Count into, and write the
integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `implementation "com.scandit.datacapture:barcode:<version>"` and
   `implementation "com.scandit.datacapture:core:<version>"` to `app/build.gradle` (the version was
   already fetched and filled in above). Ensure `minSdk` is at least 24.
2. Add `<uses-permission android:name="android.permission.CAMERA" />` and the `<uses-feature>` element
   to `AndroidManifest.xml`.
3. Request the `CAMERA` permission at runtime before scanning starts.
4. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

The code below is the official Get Started flow assembled into one Activity.

```kotlin
import android.os.Bundle
import android.widget.FrameLayout
import androidx.appcompat.app.AppCompatActivity
import com.scandit.datacapture.barcode.count.capture.BarcodeCount
import com.scandit.datacapture.barcode.count.capture.BarcodeCountListener
import com.scandit.datacapture.barcode.count.capture.BarcodeCountSession
import com.scandit.datacapture.barcode.count.capture.BarcodeCountSessionSnapshot
import com.scandit.datacapture.barcode.count.capture.BarcodeCountSettings
import com.scandit.datacapture.barcode.count.ui.view.BarcodeCountView
import com.scandit.datacapture.barcode.count.ui.view.BarcodeCountViewUiListener
import com.scandit.datacapture.barcode.data.Barcode
import com.scandit.datacapture.barcode.data.Symbology
import com.scandit.datacapture.core.capture.DataCaptureContext
import com.scandit.datacapture.core.data.FrameData
import com.scandit.datacapture.core.source.Camera
import com.scandit.datacapture.core.source.FrameSourceState

class CountActivity : AppCompatActivity(), BarcodeCountListener, BarcodeCountViewUiListener {

    // Step 1: the Data Capture Context, created with your license key.
    private val dataCaptureContext =
        DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private var camera: Camera? = null
    private lateinit var barcodeCount: BarcodeCount
    private lateinit var barcodeCountView: BarcodeCountView

    // The app's own running tally. The BarcodeCountSession is only valid inside the listener
    // callback, so we copy the recognized barcodes out into this list (step 7).
    private var allRecognizedBarcodes: List<Barcode> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Step 3: obtain the camera, apply the recommended settings, and set it as the context's
        //         frame source. Always start from BarcodeCount.createRecommendedCameraSettings().
        val cameraSettings = BarcodeCount.createRecommendedCameraSettings()
        camera = Camera.getDefaultCamera(cameraSettings)
        dataCaptureContext.setFrameSource(camera)

        // Step 2: configure the Barcode Count mode. Settings start with all symbologies disabled —
        //         enable only the ones the app needs.
        val settings = BarcodeCountSettings()
        settings.setSymbologyEnabled(Symbology.EAN13_UPCA, true)
        settings.setSymbologyEnabled(Symbology.EAN8, true)
        settings.setSymbologyEnabled(Symbology.UPCE, true)
        settings.setSymbologyEnabled(Symbology.CODE128, true)
        settings.setSymbologyEnabled(Symbology.CODE39, true)

        barcodeCount = BarcodeCount.forDataCaptureContext(dataCaptureContext, settings)

        // Step 4: register a listener for completed scan phases.
        barcodeCount.addListener(this)

        // Step 5: add the BarcodeCountView (the built-in AR counting UI). It is created via the
        //         static newInstance() factory and does NOT add itself to the hierarchy.
        val container = FrameLayout(this)
        setContentView(container)
        barcodeCountView = BarcodeCountView.newInstance(this, dataCaptureContext, barcodeCount)
        container.addView(barcodeCountView)

        // Step 8: handle the List / Exit buttons.
        barcodeCountView.uiListener = this
    }

    // Step 6: the camera is NOT turned on automatically. Switch it on when the screen resumes and
    // off when it pauses.
    override fun onResume() {
        super.onResume()
        camera?.switchToDesiredState(FrameSourceState.ON)
    }

    override fun onPause() {
        super.onPause()
        camera?.switchToDesiredState(FrameSourceState.OFF)
    }

    override fun onDestroy() {
        super.onDestroy()
        barcodeCount.removeListener(this)
    }

    // Step 7: collect recognized barcodes when a scan phase completes.
    override fun onScan(
        barcodeCount: BarcodeCount,
        session: BarcodeCountSession,
        data: FrameData
    ) {
        // The session is only valid inside this callback — copy out what you need now.
        val recognizedBarcodes = session.recognizedBarcodes
        // This is invoked on an internal recognition thread; hop to the main thread before
        // touching app state / UI.
        runOnUiThread {
            allRecognizedBarcodes = recognizedBarcodes
        }
    }

    // Step 8: the List / Exit button callbacks. "List" = show progress so far; "Exit" = counting done.
    // Prefer the (view, snapshot) overloads — the snapshot gives you the barcodes at tap time.
    override fun onListButtonTapped(view: BarcodeCountView, snapshot: BarcodeCountSessionSnapshot?) {
        // Present a list, e.g. from snapshot?.recognizedBarcodes (counting still in progress).
    }

    override fun onExitButtonTapped(view: BarcodeCountView, snapshot: BarcodeCountSessionSnapshot?) {
        // The user finished — present a summary / complete the scanning.
    }
}
```

> `BarcodeCountView` is created with the **static `BarcodeCountView.newInstance(...)` factory — not a
> constructor**, and it does **not** add itself to the view hierarchy: call `addView(barcodeCountView)`
> (or use the `DataCaptureView` overload). Note the factory takes both the Android `Context` (`this`)
> and the `DataCaptureContext`.

## What the code does (and what it does NOT do)

- Creates the `DataCaptureContext` with the license key.
- Creates and configures the **camera** (`Camera.getDefaultCamera(...)` +
  `BarcodeCount.createRecommendedCameraSettings()`), sets it as the context frame source, and drives
  its state across the Activity lifecycle.
- Builds `BarcodeCountSettings` with the user's symbologies and creates the `BarcodeCount` mode.
- Registers a `BarcodeCountListener` to copy recognized barcodes off the session.
- Creates the `BarcodeCountView`, adds it to the hierarchy, and wires the List / Exit UI listener.

What this code does **not** do:
- It does not implement an **expected/receiving list** (`BarcodeCountCaptureList`) — the "scan against
  a known list" use case. → see **`list-scanning.md`**.
- It does not customize the **highlight appearance** (the per-barcode brush, or the Dot-style colors) —
  the default highlights are used. → see **`highlights.md`**.
- It does not enable **clustering** (grouping barcodes that belong together) — `clusteringMode` is off.
  → see **`clustering.md`**.
- It does not enable **status mode** (per-barcode status icons) — defaults are used.
  → see **`status-mode.md`**.

## Step 1 — Data Capture Context

```kotlin
val dataCaptureContext = DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
```

The context is the central object tying together the frame source (camera) and the capture mode. It
requires a valid license key. On Android it is created with the static factory
`DataCaptureContext.forLicenseKey(...)`.

## Step 2 — Configure the Barcode Count mode

`BarcodeCountSettings` starts with all symbologies disabled. Enable each via
`settings.setSymbologyEnabled(symbology, true)`; `enableSymbologies(set)` enables a whole set at once,
and `enabledSymbologies` (read-only) returns what's currently on.

```kotlin
val settings = BarcodeCountSettings()
settings.setSymbologyEnabled(Symbology.EAN13_UPCA, true)

val barcodeCount = BarcodeCount.forDataCaptureContext(dataCaptureContext, settings)
```

`BarcodeCount.forDataCaptureContext(context, settings)` is the **static factory** that attaches the
mode to the context — it is **not** a constructor (`BarcodeCount(...)`) and not `forContext(...)`. The
mode is enabled by default; you do not normally set `barcodeCount.isEnabled`. Only set
`barcodeCount.isEnabled = true` to re-enable the mode after you've disabled it.

Android `Symbology` names are **uppercase with underscores**: `Symbology.EAN13_UPCA`, `Symbology.QR`
(not `QR_CODE`), `Symbology.CODE128`, `Symbology.CODE39`, `Symbology.PDF417`. For the exact constant,
consult the
[Symbology API reference](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api/symbology.html) —
don't guess. Per-symbology tuning is available via `settings.getSymbologySettings(symbology)`; set it
on `BarcodeCountSettings` before creating the mode. For example, to restrict a variable-length
symbology to a length range:

```kotlin
settings.getSymbologySettings(Symbology.CODE128).activeSymbolCounts =
    (8..20).map { it.toShort() }.toSet()
```

`activeSymbolCounts` is **`Set<Short>`** on Android — convert your ints to `Short`. Other
`SymbologySettings` members: `isColorInvertedEnabled` (`Boolean`), `checksums` (an
`EnumSet<Checksum>`), and `enabledExtensions`.

If you're sure the scene contains only unique barcodes, set
`settings.expectsOnlyUniqueBarcodes = true` to improve performance.

## Step 3 — Camera and frame source

`BarcodeCountView` does **not** manage the camera. Obtain the back camera, apply the recommended
settings for Barcode Count, and set it as the context's frame source:

```kotlin
val cameraSettings = BarcodeCount.createRecommendedCameraSettings()
val camera = Camera.getDefaultCamera(cameraSettings)
dataCaptureContext.setFrameSource(camera)
```

`BarcodeCount.createRecommendedCameraSettings()` is a **static method** (not a property). Always start
from it — do **not** build a bare `CameraSettings()`. `Camera.getDefaultCamera(...)` returns the
default (back) camera, or `null` if the device has none — keep the reference nullable.

## Step 4 — Register the listener

```kotlin
barcodeCount.addListener(this)
```

`BarcodeCountListener` is an interface with default methods, so implement only what you need.
`onScan(barcodeCount, session, data)` is called when a scan phase finishes and results can be read from
the `BarcodeCountSession`. (`onSessionUpdated`, `onObservationStarted`, and `onObservationStopped` are
also available but optional.)

## Step 5 — Capture view and AR overlays

MatrixScan Count's built-in AR UI (buttons + overlays that guide the user) is added by placing a
`BarcodeCountView` in your hierarchy. Create it with the static factory and add it yourself:

```kotlin
val barcodeCountView = BarcodeCountView.newInstance(this, dataCaptureContext, barcodeCount)
container.addView(barcodeCountView)
```

The view has two styles, chosen via the `newInstance` overload that takes a `BarcodeCountViewStyle`
(`ICON` or `DOT`). **`ICON` is the default and the recommended style** (the modern look); prefer it
unless you specifically want plain colored dots. To opt into the Dot style:

```kotlin
val barcodeCountView = BarcodeCountView.newInstance(
    this, dataCaptureContext, barcodeCount, BarcodeCountViewStyle.DOT
)
```

`style` is read-only after construction (`barcodeCountView.style`), so pick it when creating the view.

## Step 6 — Configure the camera for the scanning view (lifecycle)

The camera is not turned on automatically. Switch the camera on when the screen resumes and off when it
pauses, from the Activity/Fragment lifecycle:

```kotlin
override fun onResume() {
    super.onResume()
    camera?.switchToDesiredState(FrameSourceState.ON)
}

override fun onPause() {
    super.onPause()
    camera?.switchToDesiredState(FrameSourceState.OFF)
}
```

`switchToDesiredState` is asynchronous — there is an overload taking a
`Callback<Boolean>` if you need to know when it has finished.

> When you navigate to another screen *within* the app and back and want a faster return, you can use
> `FrameSourceState.STANDBY` instead of `OFF` on the way out (keeps the camera warm). Use `OFF` when the
> app is genuinely leaving the scanning screen.

> **Common mistake — do NOT assume the view turns the camera on.** `BarcodeCountView` does not own the
> camera (unlike `BarcodeArView`). You **must** create the camera with `Camera.getDefaultCamera(...)`,
> apply `BarcodeCount.createRecommendedCameraSettings()`, call `dataCaptureContext.setFrameSource(...)`,
> and switch the camera state yourself in the lifecycle. Omitting any of these leaves the preview black
> / frozen. There is no `barcodeCountView.onResume()` / `start()` — those belong to `BarcodeArView`, not
> `BarcodeCountView`.

## Step 7 — Store and retrieve scanned barcodes

The scanned values live on the `BarcodeCountSession`, which is **only valid inside the listener
callback**. Copy `session.recognizedBarcodes` (`List<Barcode>`) out immediately, and hop to the main
thread before touching UI (the callback runs on an internal recognition thread):

```kotlin
override fun onScan(
    barcodeCount: BarcodeCount,
    session: BarcodeCountSession,
    data: FrameData
) {
    val recognizedBarcodes = session.recognizedBarcodes
    runOnUiThread {
        allRecognizedBarcodes = recognizedBarcodes
    }
}
```

`session.additionalBarcodes` holds barcodes added programmatically (via
`barcodeCount.setAdditionalBarcodes(...)` — useful for carrying a previous batch across a
background/foreground cycle), and `session.recognizedClusters` exposes cluster grouping when enabled
(see `clustering.md`).

## Step 8 — List and Exit callbacks

The built-in UI surfaces buttons whose taps are delivered through `BarcodeCountViewUiListener`
(`barcodeCountView.uiListener = ...`). Prefer the **`(view, snapshot)` overloads** — each hands you a
**nullable** `BarcodeCountSessionSnapshot?` with the barcodes at tap time (`recognizedBarcodes`,
`additionalBarcodes`, `recognizedClusters`, `frameSequenceId`), so you can populate the List screen
directly (use a safe call, `snapshot?.…`):

```kotlin
override fun onListButtonTapped(view: BarcodeCountView, snapshot: BarcodeCountSessionSnapshot?) {
    // Show the current progress, e.g. from snapshot?.recognizedBarcodes (not necessarily finished).
}

override fun onExitButtonTapped(view: BarcodeCountView, snapshot: BarcodeCountSessionSnapshot?) {
    // The user finished counting — present a summary.
}
```

> The older single-arg `onListButtonTapped(view)` / `onExitButtonTapped(view)` overloads (no snapshot)
> are **deprecated** — you'll still see them in existing code; prefer the `(view, snapshot)` variants.

`onSingleScanButtonTapped(view)` is also available (optional). Note this `uiListener`
(`BarcodeCountViewUiListener`) is **separate** from the `listener` (`BarcodeCountViewListener`) used for
brush customization and barcode-tap callbacks — see below and `highlights.md`.

## Reacting to barcode taps (optional)

This is **optional** — the basic integration does **not** wire up tap handling, and you should add it
only if the app's use case calls for reacting to a tap on a barcode (e.g. showing details for the
tapped item). Do not add it by default.

Tapping the List / Exit buttons is already handled by the `uiListener` above. If you *do* need to react
when the user taps a **barcode highlight** itself, set the view's `listener` (a
`BarcodeCountViewListener` — separate from the `uiListener`) and implement `onRecognizedBarcodeTapped`:

```kotlin
barcodeCountView.listener = object : BarcodeCountViewListener {
    override fun onRecognizedBarcodeTapped(view: BarcodeCountView, trackedBarcode: TrackedBarcode) {
        // e.g. show details for the tapped barcode (trackedBarcode.barcode.data)
    }
}
```

`trackedBarcode` is a `TrackedBarcode` (from the batch module) exposing `.barcode`, `.identifier`, and
`.location`; `barcode.data` is the decoded string. These callbacks arrive on the main thread. There are
matching tap callbacks for the other highlight states (`onRecognizedBarcodeNotInListTapped`,
`onAcceptedBarcodeTapped`, `onRejectedBarcodeTapped`, `onFilteredBarcodeTapped`, `onClusterTapped`); the
same `listener` is also where per-barcode brush customization lives — see `highlights.md`.

## Beyond the basics

These are common follow-ups; fetch the
[Advanced Configurations](https://docs.scandit.com/sdks/android/matrixscan-count/advanced/) page and the
API reference for exact signatures before writing code.

- **Receiving / capture list** (scan against a known list): build a `BarcodeCountCaptureList` from
  `TargetBarcode`s and apply it with `barcodeCount.setBarcodeCountCaptureList(...)`. → **full guide:
  `list-scanning.md`**.
- **Control visibility**: the view exposes many `shouldShow…` toggles (`shouldShowListButton`,
  `shouldShowExitButton`, `shouldShowShutterButton`, `shouldShowFloatingShutterButton`,
  `shouldShowSingleScanButton`, `shouldShowClearHighlightsButton`, `shouldShowStatusModeButton`,
  `shouldShowUserGuidanceView`, `shouldShowHints`, `shouldShowToolbar`, `shouldShowScanAreaGuides`,
  `shouldShowListProgressBar`, `shouldShowTorchControl`), plus `torchControlPosition`. They are Kotlin
  properties, e.g. `barcodeCountView.shouldShowTorchControl = true`.
- **Tap to uncount**: if the user should be able to remove a barcode after scanning it, set
  `barcodeCountView.tapToUncountEnabled = true`. Tapping an already-counted barcode then removes it from
  the current scanned items. (The hint text is customizable via the method
  `barcodeCountView.setTextForTapToUncountHint("…")`.)
- **Highlight appearance (icons / brushes)**: customize the per-barcode **icon** (default Icon style) or
  the **Dot-style** color via the `BarcodeCountViewListener` / the view's properties.
  → **full guide: `highlights.md`**.
- **Clustering** (group barcodes that belong together): enable it with
  `BarcodeCountSettings.clusteringMode`, optionally set `expectedNumberOfBarcodesPerCluster`, read
  `session.recognizedClusters`, and edit clusters with `barcodeCount.beginClusterEditing()`.
  → **full guide: `clustering.md`**.
- **Group scanning** (split a long count into batches the user advances through — one per pallet/box):
  set `settings.groupScanningEnabled = true` to add the Next Group / Redo controls. Results still come
  back as a flat list via the listener. → **full guide: `group-scanning.md`**.
- **Status mode** (annotate each counted barcode with a status icon the user reviews): implement
  `BarcodeCountStatusProvider`, register it via `barcodeCountView.setStatusProvider(...)`. → **full
  guide: `status-mode.md`**.
- **Reset the mode**: when a counting process is over and you want to start fresh, call
  `barcodeCount.reset()` to clear the scanned list and the AR overlays (e.g. from your Exit/summary
  flow). Clear your own running tally alongside it.
- **Feedback (sound / haptic)**: configured through `barcodeCount.feedback` (a `BarcodeCountFeedback`),
  whose `success` / `failure` are `Feedback` objects. `BarcodeCountFeedback.defaultFeedback()` beeps and
  vibrates. To suppress the beep and vibration, assign a feedback whose channels are silent:
  ```kotlin
  barcodeCount.feedback = BarcodeCountFeedback().apply {
      success = Feedback(null, null)   // Feedback(Vibration?, Sound?)
  }
  ```
  Note: BarcodeCount has **no** `isSoundEnabled` / `isHapticsEnabled` boolean (that is the MatrixScan
  Pick API) — feedback is always configured via the `BarcodeCountFeedback` object.

## Advanced configurations

These are optional configurations on top of the basic integration. They mirror the official
[Advanced Configurations](https://docs.scandit.com/sdks/android/matrixscan-count/advanced/) page. Verify
exact signatures against the API reference before writing code if anything is unclear.

### Filtering (count only some of the barcodes in the scene)

If several barcode types appear in the scene and you only want to count some of them, exclude the others
through `BarcodeCountSettings.filterSettings` (a `BarcodeFilterSettings`). Excluded barcodes still need
to be *enabled* on the settings — they are decoded, then filtered out of the count and covered by a
layer in the AR view. On Android `filterSettings` is read-only on `BarcodeCountSettings`, so **mutate
the object it returns in place** (do not assign a new one). Exclude by **symbology**
(`excludedSymbologies`), by a **regex** matched against the barcode data (`excludedCodesRegex`), or by
**symbol count** (`excludedSymbolCounts`):

```kotlin
val settings = BarcodeCountSettings()
settings.setSymbologyEnabled(Symbology.CODE128, true)
settings.setSymbologyEnabled(Symbology.PDF417, true)   // must be enabled to be decoded, then filtered
settings.filterSettings.excludedSymbologies = setOf(Symbology.PDF417)

val barcodeCount = BarcodeCount.forDataCaptureContext(dataCaptureContext, settings)
```

```kotlin
// Exclude every barcode whose data starts with "1234":
settings.filterSettings.excludedCodesRegex = "^1234.*"
```

- `excludedSymbologies` is a `Set<Symbology>`; `excludedCodesRegex` is a `String`.
- An excluded symbology that isn't part of the enabled symbologies has no effect — enable it first.
- The filtered barcodes are covered by a layer in the AR view. To change its color / transparency,
  assign a `BarcodeFilterHighlightSettings` to the **view's** `filterSettings` property.

### Hardware trigger (volume button)

You can let the view react to presses of a hardware key (e.g. the device **volume button**) instead of
(or alongside) the on-screen shutter — useful for one-handed scanning. On Android, pass the **key code**
to `enableHardwareTrigger` on the `BarcodeCountView`:

```kotlin
barcodeCountView.enableHardwareTrigger(android.view.KeyEvent.KEYCODE_VOLUME_DOWN)
```

`enableHardwareTrigger(Int?)` takes a nullable key code (pass `null` to use the SDK default key). The
companion property `BarcodeCountView.hardwareTriggerSupported` reports whether the device supports it.
(This is the Android form; the iOS `hardwareTriggerEnabled` boolean does not exist here.)

### Carrying a previous batch across a background/foreground cycle

Stash the recognized barcodes and call `barcodeCount.reset()` when leaving, then restore them as
already-counted with `barcodeCount.setAdditionalBarcodes(previouslyScanned)` when returning:

```kotlin
// leaving:
val carried = allRecognizedBarcodes
barcodeCount.reset()
// returning:
barcodeCount.setAdditionalBarcodes(carried)
```

`clearAdditionalBarcodes()` removes them again.

## After wiring up

Build the project. If compile errors remain, fetch the
[MatrixScan Count API reference](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html)
to find the correct API before guessing. Always include the docs link in your answer so the user can
explore further.
