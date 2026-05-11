# MatrixScan AR iOS Integration Guide

MatrixScan AR is a pre-built AR scanning component that detects multiple barcodes simultaneously and overlays visual feedback (highlights and annotations) on top of each one. This guide covers the scanning pipeline only — the AR layer (highlights, annotations) is handled by the sibling skills `matrixscan-ar-highlight-ios` and `matrixscan-ar-annotation-ios`.

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

Once the user responds, ask them which file or view controller they'd like to integrate MatrixScan AR into. Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `ScanditBarcodeCapture` and `ScanditCaptureCore` via Swift Package Manager: `https://github.com/Scandit/datacapture-spm`
2. Make sure you have `NSCameraUsageDescription` added to your `Info.plist`
3. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com

The code example below is adapted from the official `MatrixScanARSimpleSample` (UIKit). If the user is using SwiftUI, use the SwiftUI get-started guide and sample instead (see References in SKILL.md).

```swift
import ScanditBarcodeCapture

class ScanViewController: UIViewController {
    private lazy var context = {
        // Enter your Scandit License key here.
        // Your Scandit License key is available via your Scandit SDK web account.
        DataCaptureContext.initialize(licenseKey: "-- ENTER YOUR SCANDIT LICENSE KEY HERE --")
        return DataCaptureContext.shared
    }()
    private var barcodeAr: BarcodeAr!
    private var barcodeArView: BarcodeArView!

    override func viewDidLoad() {
        super.viewDidLoad()
        setupRecognition()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        barcodeArView.start()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        barcodeArView.stop()
    }

    func setupRecognition() {
        // Configure the Barcode AR settings.
        let settings = BarcodeArSettings()

        // The settings instance initially has all symbologies disabled. Enable only the ones the app actually
        // needs — every additional enabled symbology has an impact on processing times. Replace the set below
        // with the user's chosen symbologies.
        settings.set(symbology: .ean13UPCA, enabled: true)
        settings.set(symbology: .ean8, enabled: true)
        settings.set(symbology: .upce, enabled: true)
        settings.set(symbology: .code39, enabled: true)
        settings.set(symbology: .code128, enabled: true)
        settings.set(symbology: .qr, enabled: true)
        settings.set(symbology: .dataMatrix, enabled: true)

        // Create BarcodeAr instance.
        barcodeAr = BarcodeAr(context: context, settings: settings)

        // Create and configure BarcodeArView with default view settings.
        let viewSettings = BarcodeArViewSettings()

        // Use the recommended camera settings for the BarcodeAr mode.
        let recommendedCameraSettings = BarcodeAr.recommendedCameraSettings

        // To visualize the on-going Barcode AR process on screen, setup a Barcode AR view that renders the
        // camera preview and the Barcode AR UI. The view is automatically added to the parent view hierarchy.
        barcodeArView = BarcodeArView(
            parentView: view,
            barcodeAr: barcodeAr,
            settings: viewSettings,
            cameraSettings: recommendedCameraSettings
        )
    }
}
```

> The official sample passes an `@IBOutlet weak var containerView: UIView!` as `parentView`. Use whichever container the user's screen actually has — `view` is fine for a full-screen scanner, a container outlet is fine for an embedded scanner inside a larger layout.

## What the code does (and what it does NOT do)

- Creates the `DataCaptureContext` singleton via `DataCaptureContext.initialize(licenseKey:)` + `.shared`.
- Builds a `BarcodeAr` mode with the user's chosen symbologies.
- Creates a `BarcodeArView` with the recommended camera settings. The view is added into `parentView` automatically — do not `addSubview` it yourself.
- Starts/stops the view in `viewWillAppear` / `viewWillDisappear`.

