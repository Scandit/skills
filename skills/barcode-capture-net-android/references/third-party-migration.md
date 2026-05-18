# Third-Party Barcode Scanner → BarcodeCapture Migration (.NET for Android)

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
- **Plugin.Maui.Audio** / **CommunityToolkit.Mvvm BarcodeReader** wrappers.

---

## Remove

- The third-party `<PackageReference>` entries from the `.csproj` (e.g. `ZXing.Net.Mobile`, `ZXing.Net.Mobile.Forms`, `Xamarin.Google.MLKit.BarcodeScanning`).
- All `using ZXing.*;` / `using Google.MLKit.*;` directives.
- The scanner instance and its setup code.
- Any `OnActivityResult` override that handled the scanner's return intent.
- Any UI code specific to the old scanner (intent launch, dialog, overlay it provided).

---

## Integrate BarcodeCapture

Follow `references/integration.md`. When configuring `BarcodeCaptureSettings`, map symbologies from the old scanner using the table below. **Do not guess or derive Scandit symbology names from the old library's names** — they differ (e.g. ZXing's `QR_CODE` maps to `Symbology.Qr`, not `Symbology.QrCode`).

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

If you encounter a symbology not in this table, check the [BarcodeCapture API reference](https://docs.scandit.com/data-capture-sdk/dotnet.android/barcode-capture/api.html) for the correct `Symbology` enum value before writing the code.

BarcodeCapture replaces the third-party scanner's camera and preview entirely — `DataCaptureView` becomes the live preview, and `BarcodeCaptureOverlay` draws the highlight. The activity no longer needs to manage a separate camera, preview widget, or intent round-trip.

---

## Preserve

- Custom data models — keep as-is.
- Result accumulation and deduplication logic — move verbatim into the `OnBarcodeScanned` callback (or the `BarcodeScanned` event handler).
- Any downstream business logic triggered on scan result.

---

When done, show only what changed. Do not list APIs that were unchanged. Include the setup checklist from `references/integration.md` so the user knows which NuGet packages, manifest entries, and runtime permission to add.
