# SparkScan KMP Integration Guide

SparkScan is a pre-built scanning UI for high-volume single-scanning workflows. On Kotlin
Multiplatform it ships as an `expect`/`actual` mode + view pair: the scanning logic (settings,
listener, feedback) lives in shared `commonMain` code, while the trigger-button UI is a
platform-native view (`SparkScanView`) that each host (Android, iOS) constructs and embeds.

Two integration patterns are documented here:

1. **Primary UI pattern** (teach this first) — a shared `ScreenModel` owns every SDK object, and
   each platform host constructs `SparkScanView` and embeds it via `toAndroidView()` / `toUIView()`.
   This is what the canonical sample (`ListBuildingSample`) uses, and it gives you full control
   over the view's lifecycle and UI customization.
2. **Compose Multiplatform pattern** — a single `@Composable SparkScanView(...)` from the
   `barcode-compose` module that works unmodified on both Android and iOS, at the cost of less
   granular control (it manages its own lifecycle).

## Prerequisites

- Scandit KMP SDK — add via Gradle to the shared module's `commonMain` source set. Maven group is
  `com.scandit.datacapture.kmp`; the Kotlin import root is the unrelated `com.kmp.datacapture.*`
  package — do not confuse the two.
  ```kotlin
  kotlin {
      sourceSets {
          commonMain.dependencies {
              implementation("com.scandit.datacapture.kmp:core:8.6.0")
              implementation("com.scandit.datacapture.kmp:barcode:8.6.0")
          }
      }
  }
  ```
  Only add `core-compose` / `barcode-compose` (see the **Compose Multiplatform** section below) if
  you're using the Compose composable instead of the manual `SparkScanView` pattern.

- iOS distribution is via Swift Package Manager:
  1. In Xcode: **File > Add Package Dependencies…** and add
     `https://github.com/Scandit/datacapture-kmp-spm`.
  2. The package is an umbrella XCFramework — your app links exactly **one** Kotlin framework
     product from it. Pick the variant that bundles the barcode module (needed for SparkScan); do
     not also add the native `ScanditBarcodeCapture`/`ScanditCaptureCore` XCFrameworks separately —
     they resolve transitively through the chosen product.

- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test

- Camera permission on **both** platforms:
  - Android — `AndroidManifest.xml`:
    ```xml
    <uses-feature
          android:name="android.hardware.camera"
          android:required="true" />
    <uses-permission android:name="android.permission.CAMERA" />
    ```
    Request the `CAMERA` permission at runtime using the standard Android permission API before
    scanning starts — the manifest declaration alone is not enough.
  - iOS — `Info.plist`:
    ```xml
    <key>NSCameraUsageDescription</key>
    <string>This app uses the camera to scan barcodes.</string>
    ```
    iOS shows the system permission prompt automatically on first camera use once this key is
    present; no runtime request call is needed.

## Minimal Integration

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important
to only enable the symbologies they actually need, as enabling fewer improves scanning performance
and accuracy.

Once the user responds, ask them which shared `ScreenModel` (or equivalent shared class) they'd
like SparkScan integrated into, and which Android/iOS screen hosts it. Then write the integration
code directly into those files. Do not just show the code in chat; apply it to the files.

After providing the code, show this setup checklist:

**Setup checklist:**

1. Add `implementation("com.scandit.datacapture.kmp:core:8.6.0")` and
   `implementation("com.scandit.datacapture.kmp:barcode:8.6.0")` to the shared module's
   `commonMain.dependencies` in `build.gradle.kts`
2. Add the SPM package `https://github.com/Scandit/datacapture-kmp-spm` to the iOS app, linking the
   barcode-bundling product
3. Add `<uses-permission android:name="android.permission.CAMERA" />` to `AndroidManifest.xml` and
   request it at runtime before scanning starts
4. Add `NSCameraUsageDescription` to `Info.plist`
5. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com

### Shared code (`commonMain`)

