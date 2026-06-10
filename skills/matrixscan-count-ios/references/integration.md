# MatrixScan Count iOS Integration Guide

MatrixScan Count is a pre-built bulk-counting workflow built on top of the Scandit SDK. It scans many
barcodes at once, counts them, and renders a built-in augmented-reality counting UI (highlights over
each recognized barcode plus a guidance overlay, a shutter, and List / Exit buttons) so a user can
sweep the camera across a shelf or pile and tally everything. The integration has two primary
elements: the **`BarcodeCount`** data capture mode and the **`BarcodeCountView`** pre-built UI.

This guide follows the official
[MatrixScan Count Get Started (iOS)](https://docs.scandit.com/sdks/ios/matrixscan-count/get-started/)
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
> create the `Camera`, apply `BarcodeCount.recommendedCameraSettings`, set it as the context's frame
> source, and switch it on/off yourself in the view-controller lifecycle (steps 3 and 6).

## Prerequisites

- Scandit Data Capture SDK for iOS — add via Swift Package Manager:
  - URL: `https://github.com/Scandit/datacapture-spm`
  - Add `ScanditBarcodeCapture` and `ScanditCaptureCore` package products to your target
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test
- `NSCameraUsageDescription` in `Info.plist`

## Minimal Integration (Swift)

Ask the user which barcode symbologies they need to scan. When asking about symbologies, mention that
it's important to only enable the ones they actually need — fewer enabled symbologies improves
scanning performance and accuracy.

Then ask which file or view controller they'd like to integrate MatrixScan Count into, and write the
integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `ScanditBarcodeCapture` and `ScanditCaptureCore` via Swift Package Manager: `https://github.com/Scandit/datacapture-spm`
2. Make sure you have `NSCameraUsageDescription` added to your `Info.plist`
3. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com

The code below is the official Get Started flow assembled into one view controller.

```swift
import ScanditBarcodeCapture

class CountViewController: UIViewController {

    // Step 1: the Data Capture Context, created with your license key.
    private lazy var context: DataCaptureContext = {
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()

    private var camera: Camera?
    private var barcodeCount: BarcodeCount!
    private var barcodeCountView: BarcodeCountView!

    // The app's own running tally. The BarcodeCountSession is only valid inside the listener
    // callback, so we copy the recognized barcodes out into this list (step 7).
    private var allRecognizedBarcodes: [Barcode] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRecognition()
    }

    // Step 6: the camera is NOT turned on automatically. Re-arm the view and switch the camera
    // on when it appears; switch off when it disappears, and tear the view down on the way out.
    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        barcodeCountView.prepareScanning(with: context)
        camera?.switch(toDesiredState: .on)
    }

    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
        camera?.switch(toDesiredState: .off)
        if isMovingFromParent {
            barcodeCountView.stopScanning()
        }
    }

    private func setupRecognition() {
        // Step 3: obtain the camera, apply the recommended settings, and set it as the
        //         context's frame source. Always start from BarcodeCount.recommendedCameraSettings.
        let cameraSettings = BarcodeCount.recommendedCameraSettings
        camera = Camera.default
        camera?.apply(cameraSettings)
        context.setFrameSource(camera)

        // Step 2: configure the Barcode Count mode. Settings start with all symbologies disabled —
        //         enable only the ones the app needs.
        let settings = BarcodeCountSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .ean8, enabled: true)
        settings.set(symbology: .upce, enabled: true)
        settings.set(symbology: .code128, enabled: true)
        settings.set(symbology: .code39, enabled: true)

        barcodeCount = BarcodeCount(context: context, settings: settings)

        // Step 4: register a listener for completed scan phases.
        barcodeCount.addListener(self)

        // Step 5: add the BarcodeCountView (the built-in AR counting UI). It is designed to be
        //         displayed full screen and does NOT add itself to the hierarchy.
        barcodeCountView = BarcodeCountView(frame: view.bounds,
                                            context: context,
                                            barcodeCount: barcodeCount)
        barcodeCountView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(barcodeCountView)

        // Step 8: handle the List / Exit buttons.
        barcodeCountView.uiDelegate = self
    }
}

// Step 7: collect recognized barcodes when a scan phase completes.
extension CountViewController: BarcodeCountListener {
    func barcodeCount(_ barcodeCount: BarcodeCount,
                      didScanIn session: BarcodeCountSession,
                      frameData: FrameData) {
        // The session is only valid inside this callback — copy out what you need now.
        let recognizedBarcodes = session.recognizedBarcodes
        // This is invoked on an internal recognition thread; hop to main before touching app state.
        DispatchQueue.main.async {
            self.allRecognizedBarcodes = recognizedBarcodes
        }
    }
}

// Step 8: the List / Exit button callbacks. "List" = show progress so far; "Exit" = counting finished.
// The sessionSnapshot gives you the recognized barcodes at tap time (on the main thread).
extension CountViewController: BarcodeCountViewUIDelegate {
    func listButtonTapped(for view: BarcodeCountView,
                          sessionSnapshot: BarcodeCountSessionSnapshot) {
        // Present a list, e.g. from sessionSnapshot.recognizedBarcodes (counting still in progress).
    }

    func exitButtonTapped(for view: BarcodeCountView,
                          sessionSnapshot: BarcodeCountSessionSnapshot) {
        // The user finished — present a summary / complete the scanning.
    }
}
```

> `BarcodeCountView` does **not** add itself to the view hierarchy — construct it with a `frame` and
> `addSubview` it yourself. Note the constructor takes both the `context` and the `barcodeCount` mode.

## What the code does (and what it does NOT do)

- Creates the `DataCaptureContext` with the license key.
- Creates and configures the **camera** (`Camera.default` + `BarcodeCount.recommendedCameraSettings`),
  sets it as the context frame source, and drives its state across the view-controller lifecycle.
- Builds `BarcodeCountSettings` with the user's symbologies and creates the `BarcodeCount` mode.
- Registers a `BarcodeCountListener` to copy recognized barcodes off the session.
- Creates the `BarcodeCountView`, adds it to the hierarchy, and wires the List / Exit UI delegate.

What this code does **not** do:
- It does not implement an **expected/receiving list** (`BarcodeCountCaptureList`) — the "scan against
  a known list" use case. → see **`list-scanning.md`**.
- It does not customize the **highlight appearance** (icon per barcode, or Dot-style brush colors) — the
  default highlights are used. → see **`highlights.md`**.
- It does not customize the status mode or the toolbar — defaults are used.

## Step 1 — Data Capture Context

```swift
DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
let context = DataCaptureContext.shared
```

The context is the central object tying together the frame source (camera) and the capture mode. It
requires a valid license key. `DataCaptureContext.initialize(licenseKey:)` configures the shared
instance, which you then read from `DataCaptureContext.shared` (the form used by the official sample).
The direct initializer `DataCaptureContext(licenseKey:)` also exists and is equivalent for a single
capture screen — if a codebase already uses it, leave it.

## Step 2 — Configure the Barcode Count mode

`BarcodeCountSettings` starts with all symbologies disabled. Enable each via
`settings.set(symbology:enabled:)`; `enableSymbologies(_:)` enables a whole set at once, and
`enabledSymbologies` (read-only) returns what's currently on.

```swift
let settings = BarcodeCountSettings()
settings.set(symbology: .ean13UPCA, enabled: true)

let barcodeCount = BarcodeCount(context: context, settings: settings)
```

Constructing `BarcodeCount(context:settings:)` attaches the mode to the context and **enables it** — you
do not normally set `barcodeCount.isEnabled`. Only set `barcodeCount.isEnabled = true` to re-enable the
mode after you've disabled it (e.g. after `stopScanning()` / `endScanningPhase()`).

For the exact `Symbology` case to pass (e.g. QR is `.qr`, not `.qrCode`), consult the
[Symbology API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api/symbology.html) —
don't guess the case name. Per-symbology tuning (active symbol counts, color-inverted decoding,
checksums, extensions) is available via `settings.settings(for:)`; set it on `BarcodeCountSettings`
before constructing the mode. For example, to restrict a variable-length symbology to a length range:

