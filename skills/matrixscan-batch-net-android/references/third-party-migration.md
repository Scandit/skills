# Third-Party Multi-Barcode Scanner → MatrixScan Batch Migration (.NET for Android)

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- Which framework is in use (read the `using` directives and `<PackageReference>` lines).
- Which symbologies are enabled.
- How the project is collecting "all visible barcodes" (continuous-scan loop, single-frame analyzer running on a Camera2 / CameraX preview, ML Kit `InputImage`, etc.).
- What result-handling logic exists (deduplication on `Value`, accumulation in a `List`/`HashSet`, filtering by symbology / prefix).
- What data models are defined.
- How the scanner UI is rendered (full-screen Activity, embedded camera preview Fragment, intent-based dialog).

Common third-party scanners abused for batch use in .NET Android codebases:

- **ZXing.Net.Mobile** (`ZXing.Mobile.MobileBarcodeScanner`, `ZXing.BarcodeFormat`) — usually a continuous-scan loop that restarts itself after each result. Single-barcode by design; "batch" behavior is emergent from looping.
- **ZXing.Net** — pure decoder, often paired with a hand-written CameraX preview that runs `BarcodeReader.Decode` (or `DecodeMultiple`) on each frame.
- **Google ML Kit barcode scanning** via Xamarin bindings (`Xamarin.Google.MLKit.BarcodeScanning`) — multi-result by design (`BarcodeScanner.Process(image)` returns `IList<Barcode>` per frame), so the existing loop is the closest equivalent of what BarcodeBatch already does.

MatrixScan Batch replaces all of the above: it owns the camera, runs the recognizer on every frame, tracks each barcode across frames (assigning a stable per-barcode tracking ID), and reports additions / updates / removals via `IBarcodeBatchListener.OnSessionUpdated`. There is no continuous-scan loop to re-trigger — the session updates fire on their own.

---

## Remove

- The third-party `<PackageReference>` entries from the `.csproj` (e.g. `ZXing.Net.Mobile`, `ZXing.Net.Mobile.Forms`, `ZXing.Net`, `Xamarin.Google.MLKit.BarcodeScanning`, `Xamarin.GooglePlayServices.Vision.Barcode`).
- All `using ZXing.*;` / `using Google.MLKit.*;` / `using Xamarin.Google.MLKit.*;` directives.
- The scanner instance and its setup code (`new MobileBarcodeScanner()`, `BarcodeScanner.GetClient(...)`, hand-written `BarcodeReader`).
- The continuous-scan loop / frame analyzer (the `while (...)` / `_ = StartScanAsync()` re-trigger, the `OnAnalyze(IImageProxy)` override, the ML Kit `IOnSuccessListener<IList<Barcode>>` callback).
- Any `OnActivityResult` override that handled an intent-based scanner's return value.
- Any UI code specific to the old scanner — custom camera preview Activity / Fragment, viewfinder overlay, manually-drawn highlight rectangles. MatrixScan Batch's `DataCaptureView` + `BarcodeBatchBasicOverlay` (or `BarcodeBatchAdvancedOverlay`) replace all of it.

---

## Integrate MatrixScan Batch

Follow `references/integration.md`. The key shape of the rewrite:

1. **Replace the scanner's camera setup with the Scandit camera pipeline.**
   `Camera.GetDefaultCamera()` → `camera.ApplySettingsAsync(BarcodeBatch.RecommendedCameraSettings)` → `dataCaptureContext.SetFrameSourceAsync(camera)`. Drive on/off from `OnResume` / `OnPause` via `camera.SwitchToDesiredStateAsync(FrameSourceState.On / Off)`.
2. **Replace the scanner's preview view with `DataCaptureView`.**
   `DataCaptureView.Create(dataCaptureContext)` returns an Android `View` — add it to a `FrameLayout` container in the activity layout via `container.AddView(dataCaptureView, ...)`. Remove the third-party preview view from the layout XML.
3. **Replace the scanner's symbology configuration with `BarcodeBatchSettings`.**
   Use the symbology mapping table below.
