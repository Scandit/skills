# Third-Party Barcode Scanner → BarcodeCapture Migration (iOS)

## Before Anything Else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:
- Which framework is in use (read the imports — `AVFoundation`, `VisionKit`, `Vision`, `MLKit`, `ZXing`, etc.)
- Which symbologies are enabled
- What result handling logic exists (deduplication, filtering, accumulation)
- What data models are defined
- How the scanner is presented (modal, embedded view, full-screen, navigation push)

---

## Remove

- The old framework's imports
- The scanner / detector class instance and all its setup code
- The old delegate or callback conformance (`AVCaptureMetadataOutputObjectsDelegate`, `DataScannerViewControllerDelegate`, etc.)
- Any UI presentation code specific to the old scanner (modal presentation of `DataScannerViewController`, `AVCaptureVideoPreviewLayer` setup, ZXing capture-session wiring)
- Workaround flags such as `scannerPresented`, `isScannerActive` that only existed to compensate for the old scanner's lifecycle

---

## Integrate BarcodeCapture

Follow `references/integration.md`. When configuring `BarcodeCaptureSettings`, map the symbologies from the old scanner using the table below. **Do not guess or derive Scandit symbology names from the old framework's names** — the names differ (e.g. `AVMetadataObject.ObjectType.qr` maps to `Symbology.qr`, not `Symbology.qrCode`).

### Symbology mapping

| AVFoundation / VisionKit / MLKit name | Scandit `Symbology.*` |
|---|---|
| `.qr` / `.qrCode` / `FORMAT_QR_CODE` | `.qr` |
| `.ean13` / `FORMAT_EAN_13` | `.ean13UPCA` |
| `.ean8` / `FORMAT_EAN_8` | `.ean8` |
| `.upce` / `FORMAT_UPC_E` | `.upce` |
| UPC-A (subset of EAN-13) | `.ean13UPCA` |
| `.code39` / `FORMAT_CODE_39` | `.code39` |
| `.code93` / `FORMAT_CODE_93` | `.code93` |
| `.code128` / `FORMAT_CODE_128` | `.code128` |
| `.itf14` / `.interleaved2of5` / `FORMAT_ITF` | `.interleavedTwoOfFive` |
| `.codabar` / `FORMAT_CODABAR` | `.codabar` |
| `.dataMatrix` / `FORMAT_DATA_MATRIX` | `.dataMatrix` |
| `.aztec` / `FORMAT_AZTEC` | `.aztec` |
| `.pdf417` / `FORMAT_PDF417` | `.pdf417` |

If you encounter a symbology not in this table, check the [BarcodeCapture API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html) for the correct `Symbology` enum value before writing the code.

BarcodeCapture replaces the old scanner's camera and preview entirely — `DataCaptureView` becomes the new preview surface, and `BarcodeCaptureOverlay` draws the highlight. The view controller no longer needs to manage a separate `AVCaptureSession` or preview layer.

---

## Preserve

- Custom data models — keep as-is
- Result accumulation and deduplication logic — move verbatim into the `barcodeCapture(_:didScanIn:frameData:)` callback
- Any downstream business logic triggered on scan result (UI updates, network calls, navigation)

---

When done, show only what changed. Do not list APIs that were unchanged.