```swift
settings.settings(for: .code128).activeSymbolCounts = Set(8...20)
```

`activeSymbolCounts` is **`Set<Int>` in Swift** — the underlying ObjC type is `NSSet<NSNumber*>` but it
is `NS_REFINED_FOR_SWIFT`, so assign a `Set<Int>` (e.g. `Set(8...20)`), **not** a `Set<NSNumber>`.
Other `SymbologySettings` members: `isColorInvertedEnabled: Bool`, `checksums: Checksum` (an
`OptionSet` — assign with array-literal syntax, e.g. `[.mod10]`), and `enabledExtensions` (mutate via
`set(extension:enabled:)`).

If you're sure the scene contains only unique barcodes, set
`settings.expectsOnlyUniqueBarcodes = true` to improve performance.

## Step 3 — Camera and frame source

`BarcodeCountView` does **not** manage the camera. Obtain the back camera, apply the recommended
settings for Barcode Count, and set it as the context's frame source:

```swift
let cameraSettings = BarcodeCount.recommendedCameraSettings
let camera = Camera.default
camera?.apply(cameraSettings)
context.setFrameSource(camera)
```

Always start from `BarcodeCount.recommendedCameraSettings` — do **not** build a bare `CameraSettings()`.

## Step 4 — Register the listener