The screen model owns the `DataCaptureContext`, the `SparkScan` mode, its settings, and the
`SparkScanViewSettings` the platform view factory consumes. It implements `SparkScanListener` (scan
results) and, optionally, `SparkScanFeedbackDelegate` (see **Custom Feedback** below).

```kotlin
import com.kmp.datacapture.barcode.data.Barcode
import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.barcode.spark.SparkScan
import com.kmp.datacapture.barcode.spark.SparkScanListener
import com.kmp.datacapture.barcode.spark.SparkScanSession
import com.kmp.datacapture.barcode.spark.SparkScanSettings
import com.kmp.datacapture.barcode.spark.SparkScanViewSettings
import com.kmp.datacapture.core.capture.DataCaptureContext
import com.kmp.datacapture.core.data.FrameData
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class ScanScreenModel : SparkScanListener {

    private val _scannedBarcodes = MutableStateFlow<List<String>>(emptyList())
    val scannedBarcodes: StateFlow<List<String>> = _scannedBarcodes.asStateFlow()

    val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val settings: SparkScanSettings = SparkScanSettings.sparkScanSettings().also {
        it.enableSymbologies(setOf(Symbology.EAN13_UPCA, Symbology.CODE128))
    }

    val sparkScan: SparkScan = SparkScan(settings).also {
        it.addListener(this)
    }

    /** Consumed by the platform view factory (Android/iOS host). */
    val sparkScanViewSettings: SparkScanViewSettings = SparkScanViewSettings.sparkScanViewSettings()

    override fun onBarcodeScanned(
        sparkScan: SparkScan,
        session: SparkScanSession,
        frameData: FrameData,
    ) {
        val barcode: Barcode = session.newlyRecognizedBarcode ?: return
        val data = barcode.data ?: return
        _scannedBarcodes.value = _scannedBarcodes.value + data
    }

    override fun onSessionUpdated(
        sparkScan: SparkScan,
        session: SparkScanSession,
        frameData: FrameData,
    ) = Unit

    fun dispose() {
        sparkScan.removeListener(this)
        dataCaptureContext.removeMode(sparkScan)
    }
}
```

`DataCaptureContext.initialize(licenseKey)` is a `companion object` factory; keep exactly one
shared instance for the app (e.g. behind a `by lazy` singleton, or reuse
`DataCaptureContext.sharedInstance` once it has been initialized once at app startup).

### Android host

The Android host is the only place with an Android `Context`, so it constructs `SparkScanView`
there and embeds the underlying `android.view.View` via `toAndroidView()`.

```kotlin
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.kmp.datacapture.barcode.spark.SparkScanView
import com.kmp.datacapture.barcode.ui.toAndroidView

@Composable
fun ScanScreen() {
    val context = LocalContext.current
    val screenModel = remember { ScanScreenModel() }

    val sparkScanView = remember {
        SparkScanView(
            context,
            screenModel.dataCaptureContext,
            screenModel.sparkScan,
            screenModel.sparkScanViewSettings,
        )
    }

    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_RESUME -> sparkScanView.onResume()
                Lifecycle.Event.ON_PAUSE -> sparkScanView.onPause()
                else -> Unit
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        sparkScanView.onResume()
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            sparkScanView.onPause()
            screenModel.dispose()
        }
    }

    AndroidView(
        modifier = Modifier.fillMaxSize(),
        factory = { sparkScanView.toAndroidView() },
    )
}
```

### iOS host

The iOS `SparkScanView` constructor takes **no host parameter** — it starts at zero frame and
follows Auto Layout once embedded. Wrap it in a `UIViewRepresentable` and embed the `UIView` via
`toUIView()`.

```swift
import SwiftUI
import shared

final class ScanScreenState: ObservableObject {
    let screenModel: ScanScreenModel
    let sparkScanView: SparkScanView

    init() {
        let model = ScanScreenModel()
        self.screenModel = model
        self.sparkScanView = SparkScanView(
            dataCaptureContext: model.dataCaptureContext,
            sparkScan: model.sparkScan,
            settings: model.sparkScanViewSettings
        )
    }

    deinit {
        screenModel.dispose()
    }
}

struct ScanView: View {
    @StateObject private var state = ScanScreenState()

    var body: some View {
        SparkScanViewRepresentable(sparkScanView: state.sparkScanView)
            .onAppear { state.sparkScanView.onResume() }
            .onDisappear { state.sparkScanView.onPause() }
    }
}

struct SparkScanViewRepresentable: UIViewRepresentable {
    let sparkScanView: SparkScanView

    func makeUIView(context: Context) -> UIView {
        sparkScanView.toUIView()
    }

    func updateUIView(_ uiView: UIView, context: Context) {}
}
```

