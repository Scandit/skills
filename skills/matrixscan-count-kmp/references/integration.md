# MatrixScan Count KMP Integration Guide

MatrixScan Count (API class name: `BarcodeCount`) is a data capture mode that implements an out-of-the-box scan-and-count solution. It simultaneously tracks all barcodes in the camera feed and provides a ready-to-use UI. The user presses the shutter, the SDK counts the barcodes in view, and the result is delivered in the `BarcodeCountListener.onScan` callback.

On Scandit's Kotlin Multiplatform (KMP) SDK, the shared Kotlin code (`commonMain`) owns the `DataCaptureContext`, `BarcodeCount` mode, and camera, while the counting UI can be hosted two ways:

1. **The Compose Multiplatform wrapper** (`com.kmp.datacapture.barcode.compose.BarcodeCountView`) — a `@Composable` function. This is what the official `MatrixScanCountSimpleSample` uses on Android, and is the fastest path for a Compose-based app.
2. **The base (non-Compose) `BarcodeCountView`** (`com.kmp.datacapture.barcode.count.BarcodeCountView`) hosted via platform interop — needed whenever you need something the Compose wrapper doesn't expose (brushes, icons, hint text, toolbar settings, status mode, hardware trigger, filter highlighting, accessibility labels, per-barcode delegate callbacks). This is what the sample's iOS SwiftUI host (`ScannerView.swift`) uses, via `UIViewRepresentable`.

Both paths share the same `BarcodeCount` mode and `BarcodeCountSettings` — only the view layer differs.

## Prerequisites

- Maven/Gradle dependencies (group `com.scandit.datacapture.kmp`, version `8.6.0`):
  - `com.scandit.datacapture.kmp:core`
  - `com.scandit.datacapture.kmp:barcode`
  - `com.scandit.datacapture.kmp:barcode-compose` (only if using the Compose wrapper)
- iOS: add the **`Scandit/datacapture-kmp-spm`** Swift package to the iOS app target. This vends a single Kotlin framework re-exporting the core/barcode module surfaces — do not add separate per-module CocoaPods/SPM dependencies as you would for a native iOS app.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permissions configured by the app (the SDK does not request them for you):
  - Android: `<uses-permission android:name="android.permission.CAMERA" />` in the manifest, plus a runtime permission request (e.g. `ActivityResultContracts.RequestPermission()`).
  - iOS: `NSCameraUsageDescription` in `Info.plist`.
- No separate SDK-initialize call is required (unlike Flutter). `DataCaptureContext.forLicenseKey(licenseKey)` is usable immediately from shared code.

## Step 1 — Create the DataCaptureContext

```kotlin
import com.kmp.datacapture.core.capture.DataCaptureContext

private const val LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --"

val dataCaptureContext: DataCaptureContext = DataCaptureContext.forLicenseKey(LICENSE_KEY)
```

`DataCaptureContext.sharedInstance` (a process-wide singleton, populated by calling the `DataCaptureContext.initialize(licenseKey, ...)` companion function once at app start) is the alternative used as the default argument by the Compose wrapper below — use it if you don't want to thread a context through your own screen model.

## Step 2 — Configure BarcodeCountSettings and Symbologies

All symbologies are disabled by default. Only enable the ones the app actually needs.

```kotlin
import com.kmp.datacapture.barcode.count.BarcodeCountSettings
import com.kmp.datacapture.barcode.data.Symbology

val settings: BarcodeCountSettings = BarcodeCountSettings.barcodeCountSettings().also {
    it.enableSymbologies(
        setOf(
            Symbology.EAN13_UPCA,
            Symbology.EAN8,
            Symbology.UPCE,
            Symbology.CODE39,
            Symbology.CODE128,
        ),
    )
}
```

> **Symbology naming**: KMP uses SCREAMING_SNAKE_CASE (`Symbology.EAN13_UPCA`, `Symbology.CODE128`), not C# PascalCase or Dart lowerCamelCase.

### BarcodeCountSettings Properties and Methods