```swift
barcodeCount.addListener(self)
```

`BarcodeCountListener.barcodeCount(_:didScanIn:frameData:)` is called when a scan phase finishes and
results can be read from the `BarcodeCountSession`.

## Step 5 — Capture view and AR overlays

MatrixScan Count's built-in AR UI (buttons + overlays that guide the user) is added automatically by
placing a `BarcodeCountView` in your hierarchy:

```swift
let barcodeCountView = BarcodeCountView(frame: view.bounds, context: context, barcodeCount: barcodeCount)
barcodeCountView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
view.addSubview(barcodeCountView)
```

The view has two styles, chosen via the `style:` initializer argument — `BarcodeCountViewStyle.icon`
or `.dot`. **`.icon` is the default and the recommended style** (the modern look, fully customizable);
prefer it unless you specifically want plain colored dots. To opt into the Dot style:

```swift
let barcodeCountView = BarcodeCountView(frame: view.bounds, context: context, barcodeCount: barcodeCount, style: .dot)
```

## Step 6 — Configure the camera for the scanning view (lifecycle)

The camera is not turned on automatically. Drive both the view's scanning lifecycle and the camera with
the view-controller lifecycle: re-arm the view with `barcodeCountView.prepareScanning(with: context)`
and switch the camera on when the view appears; switch it off when it disappears, and tear the view
down with `barcodeCountView.stopScanning()` when the screen is actually being popped:

```swift
override func viewWillAppear(_ animated: Bool) {
    super.viewWillAppear(animated)
    barcodeCountView.prepareScanning(with: context)
    camera?.switch(toDesiredState: .on)
}

override func viewDidDisappear(_ animated: Bool) {
    super.viewDidDisappear(animated)
    camera?.switch(toDesiredState: .off)
    if isMovingFromParent {
        barcodeCountView.stopScanning()
    }
}
```

The camera switch is asynchronous — pass a completion block to
`switch(toDesiredState:completionHandler:)` if you need to know when it has finished.

> When you navigate to another screen *within* the app and back (e.g. a List screen) and want a faster
> return, you can use `FrameSourceState.standby` instead of `.off` on the way out (keeps the camera
> warm). Use `.off` when the app is genuinely leaving the scanning screen.

> **Common mistake — do NOT assume the view turns the camera on.** `BarcodeCountView` does not own the
> camera. You **must** create `Camera.default`, apply `BarcodeCount.recommendedCameraSettings`, call
> `context.setFrameSource(...)`, and switch the camera state yourself in the lifecycle. Omitting any of
> these leaves the preview black / frozen.

## Step 7 — Store and retrieve scanned barcodes

The scanned values live on the `BarcodeCountSession`, which is **only valid inside the listener
callback**. Copy `session.recognizedBarcodes` (`[Barcode]`) out immediately, and dispatch to the main
queue before touching UIKit (the callback runs on an internal recognition thread):

```swift
extension CountViewController: BarcodeCountListener {
    func barcodeCount(_ barcodeCount: BarcodeCount,
                      didScanIn session: BarcodeCountSession,
                      frameData: FrameData) {
        let recognizedBarcodes = session.recognizedBarcodes
        DispatchQueue.main.async {
            self.allRecognizedBarcodes = recognizedBarcodes
        }
    }
}
```

`session.additionalBarcodes` holds barcodes added programmatically (via
`barcodeCount.setAdditionalBarcodes(_:)` — useful for carrying a previous batch across a
background/foreground cycle), and `session.recognizedClusters` exposes cluster grouping when enabled.

## Step 8 — List and Exit callbacks

The built-in UI surfaces buttons whose taps are delivered through `BarcodeCountViewUIDelegate`
(`barcodeCountView.uiDelegate = self`). Each callback hands you a `BarcodeCountSessionSnapshot` — the
recognized barcodes at tap time — so you can populate the List screen directly:

```swift
extension CountViewController: BarcodeCountViewUIDelegate {
    func listButtonTapped(for view: BarcodeCountView,
                          sessionSnapshot: BarcodeCountSessionSnapshot) {
        // Show the current progress, e.g. sessionSnapshot.recognizedBarcodes (not necessarily finished).
    }

    func exitButtonTapped(for view: BarcodeCountView,
                          sessionSnapshot: BarcodeCountSessionSnapshot) {
        // The user finished counting — present a summary.
    }
}
```