What this code does **not** do:
- It does not install a **highlight provider**. Without a `BarcodeArHighlightProvider`, the SDK draws default highlights. Customizing them is the `matrixscan-ar-highlight-ios` skill's scope.
- It does not install an **annotation provider**. Without a `BarcodeArAnnotationProvider`, no annotations appear. Attaching info cards, status icons, or popovers is the `matrixscan-ar-annotation-ios` skill's scope.
- It does not install a **`BarcodeArListener`**. In a typical MatrixScan AR app the output flows through the highlight and annotation providers — you rarely need the raw session. If the user specifically wants per-frame session data (list of tracked barcodes etc.), conform the view controller to `BarcodeArListener` and call `barcodeAr.addListener(self)` after constructing the mode; the callback is `barcodeAr(_:didUpdate:frameData:)` and it fires on a background queue, so dispatch to the main queue before touching UIKit.

If the user asks for highlights, annotations, or a listener in the same turn, wire up the scanning pipeline first and then tell them which sibling skill or follow-up step handles the rest.

## Symbology fine-tuning

For variable-length symbologies (Code 39, Code 128, Interleaved 2 of 5, etc.) the user often wants to restrict the accepted lengths. For other symbologies they may need color-inverted decoding or specific checksums. Access the per-symbology settings via `BarcodeArSettings.settings(for:)`:

```swift
settings.settings(for: .code39).activeSymbolCounts = Set(7...20)
settings.settings(for: .code128).isColorInvertedEnabled = true
```

Every property in this section lives on `SymbologySettings` — `activeSymbolCounts: Set<Int>`, `isColorInvertedEnabled: Bool`, `checksums: [Checksum]`, `enabledExtensions: Set<String>`. Apply them on the `BarcodeArSettings` **before** constructing `BarcodeAr`, or on the live mode via `barcodeAr.apply(_:)` after the fact if the user wants to reconfigure at runtime.

## Camera settings

The minimal example uses `BarcodeAr.recommendedCameraSettings` — a ready-made `CameraSettings` tuned for AR scanning. If the user needs to change specific knobs (resolution, zoom, focus, torch level, macro, adaptive exposure), start from the recommended settings and override only what's asked for:

```swift
let cameraSettings = BarcodeAr.recommendedCameraSettings
cameraSettings.preferredResolution = .uhd4k
cameraSettings.zoomFactor = 2.0
cameraSettings.focusGestureStrategy = .manualUntilCapture
// then pass cameraSettings into BarcodeArView(..., cameraSettings: cameraSettings)
```

Key `CameraSettings` properties: `preferredResolution: VideoResolution` (default `.fullHD`), `zoomFactor: CGFloat` (default `1.0`), `shouldPreferSmoothAutoFocus: Bool`, `focusRange: FocusRange`, `focusGestureStrategy: FocusGestureStrategy`, `zoomGestureZoomFactor: CGFloat` (default `2.0`), `torchLevel: CGFloat`, `macroMode: MacroMode` (default `.auto`), `adaptiveExposure: Bool` (default `false`).

**Do not construct `CameraSettings()` from scratch for MatrixScan AR** — you'll lose the mode-specific tuning. Always start from `BarcodeAr.recommendedCameraSettings` and modify.

### Camera position (front vs. back)

`BarcodeArViewSettings.defaultCameraPosition` (type `CameraPosition`, default `.worldFacing`) chooses which camera the view opens. Set it to `.userFacing` for a front-facing scanner. Set it on the `BarcodeArViewSettings` before constructing the view.

## Customizing feedback (sound / vibration)

`BarcodeArView` has **two separate** feedback knobs — make sure you change the right one:

- **`BarcodeArViewSettings.soundEnabled`** and **`BarcodeArViewSettings.hapticEnabled`** (both default `true`) — simple on/off toggles. Set them on the `BarcodeArViewSettings` *before* constructing the view.
- **`BarcodeAr.feedback`** (of type `BarcodeArFeedback`, added in 7.1.0) — controls the actual sound and vibration for the `scanned` and `tapped` events. Assign a customized `BarcodeArFeedback` instance if the user wants a custom sound file, custom vibration, or separate behaviors for scan vs. tap.

