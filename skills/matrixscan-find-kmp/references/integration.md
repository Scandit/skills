# MatrixScan Find (BarcodeFind) KMP Integration Guide

MatrixScan Find (API class `BarcodeFind`) is a pre-built AR search UI: give it a list of barcodes to look for, point the camera at a scene, and `BarcodeFindView` highlights each item as it is located. It is commonly paired with SparkScan — scan a list of items with SparkScan first, then hand that list to BarcodeFind to physically locate them (see "SparkScan hand-off" below). If the user's question is only about the SparkScan/scanning half, route them to the `sparkscan-kmp` skill instead.

This guide covers the Scandit Kotlin Multiplatform (KMP) SDK, version 8.6. Package root: `com.kmp.datacapture.*`.

## Prerequisites

- **Gradle (shared/androidMain)** — add the KMP artifacts, group `com.scandit.datacapture.kmp`, version `8.6.0`:
  ```kotlin
  dependencies {
      implementation("com.scandit.datacapture.kmp:core:8.6.0")
      implementation("com.scandit.datacapture.kmp:barcode:8.6.0")
      // Only if using the Compose Multiplatform wrapper (see below):
      implementation("com.scandit.datacapture.kmp:barcode-compose:8.6.0")
  }
  ```
- **iOS (SPM)** — add the `Scandit/datacapture-kmp-spm` Swift package to the iOS app target. It vends a single umbrella XCFramework (one Kotlin `shared` framework per app) that bundles the Kotlin `shared` module together with the native Scandit XCFrameworks it depends on. Do not add the native `ScanditBarcodeCapture`/`ScanditCaptureCore` CocoaPods/SPM packages separately — everything comes through the umbrella framework.
- **A valid Scandit license key**:
  - Sign in at https://ssl.scandit.com to generate one
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test
- **Camera permission**, both platforms:
  - Android `AndroidManifest.xml`:
    ```xml
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-feature
        android:name="android.hardware.camera"
        android:required="true" />
    ```
    Request the `CAMERA` permission at runtime before scanning starts, using the standard Android permission API.
  - iOS `Info.plist`:
    ```xml
    <key>NSCameraUsageDescription</key>
    <string>This app uses the camera to find items.</string>
    ```

## Minimal Integration

The KMP pattern: shared (`commonMain`) code owns the `DataCaptureContext` and the `BarcodeFind` mode; each platform host constructs the platform's `BarcodeFindView` (its constructor is platform-divergent) and registers it back with the shared code so shared code can drive its lifecycle.

**Shared code** (`commonMain`):

```kotlin
import com.kmp.datacapture.barcode.find.BarcodeFind
import com.kmp.datacapture.barcode.find.BarcodeFindItem
import com.kmp.datacapture.barcode.find.BarcodeFindItemContent
import com.kmp.datacapture.barcode.find.BarcodeFindItemSearchOptions
import com.kmp.datacapture.barcode.find.BarcodeFindListener
import com.kmp.datacapture.barcode.find.BarcodeFindSettings
import com.kmp.datacapture.barcode.find.BarcodeFindViewSettings
import com.kmp.datacapture.core.capture.DataCaptureContext

class FindScreenModel : BarcodeFindListener {

    // Replace "-- ENTER YOUR SCANDIT LICENSE KEY HERE --" with your license key.
    val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    private val settings: BarcodeFindSettings = BarcodeFindSettings.barcodeFindSettings()

    val barcodeFind: BarcodeFind =
        BarcodeFind.forContext(dataCaptureContext, settings).also { mode ->
            mode.addListener(this)
            mode.setItemList(buildItemList(listOf("9783161484100", "4006381333931")))
        }

    val viewSettings: BarcodeFindViewSettings = BarcodeFindViewSettings.barcodeFindViewSettings()

    private fun buildItemList(barcodeDataList: List<String>): Set<BarcodeFindItem> =
        barcodeDataList.map { data ->
            BarcodeFindItem(BarcodeFindItemSearchOptions(data), BarcodeFindItemContent(null, null, null))
        }.toSet()

    override fun onSearchStarted() { /* no-op */ }
    override fun onSearchPaused(foundItems: Set<BarcodeFindItem>) { /* no-op */ }
    override fun onSearchStopped(foundItems: Set<BarcodeFindItem>) { /* no-op */ }

    fun dispose() {
        barcodeFind.removeListener(this)
        dataCaptureContext.removeMode(barcodeFind)
    }
}
```

**Android host** (e.g. inside a `@Composable` screen, mirroring the `SearchAndFindSample`):

