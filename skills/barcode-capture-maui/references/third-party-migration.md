# Third-Party Barcode Scanner → BarcodeCapture Migration (.NET MAUI)

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

---

## Integrate BarcodeCapture

Follow `references/integration.md`. When configuring `BarcodeCaptureSettings`, map symbologies from the old scanner using the table below. **Do not guess or derive Scandit symbology names from the old library's names** — they differ (e.g. ZXing's `QR_CODE` maps to `Symbology.Qr`, not `Symbology.QrCode`).

### Symbology mapping

| ZXing.Net.Maui `BarcodeFormat` / ZXing `BarcodeFormat` | BarcodeScanning.Native.Maui `BarcodeFormats` | Scandit `Symbology.*` |
|---|---|---|
| `QrCode` / `QR_CODE` | `QrCode` | `Symbology.Qr` |
| `Ean13` / `EAN_13` | `Ean13` | `Symbology.Ean13Upca` |
| `Ean8` / `EAN_8` | `Ean8` | `Symbology.Ean8` |
| `UpcA` / `UPC_A` | `UpcA` | `Symbology.Ean13Upca` (UPC-A is a subset of EAN-13/UPC-A in Scandit) |
| `UpcE` / `UPC_E` | `UpcE` | `Symbology.Upce` |
| `Code39` / `CODE_39` | `Code39` | `Symbology.Code39` |
| `Code93` / `CODE_93` | `Code93` | `Symbology.Code93` |
| `Code128` / `CODE_128` | `Code128` | `Symbology.Code128` |
| `Itf` / `ITF` | `Itf` | `Symbology.InterleavedTwoOfFive` |
| `Codabar` / `CODABAR` | `Codabar` | `Symbology.Codabar` |
| `DataMatrix` / `DATA_MATRIX` | `DataMatrix` | `Symbology.DataMatrix` |
| `Aztec` / `AZTEC` | `Aztec` | `Symbology.Aztec` |
| `Pdf417` / `PDF_417` | `Pdf417` | `Symbology.Pdf417` |

If you encounter a symbology not in this table, check the BarcodeCapture API reference for the correct `Symbology` enum value before writing the code:
- [.NET Android](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html)
- [.NET iOS](https://docs.scandit.com/data-capture-sdk/dotnet.ios/barcode-capture/api.html)

BarcodeCapture replaces the third-party scanner's camera, preview, and event surface entirely:

- `<scandit:DataCaptureView>` replaces the third-party `<zxing:CameraBarcodeReaderView>` / `<barcodes:CameraView>` XAML control.
- `barcodeCapture.BarcodeScanned += handler` replaces `BarcodesDetected` / `OnDetectionFinished` callbacks.
- `BarcodeCaptureOverlay` (added in `HandlerChanged`) draws the highlight on the preview.
- `DataCaptureContext.ForLicenseKey(key)` replaces any options/initialization block the third-party library required.

---

## Preserve

- Custom data models — keep as-is.
- Result accumulation and deduplication logic — move verbatim into the `BarcodeScanned` event handler. Use `MainThread.BeginInvokeOnMainThread(() => …)` to update bound UI properties or call `DisplayAlert`.
- Any downstream business logic triggered on scan result.

---

When done, show only what changed. Do not list APIs that were unchanged. Include the setup checklist from `references/integration.md` so the user knows which NuGet packages to add (all four: Core, Core.Maui, Barcode, Barcode.Maui), the `MauiProgram.cs` builder chain update, the `<scandit:DataCaptureView>` XAML namespace + element, and the platform permission entries (`NSCameraUsageDescription` on iOS; `Permissions.Camera` on Android).
