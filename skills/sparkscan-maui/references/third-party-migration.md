# Migrating from a Third-Party Barcode Scanner to SparkScan on .NET MAUI

This guide describes how to replace common third-party barcode-scanning libraries in a **.NET MAUI** app with Scandit SparkScan. Once the swap is complete, follow [references/integration.md](./integration.md) for the full SparkScan setup. This document only describes what to remove and how to map your existing logic onto SparkScan.

## Why SparkScan (vs. BarcodeCapture)

SparkScan is the pre-built single-scanning UI: a draggable trigger button + mini preview overlay. It is the right replacement when the existing third-party scanner shows a fullscreen or sheet-style scanner UI launched from a button — most ZXing.Net.Maui / BarcodeScanning.Native.Maui apps fall into this category. If instead the project embeds a permanent camera preview inside the page (overlay-style), the appropriate replacement is `BarcodeCapture` with `DataCaptureView` — switch to the `barcode-capture-maui` skill in that case.

## Common libraries

### `ZXing.Net.Maui` (and `ZXing.Net.Maui.Controls`)

`ZXing.Net.Maui` exposes a `<zxing:CameraBarcodeReaderView>` control and a `BarcodesDetected` event. To migrate:

1. **Remove the NuGet packages**:
   ```xml
   <!-- delete -->
   <PackageReference Include="ZXing.Net.Maui" Version="..." />
   <PackageReference Include="ZXing.Net.Maui.Controls" Version="..." />
   ```
2. **Remove the builder registration** in `MauiProgram.cs`:
   ```csharp
   builder.UseBarcodeReader();   // delete
   ```
3. **Remove the XAML control and namespace**:
   ```xml
   <ContentPage xmlns:zxing="clr-namespace:ZXing.Net.Maui.Controls;assembly=ZXing.Net.MAUI.Controls">
     <zxing:CameraBarcodeReaderView … BarcodesDetected="OnBarcodesDetected" />
   </ContentPage>
   ```
4. **Delete code-behind**: `OnBarcodesDetected`, `BarcodeReaderOptions`, `CameraLocation` setters, and any `IsTorchOn` toggling.
5. **Map options to SparkScan**:
   - `BarcodeReaderOptions.Formats` → `SparkScanSettings.EnableSymbology(...)`. Mapping:
     - `BarcodeFormat.Ean13` → `Symbology.Ean13Upca`
     - `BarcodeFormat.Ean8` → `Symbology.Ean8`
     - `BarcodeFormat.UpcA` → `Symbology.Ean13Upca`
     - `BarcodeFormat.UpcE` → `Symbology.Upce`
     - `BarcodeFormat.Code128` → `Symbology.Code128`
     - `BarcodeFormat.Code39` → `Symbology.Code39`
     - `BarcodeFormat.ITF` → `Symbology.InterleavedTwoOfFive`
     - `BarcodeFormat.QrCode` → `Symbology.Qr`
     - `BarcodeFormat.DataMatrix` → `Symbology.DataMatrix`
     - `BarcodeFormat.Pdf417` → `Symbology.Pdf417`
     - `BarcodeFormat.Aztec` → `Symbology.Aztec`
   - `AutoRotate = true` → no equivalent needed; SparkScan handles rotation automatically.
   - `Multiple = true` → not a concept in SparkScan single-scan. If you need multi-scan UX, use `barcode-capture-maui`.
   - `TryHarder = true` → not needed; SparkScan's engine tunes itself.
   - `IsTorchOn` → `SparkScanViewSettings.DefaultTorchState = TorchState.On` (or expose the torch via `SparkScanView.TorchControlVisible = true` and let the user toggle).
   - `CameraLocation` → `SparkScanViewSettings.DefaultCameraPosition = CameraPosition.UserFacing` / `WorldFacing`.

### `BarcodeScanning.Native.Maui` (Google ML Kit / Apple Vision wrapper)

```xml
<PackageReference Include="BarcodeScanning.Native.Maui" Version="..." />
```

1. **Remove the NuGet package**.
2. **Remove the builder registration**:
   ```csharp
   builder.UseBarcodeScanning();   // delete
   ```
3. **Remove the XAML control**:
   ```xml
   <bs:CameraView OnDetectionFinished="OnDetectionFinished" … />
   ```
