# MatrixScan Pick iOS Integration Guide

MatrixScan Pick is a pre-built picking workflow component built on top of the Scandit SDK. It scans multiple barcodes at once, maps them against a known product list, and renders state-aware augmented-reality highlights (to-pick / picked / ignore / unknown — see "Pick states") plus a finish button for completing the session. The integration has two primary elements: the **`BarcodePick`** data capture mode and the **`BarcodePickView`** pre-built UI.

## Prerequisites

- Scandit Data Capture SDK for iOS — add via Swift Package Manager:
  - URL: `https://github.com/Scandit/datacapture-spm`
  - Add `ScanditBarcodeCapture` and `ScanditCaptureCore` package products to your target
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test
- `NSCameraUsageDescription` in `Info.plist`

## Minimal Integration (Swift)

Ask the user which barcode symbologies they need to scan, and where their product list comes from (static list, API, etc.). When asking about symbologies, mention that it's important to only enable the ones they actually need — fewer enabled symbologies improves scanning performance and accuracy.

Then ask which file or view controller they'd like to integrate MatrixScan Pick into, and write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `ScanditBarcodeCapture` and `ScanditCaptureCore` via Swift Package Manager: `https://github.com/Scandit/datacapture-spm`
2. Make sure you have `NSCameraUsageDescription` added to your `Info.plist`
3. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com

The code below is adapted from the official MatrixScan Pick Get Started guide and the `RestockingSample` (UIKit).

