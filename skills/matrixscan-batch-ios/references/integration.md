# BarcodeBatch (MatrixScan Batch) iOS Integration Guide

BarcodeBatch is the multi-barcode tracking mode. It simultaneously tracks all barcodes visible in the camera feed, reporting additions, position updates, and removals on every frame. Unlike BarcodeCapture (which scans one barcode at a time), BarcodeBatch continuously tracks every barcode in view — it does not stop or disable after a detection. The camera and lifecycle are managed manually, exactly like BarcodeCapture.

Examples below use Swift and a UIKit `UIViewController`. SwiftUI is covered at the end — the canonical approach is to wrap the UIKit view controller in a `UIViewControllerRepresentable`.

## Prerequisites

- Scandit Data Capture SDK for iOS — add via Swift Package Manager:
  - URL: `https://github.com/Scandit/datacapture-spm`
  - Add `ScanditBarcodeCapture` and `ScanditCaptureCore` package products to your target
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test
- `NSCameraUsageDescription` in `Info.plist`

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that enabling only the symbologies actually needed improves tracking performance and accuracy.

Once the user responds, ask them which view controller (or SwiftUI view) they'd like to integrate BarcodeBatch into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `ScanditBarcodeCapture` and `ScanditCaptureCore` via Swift Package Manager: `https://github.com/Scandit/datacapture-spm`
2. Make sure you have `NSCameraUsageDescription` added to your `Info.plist`
3. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com

## Framework import

```swift
import ScanditBarcodeCapture
import UIKit
```

`BarcodeBatch`, `BarcodeBatchSettings`, `BarcodeBatchListener`, `BarcodeBatchSession`, `BarcodeBatchBasicOverlay`, `BarcodeBatchAdvancedOverlay`, `TrackedBarcode`, `DataCaptureContext`, `DataCaptureView`, and `Camera` all live in `ScanditBarcodeCapture`.

## Step 1 — Create the DataCaptureContext

The canonical iOS pattern uses the shared singleton — initialize once with the license key, then read `DataCaptureContext.shared`:

```swift
private lazy var context: DataCaptureContext = {
    DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
    return DataCaptureContext.shared
}()
```

## Step 2 — Configure BarcodeBatchSettings

All symbologies are disabled by default. Enable each one explicitly; enabling only what is needed reduces tracking overhead.

```swift
let settings = BarcodeBatchSettings()
settings.set(symbology: .ean13UPCA, enabled: true)
settings.set(symbology: .ean8, enabled: true)
settings.set(symbology: .code128, enabled: true)
```

### BarcodeBatchSettings Members

| Member | Description |
|--------|-------------|
| `set(symbology:enabled:)` | Enable or disable one symbology. |
| `enableSymbologies(_:)` | Enable a `Set<Symbology>` in one call. |
| `settings(for:)` | Get per-symbology `SymbologySettings` (e.g. `activeSymbolCounts`, `isColorInvertedEnabled`, `checksums`). |

### Symbology fine-tuning

```swift
settings.settings(for: .code39).activeSymbolCounts = Set(7...20)
settings.settings(for: .code128).isColorInvertedEnabled = true
```

## Step 3 — Camera setup

The camera is set up manually. Apply `BarcodeBatch.recommendedCameraSettings` (a static type property) to the default camera, then assign the camera as the frame source.

```swift
private var camera: Camera?

// In setupRecognition():
camera = Camera.default
context.setFrameSource(camera, completionHandler: nil)

let cameraSettings = BarcodeBatch.recommendedCameraSettings
camera?.apply(cameraSettings, completionHandler: nil)
```

If the user needs to tune resolution, zoom, focus, torch, macro, or adaptive exposure, modify the recommended settings before applying — do not construct `CameraSettings()` from scratch:

```swift
let cameraSettings = BarcodeBatch.recommendedCameraSettings
cameraSettings.preferredResolution = .uhd4k
camera?.apply(cameraSettings, completionHandler: nil)
```

## Step 4 — Create BarcodeBatch

BarcodeBatch uses a direct convenience initializer (not a factory method). Passing a non-nil context attaches the mode to the context automatically.

```swift
private var barcodeBatch: BarcodeBatch!

// In setupRecognition():
barcodeBatch = BarcodeBatch(context: context, settings: settings)
barcodeBatch.addListener(self)
```