`BarcodeCountSessionSnapshot` exposes `recognizedBarcodes`, `additionalBarcodes`, `recognizedClusters`,
and `frameSequenceId` — so you can read what's been counted at tap time without maintaining your own
copy. `singleScanButtonTapped(for:)` is also available (optional).

> Older SDKs (pre-8.5) used the no-snapshot `listButtonTapped(for:)` / `exitButtonTapped(for:)`
> overloads, now deprecated — you'll still see them in existing code. Prefer the `sessionSnapshot:`
> variants above.

## Reacting to barcode taps (optional)

This is **optional** — the basic integration does **not** wire up tap handling, and you should add it
only if the app's use case calls for reacting to a tap on a barcode (e.g. showing details for the
tapped item). Do not add it by default.

Tapping the List / Exit buttons is already handled by the `uiDelegate` above. If you *do* need to react
when the user taps a **barcode highlight** itself, set the view's `delegate` (a
`BarcodeCountViewDelegate` — separate from the `uiDelegate`) and implement
`barcodeCountView(_:didTapRecognizedBarcode:)`:

```swift
barcodeCountView.delegate = self

extension CountViewController: BarcodeCountViewDelegate {
    func barcodeCountView(_ view: BarcodeCountView,
                          didTapRecognizedBarcode trackedBarcode: TrackedBarcode) {
        // e.g. show details for the tapped barcode (trackedBarcode.barcode.data)
    }
}
```

`trackedBarcode` is a `TrackedBarcode` (from the batch module) exposing `.barcode`, `.identifier`, and
`.location`. `BarcodeCountViewDelegate` is main-actor, so these callbacks arrive on the main queue.
There are matching tap callbacks for the other highlight states (`didTapRecognizedBarcodeNotInList`,
`didTapAcceptedBarcode`, `didTapRejectedBarcode`, `didTapFilteredBarcode`); the same `delegate` is also
where per-barcode brush / icon customization lives — see `highlights.md`.

## Beyond the basics