```kotlin
import android.view.View
import android.view.ViewGroup
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import com.kmp.datacapture.barcode.find.BarcodeFindView
import com.kmp.datacapture.barcode.ui.toAndroidView

@Composable
fun FindScreen(screenModel: FindScreenModel) {
    val context = LocalContext.current

    val barcodeFindView = remember {
        BarcodeFindView(context, screenModel.barcodeFind, screenModel.viewSettings)
    }

    AndroidView(
        modifier = Modifier.fillMaxSize(),
        factory = {
            val native: View = barcodeFindView.toAndroidView()
            (native.parent as? ViewGroup)?.removeView(native)
            native
        },
    )
}
```

**iOS host** (SwiftUI, mirroring `FindView.swift`):

```swift
import SwiftUI
import shared

struct FindView: View {
    let screenModel: FindScreenModel
    @State private var barcodeFindView: BarcodeFindView?

    var body: some View {
        ZStack {
            if let view = barcodeFindView {
                FindViewRepresentable { view.toUIView() }
                    .ignoresSafeArea()
            }
        }
        .onAppear {
            if barcodeFindView == nil {
                barcodeFindView = BarcodeFindView(
                    barcodeFind: screenModel.barcodeFind,
                    settings: screenModel.viewSettings
                )
            }
        }
    }
}

struct FindViewRepresentable: UIViewRepresentable {
    let makeView: () -> UIView
    func makeUIView(context: Context) -> UIView { makeView() }
    func updateUIView(_ uiView: UIView, context: Context) {}
}
```

Note the constructor difference: Android's `BarcodeFindView(context, barcodeFind, settings)` takes a `Context` first; iOS's `BarcodeFindView(barcodeFind, settings)` does not.

## Item List & Search Options

The item list drives what `BarcodeFindView` searches for. Build it from `BarcodeFindItem`, each combining `BarcodeFindItemSearchOptions` (what to search for) and an optional `BarcodeFindItemContent` (what to show once found):

```kotlin
import com.kmp.datacapture.barcode.find.BarcodeFindItem
import com.kmp.datacapture.barcode.find.BarcodeFindItemContent
import com.kmp.datacapture.barcode.find.BarcodeFindItemSearchOptions
import com.kmp.datacapture.core.ui.style.Brush

// Plain barcode data, no extra content.
val plainItem = BarcodeFindItem(
    BarcodeFindItemSearchOptions("9783161484100"),
    null,
)

// Barcode data with a custom highlight brush and item content (name, details, image).
val richItem = BarcodeFindItem(
    BarcodeFindItemSearchOptions("4006381333931", Brush(fillColor = /* ... */, strokeColor = /* ... */, strokeWidth = 2f)),
    BarcodeFindItemContent("Product name", "Additional details", null),
)

barcodeFind.setItemList(setOf(plainItem, richItem))
```

- `BarcodeFindItemSearchOptions(barcodeData: String)` and `BarcodeFindItemSearchOptions(barcodeData: String, brush: Brush?)` are the two KMP constructors — there is no raw-byte-array (`ByteArray`) constructor on KMP.
- `setItemList(items: Set<BarcodeFindItem>)` runs asynchronously and replaces the whole list each time it is called. Dedupe by barcode data yourself before calling it (e.g. `.distinctBy { it.barcodeData }` on your source list) if you're seeding it from a list of scanned barcodes.
- Changing the item list while searching updates the UI in place; `BarcodeFindView.textForItemListUpdatedHint` / `textForItemListUpdatedWhenPausedHint` control the confirmation toast shown to the user when that happens.

### SparkScan hand-off

A common flow: use SparkScan to build up a list of scanned barcodes, then seed `BarcodeFind` from that list when the user wants to locate them:

```kotlin
fun startFind(scannedBarcodeData: List<String>) {
    val items = scannedBarcodeData
        .distinctBy { it }
        .map { data -> BarcodeFindItem(BarcodeFindItemSearchOptions(data), BarcodeFindItemContent(null, null, null)) }
        .toSet()

    val find = BarcodeFind.forContext(dataCaptureContext, BarcodeFindSettings.barcodeFindSettings())
    find.setItemList(items)
}
```

For anything about the scanning/SparkScan side of this flow (symbologies, `SparkScanView`, feedback for scanning), use the `sparkscan-kmp` skill.

## Handling Found Items (Listener)

Implement `BarcodeFindListener` and register it with `addListener`:

