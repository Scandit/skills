# BarcodeCapture iOS Integration Guide

BarcodeCapture is the low-level single-barcode scanning mode. On iOS you wire it up by hand: a `DataCaptureContext`, a `Camera` as the frame source, the `BarcodeCapture` mode with a `BarcodeCaptureListener`, a `DataCaptureView` for the camera preview, and a `BarcodeCaptureOverlay` for the highlight. Unlike SparkScan, there is no pre-built UI — the camera preview and highlight rectangle are the only visuals.

Examples below use Swift and a `UIViewController`. The same APIs work in SwiftUI via a `UIViewControllerRepresentable` bridge — see the SwiftUI Get Started link in SKILL.md when the project is SwiftUI.

## Prerequisites

- Scandit Data Capture SDK for iOS — add via Swift Package Manager:
  - URL: `https://github.com/Scandit/datacapture-spm`
  - Add `ScanditBarcodeCapture` and `ScanditCaptureCore` package products to your target.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- `NSCameraUsageDescription` in `Info.plist` — the camera will not start without it.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which file or view controller they'd like to integrate BarcodeCapture into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `ScanditBarcodeCapture` and `ScanditCaptureCore` via Swift Package Manager: `https://github.com/Scandit/datacapture-spm`.
2. Make sure you have `NSCameraUsageDescription` added to your `Info.plist`.
3. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.

## Step 1 — Create the DataCaptureContext

The `DataCaptureContext` is the central hub of the SDK. From v7 onwards the recommended pattern is to call `DataCaptureContext.initialize(licenseKey:)` once at app start (or lazily on first use), then read `DataCaptureContext.shared` everywhere else.

```swift
import ScanditBarcodeCapture

DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
let context = DataCaptureContext.shared
```

Do not use the bare `DataCaptureContext(licenseKey:)` constructor — that is the v6 form and is deprecated.

## Step 2 — Configure BarcodeCaptureSettings

Choose which barcode symbologies to scan. By default, all symbologies are disabled — enable each one explicitly. Only enable what you need; each extra symbology adds processing time.

```swift
let settings = BarcodeCaptureSettings()
settings.set(symbology: .ean13UPCA, enabled: true)
settings.set(symbology: .ean8, enabled: true)
settings.set(symbology: .upce, enabled: true)
settings.set(symbology: .code39, enabled: true)
settings.set(symbology: .code128, enabled: true)

// Optional: adjust active symbol counts for variable-length symbologies
settings.settings(for: .code39).activeSymbolCounts = Set(7...20)
```

You can also enable a `Set<Symbology>` in one call:
```swift
settings.enableSymbologies([.ean13UPCA, .code128])
```

### BarcodeCaptureSettings Members

| Member | Type | Description |
|--------|------|-------------|
| `set(symbology:enabled:)` | method | Enable or disable one symbology. |
| `enableSymbologies(_:)` | method | Enable a `Set<Symbology>` in one call. |
| `settings(for:)` | method | Get per-symbology `SymbologySettings` (e.g. `activeSymbolCounts`). |
| `codeDuplicateFilter` | `TimeInterval` (seconds) | Time window to suppress duplicate scans of the same code (e.g. `0.5` = 500 ms). `0` reports every detection; `-1` reports each code only once until scanning stops; `-2` (default) uses smart filtering based on `scanIntention`. |

## Step 3 — Camera setup

`BarcodeCapture.recommendedCameraSettings` is a static property returning the recommended `CameraSettings` for BarcodeCapture. Attach the camera to the context via `setFrameSource(_:)`.

```swift
let camera = Camera.default
camera?.apply(BarcodeCapture.recommendedCameraSettings)
context.setFrameSource(camera)
```

Switch the camera on / off:

```swift
camera?.switch(toDesiredState: .on)   // start preview / scanning
camera?.switch(toDesiredState: .off)  // release the camera
```

## Step 4 — Create the BarcodeCapture mode

```swift
let barcodeCapture = BarcodeCapture(context: context, settings: settings)
```

Re-applying settings at runtime is done via `barcodeCapture.apply(settings)`.

### BarcodeCapture Members

| Member | Description |
|--------|-------------|
| `init(context:settings:)` | Designated constructor — creates the mode and attaches it to the context. |
| `isEnabled` | Pause / resume scanning without tearing down the camera. |
| `feedback` | `BarcodeCaptureFeedback` — sound / vibration on success. |
| `apply(_:)` | Update `BarcodeCaptureSettings` at runtime. |
| `addListener(_:)` / `removeListener(_:)` | Register or remove a `BarcodeCaptureListener`. |
| `BarcodeCapture.recommendedCameraSettings` | Static property — returns the recommended `CameraSettings`. |