### BarcodeBatch Members

| Member | Description |
|--------|-------------|
| `BarcodeBatch(context:settings:)` | Convenience initializer — when context is non-nil, the mode is attached to the context. |
| `isEnabled: Bool` | Pause/resume tracking without tearing down the camera. |
| `addListener(_:)` / `removeListener(_:)` | Register or remove a `BarcodeBatchListener` (weak reference). |
| `apply(_:completionHandler:)` | Update settings at runtime. |
| `BarcodeBatch.recommendedCameraSettings` | Static — returns recommended `CameraSettings`. |

## Step 5 — DataCaptureView

`DataCaptureView` is a `UIView`. Create it with the context and add it as a subview manually — the view does not auto-attach.

```swift
private var captureView: DataCaptureView!

// In setupRecognition():
captureView = DataCaptureView(context: context, frame: view.bounds)
captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
view.addSubview(captureView)
```

## Step 6 — BarcodeBatchBasicOverlay

`BarcodeBatchBasicOverlay` renders a highlight frame or dot over each tracked barcode. The convenience initializer auto-adds the overlay to the data capture view.

```swift
// Default style (.frame):
let overlay = BarcodeBatchBasicOverlay(barcodeBatch: barcodeBatch, view: captureView)

// Or choose a style explicitly:
let overlay = BarcodeBatchBasicOverlay(barcodeBatch: barcodeBatch, view: captureView, style: .dot)
```

### BarcodeBatchBasicOverlay Members

| Member | Description |
|--------|-------------|
| `init(barcodeBatch:view:)` | Convenience init — auto-adds the overlay to the view. Default `.frame` style. |
| `init(barcodeBatch:view:style:)` | Convenience init — same, with explicit style. |
| `delegate` | `BarcodeBatchBasicOverlayDelegate?` — for per-barcode brush customization. |
| `brush` | `Brush?` — uniform brush for all tracked barcodes when no delegate is set. |
| `style` | `BarcodeBatchBasicOverlayStyle` — `.frame` or `.dot` (read-only). |
| `dotRadius` | `FloatWithUnit` — controls dot size when style is `.dot` (default `0.03` fraction). |
| `setBrush(_:for:)` | Imperatively set the brush for a specific barcode. |
| `clearTrackedBarcodeBrushes()` | Clear all custom brushes. |
| `shouldShowScanAreaGuides` | Debug: show the active scan area outline. |

### Per-barcode brush customization (requires MatrixScan AR add-on)

Conform to `BarcodeBatchBasicOverlayDelegate` to return a different brush per barcode. The `brushFor` callback fires on the **rendering thread**; the `didTap` callback fires on the **main thread**.

```swift
extension ScanViewController: BarcodeBatchBasicOverlayDelegate {

    func barcodeBatchBasicOverlay(
        _ overlay: BarcodeBatchBasicOverlay,
        brushFor trackedBarcode: TrackedBarcode
    ) -> Brush? {
        // Return nil to draw nothing for this barcode.
        switch trackedBarcode.barcode.symbology {
        case .ean13UPCA:
            return Brush(fill: UIColor.green.withAlphaComponent(0.4), stroke: .green, strokeWidth: 2)
        default:
            return nil
        }
    }

    func barcodeBatchBasicOverlay(
        _ overlay: BarcodeBatchBasicOverlay,
        didTap trackedBarcode: TrackedBarcode
    ) {
        // React to the user tapping a barcode highlight.
    }
}
```

Assign the delegate after creating the overlay:
```swift
overlay.delegate = self
```

> **MatrixScan AR add-on required** for the `brushFor` delegate callback and `setBrush(_:for:)`. A uniform default brush (no delegate) does not require the add-on.

## Step 7 — BarcodeBatchListener

Conform to `BarcodeBatchListener` to receive per-frame session updates. `barcodeBatch(_:didUpdate:frameData:)` is called on a **background queue** — do not touch UIKit from inside it without dispatching to the main queue, and do not hold session collection references outside the callback.

