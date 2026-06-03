# SparkScan iOS Integration Guide

SparkScan is a pre-built scanning UI for high-volume single-scanning workflows. It overlays a trigger button on top of any screen so users can scan without leaving their workflow.

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

### Where to integrate SparkScan

**Integrate SparkScan into the app's existing view — do not create a new, separate view or screen for it.** SparkScan is an overlay: it floats a trigger button on top of whatever screen the user is on, so it belongs *inside* the view the user already has, not in a dedicated scanning screen. Adding a separate view controller (or SwiftUI `View`) just for SparkScan is the most common integration mistake — avoid it.

Decide the target view before writing any code:

1. **The user named a file or view** (in the prompt, or it's the file they have open) → integrate there.
2. **No view named, but the target is obvious from the codebase** — e.g. there is a single main view controller, or one obvious `ContentView` / screen where scanning belongs → integrate into that existing view.
3. **Ambiguous** — several candidate views and no clear signal which one → **ask the user which existing view they want SparkScan added to.** Do not guess, and do not fall back to creating a new view.

Then write the integration code **directly into that existing file**, merging it with what's already there: keep the existing properties, `@IBOutlet`s, lifecycle methods, and other UI, and add the SparkScan context, mode, view, and listener alongside them. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `ScanditBarcodeCapture` and `ScanditCaptureCore` via Swift Package Manager: `https://github.com/Scandit/datacapture-spm`
2. Make sure you have `NSCameraUsageDescription` added to your `Info.plist`
3. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com

The code example below is for UIKit and shows the SparkScan pieces in isolation — merge these into the user's existing view controller rather than replacing it or adding a new one. If the user is using SwiftUI, integrate SparkScan into their existing view (for example `ContentView`) and use the SwiftUI get-started guide and sample for the specifics (see References) — do not create a new SwiftUI view for scanning.

```swift
import ScanditBarcodeCapture

class ViewController: UIViewController {

    private lazy var context = {
        // Enter your Scandit License key here.
        // Your Scandit License key is available via your Scandit SDK web account.
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()

    private lazy var sparkScan: SparkScan = {
        let settings = SparkScanSettings()
        Set<Symbology>([.ean8, .ean13UPCA, .upce, .code39, .code128, .interleavedTwoOfFive]).forEach {
            settings.set(symbology: $0, enabled: true)
        }
        settings.settings(for: .code39).activeSymbolCounts = Set(7...20)

        let mode = SparkScan(settings: settings)
        return mode
    }()

    private var sparkScanView: SparkScanView!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRecognition()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        sparkScanView.prepareScanning()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        sparkScanView.stopScanning()
    }

    private func setupRecognition() {
        sparkScan.addListener(self)
        sparkScanView = SparkScanView(
            parentView: view,
            context: context,
            sparkScan: sparkScan,
            settings: SparkScanViewSettings()
        )
    }
}

extension ViewController: SparkScanListener {
    func sparkScan(_ sparkScan: SparkScan, didScanIn session: SparkScanSession, frameData: FrameData?) {
        guard let barcode = session.newlyRecognizedBarcode, let data = barcode.data else { return }
        DispatchQueue.main.async {
            print("Scanned barcode - \(data)")
            // Handle the barcode
        }
    }
}
```