| API | Type | Description |
|-----|------|--------------|
| `enableSymbology(symbology, enabled)` | method | Enable or disable a single symbology. |
| `enableSymbologies(symbologies)` | method | Enable multiple symbologies (`Set<Symbology>`). |
| `getSymbologySettings(symbology)` | method | Returns `SymbologySettings` for a symbology. |
| `enabledSymbologies` | `Set<Symbology>` (read-only) | Currently enabled symbologies. |
| `expectsOnlyUniqueBarcodes` | `Boolean` | Set `true` if duplicates within a batch are not expected — optimizes tracking. |
| `disableModeWhenCaptureListCompleted` | `Boolean` | Auto-disable the mode once the capture list is fully scanned. See the capture-list callout below — there is currently no way to attach a list, so this property has no observable effect on KMP. |
| `mappingEnabled` | `Boolean` | Enables the barcode mapping (spatial map) flow. |
| `groupScanningEnabled` | `Boolean` | Enables group (cluster) scanning. |
| `expectedNumberOfBarcodesPerCluster` | `Int?` | Expected barcodes per cluster when group scanning. |
| `clusteringMode` | `ClusteringMode` | `DISABLED`, `MANUAL`, `AUTO`, `AUTO_WITH_MANUAL_CORRECTION`. |
| `filterSettings` | `BarcodeFilterSettings` (read-only getter) | Mode-level filter: mutate in place, don't reassign. See Filtering below. |

### Filtering (excluding barcodes by symbology or regex)

The mode-level filter drops barcodes before they're counted — distinct from the view-level `BarcodeFilterHighlightSettings` (`view.filterSettings`), which only controls how filtered barcodes are highlighted.

```kotlin
// Enable Code 128 but never count PDF417 — PDF417 still needs to be enabled so it's
// decoded and then filtered out.
settings.enableSymbology(Symbology.CODE128, true)
settings.enableSymbology(Symbology.PDF417, true)
settings.filterSettings.excludedSymbologies = setOf(Symbology.PDF417)

// Drop every barcode whose data starts with four digits:
settings.filterSettings.excludedCodesRegex = "^\\d{4}.*"
```

`BarcodeFilterSettings` also exposes `excludedSymbolCounts` (`Map<Symbology, Set<Short>>`), `excludeEan13`, and `excludeUpca`.

## Step 3 — Construct BarcodeCount and the Camera

```kotlin
import com.kmp.datacapture.barcode.count.BarcodeCount
import com.kmp.datacapture.core.source.Camera
import com.kmp.datacapture.core.source.FrameSourceState

val barcodeCount: BarcodeCount = BarcodeCount.forContext(dataCaptureContext, settings)

// Recommended camera settings tuned for BarcodeCount.
val camera: Camera? =
    Camera.getDefaultCamera(BarcodeCount.createRecommendedCameraSettings())?.also {
        dataCaptureContext.setFrameSource(it)
    }
```

> `BarcodeCount(settings)` (the context-free constructor some other Scandit bindings expose) does **not** exist on KMP — always use the `forContext(context, settings)` companion factory. `createRecommendedCameraSettings()` is a **method** here (matching native Android), not a property (as on iOS/.NET native).

### BarcodeCount Methods and Properties

| API | Description |
|-----|-------------|
| `BarcodeCount.forContext(context, settings)` | Companion factory. Automatically added to `context` when non-null. |
| `BarcodeCount.createRecommendedCameraSettings()` | Companion factory returning `CameraSettings` tuned for BarcodeCount. |
| `addListener(listener)` / `removeListener(listener)` | Register/remove a `BarcodeCountListener`. Idempotent. |
| `applySettings(settings)` | Apply updated settings at runtime. |
| `reset()` | Resets the session, clearing the history of tracked/unscanned barcodes. |
| `setAdditionalBarcodes(barcodes)` | Inject `List<Barcode>` from a previous session as partial results. |
| `clearAdditionalBarcodes()` | Clear injected additional barcodes. |
| `startScanningPhase()` | Programmatically trigger a scan (same as pressing the shutter). |
| `endScanningPhase()` | Disables the mode and switches off the current frame source. |
| `isEnabled` | `Boolean` — enable/disable the mode. Must be `true` for frames to be processed. |
| `feedback` | `BarcodeCountFeedback` — sound/vibration on scan events. |
| `dataCaptureContext` | The context this mode is attached to (read-only, nullable). |

