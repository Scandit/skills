# Third-Party Multi-Barcode Scanner → MatrixScan Batch Migration (.NET MAUI)

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- Which framework is in use (read the `using` directives, the `<PackageReference>` lines, and the XAML namespace prefixes).
- Which symbologies are enabled.
- How the project is collecting "all visible barcodes" — a multi-result `BarcodesDetected` event (`Multiple = true` on ZXing.Net.Maui), a `BarcodeScanning.Native.Maui` `OnDetectionFinished` callback with `IReadOnlyList<BarcodeResult>`, or a hand-rolled continuous-scan loop that restarts itself after each result.
- What result-handling logic exists (deduplication on the string value, accumulation in a `List`/`HashSet`, filtering by symbology / prefix).
- What data models are defined (records, classes, DTOs that hold the scanned info).
- How the scanner UI is rendered (a XAML control inside the page, a modal `ContentPage`, a popup).

Common third-party MAUI scanners used (sometimes mis-used) for multi-barcode batch scanning:

- **ZXing.Net.Maui** / **ZXing.Net.MAUI.Controls** (`ZXing.Net.Maui.Controls.CameraBarcodeReaderView`, `ZXing.Net.Maui.BarcodeFormat`, `BarcodesDetected` event with `e.Results` array, `BarcodeReaderOptions.Multiple = true`). Real per-frame multi-detection.
- **BarcodeScanning.Native.Maui** (`BarcodeScanning.CameraView`, `BarcodeScanning.BarcodeFormats`, `OnDetectionFinished(object?, OnDetectionFinishedEventArg)` with `e.BarcodeResults`). Real per-frame multi-detection.
- **ZXing.Net.Mobile.Forms** (legacy Xamarin.Forms package, sometimes still referenced in migrated MAUI projects via the compatibility shim) — single-result; "batch" is emergent from a continuous scan loop.

MatrixScan Batch replaces all of the above. It owns the camera, runs the recognizer on every frame, tracks each barcode across frames (assigning a **stable per-barcode tracking ID**), and reports additions / updates / removals via `IBarcodeBatchListener.OnSessionUpdated`. There is no continuous-scan loop to re-trigger — the session updates fire on their own. Manual `HashSet<string>` deduplication on the barcode value can usually be replaced by tracking-ID-based deduplication (`session.AddedTrackedBarcodes` plus a `HashSet<int>` of seen `Identifier`s).

---

## Remove

- The third-party `<PackageReference>` entries from the `.csproj` (e.g. `ZXing.Net.Maui`, `ZXing.Net.MAUI.Controls`, `BarcodeScanning.Native.Maui`).
- The third-party builder extension in `MauiProgram.cs` (e.g. `.UseBarcodeReader()` or `.UseBarcodeScanning()`).
- The third-party XAML namespace and control from each page (e.g. `<zxing:CameraBarcodeReaderView>`, `<barcodes:CameraView>`).
- All `using ZXing.*;` / `using BarcodeScanning.*;` directives.
- The scanner's event handler (e.g. `BarcodesDetected`, `OnDetectionFinished`) and any options class (e.g. `BarcodeReaderOptions`, `BarcodeFormats`).
- The continuous-scan loop / frame analyzer if one was used to emulate batch behavior (`while (...)`, `_ = StartScanAsync()` re-trigger).
- Any UI code specific to the old scanner — manually-drawn highlight rectangles, custom viewfinder overlay layers. MatrixScan Batch's `<scandit:DataCaptureView>` + `BarcodeBatchBasicOverlay` (or `BarcodeBatchAdvancedOverlay`) replace all of it.

---

## Integrate MatrixScan Batch

Follow `references/integration.md`. The key shape of the rewrite:

1. **Replace the scanner's camera-and-preview XAML control with `<scandit:DataCaptureView>`.**
   Add the `xmlns:scandit="clr-namespace:Scandit.DataCapture.Core.UI.Maui;assembly=ScanditCaptureCoreMaui"` namespace. Set `DataCaptureContext="{Binding DataCaptureContext}"` on the element — mandatory.
2. **Register the Scandit MAUI builder extensions in `MauiProgram.cs`.**
   `.UseScanditCore(c => c.AddDataCaptureView()).UseScanditBarcode()`.
3. **Replace the scanner's symbology configuration with `BarcodeBatchSettings`.**
   Use the symbology mapping table below.
4. **Replace the scanner's per-result callback with `IBarcodeBatchListener.OnSessionUpdated` (or the `SessionUpdated` event).**
   Wrap UI work in `MainThread.BeginInvokeOnMainThread(...)` and **always call `frameData.Dispose()` in a `finally` block** (mandatory on iOS, safe on Android).
5. **Replace any manually-drawn highlight with `BarcodeBatchBasicOverlay`.**
   `BarcodeBatchBasicOverlay.Create(barcodeBatch)` or `Create(barcodeBatch, BarcodeBatchBasicOverlayStyle.Frame)`. Created inside `dataCaptureView.HandlerChanged` and attached via `dataCaptureView.AddOverlay(overlay)`.