4. **Replace the scanner's per-result callback with `IBarcodeBatchListener.OnSessionUpdated` (or the `SessionUpdated` event).**
   Use the result-pattern mapping table below.
5. **Replace any manually-drawn highlight with `BarcodeBatchBasicOverlay`.**
   `BarcodeBatchBasicOverlay.Create(barcodeBatch, dataCaptureView)` auto-adds itself to the view. Use `BarcodeBatchBasicOverlayStyle.Frame` (default) or `Dot`.

When configuring `BarcodeBatchSettings`, map symbologies from the old scanner using the table below. **Do not guess or derive Scandit symbology names from the old library's names** — they differ (e.g. ZXing's `QR_CODE` maps to `Symbology.Qr`, not `Symbology.QrCode`).

### Symbology mapping

| ZXing.Net / ZXing.Net.Mobile `BarcodeFormat` | ML Kit `Barcode.Format*` | Scandit `Symbology.*` |
|---|---|---|
| `QR_CODE` | `FORMAT_QR_CODE` | `Symbology.Qr` |
| `EAN_13` | `FORMAT_EAN_13` | `Symbology.Ean13Upca` |
| `EAN_8` | `FORMAT_EAN_8` | `Symbology.Ean8` |
| `UPC_A` | `FORMAT_UPC_A` | `Symbology.Ean13Upca` (UPC-A is a subset of EAN-13/UPC-A in Scandit) |
| `UPC_E` | `FORMAT_UPC_E` | `Symbology.Upce` |
| `CODE_39` | `FORMAT_CODE_39` | `Symbology.Code39` |
| `CODE_93` | `FORMAT_CODE_93` | `Symbology.Code93` |
| `CODE_128` | `FORMAT_CODE_128` | `Symbology.Code128` |
| `ITF` | `FORMAT_ITF` | `Symbology.InterleavedTwoOfFive` |
| `CODABAR` | `FORMAT_CODABAR` | `Symbology.Codabar` |
| `DATA_MATRIX` | `FORMAT_DATA_MATRIX` | `Symbology.DataMatrix` |
| `AZTEC` | `FORMAT_AZTEC` | `Symbology.Aztec` |
| `PDF_417` | `FORMAT_PDF417` | `Symbology.Pdf417` |

If you encounter a symbology not in this table, fetch the [BarcodeBatch API reference](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html) for the correct `Symbology` enum value before writing the code.

### Result-pattern mapping

| Old scanner concept | MatrixScan Batch equivalent |
|---|---|
| "I got a result, restart the scanner" (ZXing.Net.Mobile loop) | Nothing — `OnSessionUpdated` fires for every processed frame, and `AddedTrackedBarcodes` reports the new entries since the last frame. Remove the `_ = StartScanAsync()` re-trigger. |
| `result.Text` / `barcode.RawValue` | `trackedBarcode.Barcode.Data` |
| `result.BarcodeFormat` / `barcode.Format` | `trackedBarcode.Barcode.Symbology` (a `Symbology` enum value; use `new SymbologyDescription(symbology).ReadableName` for a string) |
| Per-result bounding box (`result.ResultPoints`, `barcode.BoundingBox`) | `trackedBarcode.Location` (`Quadrilateral` in image-space; the basic overlay draws the highlight for you) |
| "Have I seen this code yet?" (manual `HashSet<string>` dedupe) | `trackedBarcode.Identifier` is the stable per-barcode tracking ID. New barcodes show up in `session.AddedTrackedBarcodes`; the same physical code keeps the same identifier across frames until it leaves the view. Track identifiers in your own `HashSet<int>` if you need a "ever seen" set, or accumulate `barcode.Data` from `AddedTrackedBarcodes`. |
| "Which barcodes are currently visible?" | `session.TrackedBarcodes` — `IDictionary<int, TrackedBarcode>` keyed by tracking ID. |
| Per-frame ML Kit `IList<Barcode>` callback | `session.AddedTrackedBarcodes` + `session.UpdatedTrackedBarcodes` + `session.RemovedTrackedBarcodes` (IDs) on every frame. |

