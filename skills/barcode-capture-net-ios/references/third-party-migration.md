# Third-Party Barcode Scanner → BarcodeCapture Migration (.NET for iOS)

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- Which framework is in use (read the `using` directives and `<PackageReference>` lines).
- Which symbologies are enabled.
- What result handling logic exists (deduplication, filtering, accumulation).
- What data models are defined.
- How the scanner is launched (modal view controller, embedded view, AVFoundation pipeline).

Common third-party scanners in .NET iOS codebases:

- **ZXing.Net.Mobile** (`ZXing.Mobile.MobileBarcodeScanner`, `ZXing.BarcodeFormat`) — modal scanner UI, returns `ZXing.Result`.
- **ZXing.Net** — pure decoder, often paired with AVFoundation for camera frames.
- **AVFoundation `AVCaptureMetadataOutput` / `AVMetadataMachineReadableCodeObject`** — Apple's built-in barcode scanning via `AVMetadataObject.TypeQRCode`, `AVMetadataObject.TypeEan13Code`, etc.
- Third-party wrappers around AVFoundation.

---

## Remove

- The third-party `<PackageReference>` entries from the `.csproj` (e.g. `ZXing.Net.Mobile`, `ZXing.Net.Mobile.Forms`).
- All `using ZXing.*;` directives.
- The scanner instance and its setup code.
- Any `AVCaptureSession`, `AVCaptureMetadataOutput`, `IAVCaptureMetadataOutputObjectsDelegate` / `AVCaptureMetadataOutputObjectsDelegate` plumbing — `DataCaptureView` replaces all of it.
- Any UI code specific to the old scanner (modal presentation, preview layer, overlay it provided).

---

## Integrate BarcodeCapture

Follow `references/integration.md`. When configuring `BarcodeCaptureSettings`, map symbologies from the old scanner using the table below. **Do not guess or derive Scandit symbology names from the old library's names** — they differ (e.g. ZXing's `QR_CODE` maps to `Symbology.Qr`, not `Symbology.QrCode`).

### Symbology mapping

| ZXing.Net / ZXing.Net.Mobile `BarcodeFormat` | AVFoundation `AVMetadataObject.Type*` | Scandit `Symbology.*` |
|---|---|---|
| `QR_CODE` | `TypeQRCode` | `Symbology.Qr` |
| `EAN_13` | `TypeEAN13Code` | `Symbology.Ean13Upca` |
| `EAN_8` | `TypeEAN8Code` | `Symbology.Ean8` |
| `UPC_A` | (no direct type; subset of EAN-13) | `Symbology.Ean13Upca` |
| `UPC_E` | `TypeUPCECode` | `Symbology.Upce` |
| `CODE_39` | `TypeCode39Code` | `Symbology.Code39` |
| `CODE_93` | `TypeCode93Code` | `Symbology.Code93` |
| `CODE_128` | `TypeCode128Code` | `Symbology.Code128` |
| `ITF` | `TypeITF14Code` (note: ITF-14 is a fixed-length subset) | `Symbology.InterleavedTwoOfFive` |
| `CODABAR` | (no AVFoundation equivalent) | `Symbology.Codabar` |
| `DATA_MATRIX` | `TypeDataMatrixCode` | `Symbology.DataMatrix` |
| `AZTEC` | `TypeAztecCode` | `Symbology.Aztec` |
| `PDF_417` | `TypePDF417Code` | `Symbology.Pdf417` |

If you encounter a symbology not in this table, check the [BarcodeCapture API reference](https://docs.scandit.com/data-capture-sdk/dotnet.ios/barcode-capture/api.html) for the correct `Symbology` enum value before writing the code.

BarcodeCapture replaces the third-party scanner's camera and preview entirely — `DataCaptureView` becomes the live preview, and `BarcodeCaptureOverlay` draws the highlight. The view controller no longer needs to manage `AVCaptureSession` or a separate preview layer.

---

## Preserve

- Custom data models — keep as-is.
- Result accumulation and deduplication logic — move verbatim into the `OnBarcodeScanned` callback (or the `BarcodeScanned` event handler). Remember to dispatch UI updates via `DispatchQueue.MainQueue.DispatchAsync` and call `frameData.Dispose()` before returning.
- Any downstream business logic triggered on scan result.

---

When done, show only what changed. Do not list APIs that were unchanged. Include the setup checklist from `references/integration.md` so the user knows which NuGet packages and Info.plist key to add.
