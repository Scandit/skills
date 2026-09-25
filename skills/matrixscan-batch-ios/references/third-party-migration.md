# Third-Party Multi-Barcode Scanner → MatrixScan Batch Migration (iOS)

This guide covers replacing a custom multi-barcode scanner — most commonly **AVFoundation** (`AVCaptureMetadataOutput`) or Apple's **VisionKit** `DataScannerViewController` — with Scandit MatrixScan Batch (`BarcodeBatch`). BarcodeBatch is the right Scandit mode here because it tracks **every visible barcode simultaneously** on each frame, which matches what these multi-barcode APIs do (a single-scan use case should use BarcodeCapture or SparkScan instead).

## Before Anything Else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:
- Which framework is in use (read the imports — `AVFoundation`, `Vision`/`VisionKit`, a third-party SDK).
- Which symbologies are enabled (e.g. the `metadataObjectTypes` array, or the recognized item types).
- The result-handling logic: deduplication, accumulation, filtering, per-barcode UI.
- What data models are defined (e.g. a `ScannedBarcode` struct and the collection it feeds).
- How the scanner view is presented (embedded, modal, full-screen).

## Remove

- The old framework's imports (`import AVFoundation`, `import VisionKit`, etc.).
- The capture-session / scanner instance and all its setup (`AVCaptureSession`, `AVCaptureDeviceInput`, `AVCaptureMetadataOutput`, `AVCaptureVideoPreviewLayer`, or `DataScannerViewController`).
- The old delegate/callback conformance (`AVCaptureMetadataOutputObjectsDelegate` and its `metadataOutput(_:didOutput:from:)`, or `DataScannerViewControllerDelegate`).
- The old preview/presentation layer — `BarcodeBatch` draws into a `DataCaptureView` instead.

## Integrate MatrixScan Batch

Follow `references/integration.md` for the full integration. The MatrixScan-Batch-specific points for a migration:

- **Map the symbologies.** Translate the old type list into `BarcodeBatchSettings`. Scandit names differ from Apple's — verify each against the [BarcodeBatch API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html) rather than guessing. Common AVFoundation mappings:

  | AVFoundation `AVMetadataObject.ObjectType` | Scandit `Symbology` |
  |---|---|
  | `.ean13` | `.ean13UPCA` |
  | `.ean8` | `.ean8` |
  | `.code128` | `.code128` |
  | `.code39` | `.code39` |
  | `.code93` | `.code93` |
  | `.qr` | `.qr` |
  | `.pdf417` | `.pdf417` |
  | `.dataMatrix` | `.dataMatrix` |
  | `.aztec` | `.aztec` |
  | `.upce` | `.upce` |
  | `.itf14` | `.interleavedTwoOfFive` |

  Note that AVFoundation's `.ean13` maps to Scandit `.ean13UPCA` (EAN-13 and UPC-A share an encoding in Scandit).

- **Move the result loop into the listener.** AVFoundation reported every barcode in frame on each `metadataOutput(_:didOutput:from:)` call; BarcodeBatch reports deltas via `barcodeBatch(_:didUpdate:frameData:)`. The natural equivalent of "I just saw this barcode" is **`session.addedTrackedBarcodes`** (the barcodes newly tracked this frame). Read each `TrackedBarcode`'s `barcode.data` and `barcode.symbology`.

- **Respect threading.** `metadataOutput(_:didOutput:from:)` was delivered on the queue you chose (often `.main`). `barcodeBatch(_:didUpdate:frameData:)` always runs on a **background queue** — copy the data you need out of the session, then `DispatchQueue.main.async {}` for any UI or model mutation. Do not hold session-collection references outside the callback.

- **Dedup unchanged.** If the old code kept a `Set` of seen values (or keyed on tracking identity), keep that logic verbatim — feed it from `session.addedTrackedBarcodes` instead of the AVFoundation metadata objects.

## Preserve

- Custom data models (e.g. a `ScannedBarcode` struct) — keep as-is.
- The accumulation collection and deduplication logic — move it verbatim into the `barcodeBatch(_:didUpdate:frameData:)` flow (dispatched to main).
- Any downstream business logic triggered when a barcode is recorded.

## After

Show the setup checklist from `references/integration.md` (SPM packages, `NSCameraUsageDescription`, license-key placeholder), then a summary with **Removed** and **Added** sections listing only what changed. Do not list APIs that were unchanged.