---

## Preserve

- Custom data models — keep as-is.
- Result accumulation and deduplication logic — move it into `OnSessionUpdated` (or the `SessionUpdated` event handler). Iterate `session.AddedTrackedBarcodes` and append to the existing collection. **Wrap UI updates in `RunOnUiThread(() => { … })` because `OnSessionUpdated` runs on a background recognition thread.** Copy the data you need out of the session before scheduling the UI dispatch — the session is only safe to access from inside the callback.
- Any downstream business logic triggered on a new barcode (network lookup, database insert).
- Validation / reject behavior — if the old scanner had a "is this code valid?" check, port it as a filter when iterating `AddedTrackedBarcodes` inside `OnSessionUpdated`.

---

## Putting it all together

A typical "ZXing loop replaced with MatrixScan Batch" shape:

```csharp
public class ScannerActivity : CameraPermissionActivity, IBarcodeBatchListener
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private DataCaptureContext dataCaptureContext = null!;
    private BarcodeBatch barcodeBatch = null!;
    private Camera? camera;
    private DataCaptureView dataCaptureView = null!;

    private readonly List<ScannedBarcode> scannedBarcodes = new();
    private readonly HashSet<int> seenTrackingIds = new();

    protected override void OnCreate(Bundle? savedInstanceState)
    {
        base.OnCreate(savedInstanceState);
        this.SetContentView(Resource.Layout.activity_scanner);
        this.InitializeAndStartBatchScanning();
    }

    // … OnResume / OnPause / OnDestroy as in references/integration.md …

    private void InitializeAndStartBatchScanning()
    {
        this.dataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        this.camera = Camera.GetDefaultCamera();
        if (this.camera != null)
        {
            this.camera.ApplySettingsAsync(BarcodeBatch.RecommendedCameraSettings);
            this.dataCaptureContext.SetFrameSourceAsync(this.camera);
        }

        BarcodeBatchSettings settings = BarcodeBatchSettings.Create();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,   // from ZXing.BarcodeFormat.EAN_13
            Symbology.Code128,     // from ZXing.BarcodeFormat.CODE_128
            Symbology.Qr,          // from ZXing.BarcodeFormat.QR_CODE
        });

        this.barcodeBatch = BarcodeBatch.Create(this.dataCaptureContext, settings);
        this.barcodeBatch.AddListener(this);

        this.dataCaptureView = DataCaptureView.Create(this.dataCaptureContext);
        BarcodeBatchBasicOverlay.Create(this.barcodeBatch, this.dataCaptureView);

        var container = FindViewById<FrameLayout>(Resource.Id.data_capture_view_container);
        container?.AddView(
            this.dataCaptureView,
            new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MatchParent,
                ViewGroup.LayoutParams.MatchParent));
    }

    public void OnSessionUpdated(
        BarcodeBatch barcodeBatch,
        BarcodeBatchSession session,
        IFrameData frameData)
    {
        // Same dedupe-and-accumulate as the old ZXing loop, but driven by per-frame deltas.
        var newScans = session.AddedTrackedBarcodes
            .Where(tb => this.seenTrackingIds.Add(tb.Identifier))
            .Select(tb => new ScannedBarcode(
                tb.Barcode.Data ?? string.Empty,
                tb.Barcode.Symbology.ToString()))
            .ToList();

        if (newScans.Count == 0) return;

        RunOnUiThread(() =>
        {
            this.scannedBarcodes.AddRange(newScans);
            // update UI here
        });
    }

    public void OnObservationStarted(BarcodeBatch barcodeBatch) { }
    public void OnObservationStopped(BarcodeBatch barcodeBatch) { }
}
```

---

When done, show only what changed. Do not list APIs that were unchanged. Include the setup checklist from `references/integration.md` so the user knows which NuGet packages, manifest entries, runtime-permission flow, layout container (`FrameLayout` with `data_capture_view_container` id), and SDK-8.0+ `MainApplication.cs` to add.
