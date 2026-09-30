# Third-Party Barcode Scanner → BarcodeCapture Migration

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
- How the scanner is launched (Activity, Fragment, intent-based, embedded view)

---

## Remove

- The old framework's imports and dependencies
- The scanner class instance and all its setup code
- The old callback, listener, or `onActivityResult` override
- Any UI code specific to the old scanner (e.g. intent launch, dialog, overlay the old library provided)

---

## Integrate BarcodeCapture

Follow `references/integration.md`. When configuring `BarcodeCaptureSettings`, map the symbologies from the old scanner using the table below. **Do not guess or derive Scandit symbology names from the old library's names** — the names differ (e.g. ZXing's `QR_CODE` maps to `Symbology.QR`, not `Symbology.QR_CODE`).

### Symbology mapping

| ZXing / ML Kit name | Scandit `Symbology.*` |
|---|---|
| `QR_CODE` / `FORMAT_QR_CODE` | `Symbology.QR` |
| `EAN_13` / `FORMAT_EAN_13` | `Symbology.EAN13_UPCA` |
| `EAN_8` / `FORMAT_EAN_8` | `Symbology.EAN8` |
| `UPC_A` / `FORMAT_UPC_A` | `Symbology.EAN13_UPCA` (UPC-A is a subset of EAN-13/UPC-A) |
| `UPC_E` / `FORMAT_UPC_E` | `Symbology.UPCE` |
| `CODE_39` / `FORMAT_CODE_39` | `Symbology.CODE39` |
| `CODE_93` / `FORMAT_CODE_93` | `Symbology.CODE93` |
| `CODE_128` / `FORMAT_CODE_128` | `Symbology.CODE128` |
| `ITF` / `FORMAT_ITF` | `Symbology.INTERLEAVED_TWO_OF_FIVE` |
| `CODABAR` / `FORMAT_CODABAR` | `Symbology.CODABAR` |
| `DATA_MATRIX` / `FORMAT_DATA_MATRIX` | `Symbology.DATA_MATRIX` |
| `AZTEC` / `FORMAT_AZTEC` | `Symbology.AZTEC` |
| `PDF_417` / `FORMAT_PDF417` | `Symbology.PDF417` |

If you encounter a symbology not in this table, check the [BarcodeCapture API reference](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html) for the correct `Symbology` enum value before writing the code.

BarcodeCapture replaces the old scanner's camera and preview entirely — `DataCaptureView` becomes the new content view, and `BarcodeCaptureOverlay` draws the highlight. The Activity no longer needs to manage a separate camera or preview widget.

---

## Preserve

- Custom data models — keep as-is
- Result accumulation and deduplication logic — move verbatim into the `onBarcodeScanned` callback
- Any downstream business logic triggered on scan result

---

When done, show only what changed. Do not list APIs that were unchanged.