## Step 5 — DataCaptureView and BarcodeCaptureOverlay

`DataCaptureView(context:frame:)` creates the camera preview. Add it as a subview of the view controller's root view. `BarcodeCaptureOverlay(barcodeCapture:view:)` adds the highlight overlay to the view.

```swift
let captureView = DataCaptureView(context: context, frame: view.bounds)
captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
view.addSubview(captureView)

let overlay = BarcodeCaptureOverlay(barcodeCapture: barcodeCapture, view: captureView)
```

### BarcodeCaptureOverlay Members

| Member | Description |
|--------|-------------|
| `init(barcodeCapture:view:)` | Designated constructor — creates the overlay and adds it to the view. |
| `brush` | `Brush` — fill / stroke for recognized-barcode highlights. |
| `viewfinder` | `Viewfinder?` — optional viewfinder drawn on the preview. |

## Step 6 — Implement BarcodeCaptureListener

Conform to `BarcodeCaptureListener` on the view controller or a dedicated controller class.

```swift
extension ViewController: BarcodeCaptureListener {
    func barcodeCapture(_ barcodeCapture: BarcodeCapture,
                        didScanIn session: BarcodeCaptureSession,
                        frameData: FrameData) {
        guard let barcode = session.newlyRecognizedBarcode else { return }

        // Disable while we handle the scan, so duplicates don't fire.
        barcodeCapture.isEnabled = false

        // didScanIn is called on a background thread — dispatch UI work.
        DispatchQueue.main.async {
            // Handle the barcode: barcode.data, barcode.symbology
        }
    }
}

barcodeCapture.addListener(self)
```

### BarcodeCaptureListener Protocol

| Callback | Description |
|----------|-------------|
| `barcodeCapture(_:didScanIn:frameData:)` | A barcode was recognized. Read it from `session.newlyRecognizedBarcode`. Called on a background thread. |
| `barcodeCapture(_:didUpdate:frameData:)` | Called for every processed frame. Keep work minimal. Optional. |

### BarcodeCaptureSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `newlyRecognizedBarcode` | `Barcode?` | The barcode just scanned. |
| `newlyLocalizedBarcodes` | `[LocalizedOnlyBarcode]` | Codes that were located but not decoded. |
| `frameSequenceId` | `Int` | Identifier of the current frame sequence. |

## Step 7 — Lifecycle management

Drive the camera from `viewWillAppear` and `viewWillDisappear`. The camera must not be active while the screen is off-screen or the app is backgrounded.

```swift
override func viewWillAppear(_ animated: Bool) {
    super.viewWillAppear(animated)
    barcodeCapture.isEnabled = true
    camera?.switch(toDesiredState: .on)
}

override func viewWillDisappear(_ animated: Bool) {
    super.viewWillDisappear(animated)
    barcodeCapture.isEnabled = false
    camera?.switch(toDesiredState: .off)
}

deinit {
    barcodeCapture.removeListener(self)
    context.removeCurrentMode()
}
```

## Complete minimal example

```swift
import UIKit
import ScanditBarcodeCapture

class BarcodeScanViewController: UIViewController {

    private lazy var context: DataCaptureContext = {
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()

    private var camera: Camera?
    private var barcodeCapture: BarcodeCapture!
    private var captureView: DataCaptureView!

    override func viewDidLoad() {
        super.viewDidLoad()

        camera = Camera.default
        camera?.apply(BarcodeCapture.recommendedCameraSettings)
        context.setFrameSource(camera)

        let settings = BarcodeCaptureSettings()
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .code128, enabled: true)

        barcodeCapture = BarcodeCapture(context: context, settings: settings)
        barcodeCapture.addListener(self)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)

        _ = BarcodeCaptureOverlay(barcodeCapture: barcodeCapture, view: captureView)
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        barcodeCapture.isEnabled = true
        camera?.switch(toDesiredState: .on)
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        barcodeCapture.isEnabled = false
        camera?.switch(toDesiredState: .off)
    }

    deinit {
        barcodeCapture.removeListener(self)
        context.removeCurrentMode()
    }
}

extension BarcodeScanViewController: BarcodeCaptureListener {
    func barcodeCapture(_ barcodeCapture: BarcodeCapture,
                        didScanIn session: BarcodeCaptureSession,
                        frameData: FrameData) {
        guard let barcode = session.newlyRecognizedBarcode else { return }
        barcodeCapture.isEnabled = false
        DispatchQueue.main.async {
            // handle barcode.data and barcode.symbology
        }
    }
}
```

