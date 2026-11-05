# Third-Party Multi-Barcode Scanner → MatrixScan Batch Migration (Web)

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and replace only the third-party scanner calls underneath with Scandit ones.

This guide covers migrating a web app from **ZXing-js** (`@zxing/library`, also published as `@zxing/browser`) — the most common third-party multi-format browser scanner — to Scandit MatrixScan Batch (`BarcodeBatch*`). The same steps apply to a page built on html5-qrcode (`Html5Qrcode`, `formatsToSupport`) or on the `BarcodeDetector` API (`detector.detect(video)` in a `requestAnimationFrame` loop over a `getUserMedia` stream, often with the `barcode-detector` polyfill): `detect()` already returns every code in the frame, as `rawValue`, `format` and `boundingBox`, which map to `trackedBarcode.barcode.data`, `trackedBarcode.barcode.symbology` and `trackedBarcode.location`.

A photo decode (`scanFile()`, the file tab `Html5QrcodeScanner` shows by default, `detect(image)`) has no MatrixScan Batch equivalent: keep the upload path and decode the file as in **Photo upload** below. List it as a judgment call; never drop it silently.

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- Which package is in use (read the `import` statements and `package.json`): `@zxing/library` (older, ships the readers + a `BrowserMultiFormatReader`) or `@zxing/browser` (the newer browser-only split, `BrowserMultiFormatReader` lives here).
- Which formats are enabled — usually via `DecodeHintType.POSSIBLE_FORMATS` set to a list of `BarcodeFormat` values, or left unset (all formats).
- How the app collects barcodes — ZXing-js has no per-frame *multi*-barcode tracking; apps emulate "batch" by calling `decodeFromVideoDevice` / `decodeFromConstraints` in a continuous callback and accumulating distinct `result.getText()` values in a `Set`/array, deduplicating on the decoded string.
- What result-handling logic exists (dedup on the string value, accumulation, filtering by format/prefix).
- What data models are defined (interfaces/types holding the scanned info).

> **Key conceptual difference:** ZXing-js decodes **one** barcode per frame and reports it through a callback; "scanning many barcodes" is the app re-invoking the decoder in a loop and accumulating results. MatrixScan Batch genuinely tracks **all** visible barcodes simultaneously every frame, assigning each a **tracking ID** that holds while the barcode stays in view (a barcode that leaves and comes back gets a new one), and reports additions / updates / removals via `IBarcodeBatchListener.didUpdateSession`. There is no decode loop to re-trigger — the session updates fire on their own.

MatrixScan Batch owns the camera and renders through a `DataCaptureView`, so the old `<video>` element, the `getUserMedia` plumbing, and any hand-drawn highlight `<canvas>` are all replaced.

---

## Remove

- The old library's `import`s and its `dependencies` entry in `package.json`: `@zxing/library` / `@zxing/browser`, `html5-qrcode`, or the `barcode-detector` polyfill (the browser's own `BarcodeDetector` has no package).
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

<!-- BEGIN GENERATED symbology-table sources=zxing-js,html5-qrcode,barcode-detector style=js -->
| ZXing-js `BarcodeFormat` | html5-qrcode `Html5QrcodeSupportedFormats` | `BarcodeDetector` `formats` | Scandit `Symbology` |
|---|---|---|---|
| `QR_CODE` | `QR_CODE` | `'qr_code'` | `Symbology.QR` (**not** `QRCode`) |
| `EAN_13` | `EAN_13` | `'ean_13'` | `Symbology.EAN13UPCA` |
| `EAN_8` | `EAN_8` | `'ean_8'` | `Symbology.EAN8` |
| `UPC_A` | `UPC_A` | `'upc_a'` | `Symbology.EAN13UPCA` (UPC-A is read by the EAN-13/UPC-A symbology) |
| `UPC_E` | `UPC_E` | `'upc_e'` | `Symbology.UPCE` |
| `CODE_39` | `CODE_39` | `'code_39'` | `Symbology.Code39` |
| `CODE_93` | `CODE_93` | `'code_93'` | `Symbology.Code93` |
| `CODE_128` | `CODE_128` | `'code_128'` | `Symbology.Code128` |
| `ITF` | `ITF` | `'itf'` / `'itf_14'` (`'itf_14'` with the `barcode-detector` polyfill only) | `Symbology.InterleavedTwoOfFive` (no ITF-14 symbology; ITF-14 is a 14-digit Interleaved 2 of 5) |
| `CODABAR` | `CODABAR` | `'codabar'` | `Symbology.Codabar` |
| `DATA_MATRIX` | `DATA_MATRIX` | `'data_matrix'` | `Symbology.DataMatrix` |
| `AZTEC` | `AZTEC` | `'aztec'` | `Symbology.Aztec` |
| `PDF_417` | `PDF_417` | `'pdf417'` | `Symbology.PDF417` |
| `RSS_14` | `RSS_14` | `'databar'` / `'databar_omni'` / `'databar_stacked'` / `'databar_stacked_omni'` (`barcode-detector` polyfill only) | `Symbology.GS1Databar` |
| — | — | `'databar_limited'` (`barcode-detector` polyfill only) | `Symbology.GS1DatabarLimited` |
| `RSS_EXPANDED` | `RSS_EXPANDED` | `'databar_expanded'` / `'databar_expanded_stacked'` (`barcode-detector` polyfill only) | `Symbology.GS1DatabarExpanded` |
| `MAXICODE` | `MAXICODE` | `'maxi_code'` (`barcode-detector` polyfill only) | `Symbology.MaxiCode` |
| `UPC_EAN_EXTENSION` | `UPC_EAN_EXTENSION` | — | No symbology of its own: the 2/5-digit add-on arrives as `barcode.addOnData` on the EAN/UPC result. Look up how to enable add-ons in the API reference before writing it. |
| (no `POSSIBLE_FORMATS` hint) | (`formatsToSupport` omitted) | (`formats` omitted) | No equivalent. Enable what the app really consumes; if nothing narrows it, the recommended default set below. Never enable everything. |

