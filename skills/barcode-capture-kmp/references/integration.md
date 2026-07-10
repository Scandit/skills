# BarcodeCapture — Kotlin Multiplatform Integration

This reference covers integrating `BarcodeCapture`, Scandit's low-level single-scan mode, into a Kotlin Multiplatform (KMP) app targeting Android and iOS from a shared module. It is grounded in the canonical sample `BarcodeCaptureSimpleSample` (`01_Single_Scanning_Samples/02_Barcode_Scanning_with_Low_Level_API/`) and the KMP SDK source (`com.kmp.datacapture.*`).

Package roots used throughout: `com.kmp.datacapture.core.*` (context, camera, view, viewfinders, feedback primitives) and `com.kmp.datacapture.barcode.*` (BarcodeCapture and its settings/overlay/session/feedback/listener).

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

Add the SDK's SPM package from `Scandit/datacapture-kmp-spm` on GitHub to your iOS app target (Xcode: File > Add Package Dependencies). It ships as a single umbrella XCFramework — your app links exactly **one** Kotlin framework, so pick the variant that includes the barcode capture module (do not also add a separate "core-only" variant alongside it, or the app will contain two copies of the Kotlin runtime).

### Camera permission

- **Android**: declare `<uses-permission android:name="android.permission.CAMERA" />` in `AndroidManifest.xml`, and additionally request it at runtime before starting the camera — the manifest entry alone does not grant it. Use `ActivityResultContracts.RequestPermission()` (see the canonical sample's `HomeScreen.kt`), and only proceed to the scanner screen once `PackageManager.PERMISSION_GRANTED` is confirmed.
- **iOS**: add `NSCameraUsageDescription` to `Info.plist` with a user-facing justification string. iOS presents the system permission prompt automatically the first time the camera is started; no separate request call is needed.

## Minimal Integration

The sample's structure — and the pattern to teach first — is a **shared `ScreenModel`** that owns every Scandit object (context, camera, settings, mode, overlay) behind a `StateFlow`, plus a thin platform host on each side that builds the `DataCaptureView` and embeds it.

### 1. Shared ScreenModel (`commonMain`)

```kotlin
package com.example.scanner

import com.kmp.datacapture.barcode.capture.BarcodeCapture
import com.kmp.datacapture.barcode.capture.BarcodeCaptureListener
import com.kmp.datacapture.barcode.capture.BarcodeCaptureOverlay
import com.kmp.datacapture.barcode.capture.BarcodeCaptureSession
import com.kmp.datacapture.barcode.capture.BarcodeCaptureSettings
import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.core.data.FrameData
import com.kmp.datacapture.core.source.Camera
import com.kmp.datacapture.core.source.FrameSourceState
import com.kmp.datacapture.core.ui.DataCaptureView
import com.kmp.datacapture.core.ui.LogoStyle
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

// -- ENTER YOUR SCANDIT LICENSE KEY HERE --
internal const val LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --"

class ScannerScreenModel : BarcodeCaptureListener {

    private val _state = MutableStateFlow<ScannerUiState>(ScannerUiState.Scanning)
    val state: StateFlow<ScannerUiState> = _state.asStateFlow()

    val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize(LICENSE_KEY)

    private val camera: Camera? =
        Camera.getDefaultCamera(BarcodeCapture.createRecommendedCameraSettings())?.also {
            dataCaptureContext.setFrameSource(it)
        }

    private val settings: BarcodeCaptureSettings =
        BarcodeCaptureSettings.barcodeCaptureSettings().also {
            it.enableSymbology(Symbology.EAN13_UPCA, true)
            it.enableSymbology(Symbology.CODE128, true)
            it.enableSymbology(Symbology.QR, true)
        }

    val barcodeCapture: BarcodeCapture =
        BarcodeCapture.forContext(dataCaptureContext, settings).also {
            it.addListener(this)
        }

    // Platform hosts pass in the DataCaptureView they constructed (see below);
    // this shared function decorates it with the overlay so the setup logic
    // isn't duplicated per platform.
    fun setupDataCaptureView(view: DataCaptureView): DataCaptureView {
        view.logoStyle = LogoStyle.MINIMAL
        val overlay = BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view)
        view.addOverlay(overlay)
        return view
    }

    fun onEvent(event: ScannerEvent) {
        when (event) {
            ScannerEvent.STARTED -> {
                camera?.switchToDesiredState(FrameSourceState.ON)
                barcodeCapture.isEnabled = true
            }
            ScannerEvent.STOPPED -> {
                barcodeCapture.isEnabled = false
                camera?.switchToDesiredState(FrameSourceState.OFF)
            }
        }
    }

    override fun onBarcodeScanned(
        barcodeCapture: BarcodeCapture,
        session: BarcodeCaptureSession,
        data: FrameData,
    ) {
        val barcode = session.newlyRecognizedBarcode ?: return
        barcodeCapture.isEnabled = false
        _state.value = ScannerUiState.Scanned(
            data = barcode.data ?: "",
            symbologyName = barcode.symbology.name,
        )
    }

    override fun onSessionUpdated(
        barcodeCapture: BarcodeCapture,
        session: BarcodeCaptureSession,
        data: FrameData,
    ) = Unit

    fun dispose() {
        barcodeCapture.isEnabled = false
        barcodeCapture.removeListener(this)
        dataCaptureContext.removeMode(barcodeCapture)
        camera?.switchToDesiredState(FrameSourceState.OFF)
    }
}

sealed interface ScannerUiState {
    data object Scanning : ScannerUiState
    data class Scanned(val data: String, val symbologyName: String) : ScannerUiState
}

enum class ScannerEvent { STARTED, STOPPED }
```

`onObservationStarted` / `onObservationStopped` on `BarcodeCaptureListener` have empty default bodies — only override them if you need to react to the mode's observation lifecycle; `onBarcodeScanned` and `onSessionUpdated` must be implemented.

### 2. Android host

Android's `DataCaptureView` constructor requires a `Context`. Build the view in the host, hand it to the shared `setupDataCaptureView`, and embed the native `View` via `toAndroidView()`:

```kotlin
@Composable
fun ScannerScreen() {
    val context = LocalContext.current
    val screenModel = remember { ScannerScreenModel() }

    val dataCaptureView = remember {
        screenModel.setupDataCaptureView(
            DataCaptureView(context, screenModel.dataCaptureContext),
        )
    }

    DisposableEffect(Unit) {
        screenModel.onEvent(ScannerEvent.STARTED)
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
struct ScannerHost: View {
    @StateObject private var screenModel = ScannerScreenModel()

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

`DataCaptureContext.initialize(licenseKey)` also accepts optional `deviceName`, `externalId`, and `settings` parameters if you need them; the single-argument form is the common case.

## Symbology & settings config

Symbologies are all disabled by default — enable exactly what you need:

```kotlin
val settings = BarcodeCaptureSettings.barcodeCaptureSettings().also {
    it.enableSymbology(Symbology.EAN13_UPCA, true)
    it.enableSymbology(Symbology.CODE128, true)
    it.enableSymbology(Symbology.DATA_MATRIX, true)
}
```

- `enableSymbologies(symbologies: Set<Symbology>)` enables several at once.
- `getSymbologySettings(symbology: Symbology): SymbologySettings` returns the per-symbology settings object for extensions, checksums, and active-symbol-count tuning.
- `enabledSymbologies: Set<Symbology>` reads back the currently enabled set.
- Apply settings changes after mode creation with `barcodeCapture.applySettings(settings)`.

Duplicate filtering — `codeDuplicateFilter` is a plain `Long`, **not** a `TimeInterval`/`TimeSpan` wrapper:

```kotlin
settings.codeDuplicateFilter = 500L // milliseconds between reports of the same code
```

Special values: `0` reports every detection; `-1` reports a code only once until scanning stops; `-2` (the default) uses the Smart/Manual duplicate-filter behavior driven by `scanIntention`.

Other commonly used settings: `locationSelection`, `batterySaving`, `scanIntention`, `selectionMode`, `enabledCompositeTypes` / `enableSymbologiesForCompositeTypes(...)`, `setArucoDictionary(...)`.

## Overlay/viewfinder customization

`BarcodeCaptureOverlay` has two factories:

- `BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view)` — binds the overlay to a specific `DataCaptureView`; you still call `view.addOverlay(overlay)` yourself.
- `BarcodeCaptureOverlay.withBarcodeCapture(barcodeCapture)` — no view binding, used with the Compose composable's declarative `overlays` list (see below).

**Only two viewfinders ship on KMP: `RectangularViewfinder` and `AimerViewfinder`. `LaserlineViewfinder` is NOT available on KMP** — do not suggest it.

```kotlin
val overlay = BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view)