```swift
import ScanditBarcodeCapture

// One entry per product the scanner can RECOGNIZE: its identifier and the barcode payloads that
// map to it. Replace with the user's real model / data source.
struct ProductDatabaseEntry {
    let identifier: String
    let items: [String] // the barcode data strings that belong to this product
}

class PickViewController: UIViewController {
    private let context = DataCaptureContext(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
    private var barcodePickView: BarcodePickView!

    // The product database: everything the scanner can recognize (barcode payload → product id).
    // It can list more than the user is asked to pick.
    private let productDatabase: [ProductDatabaseEntry] = [
        .init(identifier: "product_1", items: ["9783598215438", "9783598215414"]),
        .init(identifier: "product_2", items: ["9783598215471", "9783598215481"]),
        // In the database but not in `productsToPick` → resolves to .ignore (still tappable, just not
        // highlighted or counted). Drop this line if you don't want users to interact with it.
        .init(identifier: "product_3", items: ["9783598215498"]),
    ]

    // The subset the user must actually pick, each with a target quantity → highlighted (.toPick)
    // and counted. Every identifier here must exist in productDatabase above.
    private let productsToPick: [BarcodePickProduct] = [
        BarcodePickProduct(identifier: "product_1", quantityToPick: 2),
        BarcodePickProduct(identifier: "product_2", quantityToPick: 3),
    ]

    override func viewDidLoad() {
        super.viewDidLoad()
        setupPicking()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        barcodePickView.start()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        barcodePickView.pause()
        if isMovingFromParent {
            barcodePickView.stop()
        }
    }

    private func setupPicking() {
        // 1. Settings + symbologies. The settings start with all symbologies disabled —
        //    enable only the ones the app needs.
        let settings = BarcodePickSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .ean8, enabled: true)
        settings.set(symbology: .upce, enabled: true)
        settings.set(symbology: .code128, enabled: true)

        // 2. The pick list is the products-to-pick subset (a Set of BarcodePickProduct).
        let products = Set(productsToPick)

        // 3. The product provider maps scanned barcode payloads to product identifiers,
        //    asynchronously, via the delegate below. It resolves against the full database,
        //    so a recognized product that isn't in `products` shows up as .ignore.
        let productProvider = BarcodePickAsyncMapperProductProvider(products: products,
                                                                    providerDelegate: self)

        // 4. Create the BarcodePick mode.
        let mode = BarcodePick(context: context,
                               settings: settings,
                               productProvider: productProvider)

        // 5. Observe pick state. Register a scanning listener on the MODE (not the view)
        //    to read picked / scanned items off the session as the user progresses.
        mode.addScanningListener(self)

        // 6. Create the view. It renders the camera preview and the picking UI.
        let viewSettings = BarcodePickViewSettings()
        barcodePickView = BarcodePickView(frame: view.bounds,
                                          context: context,
                                          barcodePick: mode,
                                          settings: viewSettings)
        barcodePickView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(barcodePickView)

        // 7. Observe view-lifecycle events and the finish button.
        barcodePickView.addListener(self)
        barcodePickView.uiDelegate = self

        // 8. Confirm picks. This is REQUIRED: without an action listener, a tapped item
        //    never transitions to "picked" — the SDK waits for completionHandler(true).
        barcodePickView.addActionListener(self)
    }
}

// Maps the raw barcode payloads the SDK sees to your product identifiers.
extension PickViewController: BarcodePickAsyncMapperProductProviderDelegate {
    func mapItems(_ items: [String],
                  completionHandler: @escaping ([BarcodePickProductProviderCallbackItem]) -> Void) {
        let result: [BarcodePickProductProviderCallbackItem] = items.compactMap { item in
            guard let entry = productDatabase.first(where: { $0.items.contains(item) }) else {
                return nil // not in the database → .unknown (inert; the user can't interact with it)
            }
            return BarcodePickProductProviderCallbackItem(itemData: item,
                                                          productIdentifier: entry.identifier)
        }
        completionHandler(result)
    }
}

// Scanning lifecycle callbacks (optional — implement only what you need).
extension PickViewController: BarcodePickViewListener {
    func barcodePickViewDidStartScanning(_ view: BarcodePickView) {}
    func barcodePickViewDidFreezeScanning(_ view: BarcodePickView) {}
    func barcodePickViewDidPauseScanning(_ view: BarcodePickView) {}
    func barcodePickViewDidStopScanning(_ view: BarcodePickView) {}
}

// The finish button handler.
extension PickViewController: BarcodePickViewUIDelegate {
    func barcodePickViewDidTapFinishButton(_ view: BarcodePickView) {
        // Handle the finish action — e.g. pop, dismiss, present a summary.
        // The right call depends on how this screen was presented.
    }
}

// Confirms (or rejects) pick / unpick actions. The completionHandler MUST be called —
// pass true to finalize the action, false to reject it. This is what makes a tapped item
// actually become "picked". A real app might validate against a backend before confirming.
extension PickViewController: BarcodePickActionListener {
    func didPickItem(withData data: String, completionHandler: @escaping (Bool) -> Void) {
        completionHandler(true)
    }

    func didUnpickItem(withData data: String, completionHandler: @escaping (Bool) -> Void) {
        completionHandler(true)
    }
}

// Observes pick state. session.pickedItems / scannedItems are Set<String> of itemData.
// Callbacks fire OFF the main queue — dispatch to main before touching UIKit.
extension PickViewController: BarcodePickScanningListener {
    func barcodePick(_ barcodePick: BarcodePick,
                     didUpdate scanningSession: BarcodePickScanningSession) {
        // Called on every pick / unpick — the session state has changed.
        // Update your app's view of progress here.
    }

    func barcodePick(_ barcodePick: BarcodePick,
                     didComplete scanningSession: BarcodePickScanningSession) {
        // Called when the picking session ends — e.g. on view teardown or when the mode is stopped.
        // Use this for end-of-session bookkeeping.
    }
}
```

> `BarcodePickView` does **not** add itself to the view hierarchy — construct it with a `frame` and `addSubview` it yourself. Note the constructor takes both the `context` and the `barcodePick` mode.

> **Pick confirmation is required, not optional.** `BarcodePickActionListener` (added via
> `barcodePickView.addActionListener(self)`) is what finalizes a pick. When the user taps a code,
> the SDK calls `didPickItem(withData:completionHandler:)` and waits — the item only becomes "picked"
> once you call `completionHandler(true)` (pass `false` to reject, e.g. after a failed backend check).
> Omit the action listener and items will appear to do nothing on tap. The official basic Get Started
> page leaves this out, so it is easy to miss.