```swift
extension ScanViewController: BarcodeBatchListener {

    func barcodeBatch(
        _ barcodeBatch: BarcodeBatch,
        didUpdate session: BarcodeBatchSession,
        frameData: FrameData
    ) {
        // Called on a background queue — copy data, then dispatch UI work.
        let addedData = session.addedTrackedBarcodes.compactMap { $0.barcode.data }
        let removedIdentifiers = session.removedTrackedBarcodes
        DispatchQueue.main.async {
            for data in addedData {
                // handle newly tracked barcode data
                _ = data
            }
            for identifier in removedIdentifiers {
                // handle barcode that left the frame
                _ = identifier
            }
        }
    }
}
```

Register the listener after constructing `BarcodeBatch`:
```swift
barcodeBatch.addListener(self)
```

### BarcodeBatchListener Protocol

| Method | Description |
|--------|-------------|
| `barcodeBatch(_:didUpdate:frameData:)` | Required. Called every processed frame on a background queue — copy data and dispatch UI work. |
| `didStartObserving(_:)` | Optional. Listener was registered. |
| `didStopObserving(_:)` | Optional. Listener was removed. |

### BarcodeBatchSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `trackedBarcodes` | `Dictionary<Int, TrackedBarcode>` | All currently tracked barcodes, keyed by tracking ID. |
| `addedTrackedBarcodes` | `Array<TrackedBarcode>` | Barcodes newly tracked in this frame. |
| `updatedTrackedBarcodes` | `Array<TrackedBarcode>` | Barcodes whose position changed in this frame. |
| `removedTrackedBarcodes` | `Array<Int>` | Tracking IDs of barcodes that left the view. |
| `frameSequenceId` | `Int` | Identifier of the current frame sequence. |
| `reset()` | — | Clear all tracked state (call only from within the callback). |

> **Important**: Do not hold references to `trackedBarcodes`, `addedTrackedBarcodes`, `updatedTrackedBarcodes`, or `removedTrackedBarcodes` outside `barcodeBatch(_:didUpdate:frameData:)`. Copy the data you need before the callback returns. Individual `TrackedBarcode` instances can be safely retained.

### TrackedBarcode Properties

| Property | Description |
|----------|-------------|
| `barcode` | The decoded `Barcode`. Access `.data`, `.symbology`, etc. |
| `identifier` | `Int` — unique tracking ID. Reused after the barcode leaves the frame. |
| `location` | `Quadrilateral` — barcode position in image-space coordinates. |

## Step 8 — Lifecycle management

