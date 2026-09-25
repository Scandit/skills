# Third-Party Barcode Scanner → BarcodeCapture Migration (iOS)

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and replace only the third-party scanner calls underneath with Scandit ones.

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