## What the code does (and what it does NOT do)

- Creates the `DataCaptureContext` with the license key.
- Builds `BarcodePickSettings` with the user's symbologies.
- Builds the product set (`BarcodePickProduct` with `quantityToPick`) and a `BarcodePickAsyncMapperProductProvider` whose delegate maps scanned payloads → product identifiers.
- Creates the `BarcodePick` mode and the `BarcodePickView`, adds the view to the hierarchy, and drives the `start()` / `pause()` / `stop()` lifecycle.
- Wires the view-lifecycle listener, the finish-button UI delegate, the **action listener that confirms picks** (see "Confirming picks" below — required for taps to finalize), and a **scanning listener** that observes pick state on the mode (see "Tracking picks" below — without it, the app has no way to read what was picked).

What this code does **not** do:
- It does not customize the **highlight appearance per pick state** (brushes, icons, custom views). The default highlight is used. See "Highlight configuration" below for the available styles; per-state customization is the scope of the highlights sibling skill.

## Symbologies

`BarcodePickSettings` starts with all symbologies disabled. Enable each via
`settings.set(symbology:enabled:)`. For convenience, `enableSymbologies(_:)` enables a whole set at
once, and `enabledSymbologies` (read-only) returns what's currently on.

For the exact `Symbology` case to pass (e.g. QR is `.qr`, not `.qrCode`), consult the
[Symbology API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/symbology.html) —
don't guess the case name. (The minimal example above enables a handful; the full list of symbologies
and their Swift names lives on that page.)

For variable-length symbologies (Code 39, Code 128, Interleaved 2 of 5, etc.) the user often wants
to restrict the accepted lengths. For other symbologies they may need color-inverted decoding or
specific checksums. Access the per-symbology settings via `BarcodePickSettings.settings(for:)`:

```swift
settings.settings(for: .code128).activeSymbolCounts = Set(8...20)
settings.settings(for: .code128).isColorInvertedEnabled = true
```

