# BarcodeCapture iOS Integration Guide

BarcodeCapture is the low-level single-barcode scanning mode. Unlike SparkScan, there is no pre-built UI — you wire up a `DataCaptureContext`, a `Camera` frame source, the `BarcodeCapture` mode with a `BarcodeCaptureListener`, a `DataCaptureView` for the preview, and a `BarcodeCaptureOverlay` for the highlight.

## Prerequisites

- Scandit Data Capture SDK for iOS — add via Swift Package Manager:
  - URL: `https://github.com/Scandit/datacapture-spm`
  - Add `ScanditBarcodeCapture` and `ScanditCaptureCore` package products to your target
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test
- `NSCameraUsageDescription` in `Info.plist`

## Minimal Integration (Swift)

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which file or view controller they'd like to integrate BarcodeCapture into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `ScanditBarcodeCapture` and `ScanditCaptureCore` via Swift Package Manager: `https://github.com/Scandit/datacapture-spm`
2. Make sure you have `NSCameraUsageDescription` added to your `Info.plist`
3. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com

The code example below is for UIKit. If the user is using SwiftUI, use the SwiftUI get-started guide and sample instead (see References in SKILL.md).

```swift
import UIKit
import ScanditBarcodeCapture

class ViewController: UIViewController {

    private lazy var context: DataCaptureContext = {
        // Enter your Scandit License key here.
        // Your Scandit License key is available via your Scandit SDK web account.
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()

    private var camera: Camera?
    private var barcodeCapture: BarcodeCapture!
    private var captureView: DataCaptureView!
    private var overlay: BarcodeCaptureOverlay!

    override func viewDidLoad() {
        super.viewDidLoad()

        camera = Camera.default
        camera?.apply(BarcodeCapture.recommendedCameraSettings)
        context.setFrameSource(camera)

        let settings = BarcodeCaptureSettings()
        Set<Symbology>([.ean13UPCA, .code128]).forEach {
            settings.set(symbology: $0, enabled: true)
        }

        barcodeCapture = BarcodeCapture(context: context, settings: settings)
        barcodeCapture.addListener(self)

        captureView = DataCaptureView(context: context, frame: view.bounds)
        captureView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(captureView)

        overlay = BarcodeCaptureOverlay(barcodeCapture: barcodeCapture, view: captureView)
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
}

extension ViewController: BarcodeCaptureListener {
    func barcodeCapture(_ barcodeCapture: BarcodeCapture,
                        didScanIn session: BarcodeCaptureSession,
                        frameData: FrameData) {
        guard let barcode = session.newlyRecognizedBarcode else { return }
        DispatchQueue.main.async {
            print("Scanned: \(barcode.data ?? "")")
            // Handle the barcode here.
        }
    }
}
```

## Optional configuration

All of the following are applied to the `BarcodeCaptureSettings` instance (before `BarcodeCapture(context:settings:)`, or re-applied later with `barcodeCapture.apply(settings, completionHandler:)`) or to the `BarcodeCaptureOverlay`. Use the exact Swift APIs below — many per-symbology options live on `SymbologySettings`, obtained via `settings.settings(for:)`, not directly on `BarcodeCaptureSettings`.

### Per-symbology settings

`settings.settings(for:)` returns a mutable `SymbologySettings` for one symbology. Mutate it, then apply the parent `settings`.

```swift
let symbologySettings = settings.settings(for: .code39)

// Symbology extensions (e.g. Code 39 full ASCII). Pass the extension name as a String.
symbologySettings.set(extension: "full_ascii", enabled: true)

// Optional checksums. `checksums` is a Checksum OptionSet — assign with an array literal.
symbologySettings.checksums = [.mod43]

// Active symbol counts (variable-length 1D codes). Type is Set<Int>.
settings.settings(for: .code128).activeSymbolCounts = Set(7...20)

// Color-inverted (light-on-dark) codes. This is a PER-SYMBOLOGY setting.
settings.settings(for: .qr).isColorInvertedEnabled = true
```

### Viewfinders

Assign a viewfinder to the overlay's `viewfinder` property (the overlay is created with `BarcodeCaptureOverlay(barcodeCapture:view:)`).

```swift
overlay.viewfinder = AimerViewfinder()      // target dot to aim at
overlay.viewfinder = LaserlineViewfinder()  // horizontal line for long 1D codes
```

### Overlay highlight brush

The brush draws recognized barcodes. `Brush(fill:stroke:strokeWidth:)` takes `UIColor` fill, `UIColor` stroke, and a `CGFloat` width.

```swift
overlay.brush = Brush(fill: UIColor.green.withAlphaComponent(0.2),
                      stroke: UIColor.green,
                      strokeWidth: 2)
```

### Rejecting barcodes

There is no `session.rejectBarcodes(...)` API. To reject codes whose data does not match, do the check inside `didScanIn`: set the overlay brush to `Brush.transparent` so the non-matching code is not highlighted, and `return` early before handling it.

**`overlay.brush` is overlay-wide, not per-barcode.** `BarcodeCapture` has no per-barcode brush delegate (unlike MatrixScan). Once you set the brush to transparent it stays transparent for *every* subsequent code — including matching ones — until you set it back. So in continuous scanning you MUST restore the brush on the accept path, e.g. `overlay.brush = BarcodeCaptureOverlay.defaultBrush`, or the preview goes permanently blank after the first rejected code.

**Rejection only hides the highlight — it does not mute feedback.** A rejected code is still recognized, so the default beep/vibration still fires. If "reject" should also be silent, mute feedback as well: `barcodeCapture.feedback.success = Feedback(vibration: nil, sound: nil)`. Decide which you want: suppress *only* the highlight (below), or true silent filtering (highlight + feedback both off).

```swift
func barcodeCapture(_ barcodeCapture: BarcodeCapture,
                    didScanIn session: BarcodeCaptureSession,
                    frameData: FrameData) {
    guard let barcode = session.newlyRecognizedBarcode,
          let data = barcode.data else { return }

    guard data.hasPrefix("978") else {
        // Reject: hide the highlight and stop.
        overlay.brush = Brush.transparent
        return
    }

    // Accept: restore the default highlight so matching codes stay visible.
    overlay.brush = BarcodeCaptureOverlay.defaultBrush

    DispatchQueue.main.async {
        // Handle the accepted barcode here.
    }
}
```

### Composite codes

Enabling composite codes requires BOTH steps: set `enabledCompositeTypes`, and call `enableSymbologies(forCompositeTypes:)` to turn on the underlying symbologies. Setting `enabledCompositeTypes` alone is not sufficient. `CompositeType` is an OptionSet (`.a`, `.b`, `.c`).

```swift
settings.enabledCompositeTypes = [.a, .b]
settings.enableSymbologies(forCompositeTypes: [.a, .b])
```

For other advanced configuration (custom feedback, duplicate filtering, location selection), see the Advanced Configurations and API reference linked from SKILL.md.