When configuring `BarcodeBatchSettings`, map symbologies from the old scanner using the table below. **Do not guess or derive Scandit symbology names from the old library's names** — they differ (e.g. ZXing's `QrCode` maps to `Symbology.Qr`, not `Symbology.QrCode`, which does not exist).

### Symbology mapping

| ZXing.Net.Maui `BarcodeFormat` / ZXing `BarcodeFormat` | BarcodeScanning.Native.Maui `BarcodeFormats` | Scandit `Symbology.*` |
|---|---|---|
| `QrCode` / `QR_CODE` | `QrCode` | `Symbology.Qr` |
| `Ean13` / `EAN_13` | `Ean13` | `Symbology.Ean13Upca` |
| `Ean8` / `EAN_8` | `Ean8` | `Symbology.Ean8` |
| `UpcA` / `UPC_A` | `UpcA` | `Symbology.Ean13Upca` (UPC-A is decoded by the Scandit EAN-13/UPC-A symbology) |
| `UpcE` / `UPC_E` | `UpcE` | `Symbology.Upce` |
| `Code39` / `CODE_39` | `Code39` | `Symbology.Code39` |
| `Code93` / `CODE_93` | `Code93` | `Symbology.Code93` |
| `Code128` / `CODE_128` | `Code128` | `Symbology.Code128` |
| `Itf` / `ITF` | `Itf` | `Symbology.InterleavedTwoOfFive` |
| `Codabar` / `CODABAR` | `Codabar` | `Symbology.Codabar` |
| `DataMatrix` / `DATA_MATRIX` | `DataMatrix` | `Symbology.DataMatrix` |
| `Aztec` / `AZTEC` | `Aztec` | `Symbology.Aztec` |
| `Pdf417` / `PDF_417` | `Pdf417` | `Symbology.Pdf417` |

