# Third-Party Multi-Barcode Scanner → MatrixScan Batch Migration (Web)

This guide covers migrating a web app from **ZXing-js** (`@zxing/library`, also published as `@zxing/browser`) — the most common third-party multi-format browser scanner — to Scandit MatrixScan Batch (`BarcodeBatch*`).

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- Which package is in use (read the `import` statements and `package.json`): `@zxing/library` (older, ships the readers + a `BrowserMultiFormatReader`) or `@zxing/browser` (the newer browser-only split, `BrowserMultiFormatReader` lives here).
- Which formats are enabled — usually via `DecodeHintType.POSSIBLE_FORMATS` set to a list of `BarcodeFormat` values, or left unset (all formats).
- How the app collects barcodes — ZXing-js has no per-frame *multi*-barcode tracking; apps emulate "batch" by calling `decodeFromVideoDevice` / `decodeFromConstraints` in a continuous callback and accumulating distinct `result.getText()` values in a `Set`/array, deduplicating on the decoded string.
- What result-handling logic exists (dedup on the string value, accumulation, filtering by format/prefix).
- What data models are defined (interfaces/types holding the scanned info).

> **Key conceptual difference:** ZXing-js decodes **one** barcode per frame and reports it through a callback; "scanning many barcodes" is the app re-invoking the decoder in a loop and accumulating results. MatrixScan Batch genuinely tracks **all** visible barcodes simultaneously every frame, assigning each a **stable per-barcode tracking ID**, and reports additions / updates / removals via `IBarcodeBatchListener.didUpdateSession`. There is no decode loop to re-trigger — the session updates fire on their own.

MatrixScan Batch owns the camera and renders through a `DataCaptureView`, so the old `<video>` element, the `getUserMedia` plumbing, and any hand-drawn highlight `<canvas>` are all replaced.

---

## Remove

- The `@zxing/library` / `@zxing/browser` `import`s and the `<PackageReference>` (`dependencies`) entries from `package.json`.
- The `BrowserMultiFormatReader` (or `BrowserQRCodeReader` / `MultiFormatReader`) instance and its `decodeFromVideoDevice` / `decodeFromConstraints` / `decodeFromVideoElement` call.
- The `DecodeHintType` / `BarcodeFormat` hint configuration.
- The callback's continuous-scan re-trigger and any `reader.reset()` / `controls.stop()` teardown that exists only to restart decoding.
- The raw `<video>` element and the `navigator.mediaDevices.getUserMedia` setup ZXing drove — `DataCaptureView` + the Scandit `Camera` own the preview now.
- Any manually-drawn highlight canvas/overlay — replaced by `BarcodeBatchBasicOverlay` (or `BarcodeBatchAdvancedOverlay`).

---

## Integrate MatrixScan Batch

Follow `references/integration.md`. The key shape of the rewrite:

1. **Replace the `<video>` element with a `DataCaptureView` mount point.** Add a sized, positioned `<div id="data-capture-view">` and `view.connectToElement(...)` it.
2. **Initialize the context with `DataCaptureContext.forLicenseKey(...)`** and the `barcodeCaptureLoader()` module loader.
3. **Replace the ZXing format hints with `BarcodeBatchSettings`** using the symbology mapping table below.
4. **Replace the per-result decode callback with `IBarcodeBatchListener.didUpdateSession`.** Iterate `session.addedTrackedBarcodes` for codes new this frame.
5. **Replace any manually-drawn highlight with `BarcodeBatchBasicOverlay`** (`withBarcodeBatchForViewWithStyle`).
6. **Set the cross-origin isolation (COOP/COEP) headers** — MatrixScan Batch requires browser multithreading (ZXing-js does not), so this is a new, mandatory requirement. See `references/integration.md`.

When configuring `BarcodeBatchSettings`, map formats from ZXing using the table below. **Do not guess or derive Scandit symbology names from ZXing's `BarcodeFormat` names** — they differ (e.g. ZXing's `QR_CODE` maps to `Symbology.QR` on web, ZXing's `EAN_13` and `UPC_A` both map to `Symbology.EAN13UPCA`).

### Symbology mapping

| ZXing-js `BarcodeFormat` | Scandit `Symbology` (Web) |
|---|---|
| `QR_CODE` | `Symbology.QR` |
| `EAN_13` | `Symbology.EAN13UPCA` |
| `EAN_8` | `Symbology.EAN8` |
| `UPC_A` | `Symbology.EAN13UPCA` (UPC-A is decoded by the EAN-13/UPC-A symbology) |
| `UPC_E` | `Symbology.UPCE` |
| `CODE_39` | `Symbology.Code39` |
| `CODE_93` | `Symbology.Code93` |
| `CODE_128` | `Symbology.Code128` |
| `ITF` | `Symbology.InterleavedTwoOfFive` |
| `CODABAR` | `Symbology.Codabar` |
| `DATA_MATRIX` | `Symbology.DataMatrix` |
| `AZTEC` | `Symbology.Aztec` |
| `PDF_417` | `Symbology.PDF417` |

> **Note on the web `Symbology` enum casing:** web uses `Symbology.QR` (the value `"qr"`) — **not** `Symbology.QrCode` (which does not exist) and not `Symbology.Qr` (that is the .NET/native form). Note also that some members are all-caps on web: `Symbology.PDF417`, `Symbology.UPCE`, `Symbology.EAN13UPCA`. When in doubt, check the BarcodeBatch API reference linked in `SKILL.md` before writing the code.