// Square or rounded rectangle:
overlay.viewfinder = RectangularViewfinder.withStyleAndLineStyle(
    RectangularViewfinderStyle.SQUARE,
    RectangularViewfinderLineStyle.LIGHT,
)

// Or a plain rectangle with a bare constructor / withStyle:
overlay.viewfinder = RectangularViewfinder.withStyle(RectangularViewfinderStyle.ROUNDED)

// Aimer (crosshair) viewfinder:
overlay.viewfinder = AimerViewfinder()

view.addOverlay(overlay)
```

`RectangularViewfinder` also exposes `color`, `dimming`, `disabledColor`, `disabledDimming`, `animation`, and sizing methods (`setSize`, `setWidthAndAspectRatio`, `setHeightAndAspectRatio`, `setShorterDimensionAndAspectRatio`). `AimerViewfinder` exposes `frameColor` and `dotColor`.

The overlay's highlight brush is customized via `overlay.brush = Brush(...)` (defaults from `BarcodeCaptureOverlay.defaultBrush()`), and `overlay.shouldShowScanAreaGuides` toggles the scan-area guide lines.

## Compose Multiplatform

Add `com.scandit.datacapture.kmp:core-compose:8.6.0` to `commonMain` (see Prerequisites). **`BarcodeCapture` has no dedicated `-compose` composable** — unlike SparkScan, BarcodeCount, BarcodeFind, BarcodeAr, and BarcodePick, there is no `BarcodeCaptureView` composable. Use the base `core-compose` `DataCaptureView` composable directly with the mode's overlay passed declaratively:

```kotlin
@Composable
fun ScannerScreen() {
    val context = rememberDataCaptureContext(licenseKey = LICENSE_KEY)
    val camera = rememberCamera(context)

    val barcodeCapture = remember(context) {
        BarcodeCapture.forContext(context, BarcodeCaptureSettings.barcodeCaptureSettings())
            .also { it.isEnabled = true }
    }
    val overlay = remember(barcodeCapture) {
        BarcodeCaptureOverlay.withBarcodeCapture(barcodeCapture)
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
- **The overlay instance must be `remember`-ed.** The `DataCaptureView` composable diffs the `overlays` list by content equality every recomposition; a `BarcodeCaptureOverlay` built inline (not wrapped in `remember`) is a new instance each time, causing the view to remove and re-add the overlay every recomposition (visible flicker).
- Controls (torch, camera switch, zoom) are placed declaratively via `controls = listOf(ControlPlacement(TorchSwitchControl(), Anchor.TOP_RIGHT))`.
- Focus/zoom gestures, logo style/anchor, scan-area margins, and point of interest are all parameters of the `DataCaptureView` composable with the same defaults as the imperative view.

## Lifecycle & Teardown

There is no `onDestroy` in shared code — the platform host's disposal hook (Compose `DisposableEffect`'s `onDispose`, SwiftUI's `deinit`) drives it. Tear down in this order:

```kotlin
fun dispose() {
    barcodeCapture.isEnabled = false
    barcodeCapture.removeListener(this)
    dataCaptureContext.removeMode(barcodeCapture)
    camera?.switchToDesiredState(FrameSourceState.OFF)
}
```

- Disabling the mode before removing it avoids racing a scan callback against teardown.
- `dataCaptureContext.removeMode(barcodeCapture)` is essential when the `DataCaptureContext` is long-lived (e.g. a singleton shared across screen visits) — without it, modes pile up on the context across visits and scanning slows down.
- Turn the camera off last so the preview doesn't briefly show a stale frame from a mode that's already gone.
- On Android, also pause the camera on `ON_PAUSE` (app backgrounded) and resume it on `ON_RESUME`, independent of the composition-leave teardown above — an Activity can go to the background without leaving the composable (so `onDispose` won't fire), and conversely a composable can be left without the Activity pausing (so a lifecycle observer alone isn't enough either). Handle both.

## Common Pitfalls

- Constructing `BarcodeCaptureSettings()` directly — there is no public constructor; use `BarcodeCaptureSettings.barcodeCaptureSettings()`.
- Wrapping `codeDuplicateFilter` in a `TimeInterval`/duration type — it's a plain `Long` on KMP.
- Calling `BarcodeCapture.forDataCaptureContext(...)` (the Android-native name) — the KMP factory is `BarcodeCapture.forContext(...)`.
- Constructing a `DataCaptureView` in shared `commonMain` code — the constructor signature is platform-divergent (Android needs a `Context`); construct it in each platform host.
- Calling `view.toNative()` / `mode.toNative()` directly from application code — always use the typed `toAndroidView()` / `toUIView()` extensions instead.
- Suggesting `LaserlineViewfinder` — it does not exist in the KMP viewfinder package.
- Looking for a `BarcodeCaptureView` Compose composable — it doesn't exist; use the base `core-compose` `DataCaptureView` with a `remember`-ed overlay.
- Building a fresh `BarcodeCaptureOverlay` inline inside a `@Composable` without `remember` — causes overlay churn on every recomposition.
- Forgetting `dataCaptureContext.removeMode(barcodeCapture)` on teardown when the context is a long-lived singleton — modes accumulate across screen visits.
- Requesting only the Android manifest `CAMERA` permission without also requesting it at runtime — the camera will fail to start silently until the runtime grant is present.