```kotlin
import com.kmp.datacapture.barcode.find.BarcodeFind
import com.kmp.datacapture.barcode.find.BarcodeFindItem
import com.kmp.datacapture.barcode.find.BarcodeFindListener
import com.kmp.datacapture.barcode.find.BarcodeFindSession

class MyBarcodeFindListener : BarcodeFindListener {
    override fun onSearchStarted() {
        // Search has begun.
    }

    override fun onSearchPaused(foundItems: Set<BarcodeFindItem>) {
        // Search paused; foundItems holds everything found on the last processed frame.
    }

    override fun onSearchStopped(foundItems: Set<BarcodeFindItem>) {
        // Search stopped; foundItems holds everything found since the search began.
    }

    override fun onSessionUpdated(session: BarcodeFindSession) {
        // Called on every processed frame; session.trackedBarcodes has the current scene.
        // Has a default (empty) implementation — only override if you need per-frame detail.
    }
}

barcodeFind.addListener(MyBarcodeFindListener())
```

To react to the user tapping the view's built-in finish button, use `BarcodeFindViewUiListener` on the view (see "View Customization" below) — that is a separate listener from `BarcodeFindListener`.

## Barcode Transformer

`BarcodeFindTransformer` lets you normalize or filter scanned barcode data before it's matched against the item list — e.g. to strip a prefix, or ignore certain codes entirely by returning `null`:

```kotlin
import com.kmp.datacapture.barcode.find.BarcodeFindTransformer

class NormalizingTransformer : BarcodeFindTransformer {
    override fun transformBarcodeData(data: String?): String? {
        if (data == null) return null
        // Ignore barcodes with this prefix entirely.
        if (data.startsWith("IGNORE-")) return null
        // Otherwise normalize (e.g. strip surrounding whitespace).
        return data.trim()
    }
}

barcodeFind.setBarcodeTransformer(NormalizingTransformer())
```

`transformBarcodeData` is invoked for every detected barcode on a background thread — do not touch UI state directly inside it. Pass `null` to `setBarcodeTransformer` to clear a previously set transformer.

## Feedback

`BarcodeFind.feedback` (type `BarcodeFindFeedback`) controls the sound/vibration emitted when an item is found or the item list is updated:

```kotlin
import com.kmp.datacapture.barcode.find.BarcodeFindFeedback
import com.kmp.datacapture.core.feedback.Feedback
import com.kmp.datacapture.core.feedback.Sound
import com.kmp.datacapture.core.feedback.Vibration

val feedback = BarcodeFindFeedback.defaultFeedback().apply {
    found = Feedback().apply {
        sound = Sound.defaultSound()
        vibration = Vibration.successHapticFeedback()
    }
    itemListUpdated = Feedback().apply {
        sound = null
        vibration = Vibration.selectionHapticFeedback()
    }
}

barcodeFind.feedback = feedback
```

`BarcodeFindFeedback.defaultFeedback()` returns sound + vibration enabled for the found event; the empty constructor `BarcodeFindFeedback()` emits nothing until configured.

## View Customization & UiListener

`BarcodeFindView` exposes toggles for its built-in chrome and a `uiListener` for the finish button:

```kotlin
import com.kmp.datacapture.barcode.find.BarcodeFindViewUiListener
import com.kmp.datacapture.barcode.find.BarcodeFindItem

barcodeFindView.shouldShowCarousel = true
barcodeFindView.shouldShowPauseButton = true
barcodeFindView.shouldShowFinishButton = true
barcodeFindView.shouldShowProgressBar = false
barcodeFindView.shouldShowTorchControl = false
barcodeFindView.shouldShowZoomControl = false
barcodeFindView.textForPointAtBarcodesToSearchHint = "Point your camera at the items"
barcodeFindView.textForAllItemsFoundSuccessfullyHint = "All items found!"

barcodeFindView.uiListener = object : BarcodeFindViewUiListener {
    override fun onFinishButtonTapped(foundItems: Set<BarcodeFindItem>) {
        // Navigate away, show a summary, etc.
    }
}
```

`BarcodeFindView.hardwareTriggerSupported` (a companion/static property) reports whether the current Android device supports a hardware scan trigger button; it is always `false` on iOS.

## Compose Multiplatform

The `barcode-compose` artifact (`com.scandit.datacapture.kmp:barcode-compose:8.6.0`) ships a `@Composable BarcodeFindView` wrapper that owns mode creation and start/stop lifecycle for you:

```kotlin
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.kmp.datacapture.barcode.compose.BarcodeFindView
import com.kmp.datacapture.barcode.find.BarcodeFindItem
import com.kmp.datacapture.barcode.find.BarcodeFindItemContent
import com.kmp.datacapture.barcode.find.BarcodeFindItemSearchOptions
import com.kmp.datacapture.barcode.find.BarcodeFindSettings

@Composable
fun FindScreen(barcodeDataList: List<String>, onFinished: (Set<BarcodeFindItem>) -> Unit) {
    val items = remember(barcodeDataList) {
        barcodeDataList.distinctBy { it }.map { data ->
            BarcodeFindItem(BarcodeFindItemSearchOptions(data), BarcodeFindItemContent(null, null, null))
        }.toSet()
    }

    BarcodeFindView(
        settings = BarcodeFindSettings.barcodeFindSettings(),
        itemsToFind = items,
        modifier = Modifier.fillMaxSize(),
        onFinishTap = { foundItems -> onFinished(foundItems) },
    )
}
```

Notes:
- Passing `itemsToFind` (rather than calling `setItemList` yourself) is the idiomatic Compose way to update the search list reactively — the composable applies changes via `LaunchedEffect` without rebuilding the underlying mode/view.
- The composable calls `view.onResume()` + `view.startSearching()` when it enters composition, and `view.stopSearching()` + `view.onPause()` on dispose — you do not need to wire lifecycle callbacks yourself in this variant (contrast with the raw `BarcodeFindView` embedding above, where you do).
- Pass your own `barcodeFind` (advanced override) if you need to share one `BarcodeFind` instance across the SparkScan hand-off flow described above; otherwise the composable builds and tears down its own mode.
- This composable currently has an Android actual implementation (`rememberBarcodeFindScanView`); if the user needs the Compose Multiplatform variant specifically on iOS, verify against the current SDK release before promising it — check the `barcode-compose` iOS actual before answering.

## Lifecycle & Teardown

Whichever platform you're on, the raw (non-Compose) `BarcodeFindView` lifecycle is:

- Call `barcodeFindView.onResume()` / `barcodeFindView.onPause()` from the hosting screen's resume/pause callbacks (e.g. a `LifecycleEventObserver` in Compose, or `onAppear`/`onDisappear` in SwiftUI). These are idempotent — calling one when already in that state is a no-op.
- Call `barcodeFindView.startSearching()` to begin searching once the view is part of the view hierarchy, `pauseSearching()` to pause without losing found-item state, and `stopSearching()` to end the search and clear found-item state.
- On teardown: remove the `BarcodeFindListener`, call `barcodeFind.stop()`, then `dataCaptureContext.removeMode(barcodeFind)` — remove the listener first so `stop()`'s `onSearchStopped` callback doesn't re-enter code that's already tearing the mode down.

```kotlin
fun disposeFind(barcodeFind: BarcodeFind, listener: BarcodeFindListener, context: DataCaptureContext) {
    barcodeFind.removeListener(listener)
    barcodeFind.stop()
    context.removeMode(barcodeFind)
}
```

## Pitfalls

- **Do not call `prepareSearching()` from KMP.** It is iOS-only native API (not part of the KMP `BarcodeFindView` surface at all — SDC-32543). Use `onResume()` instead; on iOS, `onResume()`'s `actual` implementation calls `prepareSearching()` internally for you.
- **`cameraStateOnStop` and `setProperty(name, value)` compile on both platforms but only affect iOS.** The Android `actual` implementation stores/no-ops them without touching the native view. Don't rely on them for Android-specific behavior changes.
- **View construction is platform-divergent.** `BarcodeFindView(context, barcodeFind, settings)` on Android vs. `BarcodeFindView(barcodeFind, settings)` on iOS — shared code cannot construct the view; only reference the constructed instance through a handle interface the platform host provides.
- **Embedding calls differ by platform.** `barcodeFindView.toAndroidView()` (extension function) vs. `barcodeFindView.toUIView()` (member function) — using the wrong one is a compile error, not a runtime bug.
- **`setItemList` replaces the whole list.** There is no incremental add/remove API — always pass the full desired set.
- **`BarcodeFindItemSearchOptions` has no raw-byte-array constructor on KMP** (unlike native Android/iOS, which do). Only `(barcodeData: String)` and `(barcodeData: String, brush: Brush?)` exist.
- **Don't confuse `BarcodeFindListener` (mode-level: search started/paused/stopped/session) with `BarcodeFindViewUiListener` (view-level: finish button tapped).** They are two separate interfaces registered on two separate objects (`barcodeFind.addListener(...)` vs. `barcodeFindView.uiListener = ...`).