## Custom Feedback

To reject barcodes and show error messages, implement `SparkScanFeedbackDelegate` on the shared
screen model and assign it to the platform view's `feedbackDelegate` property (a property on the
constructed `SparkScanView`, not on `SparkScanSettings`):

```kotlin
import com.kmp.datacapture.barcode.data.Barcode
import com.kmp.datacapture.barcode.spark.SparkScanBarcodeErrorFeedback
import com.kmp.datacapture.barcode.spark.SparkScanBarcodeFeedback
import com.kmp.datacapture.barcode.spark.SparkScanBarcodeSuccessFeedback
import com.kmp.datacapture.barcode.spark.SparkScanFeedbackDelegate

class ScanScreenModel : SparkScanListener, SparkScanFeedbackDelegate {

    // ... existing setup ...

    private fun isValidBarcode(barcode: Barcode): Boolean =
        barcode.data != null && barcode.data != "123456789"

    override fun getFeedbackForBarcode(barcode: Barcode): SparkScanBarcodeFeedback? =
        if (isValidBarcode(barcode)) {
            SparkScanBarcodeSuccessFeedback()
        } else {
            SparkScanBarcodeErrorFeedback(
                errorMessage = "Wrong barcode!",
                resumeCapturingDelay = 30_000L, // milliseconds
            )
        }
}
```

Then, in the Android host, assign it once the view exists:

```kotlin
val sparkScanView = remember {
    SparkScanView(context, screenModel.dataCaptureContext, screenModel.sparkScan, screenModel.sparkScanViewSettings)
        .also { it.feedbackDelegate = screenModel }
}
```

And on iOS:

```swift
self.sparkScanView = SparkScanView(
    dataCaptureContext: model.dataCaptureContext,
    sparkScan: model.sparkScan,
    settings: model.sparkScanViewSettings
)
self.sparkScanView.feedbackDelegate = model
```

> **Note:** `getFeedbackForBarcode` is invoked off the main thread. Do not update UI state
> directly inside it — publish through a `StateFlow` or similar and observe it from the UI layer.

`resumeCapturingDelay` is a plain `Long` in **milliseconds** (not `TimeInterval`). Both feedback
types also accept an optional `visualFeedbackColor: Color?` and `feedback: Feedback?` (sound /
vibration) if you need to override the platform defaults.

## Symbology Configuration

Enable only the symbologies the app actually needs — every extra symbology impacts scanning
performance and accuracy:

```kotlin
val settings: SparkScanSettings = SparkScanSettings.sparkScanSettings().also {
    it.enableSymbologies(
        setOf(
            Symbology.EAN13_UPCA,
            Symbology.CODE128,
            Symbology.QR,
        ),
    )
}
```

Use `enableSymbology(symbology, enabled)` to toggle one symbology at a time, and
`settings.getSymbologySettings(symbology)` to reach per-symbology tuning (e.g.
`activeSymbolCounts` for variable-length symbologies like Code 39/Code 128). Pass a
`Set<CapturePreset>` to `SparkScanSettings.sparkScanSettings(capturePresets)` instead of enabling
symbologies one by one when a built-in preset covers the use case.

## Compose Multiplatform

The `barcode-compose` module ships a declarative `@Composable SparkScanView(...)` that works
unmodified on both Android and iOS — no manual view construction, no manual `onResume()`/
`onPause()`/`startScanning()` calls. Add the dependency alongside `core-compose`:

```kotlin
commonMain.dependencies {
    implementation("com.scandit.datacapture.kmp:core-compose:8.6.0")
    implementation("com.scandit.datacapture.kmp:barcode-compose:8.6.0")
}
```

```kotlin
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.kmp.datacapture.barcode.spark.SparkScanSettings
import com.kmp.datacapture.barcode.compose.SparkScanView
import com.kmp.datacapture.barcode.data.Symbology

@Composable
fun ScanScreen() {
    SparkScanView(
        settings = SparkScanSettings.sparkScanSettings().also {
            it.enableSymbologies(setOf(Symbology.EAN13_UPCA, Symbology.CODE128))
        },
        modifier = Modifier.fillMaxSize(),
        onScan = { barcodes -> /* handle scanned barcodes */ },
    )
}
```

The composable starts scanning as the last step on entering the composition and stops it on
dispose — writing `sparkScanView.onResume()`/`startScanning()` yourself alongside it is redundant
and unsupported (there's no `SparkScanView` instance to call it on; the composable owns it
internally). `DataCaptureContext` defaults to `DataCaptureContext.sharedInstance`; call
`DataCaptureContext.initialize(licenseKey)` once at app startup so that default resolves.

View-level UI toggles (trigger button, torch, zoom, camera-switch, mini-preview controls, and the
Barcode Count/Find/Label Capture/target-mode/selection-mode buttons) are exposed as boolean
parameters directly on the composable, e.g.:

```kotlin
SparkScanView(
    settings = settings,
    triggerButtonVisible = false,
    torchControlVisible = false,
    modifier = Modifier.fillMaxSize(),
    onScan = { barcodes -> /* ... */ },
)
```

For advanced overrides (a custom `SparkScan` instance, or an overlay composable drawn above the
scanning UI), pass `sparkScan = rememberSparkScan(context, settings)` and/or an `overlay = { ... }`
slot.

## Lifecycle & Teardown

- **Manual `SparkScanView` pattern:** call `sparkScanView.onResume()` / `onPause()` from the host's
  lifecycle (`ON_RESUME`/`ON_PAUSE` on Android, `onAppear`/`onDisappear` on iOS). On the shared
  model's `dispose()`, call `sparkScan.removeListener(this)` then
  `dataCaptureContext.removeMode(sparkScan)`, in that order — matching the canonical sample. There
  is no separate `onDestroy()`; a screen re-entering the composition rebuilds the model and view.
- **Compose Multiplatform pattern:** no manual lifecycle calls at all — the composable starts
  scanning on entering composition and stops it in `onDispose`.
- Continuous, back-to-back scanning without re-tapping the trigger button: set
  `sparkScanViewSettings.scanningBehavior = SparkScanScanningBehavior.CONTINUOUS` (default is
  `SINGLE`). Combine with `previewBehavior = SparkScanPreviewBehavior.PERSISTENT` to keep the
  camera preview open between scans instead of collapsing it.

## Common Pitfalls

- Writing `SparkScanSettings()` or `SparkScanViewSettings()` — both are compile errors on KMP; use
  the `sparkScanSettings()` / `sparkScanViewSettings()` factories.
- Constructing `SparkScanView` in shared `commonMain` code — it's an `expect class` with
  platform-divergent constructors (Android needs a `Context`, iOS doesn't); construction must
  happen in each platform host.
- Assigning `feedbackDelegate` on `SparkScanSettings` — it's a property on the constructed
  `SparkScanView` instance.
- Passing a `TimeInterval` (or any duration wrapper) to `resumeCapturingDelay` — it's a plain
  `Long` in milliseconds.
- Looking for `SparkScanScanningMode.Target` or an `onScanningModeChange` callback — neither exists
  on KMP; use `scanningBehavior` + `previewBehavior` on `SparkScanViewSettings` instead.
- Forgetting `dataCaptureContext.removeMode(sparkScan)` on teardown when using the manual
  `SparkScanView` pattern — the mode stays attached to the shared context across screen visits,
  degrading performance.
- Mixing the Compose composable's implicit lifecycle with manual `onResume()`/`onPause()` calls —
  pick one pattern per screen, not both.