4. **Delete code-behind**: `OnDetectionFinished(object, OnDetectionFinishedEventArg)`, any `BarcodeFormats` flag mapping, `CameraEnabled` toggling.
5. **Map detection callback to SparkScan**:
   - `OnDetectionFinishedEventArg.BarcodeResults[0].DisplayValue` → `args.Session.NewlyRecognizedBarcode.Data` (inside `BarcodeScanned`).
   - `OnDetectionFinishedEventArg.BarcodeResults[0].RawValue` → `barcode.RawData` (returns the raw bytes when available).
   - `BarcodeFormat` flag bitmask → `SparkScanSettings.EnableSymbologies(...)` with the matching `Symbology` set.

### Native AVFoundation / Camera2 launched via a `DependencyService`

If the previous implementation reached into `Platforms/iOS/AvCameraScanner.cs` and `Platforms/Android/Camera2Scanner.cs` with `[assembly: Dependency(typeof(AvCameraScanner))]`:

1. Delete both platform files and the registered `IBarcodeScanner` interface.
2. Remove the `DependencyService.Get<IBarcodeScanner>()` lookups from your view model.
3. Add SparkScan to the page as documented in [integration.md](./integration.md) — there is no longer a need for a custom scanning page or platform abstraction.

### `Plugin.Maui.Barcode` / `Camera.MAUI.ZXing`

Same approach: remove the `<PackageReference>`, drop the builder extension call (`.UseCamera()` / `.UseBarcodeReader()` / etc.), remove the XAML control, and re-implement the scan handler against `SparkScan.BarcodeScanned`.

## Preserve in place

- The MAUI navigation, MVVM, and data layer can stay.
- The list/store the scanned codes feed into can stay — only the producer changes from a third-party library's event to `SparkScan.BarcodeScanned`.
- DI registrations of your own services (analytics, lookups) can stay.
- Audio / haptic configuration moves into `SparkScanViewSettings` (`SoundEnabled`, `HapticEnabled`); custom sounds/vibrations belong in `SparkScanBarcodeSuccessFeedback(visualFeedbackColor, brush, feedback)`.

## Reapply with SparkScan

After cleaning up:

1. Add the four Scandit NuGet packages (see [integration.md](./integration.md) Step 0).
2. Wire `.UseScanditCore().UseScanditBarcode(c => c.AddSparkScanView())` in `MauiProgram.cs`.
3. Declare `<scandit:SparkScanView>` in XAML bound to the page/VM's `DataCaptureContext`, `SparkScan`, `SparkScanViewSettings`.
4. Forward `OnAppearing` / `OnDisappearing` into `this.SparkScanView.OnAppearing()` / `OnDisappearing()`.
5. Subscribe to `SparkScan.BarcodeScanned` in the view model and dispatch UI updates via `MainThread.BeginInvokeOnMainThread(...)`.
6. (Optional) Implement `ISparkScanFeedbackDelegate` on the page for per-barcode success/error feedback.

## Pitfalls

- **Do not** try to keep both scanners in the same page. ZXing's `CameraBarcodeReaderView` and `<scandit:SparkScanView>` both want exclusive access to the camera and will fight for it.
- **Do not** wrap `SparkScan.BarcodeScanned` to look like ZXing's `BarcodesDetected` — SparkScan reports one barcode per event via `args.Session.NewlyRecognizedBarcode`. If your downstream code expected a `IEnumerable<BarcodeResult>`, simplify it to a single-barcode handler.
- **Do not** call `SparkScan.Enabled = false` in the handler to prevent duplicate scans. Use `SparkScanSettings.CodeDuplicateFilter` (`TimeSpan`) and / or `SparkScanBarcodeErrorFeedback(message, resumeCapturingDelay)` instead.
- **Builder shape** — remember that the SparkScan MAUI builder is `.UseScanditCore().UseScanditBarcode(c => c.AddSparkScanView())`, **not** the BarcodeCapture shape. If the codebase previously used BarcodeCapture or you see online snippets with `.UseScanditCore(c => c.AddDataCaptureView()).UseScanditBarcode()`, that is a different mode.
- **`SupportedOSPlatformVersion`** — the MAUI template defaults Android to 21; Scandit needs ≥ 24. Bump it before the first build.
- **`Info.plist`** — add `NSCameraUsageDescription` if iOS is in the TFM list; without it the app crashes on first camera access.