### Result-pattern mapping

| ZXing-js concept | MatrixScan Batch equivalent |
|---|---|
| `decodeFromVideoDevice(deviceId, videoEl, (result, err) => …)` continuous callback | `barcodeBatch.addListener({ didUpdateSession: (_mode, session) => … })` — fires every processed frame, no re-trigger. |
| `result.getText()` | `trackedBarcode.barcode.data` |
| `result.getBarcodeFormat()` | `trackedBarcode.barcode.symbology` (a `Symbology` enum value) |
| `result.getResultPoints()` (corner points) | `trackedBarcode.location` (`Quadrilateral` in image-space; the basic overlay draws the highlight for you, or use `view.viewQuadrilateralForFrameQuadrilateral(location)` to convert to view space) |
| "Have I seen this text yet?" (manual `Set<string>` dedupe on `getText()`) | `trackedBarcode.identifier` is the stable per-barcode tracking ID. New barcodes appear in `session.addedTrackedBarcodes`; the same physical code keeps the same identifier across frames until it leaves the view. Keep a `Set<number>` of seen identifiers for an "ever seen" set, or accumulate `barcode.data` from `addedTrackedBarcodes`. |
| "Which barcodes are visible right now?" | `session.trackedBarcodes` — `Record<string, TrackedBarcode>` keyed by tracking ID; iterate with `Object.values(...)`. |
| Barcodes that left the view | `session.removedTrackedBarcodes` — `string[]` of identifiers; `Number.parseInt(id, 10)` to match `Set<number>` keys. |

---

## Preserve

- Custom data models — keep as-is (an `interface ScannedBarcode { value: string; format: string; }` moves verbatim).
- Result accumulation and deduplication logic — move it into `didUpdateSession`. Iterate `session.addedTrackedBarcodes`, dedupe on `trackedBarcode.identifier` (or `barcode.data`), and append to the existing collection.
- Any downstream business logic triggered on a new barcode (network lookup, UI list append).
- Validation / reject behavior — if the old scanner had an "is this code valid?" check before accepting a result, port it as a filter when iterating `addedTrackedBarcodes`.

---

## Putting it all together

A typical "ZXing-js continuous multi-scan replaced with MatrixScan Batch" module shape:

```typescript
import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
} from "@scandit/web-datacapture-core";
import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchSettings,
  barcodeCaptureLoader,
  Symbology,
} from "@scandit/web-datacapture-barcode";

// Preserved data model — unchanged from the ZXing version.
interface ScannedBarcode {
  value: string;
  format: string;
}

const scannedBarcodes: ScannedBarcode[] = [];
const seenIdentifiers = new Set<number>(); // replaces the old Set<string> on getText()

async function run(): Promise<void> {
  const context = await DataCaptureContext.forLicenseKey(
    "-- ENTER YOUR SCANDIT LICENSE KEY HERE --",
    {
      libraryLocation: new URL("library/engine/", document.baseURI).toString(),
      moduleLoaders: [barcodeCaptureLoader()],
    }
  );

  const settings = new BarcodeBatchSettings();
  // Mapped from the old ZXing POSSIBLE_FORMATS hints:
  settings.enableSymbologies([
    Symbology.EAN13UPCA, // from BarcodeFormat.EAN_13 / UPC_A
    Symbology.Code128,   // from BarcodeFormat.CODE_128
    Symbology.QR,        // from BarcodeFormat.QR_CODE (NOT Symbology.QrCode / Symbology.Qr)
  ]);

  const barcodeBatch = await BarcodeBatch.forContext(context, settings);

  // Replaces the ZXing decodeFromVideoDevice continuous callback.
  barcodeBatch.addListener({
    didUpdateSession: (_mode, session) => {
      for (const trackedBarcode of session.addedTrackedBarcodes) {
        // Dedupe on the stable tracking ID instead of a Set<string> on the text.
        if (seenIdentifiers.has(trackedBarcode.identifier)) {
          continue;
        }
        seenIdentifiers.add(trackedBarcode.identifier);
        scannedBarcodes.push({
          value: trackedBarcode.barcode.data ?? "",
          format: String(trackedBarcode.barcode.symbology),
        });
      }
    },
  });

  const camera = Camera.pickBestGuess();
  await camera.applySettings(BarcodeBatch.recommendedCameraSettings);
  await context.setFrameSource(camera);

  // Replaces the raw <video> element ZXing drove.
  const view = await DataCaptureView.forContext(context);
  view.connectToElement(document.getElementById("data-capture-view")!);

  await BarcodeBatchBasicOverlay.withBarcodeBatchForViewWithStyle(
    barcodeBatch,
    view,
    BarcodeBatchBasicOverlayStyle.Frame
  );

  await context.frameSource?.switchToDesiredState(FrameSourceState.On);
  await barcodeBatch.setEnabled(true);
}

run();
```

---

When done, show only what changed. Do not list APIs that were unchanged. Include the setup checklist from `references/integration.md` so the user knows which npm packages to add (`@scandit/web-datacapture-core`, `@scandit/web-datacapture-barcode`), the COOP/COEP header requirement (new — ZXing-js did not need it), and the license-key placeholder to replace.
