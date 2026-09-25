# Third-Party Multi-Barcode Scanner → BarcodeBatch (MatrixScan Batch) Migration

This guide covers replacing a per-frame multi-barcode scanner — most commonly **Google ML Kit barcode scanning** (`com.google.mlkit.vision.barcode`) — with Scandit MatrixScan Batch (`BarcodeBatch`). ML Kit returns a `List<Barcode>` per frame but has no built-in cross-frame tracking; BarcodeBatch tracks each physical barcode across frames with a stable identifier, which is the main reason to migrate.

## Before Anything Else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:
- Which framework is in use (read the imports — e.g. `com.google.mlkit.vision.barcode.BarcodeScanning`).
- Which barcode formats are enabled (e.g. `Barcode.FORMAT_*` passed to `BarcodeScannerOptions`).
- What result handling exists (deduplication, accumulation into a list, filtering).
- What data models are defined.
- How frames are fed in (typically a CameraX `ImageAnalysis` analyzer building an `InputImage`).

---

## Remove

- The ML Kit imports and dependency (`com.google.android.gms:play-services-mlkit-barcode-scanning` / `com.google.mlkit:barcode-scanning`).
- The `BarcodeScanner` / `BarcodeScanning.getClient(...)` instance and its `BarcodeScannerOptions`.
- The `InputImage` construction and the `scanner.process(image)` success/complete listeners.
- The CameraX `ImageAnalysis` pipeline that fed frames to ML Kit — BarcodeBatch manages its own camera and preview via `DataCaptureView`.

---

## Integrate BarcodeBatch

Follow `references/integration.md` for the full setup (DataCaptureContext, manual Camera with `BarcodeBatch.createRecommendedCameraSettings()`, `DataCaptureView`, `BarcodeBatchBasicOverlay`, and a `BarcodeBatchListener`).

When configuring `BarcodeBatchSettings`, map the ML Kit formats using the table below. **Do not guess Scandit symbology names from the ML Kit names** — they differ (ML Kit's `FORMAT_QR_CODE` maps to `Symbology.QR`, not `Symbology.QR_CODE`).

### Symbology mapping

| ML Kit format (`Barcode.*`) | Scandit `Symbology.*` |
|---|---|
| `FORMAT_QR_CODE` | `Symbology.QR` |
| `FORMAT_EAN_13` | `Symbology.EAN13_UPCA` |
| `FORMAT_EAN_8` | `Symbology.EAN8` |
| `FORMAT_UPC_A` | `Symbology.EAN13_UPCA` (UPC-A is a subset of EAN-13/UPC-A) |
| `FORMAT_UPC_E` | `Symbology.UPCE` |
| `FORMAT_CODE_39` | `Symbology.CODE39` |
| `FORMAT_CODE_93` | `Symbology.CODE93` |
| `FORMAT_CODE_128` | `Symbology.CODE128` |
| `FORMAT_ITF` | `Symbology.INTERLEAVED_TWO_OF_FIVE` |
| `FORMAT_CODABAR` | `Symbology.CODABAR` |
| `FORMAT_DATA_MATRIX` | `Symbology.DATA_MATRIX` |
| `FORMAT_AZTEC` | `Symbology.AZTEC` |
| `FORMAT_PDF417` | `Symbology.PDF417` |
| `FORMAT_ALL_FORMATS` | enable each symbology the app actually needs (do not blindly enable everything — enabling only what is needed improves tracking accuracy) |

If you encounter a format not in this table, check the [BarcodeBatch API reference](https://docs.scandit.com/data-capture-sdk/android/barcode-capture/api.html) for the correct `Symbology` value before writing the code.

---

## Map the result-handling logic

ML Kit gives you a flat `List<Barcode>` every frame, so apps usually dedup by `rawValue`. BarcodeBatch gives you a `BarcodeBatchSession` in `onSessionUpdated(mode, session, data)` with proper tracking:

- Iterate `session.addedTrackedBarcodes` (newly tracked this frame) instead of re-processing every barcode every frame.
- Each `TrackedBarcode` has a stable `identifier` (`Int`) and its decoded `barcode.data`. **Prefer deduplicating by `identifier`** — it is more robust than value-based dedup because the same physical code keeps one identifier across frames. If the app's contract is strictly "unique values", you can still dedup by `barcode.data`, but key your own collection by tracking identifier where possible.
- Use `session.removedTrackedBarcodes` (a `List<Int>` of identifiers) if the UI should drop barcodes that leave the view.

`onSessionUpdated` runs on a **recognition thread**. Copy the data you need out of the session, then dispatch UI work via `runOnUiThread {}`. Never touch the session outside the callback.

```kotlin
override fun onSessionUpdated(
    mode: BarcodeBatch,
    session: BarcodeBatchSession,
    data: FrameData
) {
    val newlyTracked = session.addedTrackedBarcodes.map { it.identifier to it.barcode.data }
    runOnUiThread {
        for ((id, value) in newlyTracked) {
            if (scannedValues.none { it == value }) {
                scannedValues.add(value) // preserve the app's existing accumulation/dedup
            }
        }
    }
}
```

---

## Preserve

- Custom data models — keep as-is.
- The accumulation / deduplication collection (e.g. `scannedValues`) and any downstream business logic — move it verbatim into `onSessionUpdated`, switching the source from the ML Kit `Barcode` list to the tracked-barcode deltas.

---

## After integrating

1. Show the setup checklist from `references/integration.md` (Gradle dependencies with a concrete version, `CAMERA` manifest entry + runtime permission, license key).
2. Show the user a summary of only what changed: ML Kit APIs removed, BarcodeBatch APIs added, and the symbology mapping applied. Do not list anything that was unchanged.
