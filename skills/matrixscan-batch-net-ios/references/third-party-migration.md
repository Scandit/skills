# Third-Party Multi-Barcode Scanner → MatrixScan Batch Migration (.NET for iOS)

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- Which framework is in use (read the `using` directives and `<PackageReference>` lines).
- Which symbologies are enabled.
- How the project is collecting "all visible barcodes" — an `AVCaptureMetadataOutput` delegate that fires on every frame, a continuous ZXing.Net.Mobile scan loop that restarts itself after each result, a hand-rolled `AVCaptureVideoDataOutput` + Vision (`VNDetectBarcodesRequest`) pipeline, etc.
- What result-handling logic exists (deduplication on the string value, accumulation in a `List`/`HashSet`, filtering by symbology / prefix).
- What data models are defined.
- How the scanner UI is rendered (full-screen `UIViewController` with an `AVCaptureVideoPreviewLayer`, embedded scanner view, modal presentation).

Common third-party scanners abused for batch use in .NET iOS codebases:

- **AVFoundation `AVCaptureMetadataOutput`** — Apple's built-in barcode detector. Fires `DidOutputMetadataObjects` on the camera queue with an array of `AVMetadataMachineReadableCodeObject` per frame. Already multi-result per frame, but the developer typically rebuilds tracking / dedupe by hand.
- **AVFoundation + Vision (`VNDetectBarcodesRequest`)** — Vision-based detection running on `AVCaptureVideoDataOutput` frames. Multi-result; the developer assembles their own tracking layer.
- **ZXing.Net.Mobile** (`ZXing.Mobile.MobileBarcodeScanner`, `ZXing.BarcodeFormat`) — usually a continuous-scan loop that restarts itself after each result. Single-barcode by design; "batch" behavior is emergent from looping. **Note:** ZXing.Net.Mobile has been unmaintained on iOS for years and does not officially support modern `net*-ios` targets — moving to Scandit also lifts the dependency.
- **ZXing.Net** — pure decoder, often paired with a hand-written `AVCaptureVideoDataOutput` analyzer that runs `BarcodeReader.Decode` (or `DecodeMultiple`) on each pixel buffer.

MatrixScan Batch replaces all of the above: it owns the camera, runs the recognizer on every frame, tracks each barcode across frames (assigning a stable per-barcode tracking ID), and reports additions / updates / removals via `IBarcodeBatchListener.OnSessionUpdated`. There is no continuous-scan loop to re-trigger — the session updates fire on their own.

---

## Remove

- The third-party `<PackageReference>` entries from the `.csproj` (e.g. `ZXing.Net.Mobile`, `ZXing.Net.Mobile.Forms`, `ZXing.Net`).
- All `using ZXing.*;` directives. Keep `using AVFoundation;` / `using Vision;` only if other parts of the controller still need them; otherwise remove.
- The `AVCaptureSession`, `AVCaptureDevice`, `AVCaptureMetadataOutput` (and its `IAVCaptureMetadataOutputObjectsDelegate` delegate), `AVCaptureVideoDataOutput`, `AVCaptureVideoPreviewLayer`, and any setup code that wires them together. Scandit's `Camera` and `DataCaptureView` replace this whole stack.
- Vision pipeline pieces: `VNImageRequestHandler`, `VNDetectBarcodesRequest`, the dispatch-queue boilerplate.
- The continuous-scan loop / frame analyzer (the `while (...)` / `_ = StartScanAsync()` re-trigger, the metadata-output delegate callback, the per-frame buffer-to-CVPixelBuffer conversion).
- Any UI code specific to the old scanner — manually-drawn highlight rectangles, custom viewfinder overlay layers, the `AVCaptureVideoPreviewLayer` resize handler. MatrixScan Batch's `DataCaptureView` + `BarcodeBatchBasicOverlay` (or `BarcodeBatchAdvancedOverlay`) replace all of it.

---

## Integrate MatrixScan Batch

Follow `references/integration.md`. The key shape of the rewrite:

1. **Replace the scanner's camera setup with the Scandit camera pipeline.**
   `Camera.GetDefaultCamera()` → `camera.ApplySettingsAsync(BarcodeBatch.RecommendedCameraSettings)` → `dataCaptureContext.SetFrameSourceAsync(camera)`. Drive on/off from `ViewWillAppear` / `ViewWillDisappear` via `camera.SwitchToDesiredStateAsync(FrameSourceState.On / Off)`.
2. **Replace the scanner's preview view with `DataCaptureView`.**
   `DataCaptureView.Create(dataCaptureContext, this.View!.Bounds)` returns a `UIView`. Set `AutoresizingMask = UIViewAutoresizing.FlexibleHeight | UIViewAutoresizing.FlexibleWidth`, then `this.View.AddSubview(dataCaptureView)` and `this.View.SendSubviewToBack(dataCaptureView)`. Remove the old `AVCaptureVideoPreviewLayer` / custom preview view from the layout.