These are common follow-ups; fetch the
[Advanced Configurations](https://docs.scandit.com/sdks/ios/matrixscan-count/advanced/) page and the
API reference for exact signatures before writing code.

- **Receiving / capture list** (scan against a known list): build a `BarcodeCountCaptureList` from
  `TargetBarcode`s and apply it with `barcodeCount.setCaptureList(_:)`. The view then distinguishes
  recognized / accepted / rejected / not-in-list barcodes, and the capture-list session reports
  correct vs. wrong vs. missing. → **full guide: `list-scanning.md`** (capture list, progress, auto-finish,
  the accept/reject not-in-list action).
- **Control visibility**: the view exposes many `shouldShow…` toggles (`shouldShowListButton`,
  `shouldShowExitButton`, `shouldShowShutterButton`, `shouldShowFloatingShutterButton`,
  `shouldShowSingleScanButton`, `shouldShowClearHighlightsButton`, `shouldShowStatusModeButton`,
  `shouldShowUserGuidanceView`, `shouldShowHints`, `shouldShowToolbar`, `shouldShowScanAreaGuides`,
  `shouldShowListProgressBar`, `shouldShowTorchControl`), plus `torchControlPosition`.
- **Tap to uncount**: if the user should be able to remove a barcode after scanning it, set
  `barcodeCountView.tapToUncountEnabled = true`. Tapping an already-counted barcode then removes it from
  the current scanned items. (Verify the property name against the API reference if unsure; the hint text
  is customizable via `barcodeCountView.setTextForTapToUncountHint(_:)`.)
- **Highlight appearance (icons / brushes)**: customize the per-barcode icon (default Icon style) or the
  Dot-style color via the `BarcodeCountViewDelegate`. → **full guide: `highlights.md`**.
- **Reset the mode**: when a counting process is over and you want to start fresh, call
  `barcodeCount.reset()` to clear the scanned list and the AR overlays (e.g. from your Exit/summary
  flow). The minimal example above doesn't call it — add it where your app begins a new count.
- **Feedback (sound / haptic)**: configured through `BarcodeCount.feedback` (a `BarcodeCountFeedback`),
  whose `success` / `failure` are `Feedback` objects. The default (`BarcodeCountFeedback.defaultFeedback`)
  beeps and vibrates; the plain initializer `BarcodeCountFeedback()` is **silent** (its channels default
  to an empty `Feedback()`), so to suppress the beep and vibration assign `barcodeCount.feedback =
  BarcodeCountFeedback()`. Note: BarcodeCount has **no** `isSoundEnabled` / `isHapticsEnabled` boolean
  (that is the MatrixScan Pick API) — feedback is always configured via the `BarcodeCountFeedback` object.

## Advanced configurations

These are optional configurations on top of the basic integration. They mirror the official
[Advanced Configurations](https://docs.scandit.com/sdks/ios/matrixscan-count/advanced/) page. Verify
exact signatures against the API reference before writing code if anything is unclear.

### Filtering (count only some of the barcodes in the scene)

If several barcode types appear in the scene and you only want to count some of them, exclude the others
with a `BarcodeFilterSettings` assigned to `BarcodeCountSettings.filterSettings`. Excluded barcodes still need
to be *enabled* on the settings — they are decoded, then filtered out of the count and covered by a
colored layer in the AR view. Exclude by **symbology** (`excludedSymbologies`), by a **regex** matched
against the barcode data (`excludedCodesRegex`), or by **symbol count** (`excludedSymbolCounts`):

```swift
let filterSettings = BarcodeFilterSettings()
filterSettings.excludedSymbologies = [.pdf417]

let settings = BarcodeCountSettings()
settings.set(symbology: .code128, enabled: true)
settings.set(symbology: .pdf417, enabled: true)
settings.filterSettings = filterSettings

let barcodeCount = BarcodeCount(context: context, settings: settings)
```

```swift
// Exclude every barcode whose data starts with "1234":
filterSettings.excludedCodesRegex = "^1234.*"
```

- `excludedSymbologies` is a `Set<Symbology>`; `excludedCodesRegex` is a `String`.
- An excluded symbology that isn't part of the enabled symbologies has no effect — enable it first.
- The filtered barcodes are covered by a **transparent** layer by default. To make them visible (change
  the color / transparency), assign a highlight to the **view's** `filterSettings` property — construct
  a `BarcodeFilterHighlightSettingsBrush(brush:)` (which conforms to `BarcodeFilterHighlightSettings`)
  and set `barcodeCountView.filterSettings = BarcodeFilterHighlightSettingsBrush(brush: someBrush)`.

### Hardware trigger (volume button)

On iOS you can let the view react to presses of the device **volume button** instead of (or alongside)
the on-screen shutter — useful for one-handed scanning. Toggle it on the `BarcodeCountView`:

```swift
barcodeCountView.hardwareTriggerEnabled = true
```

`hardwareTriggerEnabled` is a `Bool` on the view. (On iOS this binds to the volume button; the
`hardwareTriggerKeyCode` / `hardwareTriggerSupported` APIs are Android-only.)

## SwiftUI

MatrixScan Count has **no native SwiftUI view** — `BarcodeCountView` is a `UIView`. Bridge it into
SwiftUI by wrapping the UIKit view controller in a `UIViewControllerRepresentable`, and keep every
`BarcodeCount*` API call inside the wrapped UIKit layer. The SwiftUI `View` struct contains no Scandit
code. See the
[SwiftUI Get Started guide](https://docs.scandit.com/sdks/ios/matrixscan-count/get-started-with-swift-ui/).

```swift
import SwiftUI
import ScanditBarcodeCapture

struct ScanView: View {
    var body: some View {
        CountViewControllerRepresentable()
            .ignoresSafeArea()
    }
}

struct CountViewControllerRepresentable: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> CountViewController {
        CountViewController()
    }

    func updateUIViewController(_ uiViewController: CountViewController, context: Context) {}
}
```

`CountViewController` is the exact UIKit class from the minimal example above — no changes. The
view-controller lifecycle (`viewWillAppear` / `viewDidDisappear`) still fires when SwiftUI presents
and dismisses the representable, so the camera on/off code carries over unchanged.

Alternatively, the official SwiftUI guide also shows wrapping the `BarcodeCountView` directly in a
`UIViewRepresentable` (instead of a view controller). Either bridge works — wrapping the view
controller is usually simpler because it gives you the lifecycle hooks for free; if you wrap the view
in a `UIViewRepresentable`, you drive `prepareScanning`/`stopScanning` and the camera state from the
representable's coordinator / `makeUIView` / `dismantleUIView` instead. Keep all `BarcodeCount*` calls
inside the wrapped UIKit layer either way.

## After wiring up

Build the project. If compile errors remain, fetch the
[MatrixScan Count API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html)
to find the correct API before guessing. Always include the docs link in your answer so the user can
explore further.