**Recommended default set** when the source scanned every format and nothing in the app narrows it: `Symbology.QR`, `Symbology.EAN13UPCA`, `Symbology.EAN8`, `Symbology.UPCE`, `Symbology.Code39`, `Symbology.Code93`, `Symbology.Code128`, `Symbology.InterleavedTwoOfFive`, `Symbology.Codabar`, `Symbology.DataMatrix`, `Symbology.Aztec`, `Symbology.PDF417`.
<!-- END GENERATED symbology-table -->

**UPC-A values.** These libraries return a UPC-A code as 12 digits when UPC-A is among the formats; `Symbology.EAN13UPCA` returns it as 13 digits with a leading `0`. When the app scanned UPC-A, keep the 12-digit values with `settings.settingsForSymbology(Symbology.EAN13UPCA).setExtensionEnabled("remove_leading_upca_zero", true)`, or flag the changed value (and the dedupe key built on it) as a judgment call.

**Format names.** `String(trackedBarcode.barcode.symbology)` gives Scandit's identifier (`ean13Upca`), not the old library's name (`EAN_13`, `'upc_a'`). When the app shows, stores or compares the old string, keep it with a small `Symbology` → old-string lookup (EAN-13 and UPC-A share `EAN13UPCA`; with `remove_leading_upca_zero` on, 12-digit data is UPC-A), or flag the changed names as a judgment call.

> **Note on the web `Symbology` enum casing:** web uses `Symbology.QR` (the value `"qr"`) — **not** `Symbology.QrCode` (which does not exist) and not `Symbology.Qr` (that is the .NET/native form). Note also that some members are all-caps on web: `Symbology.PDF417`, `Symbology.UPCE`, `Symbology.EAN13UPCA`. When in doubt, check the BarcodeBatch API reference linked in `SKILL.md` before writing the code.

### Result-pattern mapping

| ZXing-js concept | MatrixScan Batch equivalent |
|---|---|
| `decodeFromVideoDevice(deviceId, videoEl, (result, err) => …)` continuous callback | `barcodeBatch.addListener({ didUpdateSession: (_mode, session) => … })` — fires every processed frame, no re-trigger. |
| `result.getText()` | `trackedBarcode.barcode.data` |
| `result.getBarcodeFormat()` | `trackedBarcode.barcode.symbology` (a `Symbology` enum value) |
| `result.getResultPoints()` (corner points) | `trackedBarcode.location` (`Quadrilateral` in image-space; the basic overlay draws the highlight for you, or use `view.viewQuadrilateralForFrameQuadrilateral(location)` to convert to view space) |
| "Have I seen this text yet?" (manual `Set<string>` dedupe on `getText()`) | Keep the `Set<string>`, keyed on `trackedBarcode.barcode.data`. New barcodes appear in `session.addedTrackedBarcodes`. `trackedBarcode.identifier` identifies a track, not a code: the same physical code keeps it across frames while it stays in view, and gets a new one when it leaves and comes back. |
| "Which barcodes are visible right now?" | `session.trackedBarcodes` — `Record<string, TrackedBarcode>` keyed by tracking ID; iterate with `Object.values(...)`. |
| Barcodes that left the view | `session.removedTrackedBarcodes` — `string[]` of identifiers; `Number.parseInt(id, 10)` to compare with `trackedBarcode.identifier`. |