The properties available on `SymbologySettings` are: `activeSymbolCounts: Set<Int>` (the public
ObjC type is `NSSet<NSNumber*>` but it's `NS_REFINED_FOR_SWIFT` → `Set<Int>` in Swift),
`isColorInvertedEnabled: Bool`, `checksums: Checksum` (an `OptionSet`, not an array — assign with
array-literal syntax e.g. `[.mod10, .mod11]`), and `enabledExtensions: Set<String>` (read-only;
mutate via `set(extension:enabled:)`). Apply them on the `BarcodePickSettings` **before** constructing
`BarcodePick`; the mode does not expose a live `apply(_:)` for runtime reconfiguration, so symbology
changes after construction require building a new mode.

## Pick states

Each detected barcode is in one of four `BarcodePickState` values. Understanding how a barcode lands
in each state — and how it moves between them — is the key to MatrixScan Pick: the state drives both
the picking logic (can the user pick it? does it count?) and how the highlight is drawn (see
"Highlight configuration").

A barcode's state is decided by **two independent things**:

1. **Whether `mapItems` mapped its payload to a `productIdentifier`** (any product, in the list or not).
2. **Whether that product is in the initial pick list** (the `Set<BarcodePickProduct>` you passed to
   the provider) and still **needs** units — i.e. its picked count is below its `quantityToPick`.

The four states:

- `.toPick` — the payload was mapped to a product **that is in the pick list and still needs units**
  (picked count `< quantityToPick`). This is the only pickable-and-counts state: tapping it picks the
  item, it gives the normal pick confirmation, and it moves to `.picked`.
- `.picked` — the item has been picked (a pick was confirmed through the action listener).
- `.ignore` — the payload **was mapped to a real product, but that product is not part of the current
  request** — either it was never in the pick list, **or** its `quantityToPick` has already been
  fulfilled. The barcode is **still tappable and can be picked**: tapping it records the pick (the
  action listener fires, the barcode is added to the session's `pickedItems`, and it moves to
  `.picked`), and the SDK shows an **informational** "item not in list" notice so the user knows it
  wasn't part of the requested order. The notice does **not** reject the pick. This is the
  "not-in-list" case.
- `.unknown` — the payload was **not mapped to any product at all** (your `mapItems` omitted it). The
  user **cannot interact with it** — it is outside the system's knowledge, not just outside the request.

### How a barcode moves between states

- **Mapped, in the list, under quantity → `.toPick`.** Multiple payloads can map to the same product;
  all of them are `.toPick` until the product's quantity is met.
- **Pick until `quantityToPick` is reached → the remaining matching barcodes flip `.toPick` → `.ignore`.**
  Once the request for a product is fulfilled, its other still-visible barcodes are removed from the
  to-pick set, so they render as `.ignore`. **Unpicking** back below the quantity moves them back to
  `.toPick` (the transition is reversible).
- **Mapped, but the product is not in the list → `.ignore`** from the start.
- **Not mapped (omitted from the `mapItems` result) → `.unknown`.**

> The distinction between `.ignore` and `.unknown` matters: `.ignore` is a *recognized* product the app
> chose not to request (or already completed) — the user can still tap it and the pick is recorded (the
> "item not in list" notice is just informational). `.unknown` is a barcode the app could not identify
> at all — it is inert and cannot be tapped. Use `.ignore` styling for "we know this, but not now" and
> `.unknown` styling for "we don't recognize this."

## Product list and the provider

MatrixScan Pick is designed to work at the **product level** rather than the individual-barcode
level. You declare what the user needs to pick as a set of products (each with a `quantityToPick`),
and a product provider resolves each scanned barcode payload to a product identifier. The SDK
**supports mapping multiple barcode payloads to the same product** — so if one product can be
identified by more than one barcode, you can wire all of those payloads through to the same
`productIdentifier`.

### Two separate concerns: the database vs. the pick list

It helps to keep two things distinct (the minimal example above splits them deliberately):

- **The product database** — *everything the scanner can recognize*: which barcode payloads map to
  which product identifier. This is what `mapItems` resolves against. It has no quantities.
- **The products to pick** — the `Set<BarcodePickProduct>` (each with an `identifier` and a
  `quantityToPick`) that you actually hand to the provider. This is the *subset* the user is asked to
  pick; it's what gets highlighted and counted.

The database can be a **superset** of the pick list, and that gap is exactly what produces the
non-`.toPick` states (see "Pick states"):

- A payload that maps to a product **in the pick list** → `.toPick`.
- A payload that maps to a product **recognized but not in the pick list** → `.ignore` (still
  tappable, but flagged "not in list" and not counted).
- A payload **not in the database at all** (omitted from `mapItems`) → `.unknown` (inert).

So to let the user optionally pick "extra" recognized items, keep them in the database but leave them
out of `productsToPick`. To make a barcode completely non-interactive, leave it out of the database
entirely.

A `BarcodePickAsyncMapperProductProvider` resolves payloads via its delegate method:

```swift
func mapItems(
    _ items: [String],
    completionHandler: @escaping ([BarcodePickProductProviderCallbackItem]) -> Void
)
```

- `items` is the batch of raw barcode payloads the SDK has seen and needs resolved.
- For each payload you recognize, return a
  `BarcodePickProductProviderCallbackItem(itemData:productIdentifier:)`. Multiple payloads can share
  the same `productIdentifier`.
- Omit payloads you don't recognize from the returned array — those barcodes stay in the `.unknown`
  state: they were not mapped to a product, so they are never added to the to-pick set and **cannot be
  picked**.
- The mapping is **asynchronous** (call `completionHandler` when ready), so a database lookup or
  network call inside the delegate is fine.

## Confirming picks (required)

`BarcodePick` does not auto-finalize a pick when the user taps a code. Instead it asks your
`BarcodePickActionListener` to confirm: it calls `didPickItem(withData:completionHandler:)`
(or `didUnpickItem(...)` for un-picking) and waits until you invoke the completion handler.

- `completionHandler(true)` — finalize the action. On a pick (`didPickItem`) the item transitions to
  `.picked`; on an unpick (`didUnpickItem`) it transitions back to whatever state it was in before it
  was picked — `.toPick` for a required item, or `.ignore` for an optional/not-in-list one.
- `completionHandler(false)` — reject it; the item stays as it was.

This indirection exists so the app can validate a pick against a backend (stock check, task
assignment) before committing — you can call the completion handler asynchronously after a network
round-trip. If you don't need validation, confirm immediately with `completionHandler(true)`.

**This listener is mandatory for a working picking flow.** Register it with
`barcodePickView.addActionListener(self)`. Without it, tapping a code does nothing visible — the most
common "my picks don't complete" problem, and the official basic Get Started page omits it.

## Tracking picks (and unpicks)

The picking flow runs entirely inside `BarcodePick` and `BarcodePickView`, but the app usually
wants to know what's been picked — to update its own state, post the result to a backend, or decide
when the order is complete. There are two ways to observe pick state from outside the SDK.

### `BarcodePickScanningListener` (recommended)

`BarcodePick` exposes a session-level listener that fires whenever the picking state changes. The
minimal integration above already registers it on the mode (`barcodePick.addScanningListener(self)`)
and stubs out the conformance — fill in `barcodePick(_:didUpdate:)` and
`barcodePick(_:didComplete:)` with whatever your app needs.

Two things to keep in mind when implementing them:

- `pickedItems` / `scannedItems` on the session are sets of **barcode payloads** (`itemData`
  strings), not product identifiers. To get product-level state, map them back through the same
  mapping you provide in `mapItems`.
- These callbacks are **not** main-actor annotated — dispatch to the main queue before touching
  UIKit.

Use this for app-level tracking: the SDK is the source of truth and you just read it.

### Bookkeeping via `BarcodePickActionListener` (alternative)

The action listener you already wired up for pick confirmation can also drive your own counters —
increment in `didPickItem`, decrement in `didUnpickItem`. This works, but it means the app holds a
view of state separate from the SDK's session, which you then have to keep in sync. Prefer the
scanning listener above unless you already have action-listener-driven bookkeeping for another
reason.

## Highlight configuration

The highlight drawn over each detected barcode is controlled through
`BarcodePickViewSettings.highlightStyle`, which takes any `BarcodePickViewHighlightStyle`. The SDK
ships built-in styles plus a custom-view option:

- **`BarcodePickViewHighlightStyleDot`** — a circular highlight (the default).
- **`BarcodePickViewHighlightStyleDotWithIcons`** — dot with optional icons per pick state.
- **`BarcodePickViewHighlightStyleRectangular`** — a rectangular highlight sized to the barcode.
- **`BarcodePickViewHighlightStyleRectangularWithIcons`** — rectangle with optional icons per state.
- **`BarcodePickViewHighlightStyleCustomView`** — supply your own `UIView` per barcode for fully bespoke
  highlights.

All styles are state-aware via the `BarcodePickState` enum (`.toPick` / `.picked` / `.unknown` / `.ignore`).
Pick the style that fits, assign it to `viewSettings.highlightStyle`, and the view handles the
per-barcode rendering and state transitions automatically.

Per-state appearance (brushes, icons, custom views, status icons) and the full delegate-based
custom-view flow are covered by a separate skill — keep this guide focused on the picking pipeline.

## Finish button + handler

The finish button's visibility is `BarcodePickViewSettings.showFinishButton` (`Bool`). To react to
taps, set `barcodePickView.UIDelegate` and implement the optional
`BarcodePickViewUIDelegate.barcodePickViewDidTapFinishButton(_:)`.

What "finish" actually does — pop, dismiss, show a summary, signal back to a SwiftUI host — depends
on how the screen is presented in the host app, so the minimal example leaves the body as a comment.
Fill it in with whatever fits.

## Feedback (sound / haptic)

Sound and haptic feedback are simple on/off toggles on **`BarcodePickSettings`** (the mode settings,
not the view settings) — both default to `true`:

```swift
settings.isSoundEnabled = false
settings.isHapticsEnabled = false   // note: 'is' prefix and plural 'haptics'
```

Set them on `BarcodePickSettings` before constructing the `BarcodePick` mode. The Swift names use the
`is` prefix (`isSoundEnabled` / `isHapticsEnabled`) — the underlying ObjC properties are
`soundEnabled` / `hapticsEnabled` but the importer renames them based on the getter convention.

## Camera

`BarcodePickView` owns the camera — you do **not** create a `Camera` or set a `FrameSource` on the
context. The view turns the camera on during `start()` and releases it on `stop()`. The Get Started
guide uses the convenience initializer, which applies sensible camera defaults internally, so most
integrations never touch camera settings.

If the user does need to tune the camera (resolution, zoom, focus), there is an opt-in path: start
from `BarcodePick.recommendedCameraSettings` (a class property), modify it, and pass it to the
designated initializer that takes a `cameraSettings:` argument:

```swift
let cameraSettings = BarcodePick.recommendedCameraSettings
cameraSettings.preferredResolution = .uhd4k

barcodePickView = BarcodePickView(frame: view.bounds,
                                  context: context,
                                  barcodePick: mode,
                                  settings: viewSettings,
                                  cameraSettings: cameraSettings)
```

Passing `nil` (or using the 4-argument initializer) keeps the internal defaults. Always start from
`BarcodePick.recommendedCameraSettings` rather than constructing `CameraSettings()` from scratch.

> **Common mistake — do NOT use the generic Scandit Core camera APIs here.** To change the resolution
> (or any camera setting) in MatrixScan Pick you go through the `cameraSettings:` initializer above —
> you do **not**:
> - create a `Camera` (`Camera.default`), nor
> - call `context.setFrameSource(...)` / assign `context.frameSource` (it is get-only on this path), nor
> - build a bare `CameraSettings()`.
>
> Those are the generic DataCaptureContext camera pattern used by *other* Scandit modes; `BarcodePickView`
> manages its own camera, so they don't apply. For 4K, the only change is
> `cameraSettings.preferredResolution = .uhd4k` on `BarcodePick.recommendedCameraSettings` (the case is
> `.uhd4k` — not `.uHD` or `.uhd`), passed to the view's `cameraSettings:` initializer.

## Control visibility (finish / pause / zoom / torch buttons)

`BarcodePickViewSettings` toggles the built-in buttons (all `Bool`):

- `showFinishButton`
- `showPauseButton`
- `showZoomButton` + `zoomButtonPosition` (`Anchor`)
- `showTorchButton` + `torchButtonPosition` (`Anchor`)

> **Common mistake — use these built-in toggles; do NOT roll your own.** To show a torch (flashlight)
> control, set `viewSettings.showTorchButton = true` and let `BarcodePickView` render and wire it. Do
> **not** add your own `UIButton` and toggle the camera torch directly (e.g. `context.frameSource as?
> Camera` then setting `desiredTorchState`) — the view owns the camera, so a hand-rolled torch button is
> both unnecessary and fights the view's camera management. The same applies to the finish / pause / zoom
> buttons: flip the corresponding `show…Button` flag rather than building a custom control.

The same settings object also controls UI text and overlays: `showGuidelines` +
`initialGuidelineText` / `moveCloserGuidelineText` / `tapShutterToPauseGuidelineText`, `showHints` +
the various `on…HintText` strings, `showLoadingDialog` + `loadingDialogTextForPicking` /
`loadingDialogTextForUnpicking`, and `logoStyle` / `logoAnchor`.

## Lifecycle: start / freeze / pause / stop / reset

`BarcodePickView` exposes five lifecycle methods:

- **`start()`** — starts the camera and scanning. Call in `viewWillAppear` (and `viewDidAppear`).
- **`freeze()`** — freezes the current frame / scanning without releasing the camera.
- **`pause()`** — pauses scanning without tearing down the camera.
- **`stop()`** — stops scanning and releases the camera.
- **`reset()`** — clears the current picking state.

The recommended teardown pattern (from the Get Started guide) calls `pause()` in `viewWillDisappear`,
then `stop()` only `if isMovingFromParent` (i.e. the screen is truly being popped, not just covered by
another view).

## SwiftUI

MatrixScan Pick has **no native SwiftUI view** — `BarcodePickView` is a `UIView`. Bridge it into SwiftUI
by wrapping the UIKit view controller in a `UIViewControllerRepresentable`, and keep every
`BarcodePick*` API call inside the wrapped UIKit layer. The SwiftUI `View` struct contains no Scandit
code.

> The [SwiftUI Get Started guide](https://docs.scandit.com/sdks/ios/matrixscan-pick/get-started-with-swift-ui/)
> also documents a `UIViewRepresentable` + `Coordinator` alternative where the coordinator owns the SDK
> objects directly. **Prefer the `UIViewControllerRepresentable` pattern below** — it keeps the UIKit
> lifecycle (`viewWillAppear` / `viewWillDisappear` / `deinit`) intact, which matters for Pick because
> the `start()` / `pause()` / `stop()` + `isMovingFromParent` flow lives on the view controller, and the
> action listener and finish-button UI delegate fit naturally there too. The same view controller also
> stays reusable from UIKit. Only fall back to the coordinator pattern if the project already has a
> strong reason to.

Canonical shape:

```swift
import SwiftUI
import ScanditBarcodeCapture

struct ScanView: View {
    var body: some View {
        PickViewControllerRepresentable()
            .ignoresSafeArea()
    }
}

struct PickViewControllerRepresentable: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> PickViewController {
        PickViewController()
    }

    func updateUIViewController(_ uiViewController: PickViewController, context: Context) {}
}
```

`PickViewController` is the exact UIKit class from the minimal example above — no changes. The SwiftUI
`View` struct contains no Scandit code. The finish-button handler in `PickViewController` stays a
comment placeholder; in SwiftUI, the host typically owns dismissal (e.g. an `@Environment(\.dismiss)`
action) and signals back into the UIKit class however the app prefers.

### SwiftUI cleanup

The view controller's `viewWillAppear` / `viewWillDisappear` / `deinit` still fire when SwiftUI presents
and dismisses the representable, so the UIKit lifecycle code (`start()`, `pause()` / `stop()` when
`isMovingFromParent`, `addActionListener` registration) carries over unchanged — no extra SwiftUI-side
teardown is required. When SwiftUI removes the representable from the view tree, it releases its
strong reference to `PickViewController`, which triggers `deinit`.

If you need to react to SwiftUI-side teardown explicitly (e.g. to stop a related service), implement
the static `dismantleUIViewController` on the representable:

```swift
struct PickViewControllerRepresentable: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> PickViewController {
        PickViewController()
    }

    func updateUIViewController(_ uiViewController: PickViewController, context: Context) {}

    static func dismantleUIViewController(_ uiViewController: PickViewController, coordinator: ()) {
        // Optional: extra teardown beyond what the view controller's deinit handles.
    }
}
```

Do not move the action-listener removal or `stop()` call out of the view controller into
`dismantleUIViewController` — keep the `BarcodePick` lifecycle inside the UIKit class so the same view
controller works when used directly from UIKit.

## Threading

`BarcodePickViewListener` and `BarcodePickViewUIDelegate` are declared main-actor (`NS_SWIFT_UI_ACTOR`),
so their callbacks — including `barcodePickViewDidTapFinishButton(_:)` — arrive on the main queue and
can touch UIKit directly.

`BarcodePickScanningListener` and `BarcodePickActionListener` are **not** main-actor annotated.
Dispatch to the main queue before touching UIKit from `barcodePick(_:didUpdate:)`,
`barcodePick(_:didComplete:)`, `didPickItem(withData:completionHandler:)`, or
`didUnpickItem(withData:completionHandler:)`.

## After wiring up

Build the project. If compile errors remain, fetch the [MatrixScan Pick API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html) to find the correct API before guessing. Always include the docs link in your answer so the user can explore further.
