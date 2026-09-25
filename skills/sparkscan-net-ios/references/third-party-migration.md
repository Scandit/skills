# Third-Party Barcode Scanner → SparkScan Migration (.NET for iOS)

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
- The scanner instance, its setup code, the callback / listener conformance.
- Any `AVCaptureSession`, `AVCaptureMetadataOutput`, `IAVCaptureMetadataOutputObjectsDelegate` / `AVCaptureMetadataOutputObjectsDelegate` plumbing — `SparkScanView` replaces all of it.
- Any UI code specific to the old scanner (modal presentation, preview layer, overlay it provided).

SparkScan replaces the third-party scanner's camera, preview, and UI entirely. There is no separate camera setup or `DataCaptureView` to wire up — `SparkScanView` owns its own camera and overlays the trigger button on top of the host view controller's view.

---

## Integrate SparkScan

Follow `references/integration.md`. When configuring `SparkScanSettings`, map symbologies from the old scanner using the table below. **Do not guess or derive Scandit symbology names from the old library's names** — they differ (e.g. ZXing's `QR_CODE` maps to `Symbology.Qr`, not `Symbology.QrCode`).

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

If you encounter a symbology not in this table, check the [SparkScan API reference](https://docs.scandit.com/data-capture-sdk/dotnet.ios/barcode-capture/api.html) for the correct `Symbology` enum value before writing the code.

---

## Preserve

- Custom data models — keep as-is.
- Result accumulation and deduplication logic — move verbatim into the `BarcodeScanned` event handler (or `ISparkScanListener.OnBarcodeScanned`). Wrap UI updates in `DispatchQueue.MainQueue.DispatchAsync(() => { … })` because the SparkScan callback runs on a background thread.
- Always dispose any image buffers you read from `SparkScanEventArgs.FrameData`: `using var imageBuffer = args.FrameData?.ImageBuffers.LastOrDefault();`.
- Any downstream business logic triggered on scan result.
- Validation / reject behavior — if the old scanner displayed an error for invalid codes, port that logic into `ISparkScanFeedbackDelegate.GetFeedbackForBarcode(Barcode)`, returning a `SparkScanBarcodeErrorFeedback("...", TimeSpan.FromSeconds(...))`.

---

When done, show only what changed. Do not list APIs that were unchanged. Include the setup checklist from `references/integration.md` so the user knows which NuGet packages, `Info.plist` key (`NSCameraUsageDescription`), and `AppDelegate` initialization (SDK 8.0+) to add.
