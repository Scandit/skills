# Third-Party Barcode Scanner → BarcodeCapture Migration (.NET MAUI)

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and replace only the third-party scanner calls underneath with Scandit ones.

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- Which framework is in use (read the `using` directives and `<PackageReference>` lines).
- Which symbologies are enabled.
- What result handling logic exists (deduplication, filtering, accumulation).
- What data models are defined.
- How the scanner is launched (XAML control, modal page, popup).

Common third-party MAUI barcode scanners:

- **ZXing.Net.Maui** / **ZXing.Net.MAUI.Controls** (`ZXing.Net.Maui.Controls.CameraBarcodeReaderView`, `ZXing.Net.Maui.BarcodeFormat`, `BarcodesDetected` event).
- **BarcodeScanning.Native.Maui** (`BarcodeScanning.CameraView`, `BarcodeScanning.BarcodeFormats`).
- **ZXing.Net.Mobile.Forms** (legacy Xamarin.Forms package, sometimes still referenced in migrated MAUI projects via the compatibility shim).

---

## Remove

- The third-party `<PackageReference>` entries from the `.csproj` (e.g. `ZXing.Net.Maui`, `ZXing.Net.MAUI.Controls`, `BarcodeScanning.Native.Maui`).
- The third-party builder extension in `MauiProgram.cs` (e.g. `.UseBarcodeReader()` or `.UseScanditCommunity()`).
- The third-party XAML namespace and control from each page (e.g. `<zxing:CameraBarcodeReaderView>`).
- All `using ZXing.*;` / `using BarcodeScanning.*;` directives.
- The scanner's event handler (e.g. `BarcodesDetected`) and any options class (e.g. `BarcodeReaderOptions`).
- Still-image decode calls (`BarcodeReader.DecodeAsync`, `Methods.ScanFromImageAsync`) migrate too; see "Still-image decode" below. Never drop them or replace them with an error message.

---

## Integrate BarcodeCapture

Follow `references/integration.md`. When configuring `BarcodeCaptureSettings`, map symbologies from the old scanner using the table below. **Do not guess or derive Scandit symbology names from the old library's names** — they differ (e.g. ZXing's `QR_CODE` maps to `Symbology.Qr`, not `Symbology.QrCode`).

### Symbology mapping

<!-- BEGIN GENERATED symbology-table sources=zxing-net-maui,zxing-net,barcodescanning-native-maui style=csharp -->
| ZXing.Net.Maui `BarcodeFormat` | ZXing.Net / ZXing.Net.Mobile `BarcodeFormat` | BarcodeScanning.Native.Maui `BarcodeFormats` | Scandit `Symbology` |
|---|---|---|---|
| `QrCode` | `QR_CODE` | `QRCode` | `Symbology.Qr` |
| `Ean13` | `EAN_13` | `Ean13` | `Symbology.Ean13Upca` |
| `Ean8` | `EAN_8` | `Ean8` | `Symbology.Ean8` |
| `UpcA` | `UPC_A` | `Upca` | `Symbology.Ean13Upca` (UPC-A is read by the EAN-13/UPC-A symbology) |
| `UpcE` | `UPC_E` | `Upce` | `Symbology.Upce` |
| `Code39` | `CODE_39` | `Code39` | `Symbology.Code39` |
| `Code93` | `CODE_93` | `Code93` | `Symbology.Code93` |
| `Code128` | `CODE_128` | `Code128` | `Symbology.Code128` |
| `Itf` | `ITF` | `Itf` / `I2OF5` | `Symbology.InterleavedTwoOfFive` (no ITF-14 symbology; ITF-14 is a 14-digit Interleaved 2 of 5) |
| `Codabar` | `CODABAR` | `CodaBar` | `Symbology.Codabar` |
| `DataMatrix` | `DATA_MATRIX` | `DataMatrix` | `Symbology.DataMatrix` |
| `Aztec` | `AZTEC` | `Aztec` | `Symbology.Aztec` |
| `Pdf417` | `PDF_417` | `Pdf417` | `Symbology.Pdf417` |

**Recommended default set** when the source scanned every format and nothing in the app narrows it: `Symbology.Qr`, `Symbology.Ean13Upca`, `Symbology.Ean8`, `Symbology.Upce`, `Symbology.Code39`, `Symbology.Code93`, `Symbology.Code128`, `Symbology.InterleavedTwoOfFive`, `Symbology.Codabar`, `Symbology.DataMatrix`, `Symbology.Aztec`, `Symbology.Pdf417`.
<!-- END GENERATED symbology-table -->