Drive the camera and `isEnabled` flag from `viewWillAppear` and `viewWillDisappear`. Remove the listener in `deinit` to make the lifecycle explicit (listeners are weakly held, so missing this won't leak, but it is best practice).

```swift
override func viewWillAppear(_ animated: Bool) {
    super.viewWillAppear(animated)
    barcodeBatch.isEnabled = true
    camera?.switch(toDesiredState: .on)
}

override func viewWillDisappear(_ animated: Bool) {
    super.viewWillDisappear(animated)
    barcodeBatch.isEnabled = false
    camera?.switch(toDesiredState: .off)
}

deinit {
    barcodeBatch.removeListener(self)
}
```

> When using the shared singleton (`DataCaptureContext.shared`), modes stay attached for the app's lifetime — removing the listener is the only cleanup needed. `DataCaptureContext` does expose `removeCurrentMode()`, `removeMode(_:)`, and `dispose()` if explicit teardown is required; the singleton flow simply doesn't need them.

## Complete minimal example (UIKit)

```swift
import ScanditBarcodeCapture
import UIKit

class ScanViewController: UIViewController {

    private lazy var context: DataCaptureContext = {
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()
    private var camera: Camera?
    private var barcodeBatch: BarcodeBatch!
    private var captureView: DataCaptureView!
    private var overlay: BarcodeBatchBasicOverlay!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRecognition()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        barcodeBatch.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        barcodeBatch.isEnabled = false
        camera?.switch(toDesiredState: .off)
    }

    deinit {
        barcodeBatch.removeListener(self)
    }

    private func setupRecognition() {
        camera = Camera.default
        context.setFrameSource(camera, completionHandler: nil)

        let cameraSettings = BarcodeBatch.recommendedCameraSettings
        camera?.apply(cameraSettings, completionHandler: nil)

        let settings = BarcodeBatchSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .code128, enabled: true)

        barcodeBatch = BarcodeBatch(context: context, settings: settings)
        barcodeBatch.addListener(self)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)

        overlay = BarcodeBatchBasicOverlay(barcodeBatch: barcodeBatch, view: captureView)
    }
}

extension ScanViewController: BarcodeBatchListener {

    func barcodeBatch(
        _ barcodeBatch: BarcodeBatch,
        didUpdate session: BarcodeBatchSession,
        frameData: FrameData
    ) {
        let addedData = session.addedTrackedBarcodes.compactMap { $0.barcode.data }
        DispatchQueue.main.async {
            for data in addedData {
                _ = data
            }
        }
    }
}
```

## Optional: BarcodeBatchAdvancedOverlay (requires MatrixScan AR add-on)

`BarcodeBatchAdvancedOverlay` anchors a custom `UIView` to each tracked barcode in real time. The convenience initializer auto-adds the overlay to the data capture view.

```swift
private var advancedOverlay: BarcodeBatchAdvancedOverlay!

// In setupRecognition(), after creating captureView:
advancedOverlay = BarcodeBatchAdvancedOverlay(barcodeBatch: barcodeBatch, view: captureView)
advancedOverlay.delegate = self
```

```swift
extension ScanViewController: BarcodeBatchAdvancedOverlayDelegate {

    func barcodeBatchAdvancedOverlay(
        _ overlay: BarcodeBatchAdvancedOverlay,
        viewFor trackedBarcode: TrackedBarcode
    ) -> UIView? {
        let label = UILabel()
        label.text = trackedBarcode.barcode.data
        label.backgroundColor = .white
        label.sizeToFit()
        return label
    }

    func barcodeBatchAdvancedOverlay(
        _ overlay: BarcodeBatchAdvancedOverlay,
        anchorFor trackedBarcode: TrackedBarcode
    ) -> Anchor {
        return .topCenter
    }

    func barcodeBatchAdvancedOverlay(
        _ overlay: BarcodeBatchAdvancedOverlay,
        offsetFor trackedBarcode: TrackedBarcode
    ) -> PointWithUnit {
        return PointWithUnit(
            x: FloatWithUnit(value: 0, unit: .fraction),
            y: FloatWithUnit(value: -1, unit: .fraction)
        )
    }
}
```

All three advanced-overlay delegate methods are called on the **main thread**.

To update the view for a specific barcode imperatively (e.g. after a data lookup):
```swift
advancedOverlay.setView(updatedView, for: trackedBarcode)
advancedOverlay.setAnchor(.topCenter, for: trackedBarcode)
advancedOverlay.setOffset(offset, for: trackedBarcode)
advancedOverlay.clearTrackedBarcodeViews() // remove all views
```

### BarcodeBatchAdvancedOverlay Members

| Member | Description |
|--------|-------------|
| `init(barcodeBatch:view:)` | Convenience init — auto-adds the overlay to the view. |
| `delegate` | `BarcodeBatchAdvancedOverlayDelegate?` |
| `setView(_:for:)` | Set or update the `UIView` for a barcode. Pass `nil` to remove. Thread-safe. |
| `setAnchor(_:for:)` | Override the anchor for a barcode. Thread-safe. |
| `setOffset(_:for:)` | Override the offset for a barcode. Thread-safe. |
| `clearTrackedBarcodeViews()` | Remove all anchored views. |
| `shouldShowScanAreaGuides` | Debug: show the active scan area. |

Imperatively set values (`setView`/`setAnchor`/`setOffset`) take precedence over delegate callbacks — if a value has been set imperatively, the delegate method is not called.

> For additional listener methods or tap handling, fetch the [Adding AR Overlays](https://docs.scandit.com/sdks/ios/matrixscan/advanced/) page.

## SwiftUI

`DataCaptureView` is a `UIView` — it cannot be dropped into SwiftUI directly. Wrap the scanning view controller in a `UIViewControllerRepresentable` and keep every BarcodeBatch API call (context, mode, settings, view, lifecycle) **inside the wrapped UIKit view controller**. Mixing BarcodeBatch APIs into a SwiftUI `View` struct breaks the SDK's view lifecycle expectations.

> The Scandit SwiftUI Get Started page also documents a `UIViewRepresentable` + `Coordinator` alternative, where the coordinator owns the SDK objects directly. Prefer the `UIViewControllerRepresentable` pattern below — it keeps the UIKit lifecycle (`viewWillAppear` / `viewWillDisappear` / `deinit`) intact and the same view controller works when reused from UIKit. Only fall back to the coordinator pattern if the project already has a strong reason to.

Canonical shape:

```swift
import SwiftUI
import ScanditBarcodeCapture

struct ScanView: View {
    var body: some View {
        ScanViewControllerRepresentable()
            .edgesIgnoringSafeArea(.all)
    }
}

struct ScanViewControllerRepresentable: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> ScanViewController {
        ScanViewController()
    }

    func updateUIViewController(_ uiViewController: ScanViewController, context: Context) {}
}
```

`ScanViewController` is the exact UIKit class from the minimal example above — no changes. The SwiftUI `View` struct contains no Scandit code.

### SwiftUI cleanup

The view controller's `viewWillAppear` / `viewWillDisappear` / `deinit` still fire when SwiftUI presents and dismisses the representable, so the UIKit lifecycle code carries over unchanged — no extra SwiftUI-side teardown is required. When SwiftUI removes the representable from the view tree, it releases its strong reference to `ScanViewController`, which triggers `deinit` and the `removeListener` call.

If you need to react to SwiftUI-side teardown explicitly (e.g. to stop a related service), implement the static `dismantleUIViewController` on the representable:

```swift
struct ScanViewControllerRepresentable: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> ScanViewController {
        ScanViewController()
    }

    func updateUIViewController(_ uiViewController: ScanViewController, context: Context) {}

    static func dismantleUIViewController(_ uiViewController: ScanViewController, coordinator: ()) {
        // Optional: extra teardown beyond what the view controller's deinit handles.
    }
}
```

Do not move `removeListener` or camera-off calls out of the view controller into `dismantleUIViewController` — keep BarcodeBatch lifecycle inside the UIKit class so the same view controller works when used directly from UIKit.

## Key Rules

1. **Convenience initializer, not factory** — `BarcodeBatch(context: context, settings: settings)` is a direct convenience initializer. Passing a non-nil context attaches the mode to the context.
2. **Manual camera** — `Camera.default`, then `context.setFrameSource(camera, completionHandler: nil)` and `camera?.apply(BarcodeBatch.recommendedCameraSettings, completionHandler: nil)`. Drive on/off from `viewWillAppear`/`viewWillDisappear`.
3. **Background queue** — `barcodeBatch(_:didUpdate:frameData:)` runs off the main thread. Copy the data you need, then `DispatchQueue.main.async {}` for UI work.
4. **Don't hold session references** — `trackedBarcodes`, `addedTrackedBarcodes`, `updatedTrackedBarcodes`, `removedTrackedBarcodes` are only safe within the callback. Copy data before the callback returns.
5. **Overlay auto-adds** — `BarcodeBatchBasicOverlay(barcodeBatch:view:)` and `BarcodeBatchAdvancedOverlay(barcodeBatch:view:)` both add themselves to the `DataCaptureView` automatically.
6. **DataCaptureView is manual** — call `view.addSubview(captureView)` yourself; unlike `BarcodeArView`, `DataCaptureView` does not auto-attach.
7. **AR add-on required** — per-barcode brush customization (the `brushFor` delegate, `setBrush(_:for:)`) and `BarcodeBatchAdvancedOverlay` both require the MatrixScan AR add-on license.
8. **isEnabled for pause/resume** — toggle `barcodeBatch.isEnabled` to pause and resume tracking without tearing down the camera.
9. **Cleanup** — call `barcodeBatch.removeListener(self)` in `deinit`. Listeners are weakly held, so this is best practice, not a leak prevention. When using the shared singleton, modes stay attached for the app's lifetime — no extra teardown is required. `removeCurrentMode()` / `dispose()` exist on `DataCaptureContext` if you want explicit teardown. In SwiftUI, the wrapped view controller's `deinit` fires when the representable is removed.
10. **Symbologies** — all disabled by default; enable only what is needed. Cases are camelCase: `.ean13UPCA`, `.code128`, `.qr`.
11. **Camera permission** — add `NSCameraUsageDescription` to `Info.plist`. iOS shows the permission prompt automatically when the camera first starts.