If you encounter a symbology not in this table, check the BarcodeBatch API reference for the correct `Symbology` enum value before writing the code:
- [.NET Android](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html)
- [.NET iOS](https://docs.scandit.com/data-capture-sdk/dotnet.ios/barcode-capture/api.html)

### Result-pattern mapping

| Old scanner concept | MatrixScan Batch equivalent |
|---|---|
| "I got a result, restart the scanner" (legacy ZXing.Net.Mobile loop) | Nothing — `OnSessionUpdated` fires for every processed frame. Remove the re-trigger. |
| `BarcodesDetected` event handler with `e.Results.Length > 1` (ZXing.Net.Maui multi-mode) | `IBarcodeBatchListener.OnSessionUpdated` — iterate `session.AddedTrackedBarcodes` for the codes that are new this frame, plus `session.UpdatedTrackedBarcodes` for ones whose position changed, plus `session.RemovedTrackedBarcodes` (an `IList<int>` of tracking IDs) for ones that left the view. |
| `OnDetectionFinished` per-frame result list (BarcodeScanning.Native.Maui) | Same — process per-frame deltas from the session inside `OnSessionUpdated`. |
| `result.Value` / `result.RawValue` | `trackedBarcode.Barcode.Data` |
| `result.Format` / `barcodeResult.BarcodeFormat` | `trackedBarcode.Barcode.Symbology` (a `Symbology` enum; use `new SymbologyDescription(symbology).ReadableName` for a human string) |
| Per-result bounding box (`result.BoundingBox`, `result.ResultPoints`) | `trackedBarcode.Location` (`Quadrilateral` in image-space; the basic overlay draws the highlight for you, or call `dataCaptureView.MapFrameQuadrilateralToView(location)` to convert to view space) |
| "Have I seen this code yet?" (manual `HashSet<string>` dedupe on `result.Value`) | `trackedBarcode.Identifier` is the stable per-barcode tracking ID. New barcodes show up in `session.AddedTrackedBarcodes`; the same physical code keeps the same identifier across frames until it leaves the view. Track identifiers in your own `HashSet<int>` if you need an "ever seen" set, or accumulate `Barcode.Data` from `AddedTrackedBarcodes`. |
| "Which barcodes are currently visible?" | `session.TrackedBarcodes` — `IDictionary<int, TrackedBarcode>` keyed by tracking ID. |

---

## Preserve

- Custom data models — keep as-is (records like `record ScannedBarcode(string Value, string Format)` move verbatim).
- Result accumulation and deduplication logic — move it into `OnSessionUpdated` (or the `SessionUpdated` event handler). Iterate `session.AddedTrackedBarcodes` and append to the existing collection. **Wrap UI updates in `MainThread.BeginInvokeOnMainThread(() => { … })` because `OnSessionUpdated` runs on a background recognition thread.** Copy the data you need out of the session before scheduling the dispatch — the session is only safe to access from inside the callback. **Always end the callback with `frameData.Dispose()` in a `finally` block** (mandatory on iOS, safe on Android).
- Any downstream business logic triggered on a new barcode (network lookup, database insert).
- Validation / reject behavior — if the old scanner had a "is this code valid?" check, port it as a filter when iterating `AddedTrackedBarcodes` inside `OnSessionUpdated`.

---

## Putting it all together

A typical "ZXing.Net.Maui multi-detection replaced with MatrixScan Batch" view-model shape:

```csharp
using System.Collections.Generic;
using System.Linq;
using Scandit.DataCapture.Barcode.Batch.Capture;
using Scandit.DataCapture.Barcode.Batch.Data;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;
using Scandit.DataCapture.Core.Data;
using Scandit.DataCapture.Core.Source;

namespace MyApp.ViewModels;

public partial class MainPageViewModel : BaseViewModel, IBarcodeBatchListener
{
    public const string ScanditLicenseKey = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    private readonly List<ScannedBarcode> scannedBarcodes = new();
    private readonly HashSet<int> seenTrackingIds = new();
    private readonly Camera? camera;

    public DataCaptureContext DataCaptureContext { get; }
    public BarcodeBatch BarcodeBatch { get; }

    public IEnumerable<ScannedBarcode> ScannedBarcodes => this.scannedBarcodes;

    public MainPageViewModel()
    {
        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(ScanditLicenseKey);

        this.camera = Camera.GetCamera(CameraPosition.WorldFacing);
        this.camera?.ApplySettingsAsync(BarcodeBatch.RecommendedCameraSettings);
        this.DataCaptureContext.SetFrameSourceAsync(this.camera);

        var settings = BarcodeBatchSettings.Create();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,     // from ZXing BarcodeFormat.Ean13
            Symbology.Code128,       // from ZXing BarcodeFormat.Code128
            Symbology.Qr,            // from ZXing BarcodeFormat.QrCode (not Symbology.QrCode!)
        });

        this.BarcodeBatch = BarcodeBatch.Create(this.DataCaptureContext, settings);
        this.BarcodeBatch.AddListener(this);
    }

    public override async Task SleepAsync()
    {
        this.BarcodeBatch.Enabled = false;
        if (this.camera != null)
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.Off);
    }

    public override async Task ResumeAsync()
    {
        var status = await Permissions.CheckStatusAsync<Permissions.Camera>();
        if (status != PermissionStatus.Granted)
        {
            status = await Permissions.RequestAsync<Permissions.Camera>();
            if (status != PermissionStatus.Granted) return;
        }

        this.BarcodeBatch.Enabled = true;
        if (this.camera != null)
            await this.camera.SwitchToDesiredStateAsync(FrameSourceState.On);
    }

    public void OnObservationStarted(BarcodeBatch barcodeBatch) { }
    public void OnObservationStopped(BarcodeBatch barcodeBatch) { }

    public void OnSessionUpdated(
        BarcodeBatch barcodeBatch,
        BarcodeBatchSession session,
        IFrameData frameData)
    {
        try
        {
            // Same dedupe-and-accumulate as the old ZXing BarcodesDetected handler,
            // but driven by per-frame deltas and a stable tracking ID.
            var newScans = session.AddedTrackedBarcodes
                .Where(tb => this.seenTrackingIds.Add(tb.Identifier))
                .Select(tb => new ScannedBarcode(
                    tb.Barcode.Data ?? string.Empty,
                    tb.Barcode.Symbology.ToString()))
                .ToList();

            if (newScans.Count == 0) return;

            MainThread.BeginInvokeOnMainThread(() =>
            {
                this.scannedBarcodes.AddRange(newScans);
                this.OnPropertyChanged(nameof(this.ScannedBarcodes));
            });
        }
        finally
        {
            // Mandatory on iOS to avoid a frozen / stuttering preview; safe on Android too.
            frameData.Dispose();
        }
    }
}

public record ScannedBarcode(string Value, string Format);
```

The matching XAML replaces `<zxing:CameraBarcodeReaderView>` with `<scandit:DataCaptureView>`:

```xml
<ContentPage xmlns="http://schemas.microsoft.com/dotnet/2021/maui"
             xmlns:x="http://schemas.microsoft.com/winfx/2009/xaml"
             xmlns:scandit="clr-namespace:Scandit.DataCapture.Core.UI.Maui;assembly=ScanditCaptureCoreMaui"
             xmlns:vm="clr-namespace:MyApp.ViewModels"
             x:Class="MyApp.Views.MainPage">
    <ContentPage.BindingContext>
        <vm:MainPageViewModel />
    </ContentPage.BindingContext>
    <AbsoluteLayout>
        <scandit:DataCaptureView x:Name="dataCaptureView"
                                 AbsoluteLayout.LayoutBounds="0,0,1,1"
                                 AbsoluteLayout.LayoutFlags="All"
                                 DataCaptureContext="{Binding DataCaptureContext}" />
    </AbsoluteLayout>
</ContentPage>
```

And the page code-behind creates the basic overlay inside `HandlerChanged` (see `references/integration.md` Step 4 for the full pattern).

---

When done, show only what changed. Do not list APIs that were unchanged. Include the setup checklist from `references/integration.md` so the user knows which NuGet packages to add (all four: Core, Core.Maui, Barcode, Barcode.Maui), the `MauiProgram.cs` builder chain update, the `<scandit:DataCaptureView>` XAML namespace + element, and the platform permission entries (`NSCameraUsageDescription` on iOS; `Permissions.Camera` on Android).