## Step 4 — BarcodeCountListener

```kotlin
import com.kmp.datacapture.barcode.count.BarcodeCount
import com.kmp.datacapture.barcode.count.BarcodeCountListener
import com.kmp.datacapture.barcode.count.BarcodeCountSession
import com.kmp.datacapture.core.data.FrameData

class CountScreenModel : BarcodeCountListener {

    override fun onScan(barcodeCount: BarcodeCount, session: BarcodeCountSession, frameData: FrameData) {
        val recognized = session.recognizedBarcodes
        for (barcode in recognized) {
            println("Scanned: ${barcode.data} (${barcode.symbology})")
        }
    }
}

// barcodeCount.addListener(this) once constructed.
```

### BarcodeCountListener Callbacks

| Callback | Description |
|----------|-------------|
| `onScan(barcodeCount, session, frameData)` | Called once the scanning phase is over (shutter pressed or `startScanningPhase()` called). |
| `onSessionUpdated(barcodeCount, session, frameData)` | Default no-op. Override to react on **every processed frame**, not just on shutter press. |
| `onObservationStarted(barcodeCount)` | Default no-op. |
| `onObservationStopped(barcodeCount)` | Default no-op. |

> `onScan`/`onSessionUpdated` hand you `frameData: FrameData` directly (synchronous parameter) — there is no async "get frame data" accessor here the way Flutter's `Future<FrameData> Function()` works.

### BarcodeCountSession Properties

| Property | Type | Description |
|----------|------|--------------|
| `recognizedBarcodes` | `List<Barcode>` | All currently recognized barcodes. |
| `additionalBarcodes` | `List<Barcode>` | Barcodes injected via `setAdditionalBarcodes`. |
| `frameSequenceID` | `Int` | Identifier of the current frame sequence. |
| `reset()` | method | Resets the session state, clearing all recognized barcodes. |
| `getSpatialMap()` | method | `BarcodeSpatialGrid?` — requires `mappingEnabled = true`. |
| `getSpatialMap(rows, columns)` | method | Spatial map fitted to expected grid size. |

A cold-Flow alternative is also available: `BarcodeCount.sessionUpdates: Flow<BarcodeCountSession>` (in `com.kmp.datacapture.barcode.count`) — collecting it registers a listener internally and removes it on cancellation. This is what the Compose wrapper below uses internally to drive `onScan`.

## Step 5 — Host the View: Compose Wrapper (sample pattern)

The Compose Multiplatform wrapper is the fastest path and mirrors the official `MatrixScanCountSimpleSample`'s Android screen:

```kotlin
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.kmp.datacapture.barcode.compose.BarcodeCountView

@Composable
fun ScannerScreen(
    screenModel: CountScreenModel,
    dataCaptureContext: DataCaptureContext,
    barcodeCount: BarcodeCount,
    settings: BarcodeCountSettings,
    onListTap: () -> Unit,
    onExitTap: () -> Unit,
) {
    Box(modifier = Modifier.fillMaxSize()) {
        BarcodeCountView(
            settings = settings,
            modifier = Modifier.fillMaxSize(),
            showListButton = true,
            showExitButton = true,
            onScan = { barcodes -> /* update your own aggregated list */ },
            onExitTap = onExitTap,
            onListTap = onListTap,
            context = dataCaptureContext,
            barcodeCount = barcodeCount,
        )
    }
}
```

If you don't already own a `BarcodeCount` instance, let the wrapper build (and tear down) one for you with `rememberBarcodeCount`:

```kotlin
import com.kmp.datacapture.barcode.compose.BarcodeCountView
import com.kmp.datacapture.barcode.compose.rememberBarcodeCount

@Composable
fun ScannerScreen(settings: BarcodeCountSettings, onExitTap: () -> Unit) {
    val barcodeCount = rememberBarcodeCount(settings = settings)
    BarcodeCountView(
        settings = settings,
        barcodeCount = barcodeCount,
        onExitTap = onExitTap,
    )
}
```