---

## Preserve

- Custom data models — keep as-is (an `interface ScannedBarcode { value: string; format: string; }` moves verbatim).
- Result accumulation and deduplication logic — move it into `didUpdateSession`. Iterate `session.addedTrackedBarcodes`, dedupe on `trackedBarcode.barcode.data` (the identifier changes when a barcode re-enters the frame), and append to the existing collection.
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
const seenValues = new Set<string>(); // the same Set<string> the ZXing version kept on getText()

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
        // Dedupe on the data, not the identifier: a code that leaves and re-enters the view gets a new identifier.
        const value = trackedBarcode.barcode.data ?? "";
        if (seenValues.has(value)) {
          continue;
        }
        seenValues.add(value);
        scannedBarcodes.push({
          value,
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

## Photo upload

Decode an uploaded photo with a `BarcodeCapture` mode fed by `ImageFrameSource.fromFile(file)` on the same context. `BarcodeCapture.forContext` replaces `BarcodeBatch` on the context and the image replaces the camera, so disable `BarcodeBatch` and switch the camera off first, and put both back in a `finally`, whatever the outcome (a file that is not an image, a timeout). Compiled against 8.6.1:

```typescript
import {
  BarcodeCapture,
  BarcodeCaptureSettings,
  ScanIntention,
  type BarcodeBatch,
  type Symbology,
} from "@scandit/web-datacapture-barcode";
import {
  type Camera,
  type DataCaptureContext,
  FrameSourceState,
  ImageFrameSource,
} from "@scandit/web-datacapture-core";

const PHOTO_DECODE_TIMEOUT_MS = 10_000;

export async function decodePhoto(
  context: DataCaptureContext,
  barcodeBatch: BarcodeBatch,
  camera: Camera,
  file: File,
  symbologies: Symbology[],
): Promise<string | null> {
  const settings = new BarcodeCaptureSettings();
  settings.scanIntention = ScanIntention.Manual;
  settings.enableSymbologies(symbologies);

  let timeout: ReturnType<typeof setTimeout> | undefined;
  try {
    await barcodeBatch.setEnabled(false);
    await camera.switchToDesiredState(FrameSourceState.Off);
    const barcodeCapture = await BarcodeCapture.forContext(context, settings);
    const decoded = new Promise<string | null>((resolve) => {
      barcodeCapture.addListener({
        didScan: (_barcodeCapture, session) => resolve(session.newlyRecognizedBarcode?.data ?? null),
        didUpdateSession: (_barcodeCapture, session) => {
          if (session.newlyRecognizedBarcode == null) {
            resolve(null);
          }
        },
      });
    });
    const imageSource = await ImageFrameSource.fromFile(file);
    await context.setFrameSource(imageSource);
    await imageSource.switchToDesiredState(FrameSourceState.On);
    const timedOut = new Promise<never>((_resolve, reject) => {
      timeout = setTimeout(() => reject(new Error("The photo was not processed in time")), PHOTO_DECODE_TIMEOUT_MS);
    });
    return await Promise.race([decoded, timedOut]);
  } finally {
    clearTimeout(timeout);
    await context.setMode(barcodeBatch);
    await context.setFrameSource(camera);
    await camera.switchToDesiredState(FrameSourceState.On);
    await barcodeBatch.setEnabled(true);
  }
}
```

`decodePhoto` resolves `null` for a photo without a code as soon as that frame is processed (its session update has no new barcode); `didScan` alone would leave it waiting for the timeout. It rejects for a file that is not an image, and when no result arrives in time. The photo path runs Barcode Capture, so the license key must cover it as well as MatrixScan Batch; a key without it shows up as that timeout. Pass the symbologies the camera scan enables. Barcode Capture reports one barcode per photo, where `detect(image)` or `scanFile()` could return several: list that as a judgment call. Disable the photo input while a decode runs. Feed a decoded code through the same dedupe and list as the camera codes, and keep the app's "nothing found" message.

---

## Setup checklist and summary

When done, show only what changed. Do not list APIs that were unchanged.

**Setup checklist:** the one from `references/integration.md` (npm packages `@scandit/web-datacapture-core` and `@scandit/web-datacapture-barcode`, the license-key placeholder to replace), plus removing each old scanner package by name (for example `npm uninstall barcode-detector`) and the COOP/COEP header requirement, which is new: the old libraries did not need it.

**Summary:** always end with a "Summary of changes" section listing what was removed (the old scanner's APIs and markup), what was added (the `BarcodeBatch` set-up, view and overlay), the format → symbology mapping, and every judgment call.