If you encounter a symbology not in this table, check the BarcodeCapture API reference for the correct `Symbology` enum value before writing the code:
- [.NET Android](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html)
- [.NET iOS](https://docs.scandit.com/data-capture-sdk/dotnet.ios/barcode-capture/api.html)

BarcodeCapture replaces the third-party scanner's camera, preview, and event surface entirely:

- `<scandit:DataCaptureView>` replaces the third-party `<zxing:CameraBarcodeReaderView>` / `<barcodes:CameraView>` XAML control.
- `barcodeCapture.BarcodeScanned += handler` replaces `BarcodesDetected` / `OnDetectionFinished` callbacks.
- `BarcodeCaptureOverlay` (added in `HandlerChanged`) draws the highlight on the preview.
- `DataCaptureContext.ForLicenseKey(key)` replaces any options/initialization block the third-party library required.

---

## Still-image decode

Gallery or file scanning moves to an `ImageFrameSource` that feeds the same `BarcodeCapture` mode.

| Third-party call | Scandit replacement |
|---|---|
| ZXing.Net.Maui `BarcodeReader.Decode(stream, options)` / `DecodeAsync(...)` / `DecodeFromFileAsync(path, ...)` → `BarcodeResult[]` | `await ImageSource.FromFile(path).CreateImageFrameSourceAsync(mauiContext)` (or `ImageSource.FromStream(() => stream)`) → `ImageFrameSource?` |
| BarcodeScanning.Native.Maui `Methods.ScanFromImageAsync(byte[] / FileResult / string / Stream)` → `IReadOnlySet<BarcodeResult>` | Same. For a `FileResult` use `ImageSource.FromFile(file.FullPath)`; for `byte[]` use `ImageSource.FromStream(() => new MemoryStream(bytes))` |
| `BarcodeReaderOptions.Formats` | The `BarcodeCaptureSettings` symbologies (mapping table above) |
| `result.Value` / `result.DisplayValue` | `args.Session.NewlyRecognizedBarcode?.Data` in `BarcodeScanned` |

`CreateImageFrameSourceAsync` is an extension method in `Scandit.DataCapture.Core.Source` (package `Scandit.DataCapture.Core.Maui`, Android and iOS targets). It takes the `IMauiContext` of a loaded element, e.g. `this.Handler.MauiContext` in a page. It returns `null` when the image cannot be loaded: report that as the old "nothing decoded" case.

Steps:

1. Create `BarcodeCapture` on the context with the symbologies enabled, and subscribe to `BarcodeScanned`. An image-only screen needs no `DataCaptureView`, overlay, camera or camera permission, and registers `.UseScanditCore().UseScanditBarcode()`.
2. `await context.SetFrameSourceAsync(imageSource);` and make sure `barcodeCapture.Enabled = true`.
3. `await imageSource.SwitchToDesiredStateAsync(FrameSourceState.On);` The result arrives in `BarcodeScanned`, not as a return value.
4. The source delivers its image once per switch to On. Create a new source per image, and set the camera back as the frame source (`SetFrameSourceAsync(camera)`) before live scanning resumes.

When the old code used the return value (`var results = await BarcodeReader.DecodeAsync(...)`), keep the method's signature and complete a `TaskCompletionSource` of the old return type from `BarcodeScanned`. Nothing signals "no barcode in this image", so finish with `null` after a short timeout (e.g. `Task.WhenAny(tcs.Task, Task.Delay(TimeSpan.FromSeconds(2)))`). After the result or the timeout, clear the pending `TaskCompletionSource` (so a later image cannot complete a stale one) and switch the source Off. List the timeout as a judgment call in the summary. `BarcodeScanned` runs on a background thread, so update UI through `MainThread.BeginInvokeOnMainThread`.

`BarcodeCapture` reports one barcode per image. When the old code read several results from one image (`Multiple = true`, a loop over the result set), use `matrixscan-batch-net-maui` instead.

---

## Preserve

- Custom data models — keep as-is.
- Result accumulation and deduplication logic — move verbatim into the `BarcodeScanned` event handler. Use `MainThread.BeginInvokeOnMainThread(() => …)` to update bound UI properties or call `DisplayAlert`.
- Any downstream business logic triggered on scan result.

---

When done, show only what changed. Do not list APIs that were unchanged. If a still-image path moved to `ImageFrameSource`, say so in the summary and list the timeout as a judgment call. Include the setup checklist from `references/integration.md` so the user knows which NuGet packages to add (all four: Core, Core.Maui, Barcode, Barcode.Maui), the `MauiProgram.cs` builder chain update, and, when the page scans live, the `<scandit:DataCaptureView>` XAML namespace + element and the platform permission entries (`NSCameraUsageDescription` on iOS; `Permissions.Camera` on Android).
