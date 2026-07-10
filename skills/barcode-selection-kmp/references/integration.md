# BarcodeSelection — Kotlin Multiplatform Integration

This reference covers integrating `BarcodeSelection`, Scandit's tap-to-select / aim-to-select mode for choosing individual barcodes out of a dense scene with several codes visible at once, into a Kotlin Multiplatform (KMP) app targeting Android and iOS from a shared module. It is grounded in the canonical sample `BarcodeSelectionSimpleSample` (`01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low_Level_API/`) and the KMP SDK source (`com.kmp.datacapture.*`).

Package roots used throughout: `com.kmp.datacapture.core.*` (context, camera, view, feedback primitives) and `com.kmp.datacapture.barcode.*` (BarcodeSelection and its settings/selection-type/strategy/session/overlay/listener, and `Symbology`/`Barcode`/`CapturePreset`).

`BarcodeSelection` requires the MatrixScan add-on entitlement on the Scandit license.

## Prerequisites

### Gradle (commonMain)

Add the core and barcode KMP modules to your shared module's `commonMain` source set:

```kotlin
// shared/build.gradle.kts
kotlin {
    sourceSets {
        commonMain.dependencies {
            implementation("com.scandit.datacapture.kmp:core:8.6.0")
            implementation("com.scandit.datacapture.kmp:barcode:8.6.0")
        }
    }
}
```

If you'll also use the Compose Multiplatform view (see below), additionally add:

```kotlin
implementation("com.scandit.datacapture.kmp:core-compose:8.6.0")
```

### iOS (Swift Package Manager)

Add the SDK's SPM package from `Scandit/datacapture-kmp-spm` on GitHub to your iOS app target (Xcode: File > Add Package Dependencies). It ships as a single umbrella XCFramework — your app links exactly **one** Kotlin framework, so pick the variant that includes the barcode module (do not also add a separate "core-only" variant alongside it, or the app will contain two copies of the Kotlin runtime).

### Camera permission