If the user just wants to mute feedback, toggling `soundEnabled` / `hapticEnabled` on the view settings is enough. Only reach for `BarcodeArFeedback` if they want custom sounds or per-event control.

## Control visibility (torch / zoom / camera switch / macro)

`BarcodeArView` exposes control buttons that are **hidden by default**. Enable only the ones the user asks for:

- `shouldShowTorchControl` (default `false`) + `torchControlPosition` (default `.topLeft`) + `torchControlOffset`
- `shouldShowZoomControl` (default `false`) + `zoomControlPosition` (default `.bottomRight`) + `zoomControlOffset`
- `shouldShowCameraSwitchControl` (default `false`) + `cameraSwitchControlPosition` (default `.topRight`) + `cameraSwitchControlOffset`
- `shouldShowMacroModeControl` (default `false`) + `macroModeControlPosition` (default `.topRight`) + `macroModeControlOffset`

These are set on the `BarcodeArView` instance (not on `BarcodeArViewSettings`) after it is created.

## Lifecycle: start / stop / pause / reset

`BarcodeArView` exposes four lifecycle methods. They are **not** interchangeable — use the one that matches intent:

- **`start()`** — starts the camera and scanning. Call in `viewWillAppear`.
- **`stop()`** — stops the camera and scanning. Call in `viewWillDisappear`. This is the usual "user is leaving the screen" signal.
- **`pause()`** — pauses scanning without tearing down the camera. Use when the user is staying on the screen but scanning needs to halt temporarily (e.g. a confirmation dialog is shown over the scan view). Resume by calling `start()` again.
- **`reset()`** — clears the currently drawn highlights and refreshes the providers. Use when the "scan session" concept restarts mid-screen (e.g. the user picked a different task and previously tracked barcodes should no longer be shown). Does not stop the camera.

Rule of thumb: `stop` when the screen is going away, `pause` when scanning pauses but the screen stays, `reset` when the visible state needs to clear without interrupting the camera.

## SwiftUI

`BarcodeArView` is a `UIView` — it cannot be dropped into SwiftUI directly. Wrap the scanning view controller in a `UIViewControllerRepresentable` and keep every MatrixScan AR API call (context, mode, settings, view, lifecycle) **inside the wrapped UIKit view controller**. This matters because the sibling skills (`matrixscan-ar-highlight-ios`, `matrixscan-ar-annotation-ios`) assume highlights/annotations are wired up on the UIKit side — if a SwiftUI user tries to touch Scandit APIs from the `View` struct, downstream work breaks.

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

## Threading

`BarcodeArListener.barcodeAr(_:didUpdate:frameData:)` fires on a background queue — do not touch UIKit from inside it without dispatching to the main queue. This is **different** from the annotation/highlight `UIDelegate` callbacks on the view, which already run on the main queue.

## What belongs in this skill vs. the siblings

| Question shape | Skill |
|---|---|
| "Add MatrixScan AR to my app" / "set up the scanner" / "configure symbologies / camera / feedback / torch" | This skill |
| "Change the shape/color of the thing drawn over each barcode" / anything about `BarcodeArRectangleHighlight`, `BarcodeArCircleHighlight`, `BarcodeArHighlightProvider` | `matrixscan-ar-highlight-ios` |
| "Show an info card / status icon / popover on each barcode" / anything about `BarcodeArInfoAnnotation`, `BarcodeArPopoverAnnotation`, `BarcodeArStatusIconAnnotation`, `BarcodeArResponsiveAnnotation`, `BarcodeArAnnotationProvider` | `matrixscan-ar-annotation-ios` |
| "Handle a tap on a highlight" (`BarcodeArViewUIDelegate.barcodeAr(_:didTapHighlightFor:highlight:)`) | `matrixscan-ar-highlight-ios` |
| "Handle a tap on an annotation" (per-annotation delegate) | `matrixscan-ar-annotation-ios` |

## After wiring up

Build the project. If compile errors remain, fetch the [MatrixScan AR API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html) to find the correct API before guessing. Always include the docs link in your answer so the user can explore further.
