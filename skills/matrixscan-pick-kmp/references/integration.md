# MatrixScan Pick KMP Integration Guide

MatrixScan Pick is a pre-built picking workflow component. It scans multiple barcodes at once,
maps them against a known product list, and renders state-aware augmented-reality highlights
(to-pick / picked / ignore / unknown — see "Pick states") plus a finish button. On Scandit's
Kotlin Multiplatform (KMP) SDK the integration is split across a **shared `commonMain` piece**
(the `BarcodePick` mode, settings, and product provider — all pure Kotlin, usable from a
`ScreenModel`/`ViewModel`) and a **platform-specific view piece** (`BarcodePickView` is
constructed differently on Android vs iOS, because Android's constructor needs a `Context` and
iOS's does not).

There are **two ways to host the view**: the base-module `BarcodePickView` (you build the
platform view yourself and embed it — `AndroidView`/`toAndroidView()` on Android,
`UIViewRepresentable`/`toUIView()` on iOS), or the `barcode-compose` module's `BarcodePickView`
composable (Compose Multiplatform, one call site, no per-platform code). Start with the
base-module pattern below (it matches the `RestockingSample`); the Compose composable is covered
in its own section near the end.

## Prerequisites

- Maven group `com.scandit.datacapture.kmp`, version `8.6.0`:
  - `com.scandit.datacapture.kmp:core`
  - `com.scandit.datacapture.kmp:barcode`
  - `com.scandit.datacapture.kmp:barcode-compose` (only if using the Compose composable)
- iOS side: the umbrella SPM package `Scandit/datacapture-kmp-spm` supplies the single Kotlin
  framework the app links against — do not add per-module iOS frameworks separately.
- A valid Scandit license key (sign in at https://ssl.scandit.com to generate one; sign up at
  https://ssl.scandit.com/dashboard/sign-up?p=test if you don't have an account)
- Camera usage permission declared per platform (`NSCameraUsageDescription` in iOS `Info.plist`,
  the `android.permission.CAMERA` permission on Android)

## Minimal Integration (shared `commonMain` + platform hosts)

Ask the user which barcode symbologies they need to scan, and where their product list comes
from (static list, API, etc.). When asking about symbologies, mention that it's important to
only enable the ones they actually need — fewer enabled symbologies improves scanning
performance and accuracy.

Then ask which screen model / view model they'd like MatrixScan Pick wired into (or which
`commonMain` source set contains the picking screen's state holder), and write the integration
code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add the `com.scandit.datacapture.kmp:core` and `com.scandit.datacapture.kmp:barcode`
   dependencies (version `8.6.0`) to the shared module's `commonMain` source set.
2. On iOS, make sure the app links `Scandit/datacapture-kmp-spm` (the umbrella SPM package) and
   has `NSCameraUsageDescription` in `Info.plist`.
3. On Android, make sure the app declares the `android.permission.CAMERA` permission.
4. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with the real key from https://ssl.scandit.com

The code below is adapted from the official MatrixScan Pick KMP Get Started guide and the
`RestockingSample`.

```kotlin
package com.example.picking

import com.kmp.datacapture.barcode.data.Symbology
import com.kmp.datacapture.barcode.pick.BarcodePick
import com.kmp.datacapture.barcode.pick.BarcodePickActionCallback
import com.kmp.datacapture.barcode.pick.BarcodePickActionListener
import com.kmp.datacapture.barcode.pick.BarcodePickAsyncMapperProductProvider
import com.kmp.datacapture.barcode.pick.BarcodePickAsyncMapperProductProviderCallback
import com.kmp.datacapture.barcode.pick.BarcodePickListener
import com.kmp.datacapture.barcode.pick.BarcodePickProduct
import com.kmp.datacapture.barcode.pick.BarcodePickProductProviderCallback
import com.kmp.datacapture.barcode.pick.BarcodePickProductProviderCallbackItem
import com.kmp.datacapture.barcode.pick.BarcodePickScanningListener
import com.kmp.datacapture.barcode.pick.BarcodePickScanningSession
import com.kmp.datacapture.barcode.pick.BarcodePickSession
import com.kmp.datacapture.barcode.pick.BarcodePickSettings
import com.kmp.datacapture.barcode.pick.BarcodePickView
import com.kmp.datacapture.barcode.pick.BarcodePickViewSettings
import com.kmp.datacapture.barcode.pick.BarcodePickViewUiListener
import com.kmp.datacapture.core.capture.DataCaptureContext

// One entry per product the scanner can RECOGNIZE: its identifier and the barcode payloads that
// map to it. Replace with the user's real model / data source.
data class ProductDatabaseEntry(val identifier: String, val items: Set<String>)

// Platform-agnostic handle the host registers so this screen model can drive view lifecycle
// without depending on a platform view type (BarcodePickView's constructor differs per platform).
interface BarcodePickViewHandle {
    fun start()
    fun pause()
    fun stop()
}

class PickingScreenModel :
    BarcodePickActionListener,
    BarcodePickListener,
    BarcodePickScanningListener,
    BarcodePickViewUiListener {

    // The product database: everything the scanner can recognize (barcode payload → product id).
    // It can list more than the user is asked to pick.
    private val productDatabase: List<ProductDatabaseEntry> = listOf(
        ProductDatabaseEntry("product_1", setOf("9783598215438", "9783598215414")),
        ProductDatabaseEntry("product_2", setOf("9783598215471", "9783598215481")),
        // In the database but not in `productsToPick` → resolves to IGNORE (still tappable, just
        // not highlighted or counted). Drop this line if you don't want users to interact with it.
        ProductDatabaseEntry("product_3", setOf("9783598215498")),
    )

    // The subset the user must actually pick, each with a target quantity → highlighted (TO_PICK)
    // and counted. Every identifier here must exist in productDatabase above.
    private val productsToPick: Set<BarcodePickProduct> = setOf(
        BarcodePickProduct("product_1", 2),
        BarcodePickProduct("product_2", 3),
    )

    private val dataCaptureContext: DataCaptureContext =
        DataCaptureContext.initialize("-- ENTER YOUR SCANDIT LICENSE KEY HERE --")

    // 1. Settings + symbologies. Settings start with all symbologies disabled — enable only the
    //    ones the app needs.
    private val barcodePickSettings: BarcodePickSettings = BarcodePickSettings.barcodePickSettings().also {
        it.enableSymbology(Symbology.EAN13_UPCA, true)
        it.enableSymbology(Symbology.EAN8, true)
        it.enableSymbology(Symbology.UPCE, true)
        it.enableSymbology(Symbology.CODE128, true)
    }

    // 2. The product provider maps scanned barcode payloads to product identifiers, resolved
    //    asynchronously via the callback below, against the full database — a recognized product
    //    that isn't in `productsToPick` shows up as IGNORE.
    private val productProvider = BarcodePickAsyncMapperProductProvider(
        productsToPick,
        object : BarcodePickAsyncMapperProductProviderCallback {
            override fun mapItems(itemsData: Set<String>, callback: BarcodePickProductProviderCallback) {
                val mapped = itemsData.map { item ->
                    val entry = productDatabase.firstOrNull { item in it.items }
                    BarcodePickProductProviderCallbackItem(item, entry?.identifier)
                }.toSet()
                callback.onData(mapped)
            }
        },
    )

    // 3. Create the BarcodePick mode via the companion factory (there is no public constructor).
    val barcodePick: BarcodePick =
        BarcodePick.forContext(dataCaptureContext, barcodePickSettings, productProvider).also {
            // Observe pick state. addListener/addScanningListener register on the MODE (not the
            // view) to read picked / scanned items off the session as the user progresses.
            it.addListener(this)
            it.addScanningListener(this)
        }

    // 4. View settings, built here so both platform hosts read the same configuration.
    val barcodePickViewSettings: BarcodePickViewSettings = BarcodePickViewSettings.barcodePickViewSettings()

    private var viewHandle: BarcodePickViewHandle? = null

    // Called by the platform host once it has constructed its BarcodePickView (see the Android /
    // iOS sections below) so this screen model can drive start()/pause()/stop().
    fun registerBarcodePickView(handle: BarcodePickViewHandle) {
        viewHandle = handle
    }

    fun unregisterBarcodePickView() {
        viewHandle = null
    }

    fun onResumed() = viewHandle?.start()
    fun onPaused() = viewHandle?.pause()

    fun dispose() {
        barcodePick.removeListener(this)
        barcodePick.removeScanningListener(this)
        viewHandle?.stop()
        viewHandle = null
    }

    // BarcodePickActionListener ------------------------------------------------
    // Confirms picks. REQUIRED: without an action listener, a tapped item never transitions to
    // "picked" — the SDK waits for callback.onFinish(true). Registered on the VIEW, not the mode
    // (see BarcodePickView.addActionListener below).
    override fun onPick(itemData: String, callback: BarcodePickActionCallback) {
        callback.onFinish(true)
    }

    override fun onUnpick(itemData: String, callback: BarcodePickActionCallback) {
        callback.onFinish(true)
    }

    // BarcodePickListener / BarcodePickScanningListener -------------------------
    override fun onSessionUpdated(barcodePick: BarcodePick, session: BarcodePickSession) {
        // Called on every mode-level session update.
    }

    override fun onScanningSessionUpdated(barcodePick: BarcodePick, session: BarcodePickScanningSession) {
        // session.pickedItems / session.scannedItems are Set<String> of itemData (barcode
        // payloads), not product identifiers — map them back through the same mapping used above
        // if you need product-level state.
    }

    override fun onScanningSessionCompleted(barcodePick: BarcodePick, session: BarcodePickScanningSession) {
        // Called when the picking session ends.
    }

    // BarcodePickViewUiListener --------------------------------------------------
    // The finish button handler (the ONLY listener that reacts to the finish button on KMP —
    // there is no separate "UI delegate" type).
    override fun onFinishButtonTapped(view: BarcodePickView) {
        // Handle the finish action — e.g. navigate away, show a summary.
    }
}
```

### Android host

```kotlin
@Composable
fun PickScreen(screenModel: PickingScreenModel) {
    val context = LocalContext.current
    val barcodePickView = remember {
        BarcodePickView(context, screenModel.barcodePick, screenModel.barcodePickViewSettings).also { view ->
            view.uiListener = screenModel
            view.addActionListener(screenModel)
            screenModel.registerBarcodePickView(object : BarcodePickViewHandle {
                override fun start() = view.start()
                override fun pause() = view.pause()
                override fun stop() = view.stop()
            })
        }
    }

    DisposableEffect(barcodePickView) {
        barcodePickView.start()
        onDispose {
            barcodePickView.stop()
            screenModel.unregisterBarcodePickView()
        }
    }

    AndroidView(
        modifier = Modifier.fillMaxSize(),
        factory = { barcodePickView.toAndroidView() },
    )
}
```

> `BarcodePickView(context, barcodePick, settings)` on Android takes a `Context` as its first
> parameter — this is the platform divergence from iOS. `toAndroidView()` (an extension in
> `com.kmp.datacapture.barcode.ui`) returns the platform `android.view.View` to embed via
> `AndroidView`.

### iOS host

```swift
struct PickView: View {
    let screenModel: PickingScreenModel
    @State private var barcodePickView: BarcodePickView?

    var body: some View {
        ZStack {
            if let bpv = barcodePickView {
                BarcodePickViewRepresentable { bpv.toUIView() }
                    .ignoresSafeArea()
            }
        }
        .onAppear {
            if barcodePickView == nil {
                let view = BarcodePickView(
                    barcodePick: screenModel.barcodePick,
                    settings: screenModel.barcodePickViewSettings
                )
                view.uiListener = screenModel
                view.addActionListener(listener: screenModel)
                barcodePickView = view
                screenModel.registerBarcodePickView(handle: /* wraps view.start/pause/stop */)
                view.start()
            }
        }
        .onDisappear {
            barcodePickView?.stop()
            screenModel.unregisterBarcodePickView()
        }
    }
}
```

> `BarcodePickView(barcodePick:settings:)` on iOS takes **no** `context` parameter — the view
> binds to `barcodePick.dataCaptureContext` internally. `toUIView()` (a member function) returns
> the platform `UIView` to embed via a `UIViewRepresentable`.

> `BarcodePickView.uiListener` is settable exactly once per instance in this pattern (assign the
> screen model directly if it implements `BarcodePickViewUiListener`); `addActionListener` /
> `addListener` (for `BarcodePickViewListener` lifecycle events) support multiple registrations.

## What the code does (and what it does NOT do)

- Creates the `DataCaptureContext` via `DataCaptureContext.initialize(licenseKey)`.
- Builds `BarcodePickSettings` via the `barcodePickSettings()` companion factory (there is no
  public constructor) with the user's symbologies.
- Builds the product set (`BarcodePickProduct(identifier, quantityToPick)`) and a
  `BarcodePickAsyncMapperProductProvider` whose callback maps scanned payloads → product
  identifiers.
- Creates the `BarcodePick` mode via `BarcodePick.forContext(...)` and registers `BarcodePickListener`
  / `BarcodePickScanningListener` on the mode.
- Leaves platform view construction, the `BarcodePickActionListener` registration (on the
  **view**), and the `BarcodePickViewUiListener` finish-button handler to the platform host, which
  drives `start()` / `pause()` / `stop()`.

What this code does **not** do:
- It does not customize the **highlight appearance per pick state** (brushes, icons, custom
  views). The default highlight is used. See "Highlight configuration" below for the available
  styles; per-state customization is the scope of the highlights sibling guide.

## Symbologies

`BarcodePickSettings` starts with all symbologies disabled. Enable each via
`enableSymbology(symbology, enabled)`. For convenience, `enableSymbologies(symbologies: Set<Symbology>)`
enables a whole set at once, and `enabledSymbologies` (read-only) returns what's currently on.

For variable-length symbologies (Code 39, Code 128, Interleaved 2 of 5, etc.) the user often wants
to restrict the accepted lengths. Access the per-symbology settings via
`settings.getSymbologySettings(symbology)`:

```kotlin
val code128Settings = settings.getSymbologySettings(Symbology.CODE128)
code128Settings.activeSymbolCounts = setOf<Short>(8, 9, 10, 12, 20)
code128Settings.isColorInvertedEnabled = true
```

The properties available on `SymbologySettings` are: `activeSymbolCounts: Set<Short>` (note the
element type is `Short`, not `Int` — passing `Set<Int>` will not compile), `isEnabled: Boolean`,
`isColorInvertedEnabled: Boolean`, `checksums: Set<Checksum>`, and `enabledExtensions: Set<String>`
(read-only; mutate via `setExtensionEnabled(extension, enabled)`). Apply them **before**
constructing `BarcodePick`.

## Pick states

Each detected barcode is in one of four `BarcodePickState` values (an `enum class`:
`TO_PICK`, `PICKED`, `IGNORE`, `UNKNOWN`). A barcode's state is decided by two independent things:

1. **Whether `mapItems` mapped its payload to a `productIdentifier`** (any product, in the list or not).
2. **Whether that product is in the initial pick list** (the `Set<BarcodePickProduct>` passed to
   the provider) and still **needs** units — i.e. its picked count is below its `quantityToPick`.

- `TO_PICK` — mapped to a product that's in the pick list and still needs units. Tapping it picks
  the item and moves it to `PICKED`.
- `PICKED` — the item has been picked (a pick was confirmed through the action listener).
- `IGNORE` — mapped to a real product that is **not part of the current request** (never in the
  pick list, or its quantity is already fulfilled). Still tappable and pickable; the SDK shows an
  informational "item not in list" notice.
- `UNKNOWN` — the payload was **not mapped to any product at all** (`mapItems` omitted it). The
  user cannot interact with it.

## Product list and the provider

MatrixScan Pick works at the **product level**: you declare what the user needs to pick as a set
of `BarcodePickProduct` (each with a `quantityToPick`), and a product provider resolves each
scanned barcode payload to a product identifier. Multiple barcode payloads can map to the same
product.

Keep the **product database** (everything the scanner can recognize) distinct from the
**products to pick** (the subset passed to the provider) — see the minimal example above.
`BarcodePickAsyncMapperProductProviderCallback.mapItems(itemsData: Set<String>, callback: BarcodePickProductProviderCallback)`
is called by the SDK on a background thread with the batch of scanned payloads; call
`callback.onData(mappedItems)` (a `Set<BarcodePickProductProviderCallbackItem>`) when the lookup
is complete — this can happen on a different thread. Omit payloads you don't recognize; they stay
`UNKNOWN`.

`BarcodePickAsyncMapperProductProvider(productsToPick: Set<BarcodePickProduct>, callback: BarcodePickAsyncMapperProductProviderCallback)`
is the concrete provider class. Use `updateProductList(products: Set<BarcodePickProduct>)` to
replace the product set at runtime.

## Confirming picks (required)

`BarcodePick` does not auto-finalize a pick when the user taps a code. The **view** (not the
mode) asks the registered `BarcodePickActionListener` to confirm: it calls
`onPick(itemData, callback)` (or `onUnpick(itemData, callback)`) and waits until
`callback.onFinish(result: Boolean)` is invoked.

- `callback.onFinish(true)` — finalize the action.
- `callback.onFinish(false)` — reject it; the item stays as it was.

Register with `barcodePickView.addActionListener(listener)`. **This is mandatory** — without it,
tapping a code does nothing visible.

## Tracking picks (and unpicks)

`BarcodePickScanningListener` (registered on the **mode** via `barcodePick.addScanningListener(...)`)
is the recommended way to observe pick state: `onScanningSessionUpdated` /
`onScanningSessionCompleted` receive a `BarcodePickScanningSession` whose `pickedItems` /
`scannedItems` are `Set<String>` of barcode payloads. `BarcodePickListener` (registered via
`barcodePick.addListener(...)`) delivers the broader `BarcodePickSession` (`trackedItems`,
`addedItems`, `trackedObjects`, `addedObjects`) to `onSessionUpdated`.

## Explicit selection: `selectItemWithData` / confirm / cancel

Beyond the tap-driven flow above, `BarcodePick` exposes a lower-level, explicit selection API for
driving a pick/unpick from outside the view (e.g. a separate picklist UI row, a hardware trigger):

```kotlin
barcodePick.selectItemWithData(itemData, object : BarcodePickSelectItemActionCallback {
    override fun onFinish(action: BarcodePickAction) {
        // action is one of BarcodePickAction.NONE / PICK / UNPICK — the action that WILL happen.
    }
})

// Later, once you've decided to go through with it (this still routes through the registered
// BarcodePickActionListener.onPick/onUnpick, exactly like a tap):
barcodePick.confirmActionForItemWithData(itemData)

// Or reject it:
barcodePick.cancelActionForItemWithData(itemData)
```

`selectItemWithData` only reports what action *would* happen; it does not itself confirm anything.
`confirmActionForItemWithData` / `cancelActionForItemWithData` are the ones that actually finalize
or cancel a pending selection, and they still go through the same `BarcodePickActionListener`
registered on the view. No action is performed if the item is not currently selected.

## Finish button + handler

The finish button's visibility is `BarcodePickViewSettings.showFinishButton` (`Boolean`). To react
to taps, set `barcodePickView.uiListener` to something implementing
`BarcodePickViewUiListener.onFinishButtonTapped(view: BarcodePickView)`. There is only one
`uiListener` slot per view (not a multi-listener list like `addListener`/`addActionListener`).

## Feedback (sound / haptics) and caching

Sound and haptic feedback are simple on/off toggles on **`BarcodePickSettings`** (the mode
settings, not the view settings) — both default to `true`:

```kotlin
settings.soundEnabled = false
settings.hapticsEnabled = false
```

Note: unlike iOS's `isSoundEnabled`/`isHapticsEnabled`, the KMP Kotlin property names have **no**
`is` prefix. `settings.cachingEnabled` toggles decoded-barcode caching.

## Camera

`BarcodePickView` owns the camera; you do not create a `Camera` or set a frame source on the
context yourself. If the user needs to tune the camera (resolution, zoom, focus), start from
`BarcodePick.recommendedCameraSettings()` (a companion function, called with `()` — it is not a
property in Kotlin) and modify it. Always start from `recommendedCameraSettings()` rather than
constructing camera settings from scratch.

## Control visibility (finish / pause / zoom / torch buttons)

`BarcodePickViewSettings` toggles the built-in buttons (all `Boolean`): `showFinishButton`,
`showPauseButton`, `showZoomButton` (+ `zoomButtonPosition: Anchor`), `showTorchButton` (+
`torchButtonPosition: Anchor`), plus `shouldShowScanAreaGuides`, `showGuidelines`, `showHints`,
`showLoadingDialog`, `hardwareTriggerEnabled` (+ `hardwareTriggerKeyCode: Int?`), the various
guideline/hint/loading-dialog text properties, `uiButtonsOffset`, `logoStyle`, and `logoAnchor`.
Use these built-in toggles rather than rolling your own controls — `BarcodePickView` owns the
camera and its UI chrome.

## Lifecycle: start / pause / stop / freeze / reset

`BarcodePickView` exposes:

- **`start()`** — starts or resumes picking. Call when the view becomes visible / on resume.
- **`pause()`** — pauses picking; the view stays alive and can be resumed with `start()`.
- **`stop()`** — tears the view down for good and releases its resources; the view is no longer
  usable afterwards.
- **`freeze()`** — freezes the camera/highlight positions to make selection easier; resume with `start()`.
- **`reset()`** — clears any picked/tracked items without tearing the view down.

The `RestockingSample` pattern: `start()` as the final mount step (after registering listeners),
`stop()` once as a terminal teardown on dispose, `pause()`/resume via the host lifecycle
(`ON_PAUSE`/`ON_RESUME` on Android, `onDisappear`/`onAppear` on iOS).

## Compose (`barcode-compose` module)

The `barcode-compose` module ships a Compose Multiplatform `BarcodePickView` composable that
replaces the per-platform host code above with one call site shared between Android and iOS:

```kotlin
import com.kmp.datacapture.barcode.compose.BarcodePickView
import com.kmp.datacapture.barcode.compose.rememberBarcodePickViewState

@Composable
fun PickScreen(settings: BarcodePickSettings, productProvider: BarcodePickAsyncMapperProductProvider) {
    val state = rememberBarcodePickViewState()

    BarcodePickView(
        settings = settings,
        productProvider = productProvider,
        modifier = Modifier.fillMaxSize(),
        onFinishTap = { /* handle finish */ },
        state = state,
    )
}
```

- `settings` / `productProvider` build the `BarcodePick` mode for you (via `rememberBarcodePick`)
  unless you pass an explicit `barcodePick:` override — in which case `settings`/`productProvider`
  are ignored.
- `viewSettings: BarcodePickViewSettings` (defaults to `BarcodePickViewSettings.barcodePickViewSettings()`).
- `context: DataCaptureContext` defaults to `DataCaptureContext.sharedInstance`.
- `onFinishTap: (() -> Unit)?` replaces wiring a `BarcodePickViewUiListener` by hand.
- `overlay: @Composable BoxScope.() -> Unit` draws Compose content on top of the view, inside the
  hosting `Box`.
- `state: BarcodePickViewState` (from `rememberBarcodePickViewState()`) exposes `start()`,
  `pause()`, `stop()`, `freeze()` for imperative control — calling one of these before the view has
  mounted throws `IllegalStateException`.
- The composable starts the session as its final mount step and stops it on dispose — you do not
  call `start()`/`stop()` yourself in the common case.
- As of this SDK version the composable exposes **no parameter for `BarcodePickActionListener`** —
  it wires up the finish-button listener (`onFinishTap`) but not pick/unpick confirmation. If the
  user needs `BarcodePickActionListener` (required for taps to actually finalize a pick — see
  "Confirming picks (required)" above), use the base-module `BarcodePickView` pattern instead of
  the compose composable, or check the API reference in case this has since been added.

## After wiring up

If a symbol doesn't resolve, fetch the
[MatrixScan Pick Advanced guide](https://docs.scandit.com/sdks/kmp/matrixscan-pick/advanced/)
and confirm the exact signature before guessing. Always include the docs link in your answer.
