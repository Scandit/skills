# Third-Party Barcode Scanner → BarcodeCapture Migration (iOS)

## Before Anything Else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:
- Which framework is in use (read the imports)
- Which symbologies are enabled
- What result handling logic exists (deduplication, filtering, accumulation)
- What data models are defined
- How the scanner is presented (modal, embedded, full-screen, navigation push)

## Remove

- The old framework's imports
- The scanner / detector class instance and all its setup code
- The old delegate or callback conformance
- Any UI presentation code specific to the old scanner (e.g. modal presentation, `AVCaptureVideoPreviewLayer`, intent launch)

## Integrate BarcodeCapture

Follow `references/integration.md`. When configuring `BarcodeCaptureSettings`, map the symbologies from the old scanner. Scandit symbology names differ from other libraries — verify each one against the [BarcodeCapture API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html) rather than guessing from the old framework's name.

## Preserve

- Custom data models — keep as-is
- Result accumulation and deduplication logic — move verbatim into the `barcodeCapture(_:didScanIn:frameData:)` callback
- Any downstream business logic triggered on scan result

When done, show only what changed. Do not list APIs that were unchanged.