## Optional configuration

### Async work after a scan

When the scan result requires a network or database call, disable scanning immediately on the scanner thread, then perform the async work on the main thread. Re-enable in a way that guarantees scanning resumes even if the lookup fails (e.g. using `defer` or completion-handler `finally`-style cleanup).

```swift
func barcodeCapture(_ barcodeCapture: BarcodeCapture,
                    didScanIn session: BarcodeCaptureSession,
                    frameData: FrameData) {
    guard let data = session.newlyRecognizedBarcode?.data else { return }
    barcodeCapture.isEnabled = false  // prevent duplicate scans while lookup is in flight

    Task { @MainActor in
        defer { barcodeCapture.isEnabled = true }
        do {
            let result = try await lookUpProduct(data)
            // update UI with result — already on the main actor
        } catch {
            // surface the error to the user
        }
    }
}
```

If the project is pre-async/await, use `URLSession` with a completion handler and re-enable scanning inside the completion:
```swift
URLSession.shared.dataTask(with: url) { _, _, _ in
    DispatchQueue.main.async {
        barcodeCapture.isEnabled = true
    }
}.resume()
```

### BarcodeCaptureFeedback

By default, BarcodeCapture beeps and vibrates on success. To customize feedback, mutate the `success` property of `barcodeCapture.feedback`:

```swift
// Suppress all feedback (silent mode):
barcodeCapture.feedback.success = Feedback(vibration: nil, sound: nil)

// Restore default success feedback:
barcodeCapture.feedback.success = Feedback.default
```

For more granular per-result feedback, fetch the BarcodeCapture API reference — the exact `Feedback` constructor arguments need to be verified against the docs.

### Viewfinder

Attach a viewfinder to the overlay to draw a guide on the preview. `RectangularViewfinder(style:)` accepts a `RectangularViewfinderStyle`:

```swift
overlay.viewfinder = RectangularViewfinder(style: .square)
```

### CodeDuplicateFilter

Suppress duplicate scans of the same code within a time window. The value is a `TimeInterval` measured in **seconds** (Swift `Double`). `-1` reports each code only once until scanning is stopped; `0` reports every detection; `-2` (the default) uses smart filtering based on `scanIntention`.

```swift
settings.codeDuplicateFilter = 0.5  // suppress duplicates within 500 ms
```

Set this before constructing `BarcodeCapture(context:settings:)`. To change at runtime, use `barcodeCapture.apply(newSettings)`.

### LocationSelection

To restrict scanning to a sub-area of the preview, fetch the [BarcodeCapture API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html) for the `RectangularLocationSelection` API — the exact constructor needs to be verified against the live docs.

### Composite codes

Composite codes (linear + 2D companion) require both symbologies and composite types to be enabled. `BarcodeCaptureSettings.enableSymbologies(forCompositeTypes:)` is the entry point — fetch the API reference for the exact `CompositeType` values.

## Key Rules

1. **One context per app session** — call `DataCaptureContext.initialize(licenseKey:)` once and reuse `DataCaptureContext.shared`.
2. **Constructor wires the mode** — `BarcodeCapture(context:settings:)` both creates the mode and attaches it to the context.
3. **Listener thread** — `barcodeCapture(_:didScanIn:frameData:)` runs on a background thread; always dispatch UI work via `DispatchQueue.main.async`.
4. **Disable inside didScanIn** — set `barcodeCapture.isEnabled = false` before doing any non-trivial work to avoid duplicate scans.
5. **Camera lifecycle** — turn the camera off in `viewWillDisappear`, back on in `viewWillAppear`. Call `context.removeCurrentMode()` in `deinit`.
6. **Overlay is explicit** — `BarcodeCaptureOverlay(barcodeCapture:view:)` adds the overlay to the view in one step. There is no implicit overlay.
7. **`NSCameraUsageDescription`** — add it to `Info.plist`; iOS will not start the camera otherwise.
8. **Symbologies** — enable only what's needed. Variable-length 1D symbologies (Code39, Code128, ITF) may need `activeSymbolCounts` adjusted.
9. **Settings before construction** — configure `BarcodeCaptureSettings` before passing to `BarcodeCapture(context:settings:)`. To change at runtime, use `barcodeCapture.apply(newSettings)`.
