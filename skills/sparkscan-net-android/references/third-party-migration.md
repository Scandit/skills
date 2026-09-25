# Third-Party Barcode Scanner → SparkScan Migration (.NET for Android)

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- Which framework is in use (read the `using` directives and `<PackageReference>` lines).
- Which symbologies are enabled.
- What result handling logic exists (deduplication, filtering, accumulation).
- What data models are defined.
- How the scanner is launched (Activity, Fragment, intent-based, embedded view).

Common third-party scanners in .NET Android codebases:

- **ZXing.Net.Mobile** (`ZXing.Mobile.MobileBarcodeScanner`, `ZXing.BarcodeFormat`) — usually intent-based, returns `ZXing.Result`.
- **ZXing.Net** — pure decoder, often paired with a custom camera preview.
- **Google ML Kit barcode scanning** via Xamarin/MAUI bindings (`Xamarin.Google.MLKit.BarcodeScanning`).

---

## Remove

- The third-party `<PackageReference>` entries from the `.csproj` (e.g. `ZXing.Net.Mobile`, `ZXing.Net.Mobile.Forms`, `Xamarin.Google.MLKit.BarcodeScanning`).
- All `using ZXing.*;` / `using Google.MLKit.*;` directives.
- The scanner instance, its setup code, the callback / listener conformance, and any `OnActivityResult` override that handled the scanner's return intent.
- Any UI code specific to the old scanner (intent launch, dialog, overlay, custom camera preview Activity / Fragment).

SparkScan replaces the third-party scanner's camera, preview, and UI entirely. There is no separate camera setup or `DataCaptureView` to wire up — `SparkScanView` owns its own camera and overlays the trigger button on top of the host activity's layout.

---

## Integrate SparkScan

Follow `references/integration.md`. When configuring `SparkScanSettings`, map symbologies from the old scanner using the table below. **Do not guess or derive Scandit symbology names from the old library's names** — they differ (e.g. ZXing's `QR_CODE` maps to `Symbology.Qr`, not `Symbology.QrCode`).

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

If you encounter a symbology not in this table, check the [SparkScan API reference](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html) for the correct `Symbology` enum value before writing the code.

The activity layout must be wrapped in `<com.scandit.datacapture.barcode.spark.ui.SparkScanCoordinatorLayout>` so that the trigger button and mini preview are positioned correctly. See `references/integration.md` Step 5.

---

## Preserve

- Custom data models — keep as-is.
- Result accumulation and deduplication logic — move verbatim into the `BarcodeScanned` event handler (or `ISparkScanListener.OnBarcodeScanned`). Wrap UI updates in `RunOnUiThread(() => { … })` because the SparkScan callback runs on a background thread.
- Any downstream business logic triggered on scan result.
- Validation / reject behavior — if the old scanner displayed an error for invalid codes, port that logic into `ISparkScanFeedbackDelegate.GetFeedbackForBarcode(Barcode)`, returning a `SparkScanBarcodeErrorFeedback("...", TimeSpan.FromSeconds(...))`.

---

When done, show only what changed. Do not list APIs that were unchanged. Include the setup checklist from `references/integration.md` so the user knows which NuGet packages, manifest entries, runtime permission flow, and layout container (`SparkScanCoordinatorLayout`) to add.