- **Android**: declare `<uses-permission android:name="android.permission.CAMERA" />` in `AndroidManifest.xml`, and additionally request it at runtime before starting the camera — the manifest entry alone does not grant it. Use `ActivityResultContracts.RequestPermission()` (see the canonical sample's `HomeScreen.kt`), and only proceed to the scanner screen once `PackageManager.PERMISSION_GRANTED` is confirmed.
- **iOS**: add `NSCameraUsageDescription` to `Info.plist` with a user-facing justification string. iOS presents the system permission prompt automatically the first time the camera is started; no separate request call is needed.

## Minimal Integration

The sample's structure — and the pattern to teach first — is a **shared `ScreenModel`** that owns every Scandit object (context, camera, settings, mode, overlay) behind a `StateFlow`, plus a thin platform host on each side that builds the `DataCaptureView` and embeds it.

### 1. Shared ScreenModel (`commonMain`)

```kotlin
package com.example.selection

import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.barcode.selection.BarcodeSelection
import com.kmp.datacapture.barcode.selection.BarcodeSelectionBasicOverlay
import com.kmp.datacapture.barcode.selection.BarcodeSelectionListener
import com.kmp.datacapture.barcode.selection.BarcodeSelectionSession
import com.kmp.datacapture.barcode.selection.BarcodeSelectionSettings
import com.kmp.datacapture.barcode.selection.BarcodeSelectionTapSelection
import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.core.data.FrameData
import com.kmp.datacapture.core.source.Camera
import com.kmp.datacapture.core.source.FrameSourceState
import com.kmp.datacapture.core.ui.DataCaptureView
import com.kmp.datacapture.core.ui.LogoStyle
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

internal const val LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --"

class SelectionScreenModel : BarcodeSelectionListener {

    private val _state = MutableStateFlow(SelectionUiState())
    val state: StateFlow<SelectionUiState> = _state.asStateFlow()

    val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize(LICENSE_KEY)

    private val camera: Camera? =
        Camera.getDefaultCamera(BarcodeSelection.createRecommendedCameraSettings())?.also {
            dataCaptureContext.setFrameSource(it)
        }

    // All symbologies are disabled by default — enable exactly what you need.
    // The default selectionType is Tap-to-Select.
    private val settings: BarcodeSelectionSettings =
        BarcodeSelectionSettings.barcodeSelectionSettings().also {
            it.selectionType = BarcodeSelectionTapSelection.tapSelection()
            it.enableSymbology(Symbology.EAN13_UPCA, true)
            it.enableSymbology(Symbology.CODE128, true)
            it.enableSymbology(Symbology.QR, true)
        }

    val barcodeSelection: BarcodeSelection =
        BarcodeSelection.forContext(dataCaptureContext, settings).also {
            it.addListener(this)
        }

    fun setupDataCaptureView(view: DataCaptureView): DataCaptureView {
        view.logoStyle = LogoStyle.MINIMAL
        view.addOverlay(BarcodeSelectionBasicOverlay.withBarcodeSelectionForView(barcodeSelection, view))
        return view
    }

    fun onEvent(event: SelectionEvent) {
        when (event) {
            SelectionEvent.STARTED -> {
                camera?.switchToDesiredState(FrameSourceState.ON)
                barcodeSelection.isEnabled = true
            }
            SelectionEvent.STOPPED -> {
                barcodeSelection.isEnabled = false
                camera?.switchToDesiredState(FrameSourceState.OFF)
            }
        }
    }

    override fun onSelectionUpdated(
        barcodeSelection: BarcodeSelection,
        session: BarcodeSelectionSession,
        frameData: FrameData?,
    ) {
        // newlySelectedBarcodes/newlyUnselectedBarcodes are Lists — a single
        // frame can select or unselect more than one barcode (e.g. after
        // selectUnselectedBarcodes()).
        val barcode = session.newlySelectedBarcodes.firstOrNull() ?: return
        _state.value = _state.value.copy(
            lastSelectionData = barcode.data ?: "",
            lastSelectionCount = session.getCount(barcode),
        )
    }

    override fun onSessionUpdated(
        barcodeSelection: BarcodeSelection,
        session: BarcodeSelectionSession,
        frameData: FrameData?,
    ) = Unit

    fun dispose() {
        barcodeSelection.isEnabled = false
        barcodeSelection.removeListener(this)
        dataCaptureContext.removeMode(barcodeSelection)
        camera?.switchToDesiredState(FrameSourceState.OFF)
    }
}

data class SelectionUiState(
    val lastSelectionData: String = "",
    val lastSelectionCount: Int = 0,
)

enum class SelectionEvent { STARTED, STOPPED }
```

`onObservationStarted` / `onObservationStopped` on `BarcodeSelectionListener` have empty default bodies — only override them if you need to react to the mode's observation lifecycle; `onSelectionUpdated` and `onSessionUpdated` must be implemented. Note `frameData` is nullable (`FrameData?`) — it is `null` when the camera is frozen and the selection changes.

### 2. Android host

Android's `DataCaptureView` constructor requires a `Context`. Build the view in the host, hand it to the shared `setupDataCaptureView`, and embed the native `View` via `toAndroidView()`:

```kotlin
@Composable
fun SelectionScreen() {
    val context = LocalContext.current
    val screenModel = remember { SelectionScreenModel() }

    val dataCaptureView = remember {
        screenModel.setupDataCaptureView(
            DataCaptureView(context, screenModel.dataCaptureContext),
        )
    }

    DisposableEffect(Unit) {
        screenModel.onEvent(SelectionEvent.STARTED)
        onDispose { screenModel.dispose() }
    }

    AndroidView(
        modifier = Modifier.fillMaxSize(),
        factory = { dataCaptureView.toAndroidView() },
    )
}
```

### 3. iOS host

iOS's `DataCaptureView` constructor takes no `Context` parameter. Embed the native `UIView` via `toUIView()` inside a `UIViewRepresentable`:

```swift
struct SelectionHost: View {
    @StateObject private var screenModel = SelectionScreenModel()

    var body: some View {
        DataCaptureViewRepresentable {
            screenModel.setupDataCaptureView(
                view: DataCaptureView(dataCaptureContext: screenModel.dataCaptureContext)
            ).toUIView()
        }
        .edgesIgnoringSafeArea(.all)
        .onAppear { screenModel.onEvent(event: .started) }
        .onDisappear { screenModel.onEvent(event: .stopped) }
    }
}

struct DataCaptureViewRepresentable: UIViewRepresentable {
    let makeView: () -> UIView
    func makeUIView(context: Context) -> UIView { makeView() }
    func updateUIView(_ uiView: UIView, context: Context) {}
}
```

## Selection types: Tap vs Aimer, and strategies

`settings.selectionType: BarcodeSelectionType` chooses how the user selects barcodes. Defaults to Tap-to-Select.

### Tap-to-Select

```kotlin
settings.selectionType = BarcodeSelectionTapSelection.tapSelection().also {
    it.tapBehavior = BarcodeSelectionTapBehavior.TOGGLE_SELECTION   // or .REPEAT_SELECTION
    it.freezeBehavior = BarcodeSelectionFreezeBehavior.MANUAL       // or .MANUAL_AND_AUTOMATIC
    it.shouldFreezeOnDoubleTap = true
}
```

- `BarcodeSelectionTapBehavior.TOGGLE_SELECTION` (default): tapping an unselected barcode selects it; tapping an already-selected barcode unselects it.
- `BarcodeSelectionTapBehavior.REPEAT_SELECTION`: tapping an unselected barcode selects it; tapping an already-selected barcode increments its count (read via `session.getCount(barcode)`) instead of unselecting it.
- `BarcodeSelectionFreezeBehavior.MANUAL` (default): the preview only freezes when the user double-taps. `.MANUAL_AND_AUTOMATIC` additionally auto-freezes once every barcode in view has been recognized (still beta).

### Aim-to-Select

```kotlin
settings.selectionType = BarcodeSelectionAimerSelection.aimerSelection().also {
    it.aimerBehavior = BarcodeSelectionAimerBehavior.REPEAT_SELECTION   // or .TOGGLE_SELECTION
    it.selectionStrategy = BarcodeSelectionManualSelectionStrategy()    // or BarcodeSelectionAutoSelectionStrategy()
}
```

There is also a convenience constructor for setting the aimer behavior directly: `BarcodeSelectionAimerSelection(BarcodeSelectionAimerBehavior.TOGGLE_SELECTION)`.

- `BarcodeSelectionManualSelectionStrategy()` (default): the user must aim at a barcode **and** tap (or your code calls `barcodeSelection.selectAimedBarcode()`) to select it.
- `BarcodeSelectionAutoSelectionStrategy()`: barcodes are selected automatically as soon as the SDK's internal algorithm understands the aiming intent — no tap required. `BarcodeSelectionAimerBehavior` is ignored in this mode; `REPEAT_SELECTION` behavior is always used.
- `BarcodeSelectionAimerBehavior.REPEAT_SELECTION` (default, manual strategy only): aiming an already-selected barcode increments its count. `.TOGGLE_SELECTION`: aiming and tapping an already-selected barcode unselects it.

### Switching selection type at runtime

No need to recreate `BarcodeSelection` — mutate `settings.selectionType` and reapply:

```kotlin
settings.selectionType = BarcodeSelectionAimerSelection.aimerSelection()
barcodeSelection.applySettings(settings)
```

### Other settings

```kotlin
settings.singleBarcodeAutoDetection = true   // auto-select when exactly one barcode is tracked; default false
settings.tapGestureForSelectionEnabled = false  // disable tap selection; only affects manual aimer selection; default true
settings.swipeGesturesEnabled = true          // swipe right selects all in view, swipe left deselects all; default true
settings.codeDuplicateFilter = 500L           // milliseconds before an auto-reselected code counts again; plain Long, not TimeInterval
```

`CapturePreset`-based settings for a specific vertical:

```kotlin
import com.kmp.datacapture.barcode.data.CapturePreset

val settings = BarcodeSelectionSettings.barcodeSelectionSettings(setOf(CapturePreset.RETAIL))
```

## Handling selections: listener + session counts

`session.newlySelectedBarcodes` and `session.newlyUnselectedBarcodes` are `List<Barcode>` (a frame can select/unselect more than one code, e.g. after `selectUnselectedBarcodes()` or a swipe-select-all gesture). `session.selectedBarcodes` is the full current selection. `session.getCount(barcode)` returns how many times a barcode has been selected — relevant when using `REPEAT_SELECTION` tap/aimer behavior, where a re-select bumps the count instead of toggling the barcode off:

```kotlin
override fun onSelectionUpdated(
    barcodeSelection: BarcodeSelection,
    session: BarcodeSelectionSession,
    frameData: FrameData?,
) {
    session.newlySelectedBarcodes.forEach { barcode ->
        val timesSelected = session.getCount(barcode)
        // update UI with barcode.data, barcode.symbology, timesSelected
    }
    session.newlyUnselectedBarcodes.forEach { barcode ->
        // remove barcode.data from the selected-items UI list
    }
}
```

Programmatic selection control, callable from anywhere (dispatched asynchronously, may take effect on the next frame):

```kotlin
barcodeSelection.selectUnselectedBarcodes()          // select everything currently tracked
barcodeSelection.selectAimedBarcode()                // manual aimer selection only
barcodeSelection.unselectBarcodes(listOf(barcode))    // remove specific barcodes from the selection
barcodeSelection.increaseCountForBarcodes(listOf(barcode))
barcodeSelection.setSelectBarcodeEnabled(barcode, false)  // disable/enable selection of a specific barcode
barcodeSelection.reset()                              // clears selection history/counts; does not touch isEnabled or camera
```

`session.selectUnselectedBarcodes()` (on the session, from inside a listener callback) and `session.reset()` are also available as session-scoped equivalents of the mode-level calls.

## Unfreeze / freeze the camera

Freezing the preview is useful with Tap-to-Select's `MANUAL` freeze behavior (typically triggered by a double-tap gesture the SDK handles internally) but can also be driven programmatically, e.g. from a UI button:

```kotlin
barcodeSelection.freezeCamera()
// ... user taps multiple barcodes on the frozen frame ...
barcodeSelection.unfreezeCamera()
```

`BarcodeSelectionBasicOverlay.frozenBackgroundColor: Color` controls the overlay's tint while frozen (semi-transparent black by default).

## Overlay & brush customization

`BarcodeSelectionBasicOverlay` has two factories:

- `BarcodeSelectionBasicOverlay.withBarcodeSelectionForView(barcodeSelection, view)` — constructs the overlay and adds it to the given `DataCaptureView` in one step.
- `BarcodeSelectionBasicOverlay.withBarcodeSelection(barcodeSelection)` — no view binding, used with the Compose composable's declarative `overlays` list (see below); call `view.addOverlay(overlay)` yourself if using the imperative view.

Four brush states, each independently assignable, plus per-style defaults:

```kotlin
import com.kmp.datacapture.barcode.selection.BarcodeSelectionBasicOverlayStyle

val style = overlay.style   // read-only; defaults to FRAME

overlay.trackedBrush = BarcodeSelectionBasicOverlay.defaultTrackedBrushForStyle(style)   // recognized, not yet selected/aimed
overlay.aimedBrush = BarcodeSelectionBasicOverlay.defaultAimedBrushForStyle(style)       // currently aimed at (aimer mode only)
overlay.selectingBrush = BarcodeSelectionBasicOverlay.defaultSelectingBrushForStyle(style) // transient, during selection
overlay.selectedBrush = BarcodeSelectionBasicOverlay.defaultSelectedBrushForStyle(style)   // currently selected
```

Hide a state entirely by assigning `Brush.transparent()`. Choose the style (`FRAME` or `DOT`) by constructing the overlay and then reading defaults for that style — `style` itself is read-only; there is no `BarcodeSelectionBasicOverlay(barcodeSelection, style)` factory documented for KMP, so pick per-brush defaults via the `defaultXBrushForStyle(BarcodeSelectionBasicOverlayStyle.DOT)` overloads if you want the dot look.

Per-barcode custom brushes, evaluated on an internal recognition thread (must return quickly):

```kotlin
overlay.setTrackedBarcodeBrushProvider(object : BarcodeSelectionBrushProvider {
    override fun brushForBarcode(barcode: Barcode): Brush? =
        if (barcode.data?.startsWith("DMG") == true) Brush.transparent() else null // null = overlay default
})
overlay.setAimedBarcodeBrushProvider(myAimedBrushProvider)
```

`overlay.viewfinder` is **read-only** — you cannot swap in a different `Viewfinder` instance (unlike `BarcodeCaptureOverlay.viewfinder`). It is only visible in aimer selection mode.

Other overlay controls: `overlay.shouldShowScanAreaGuides = true` (debug-only scan-area visualization), `overlay.shouldShowHints = false` (suppress the built-in "tap to select" / "double tap to freeze" hint text), `overlay.clearSelectedBarcodeBrushes()` (clears currently displayed highlights without affecting new ones), and `setTextForTapToSelectHint(text)` / `setTextForSelectOrDoubleTapToFreezeHint(text)` / `setTextForDoubleTapToUnfreezeHint(text)` / `setTextForTapAnywhereToSelectHint(text)` / `setTextForAimToSelectAutoHint(text)` to localize/customize hint copy.

## Feedback

```kotlin
// Convenience: toggle sound/vibration without touching the Feedback object directly.
barcodeSelection.setFeedback(soundEnabled = true, vibrationEnabled = false)

// Finer control: assign a custom Feedback to the .selection property.
import com.kmp.datacapture.core.feedback.Feedback
import com.kmp.datacapture.core.feedback.Sound

barcodeSelection.feedback.selection = Feedback(null, Sound.defaultSound())

// Or restore the SDK default (sound on, no vibration):
barcodeSelection.feedback = BarcodeSelectionFeedback.defaultFeedback()

// Or silence entirely with a fresh, unconfigured instance:
barcodeSelection.feedback = BarcodeSelectionFeedback()
```

## Compose Multiplatform

Add `com.scandit.datacapture.kmp:core-compose:8.6.0` to `commonMain` (see Prerequisites). **`BarcodeSelection` has no dedicated `-compose` composable.** Use the base `core-compose` `DataCaptureView` composable directly with the mode's overlay passed declaratively:

```kotlin
@Composable
fun SelectionScreen() {
    val context = rememberDataCaptureContext(licenseKey = LICENSE_KEY)
    val camera = rememberCamera(context)

    val barcodeSelection = remember(context) {
        BarcodeSelection.forContext(context, BarcodeSelectionSettings.barcodeSelectionSettings())
            .also { it.isEnabled = true }
    }
    val overlay = remember(barcodeSelection) {
        BarcodeSelectionBasicOverlay.withBarcodeSelection(barcodeSelection)
    }

    DataCaptureView(
        context = context,
        modifier = Modifier.fillMaxSize(),
        overlays = listOf(overlay),
    )
}
```

- `rememberDataCaptureContext(licenseKey)` creates and remembers the `DataCaptureContext`, re-keyed on `licenseKey`.
- `rememberCamera(context, position = CameraPosition.WORLD_FACING)` creates the `Camera`, wires it as the context's frame source, and turns it on entering composition / off on dispose — you do not need to call `switchToDesiredState` yourself when using this helper.
- **The overlay instance must be `remember`-ed.** The `DataCaptureView` composable diffs the `overlays` list by content equality every recomposition; a `BarcodeSelectionBasicOverlay` built inline (not wrapped in `remember`) is a new instance each time, causing the view to remove and re-add the overlay every recomposition (visible flicker).
- Controls (torch, camera switch, zoom) are placed declaratively via `controls = listOf(ControlPlacement(TorchSwitchControl(), Anchor.TOP_RIGHT))`.

## Lifecycle & Teardown

There is no `onDestroy` in shared code — the platform host's disposal hook (Compose `DisposableEffect`'s `onDispose`, SwiftUI's `deinit`) drives it. Tear down in this order:

```kotlin
fun dispose() {
    barcodeSelection.isEnabled = false
    barcodeSelection.removeListener(this)
    dataCaptureContext.removeMode(barcodeSelection)
    camera?.switchToDesiredState(FrameSourceState.OFF)
}
```

- Disabling the mode before removing it avoids racing a selection callback against teardown.
- `dataCaptureContext.removeMode(barcodeSelection)` is essential when the `DataCaptureContext` is long-lived (e.g. a singleton shared across screen visits) — without it, modes pile up on the context across visits and scanning slows down.
- Turn the camera off last so the preview doesn't briefly show a stale frame from a mode that's already gone.
- On Android, also pause the camera on `ON_PAUSE` (app backgrounded) and resume it on `ON_RESUME`, independent of the composition-leave teardown above — an Activity can go to the background without leaving the composable (so `onDispose` won't fire), and conversely a composable can be left without the Activity pausing (so a lifecycle observer alone isn't enough either). Handle both.

## Common Pitfalls

- Constructing `BarcodeSelectionSettings()` directly — there is no public constructor; use `BarcodeSelectionSettings.barcodeSelectionSettings()` (or the `CapturePreset` overload).
- Calling `BarcodeSelection.forDataCaptureContext(...)` (the Android-native name) — the KMP factory is `BarcodeSelection.forContext(...)`.
- Assuming `session.newlySelectedBarcodes` is a single nullable `Barcode` like `BarcodeCapture`'s `newlyRecognizedBarcode` — it's a `List<Barcode>`; a frame can select more than one code.
- Treating `frameData` in `onSelectionUpdated`/`onSessionUpdated` as non-null — it is `FrameData?` and is `null` when the camera is frozen and the selection changes.
- Trying to assign `overlay.viewfinder = ...` — it is read-only on `BarcodeSelectionBasicOverlay`; only the four brush properties (`trackedBrush`, `aimedBrush`, `selectingBrush`, `selectedBrush`) are settable.
- Using `barcodeSelection.selectAimedBarcode()` with `BarcodeSelectionAutoSelectionStrategy` — the call is meaningful only with `BarcodeSelectionManualSelectionStrategy`.
- Forgetting that `BarcodeSelectionAimerBehavior` has no effect under `BarcodeSelectionAutoSelectionStrategy` (it always behaves like `REPEAT_SELECTION`).
- Wrapping `codeDuplicateFilter` in a `TimeInterval`/duration type — it's a plain `Long` on KMP.
- Constructing a `DataCaptureView` in shared `commonMain` code — the constructor signature is platform-divergent (Android needs a `Context`); construct it in each platform host.
- Calling `view.toNative()` / `mode.toNative()` directly from application code — always use the typed `toAndroidView()` / `toUIView()` extensions instead.
- Looking for a `BarcodeSelectionView` Compose composable — it doesn't exist; use the base `core-compose` `DataCaptureView` with a `remember`-ed overlay.
- Building a fresh `BarcodeSelectionBasicOverlay` inline inside a `@Composable` without `remember` — causes overlay churn on every recomposition.
- Forgetting `dataCaptureContext.removeMode(barcodeSelection)` on teardown when the context is a long-lived singleton — modes accumulate across screen visits.
- Assuming `BarcodeSelection` works without extra licensing — it requires the MatrixScan add-on entitlement.