3. **Replace the scanner's symbology configuration with `BarcodeBatchSettings`.**
   Use the symbology mapping table below.
4. **Replace the scanner's per-result callback with `IBarcodeBatchListener.OnSessionUpdated` (or the `SessionUpdated` event).**
   Use the result-pattern mapping table below. Wrap UI work in `DispatchQueue.MainQueue.DispatchAsync(...)` and **always call `frameData.Dispose()` in a `finally` block**.
5. **Replace any manually-drawn highlight with `BarcodeBatchBasicOverlay`.**
   `BarcodeBatchBasicOverlay.Create(barcodeBatch, dataCaptureView)` auto-adds itself to the view. Use `BarcodeBatchBasicOverlayStyle.Frame` (default) or `Dot`.

When configuring `BarcodeBatchSettings`, map symbologies from the old scanner using the table below. **Do not guess or derive Scandit symbology names from the old library's names** — they differ (e.g. AVFoundation's `AVMetadataObjectType.QRCode` and ZXing's `QR_CODE` both map to `Symbology.Qr`, not `Symbology.QrCode`).

### Symbology mapping

| AVFoundation `AVMetadataObjectType` | ZXing.Net / ZXing.Net.Mobile `BarcodeFormat` | Scandit `Symbology.*` |
|---|---|---|
| `QRCode` | `QR_CODE` | `Symbology.Qr` |
| `EAN13Code` | `EAN_13` | `Symbology.Ean13Upca` |
| `EAN8Code` | `EAN_8` | `Symbology.Ean8` |
| `UPCECode` | `UPC_E` | `Symbology.Upce` |
| `Code39Code` / `Code39Mod43Code` | `CODE_39` | `Symbology.Code39` |
| `Code93Code` | `CODE_93` | `Symbology.Code93` |
| `Code128Code` | `CODE_128` | `Symbology.Code128` |
| `ITF14Code` / `Interleaved2of5Code` | `ITF` | `Symbology.InterleavedTwoOfFive` |
| (not supported directly) | `CODABAR` | `Symbology.Codabar` |
| `DataMatrixCode` | `DATA_MATRIX` | `Symbology.DataMatrix` |
| `AztecCode` | `AZTEC` | `Symbology.Aztec` |
| `PDF417Code` | `PDF_417` | `Symbology.Pdf417` |

AVFoundation has no `UPC_A` constant of its own — UPC-A is reported as `EAN13Code` with a leading `0`. The Scandit equivalent is `Symbology.Ean13Upca` (which decodes both EAN-13 and UPC-A natively).