`rememberBarcodeCount(context, settings)` removes the mode from `context` when the composable leaves composition — without it, `BarcodeCount.forContext` registers the mode on the (by default process-wide) context, and navigating in/out of a screen would accumulate a fresh mode every time.

### Composable Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `settings` | `BarcodeCountSettings.barcodeCountSettings()` | Ignored if an explicit `barcodeCount` is passed. |
| `style` | `BarcodeCountViewStyle.ICON` | Bound at construction; changing it rebuilds the view. |
| `modifier` | `Modifier` | Compose modifier for the hosting box. |
| `showUserGuidanceView` | `true` | Shows the user-guidance overlay. |
| `showListButton` | `true` | Shows the list button. |
| `showExitButton` | `true` | Shows the exit button. |
| `showShutterButton` | `true` | Shows the shutter button. |
| `showToolbar` | `true` | Shows the collapsable toolbar. |
| `showSingleScanButton` | `false` | Shows the single-scan button. |
| `onScan` | `{}` | Invoked with `List<Barcode>` (the session's recognized barcodes) on each update. |
| `onExitTap` / `onListTap` / `onSingleScanTap` | `null` | Invoked on the matching button tap; `null` leaves it unhandled. |
| `overlay` | `{}` | `@Composable BoxScope.() -> Unit` — Compose content drawn on top of the view. |
| `context` | `DataCaptureContext.sharedInstance` | The context the mode is attached to. |
| `barcodeCount` | built from `settings` via `rememberBarcodeCount` | Advanced override — pass your own long-lived mode instance to survive navigation. |

> **What this composable does NOT expose**: brushes (`recognizedBrush`/`notInListBrush`/`acceptedBrush`/`rejectedBrush`), per-barcode icon/brush overrides, `setStatusProvider`, `setToolbarSettings`, hint-text setters, `enableHardwareTrigger`, `tapToUncountEnabled`, `filterSettings` (view-level), accessibility labels, torch control, or the per-barcode `BarcodeCountViewListener` delegate. For any of these, use the base-view interop pattern below.

## Step 6 — Host the View: Base-View Interop Alternative

Use this when you need customization the Compose wrapper doesn't expose, or when the app isn't Compose-based. The base `BarcodeCountView` constructor **differs per platform** and cannot be called from shared `commonMain` code — construct it in platform-specific code and expose it through `toAndroidView()` / `toUIView()`.

### Android (Kotlin, inside or outside Compose)

```kotlin
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.activity.ComponentActivity
import com.kmp.datacapture.barcode.count.BarcodeCount
import com.kmp.datacapture.barcode.count.BarcodeCountView
import com.kmp.datacapture.barcode.count.BarcodeCountViewStyle
import com.kmp.datacapture.barcode.ui.toAndroidView

@Composable
fun CustomScannerScreen(barcodeCount: BarcodeCount) {
    val activity = LocalContext.current as ComponentActivity
    val view = remember(activity, barcodeCount) {
        BarcodeCountView(activity, barcodeCount, BarcodeCountViewStyle.DOT).apply {
            recognizedBrush = defaultRecognizedBrush()
            onResume()
        }
    }
    AndroidView(modifier = Modifier.fillMaxSize(), factory = { view.toAndroidView() })
}
```

### iOS (Swift, consuming the shared Kotlin framework)

This is the exact pattern used by the sample's `ScannerView.swift`:

```swift
import SwiftUI
import shared

private struct BarcodeCountViewRepresentable: UIViewRepresentable {
    let barcodeCount: BarcodeCount

    func makeUIView(context: Context) -> UIView {
        let view = BarcodeCountView(barcodeCount: barcodeCount, style: .icon)
        view.shouldShowListButton = true
        view.shouldShowExitButton = true
        view.onResume()
        return view.toUIView()
    }

    func updateUIView(_ uiView: UIView, context: Context) {}

    static func dismantleUIView(_ uiView: UIView, coordinator: ()) {
        // Retain a reference to the BarcodeCountView (e.g. in a Coordinator) to call onPause() here.
    }
}
```

> The `BarcodeCountViewUiListener` interface (`onExitButtonTapped`, `onListButtonTapped`, `onSingleScanButtonTapped`) has **two overloads each** for exit/list (a no-arg one and a `snapshot: BarcodeCountSessionSnapshot?` one); Swift requires implementing **all five** methods even though the Kotlin interface gives each a default empty body — Kotlin interface defaults are not optional Swift protocol requirements.

## Step 7 — Status Mode / Status Provider

Only reachable through the base `BarcodeCountView` (not the Compose wrapper). Implement `BarcodeCountStatusProvider` to assign a status icon per scanned barcode:

```kotlin
import com.kmp.datacapture.barcode.batch.TrackedBarcode
import com.kmp.datacapture.barcode.count.BarcodeCountStatusProvider
import com.kmp.datacapture.barcode.count.BarcodeCountStatusProviderCallback
import com.kmp.datacapture.barcode.count.BarcodeCountStatusResult
import com.kmp.datacapture.barcode.count.BarcodeCountStatusItem
import com.kmp.datacapture.core.ui.ScanditIconBuilder
import com.kmp.datacapture.core.ui.ScanditIconShape
import com.kmp.datacapture.core.ui.ScanditIconType
import com.kmp.datacapture.core.common.Color

class AcceptRejectStatusProvider : BarcodeCountStatusProvider {
    override fun onStatusRequested(
        barcodes: List<TrackedBarcode>,
        callback: BarcodeCountStatusProviderCallback,
    ) {
        val items = barcodes.map { tracked ->
            val accepted = tracked.barcode.data?.startsWith("4") == true
            val icon = ScanditIconBuilder()
                .withIcon(if (accepted) ScanditIconType.CHECKMARK else ScanditIconType.EXCLAMATION_MARK)
                .withIconColor(Color.fromRgba(255, 255, 255))
                .withBackgroundColor(if (accepted) Color.fromRgba(0, 200, 68) else Color.fromRgba(255, 45, 45))
                .withBackgroundShape(ScanditIconShape.CIRCLE)
                .build()
            BarcodeCountStatusItem.create(tracked, icon)
        }
        callback.onStatusReady(
            BarcodeCountStatusResult.Success(
                statusList = items,
                statusModeEnabledMessage = null,
                statusModeDisabledMessage = null,
            ),
        )
    }
}

// Attach it to the base BarcodeCountView (see Step 6):
view.setStatusProvider(AcceptRejectStatusProvider())
view.shouldShowStatusIconsOnScan = true   // status icons appear automatically on scan
// Or, to show them only when the button is tapped instead:
// view.shouldShowStatusModeButton = true
```

> `ScanditIconType` cases: `CHECKMARK`, `EXCLAMATION_MARK` (among others). `ScanditIconShape` cases: `CIRCLE`, `SQUARE`.

`BarcodeCountStatusResult` factory companions: `Success(statusList, statusModeEnabledMessage, statusModeDisabledMessage)`, `Error(statusList, errorMessage, statusModeDisabledMessage)`, `Abort(errorMessage)`. `BarcodeCountStatusItem.create(barcode: TrackedBarcode, icon: ScanditIcon?)` — pass `icon = null` to show no status for that barcode (it's still "handled"; a barcode you omit from the list entirely is instead treated as missing its status).

## Step 8 — Capture Lists (Scanning Against a List) — NOT YET AVAILABLE ON KMP

`BarcodeCountCaptureList`, `TargetBarcode`, `BarcodeCountCaptureListListener`, and `BarcodeCountCaptureListSession` all exist on KMP 8.6 and are fully constructible:

```kotlin
import com.kmp.datacapture.barcode.count.BarcodeCountCaptureList
import com.kmp.datacapture.barcode.count.TargetBarcode

val targetBarcodes = listOf(
    TargetBarcode.create("0123456789012", 2),
    TargetBarcode.create("9780201379624", 1),
)
val captureList = BarcodeCountCaptureList.create(myListener, targetBarcodes)
```

**However, there is no method on `BarcodeCount` to attach this list to the mode.** The native SDKs' `SetBarcodeCountCaptureList` / `setCaptureList` method has no `kmp` entry in the API reference's availability list, and the KMP `BarcodeCount` class (Android and iOS actuals) has no matching member. Do not write `barcodeCount.setBarcodeCountCaptureList(...)` — it does not exist and will not compile.

Practical consequence: build a `BarcodeCountCaptureList` if you like, but it cannot currently drive `session.correctBarcodes` / `wrongBarcodes` / `missingBarcodes` on KMP, and `BarcodeCountSettings.disableModeWhenCaptureListCompleted` has no attached list to react to. If a user asks for scanning-against-a-list on KMP, tell them this is not yet wired up rather than assembling code that looks complete but silently does nothing.

## Step 9 — Toolbar & UI Customization (Base View)

All reachable only via the base `BarcodeCountView` (see Step 6):

```kotlin
view.shouldShowToolbar = false
view.shouldShowExitButton = false
view.shouldShowFloatingShutterButton = true
view.shouldShowClearHighlightsButton = true
view.tapToUncountEnabled = true
view.setTextForTapToUncountHint("Tap to remove")

view.setTextForTapShutterToScanHint("Tap to scan")
view.setTextForScanningHint("Scanning…")
view.setTextForMoveCloserAndRescanHint("Move closer and scan again")
view.setTextForMoveFurtherAndRescanHint("Move further and scan again")

view.shouldShowTorchControl = true
view.torchControlPosition = Anchor.TOP_LEFT

// Hardware trigger (enterprise devices). Pass null for the default key on Android;
// on iOS any call enables the volume button.
if (BarcodeCountView.hardwareTriggerSupported) {
    view.enableHardwareTrigger(null)
}
```

### Toolbar text (`BarcodeCountToolbarSettings`)

```kotlin
import com.kmp.datacapture.barcode.count.BarcodeCountToolbarSettings

val toolbarSettings = BarcodeCountToolbarSettings().apply {
    audioOnButtonText = "Sound On"
    audioOffButtonText = "Sound Off"
    vibrationOnButtonText = "Vibration On"
    vibrationOffButtonText = "Vibration Off"
}
view.setToolbarSettings(toolbarSettings)
```

### Brushes (Dot style only)

```kotlin
import com.kmp.datacapture.core.ui.style.Brush
import com.kmp.datacapture.core.common.Color

view.recognizedBrush = Brush(
    Color.fromRgba(0, 204, 68, 102),
    Color.fromRgba(0, 204, 68, 255),
    1.0f,
)
view.notInListBrush = Brush(
    Color.fromRgba(255, 45, 45, 102),
    Color.fromRgba(255, 45, 45, 255),
    1.0f,
)
```

Brush properties (`recognizedBrush`, `notInListBrush`, `acceptedBrush`, `rejectedBrush`) and their per-barcode setters (`setBrushForRecognizedBarcode`, `setBrushForRecognizedBarcodeNotInList`, `setBrushForAcceptedBarcode`, `setBrushForRejectedBarcode`) only have a visible effect in `BarcodeCountViewStyle.DOT` — they're ignored in the default `ICON` style. Use `setIconForRecognizedBarcode` / `setIconForRecognizedBarcodeNotInList` / `setIconForAcceptedBarcode` / `setIconForRejectedBarcode` (each taking a `BarcodeCountIcon`) to recolor per-barcode state in `ICON` style instead.

### Per-barcode delegate (`BarcodeCountViewListener`)

```kotlin
import com.kmp.datacapture.barcode.count.BarcodeCountViewListener

class CustomizationListener : BarcodeCountViewListener {
    override fun onRecognizedBarcodeTapped(view: BarcodeCountView, trackedBarcode: TrackedBarcode) {
        println("Tapped: ${trackedBarcode.barcode.data}")
    }
}

view.listener = CustomizationListener()
```

`BarcodeCountViewListener` also has `brushForRecognizedBarcode`/`brushForRecognizedBarcodeNotInList`/`brushForAcceptedBarcode`/`brushForRejectedBarcode`/`brushForCluster`, `iconForRecognizedBarcode`/`iconForRecognizedBarcodeNotInList`/`iconForAcceptedBarcode`/`iconForRejectedBarcode`, `onFilteredBarcodeTapped`, `onRecognizedBarcodeNotInListTapped`, `onAcceptedBarcodeTapped`, `onRejectedBarcodeTapped`, `onClusterTapped`, and `onCaptureListCompleted` — all with default no-op/`null` implementations, so override only what you need. `view.listener` is a single settable property (not `addListener`/`removeListener` — that pair is reserved for `BarcodeCountViewUiListener`, which does support multiple registered listeners on KMP).

## Step 10 — Feedback

```kotlin
import com.kmp.datacapture.barcode.count.BarcodeCountFeedback

// Default: sound + vibration for both success and failure.
barcodeCount.feedback = BarcodeCountFeedback.defaultFeedback()

// Silence everything:
barcodeCount.feedback = BarcodeCountFeedback()
```

`BarcodeCountFeedback` exposes `success: Feedback` and `failure: Feedback` (both mutable), plus the `defaultFeedback()` companion factory.

## Step 11 — Lifecycle & Teardown

The camera and the mode are independent — the view does not own the camera. Toggle both explicitly:

```kotlin
fun resumeFrameSource() {
    barcodeCount.isEnabled = true
    camera?.switchToDesiredState(FrameSourceState.ON)
}

fun pauseFrameSource() {
    camera?.switchToDesiredState(FrameSourceState.OFF)
}

fun dispose() {
    camera?.switchToDesiredState(FrameSourceState.OFF)
    barcodeCount.removeListener(this)
    dataCaptureContext.removeMode(barcodeCount)
}
```

The **view itself** also has its own resume/pause lifecycle, independent of the camera:

- Compose wrapper: calls `view.onResume()` as its final mount step and `view.onPause()` on dispose automatically — you don't call these yourself.
- Base-view interop: call `view.onResume()` after construction (Android: once added to the hierarchy; iOS: in `makeUIView`) and `view.onPause()` on teardown (`dismantleUIView` / `onDestroy`). Calling either when already in that state is a no-op.

Registering the same `BarcodeCountViewUiListener` twice is a no-op (idempotent) on the base view.

## Common Pitfalls

1. **Don't reach for Compose-wrapper parameters that don't exist.** Brushes, icons, hints, toolbar settings, the status provider, hardware trigger, `tapToUncountEnabled`, and the per-barcode `BarcodeCountViewListener` are only on the base `BarcodeCountView` — see Step 6.
2. **Don't invent `setBarcodeCountCaptureList` / `setCaptureList` on `BarcodeCount`.** It does not exist on KMP 8.6 — see Step 8. `BarcodeCountCaptureList` and its listener/session types exist but cannot currently be attached to the mode.
3. **Don't construct `BarcodeCount(settings)`.** Use `BarcodeCount.forContext(context, settings)` — the context-free constructor from Flutter/JS bindings has no KMP equivalent.
4. **Don't call the base `BarcodeCountView` constructor from `commonMain`.** Its signature differs per platform (Android needs a `Context`, iOS doesn't) — construct it in platform-specific code, exactly like the sample's iOS `ScannerView.swift` / the compose module's internal `rememberBarcodeCountScanView`.
5. **Brushes only render in `BarcodeCountViewStyle.DOT`.** In the default `ICON` style, set the analogous `iconFor*` callback / `*Icon` property instead — a brush set on an `ICON`-style view silently does nothing.
6. **Symbology case matters.** `Symbology.EAN13_UPCA`, not `Symbology.Ean13Upca` or `Symbology.ean13Upca`.
7. **`onScan` only fires once per shutter press.** For per-frame reactions (e.g. live highlighting logic), override `onSessionUpdated` instead — it is a no-op by default and easy to forget.
8. **The camera is not owned by the view.** You must call `dataCaptureContext.setFrameSource(camera)` and toggle `camera.switchToDesiredState(...)` yourself in your screen's resume/pause lifecycle; the pre-built view only owns its own `onResume()`/`onPause()` UI lifecycle, not the camera.
9. **`toNative()` is an internal bridging API**, not meant for app code. Use the typed `toAndroidView()` / `toUIView()` extensions instead when you need the platform view.