If you encounter a symbology not in this table, fetch the [BarcodeBatch API reference](https://docs.scandit.com/data-capture-sdk/dotnet.ios/barcode-capture/api.html) for the correct `Symbology` enum value before writing the code.

### Result-pattern mapping

| Old scanner concept | MatrixScan Batch equivalent |
|---|---|
| "I got a result, restart the scanner" (ZXing.Net.Mobile loop) | Nothing — `OnSessionUpdated` fires for every processed frame, and `AddedTrackedBarcodes` reports the new entries since the last frame. Remove the `_ = StartScanAsync()` re-trigger. |
| `result.Text` / `metadataObject.StringValue` | `trackedBarcode.Barcode.Data` |
| `result.BarcodeFormat` / `metadataObject.Type` | `trackedBarcode.Barcode.Symbology` (a `Symbology` enum value; use `new SymbologyDescription(symbology).ReadableName` for a string) |
| Per-result bounding box (`metadataObject.Bounds`, `VNBarcodeObservation.BoundingBox`, `result.ResultPoints`) | `trackedBarcode.Location` (`Quadrilateral` in image-space; the basic overlay draws the highlight for you) |
| "Have I seen this code yet?" (manual `HashSet<string>` dedupe) | `trackedBarcode.Identifier` is the stable per-barcode tracking ID. New barcodes show up in `session.AddedTrackedBarcodes`; the same physical code keeps the same identifier across frames until it leaves the view. Track identifiers in your own `HashSet<int>` if you need a "ever seen" set, or accumulate `barcode.Data` from `AddedTrackedBarcodes`. |
| "Which barcodes are currently visible?" | `session.TrackedBarcodes` — `IDictionary<int, TrackedBarcode>` keyed by tracking ID. |
| AVFoundation per-frame `IAVCaptureMetadataOutputObjectsDelegate.DidOutputMetadataObjects(captureOutput, metadataObjects, fromConnection)` callback | `session.AddedTrackedBarcodes` + `session.UpdatedTrackedBarcodes` + `session.RemovedTrackedBarcodes` (IDs) on every frame inside `OnSessionUpdated`. |
| Vision `VNDetectBarcodesRequest` per-frame `results` array | Same — process per-frame deltas from the session inside `OnSessionUpdated`. |

---

## Preserve

- Custom data models — keep as-is.
- Result accumulation and deduplication logic — move it into `OnSessionUpdated` (or the `SessionUpdated` event handler). Iterate `session.AddedTrackedBarcodes` and append to the existing collection. **Wrap UI updates in `DispatchQueue.MainQueue.DispatchAsync(() => { … })` because `OnSessionUpdated` runs on a background recognition queue.** Copy the data you need out of the session before scheduling the UI dispatch — the session is only safe to access from inside the callback. **Always end the callback with `frameData.Dispose()` in a `finally` block** (or the preview freezes / stutters).
- Any downstream business logic triggered on a new barcode (network lookup, database insert).
- Validation / reject behavior — if the old scanner had a "is this code valid?" check, port it as a filter when iterating `AddedTrackedBarcodes` inside `OnSessionUpdated`.

---

## Putting it all together

A typical "AVCaptureMetadataOutput loop replaced with MatrixScan Batch" shape:

```csharp
using System.Collections.Generic;
using System.Linq;
using CoreFoundation;
using UIKit;

using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Batch.UI.Overlay;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;
using Scandit.DataCapture.Core.UI;

public partial class ScannerViewController : UIViewController, IBarcodeBatchListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeBatch barcodeBatch = null!;
    private Camera? camera;

    private readonly List<ScannedBarcode> scannedBarcodes = new();
    private readonly HashSet<int> seenTrackingIds = new();

    public ScannerViewController(IntPtr handle) : base(handle) { }

    public override void ViewDidLoad()
    {
        base.ViewDidLoad();
        this.InitializeAndStartBatchScanning();
    }

    public override void ViewWillAppear(bool animated)
    {
        base.ViewWillAppear(animated);
        this.barcodeBatch.Enabled = true;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    public override void ViewWillDisappear(bool animated)
    {
        base.ViewWillDisappear(animated);
        this.barcodeBatch.Enabled = false;
        this.camera?.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }

    private void InitializeAndStartBatchScanning()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        this.camera = Camera.GetDefaultCamera();
        if (this.camera != null)
        {
            var cameraSettings = BarcodeBatch.RecommendedCameraSettings;
            cameraSettings.PreferredResolution = VideoResolution.FullHd;
            this.camera.ApplySettingsAsync(cameraSettings);
            this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        BarcodeBatchSettings settings = BarcodeBatchSettings.Create();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,   // from AVMetadataObjectType.EAN13Code / ZXing EAN_13
            Symbology.Code128,     // from AVMetadataObjectType.Code128Code / ZXing CODE_128
            Symbology.Qr,          // from AVMetadataObjectType.QRCode    / ZXing QR_CODE
        });

        this.barcodeBatch = BarcodeBatch.Create(this.dataCaptureContext, settings);
        this.barcodeBatch.AddListener(this);

        var dataCaptureView = DataCaptureView.Create(this.dataCaptureContext, this.View!.Bounds);
        UIView platformView = dataCaptureView;
        platformView.AutoresizingMask = UIViewAutoresizing.FlexibleHeight |
                                        UIViewAutoresizing.FlexibleWidth;
        this.View.AddSubview(dataCaptureView);
        this.View.SendSubviewToBack(dataCaptureView);

        BarcodeBatchBasicOverlay.Create(this.barcodeBatch, dataCaptureView);
    }

    public void OnSessionUpdated(
        BarcodeBatch barcodeBatch,
        BarcodeBatchSession session,
        IFrameData frameData)
    {
        try
        {
            // Same dedupe-and-accumulate as the old AVFoundation / ZXing loop,
            // but driven by per-frame deltas.
            var newScans = session.AddedTrackedBarcodes
                .Where(tb => this.seenTrackingIds.Add(tb.Identifier))
                .Select(tb => new ScannedBarcode(
                    tb.Barcode.Data ?? string.Empty,
                    tb.Barcode.Symbology.ToString()))
                .ToList();

            if (newScans.Count == 0) return;

            DispatchQueue.MainQueue.DispatchAsync(() =>
            {
                this.scannedBarcodes.AddRange(newScans);
                // update UI here
            });
        }
        finally
        {
            // Mandatory on iOS to avoid a frozen / stuttering preview.
            frameData.Dispose();
        }
    }

    public void OnObservationStarted(BarcodeBatch barcodeBatch) { }
    public void OnObservationStopped(BarcodeBatch barcodeBatch) { }
}
```

---

When done, show only what changed. Do not list APIs that were unchanged. Include the setup checklist from `references/integration.md` so the user knows which NuGet packages, `Info.plist` entries (`NSCameraUsageDescription`), `SupportedOSPlatformVersion`, and SDK-8.0+ `AppDelegate.FinishedLaunching` initialization to add.
