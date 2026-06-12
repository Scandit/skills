# Third-Party Multi-Barcode Scanner → MatrixScan Batch Migration (Cordova)

This guide covers replacing a third-party Cordova barcode plugin with Scandit MatrixScan Batch (`BarcodeBatch`).

> **Language note**: Examples use plain JavaScript via the global `Scandit.*` namespace. Do not emit `import` from `scandit-cordova-datacapture-*` in WebView runtime code.

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- Which plugin is in use (read the plugin id / the global it calls).
- Which formats are enabled, and how they are expressed (string names vs. numeric ML Kit constants vs. bitmask).
- How the project collects "all visible barcodes" (a single-shot `scan()` call re-triggered in a loop, vs. a continuous-scan callback that returns a `barcodes` array per frame).
- The result-handling logic (deduplication by value, accumulation in an array/`Set`, filtering by format / prefix).
- The data models defined for results.

Common third-party Cordova scanners abused for batch use:

- **`phonegap-plugin-barcodescanner`** (`cordova.plugins.barcodeScanner.scan(success, fail, options)`) — single-shot by design. "Batch" behavior is emergent: the app re-calls `scan()` in a loop and dedups results. The returned `result.text` / `result.format` is one barcode per call.
- **A Cordova ML Kit barcode plugin** (e.g. `cordova-plugin-mlkit-barcode-scanner`, called via `window.cordova.plugins.mlkit.barcodeScanner.scan(options, success, fail)`) — multi-result by design: each callback delivers `results.barcodes`, an array of every barcode in the frame, each with `displayValue` and a numeric `format`.

MatrixScan Batch replaces all of the above. It owns the camera, runs the recognizer on every frame, tracks each barcode across frames (assigning a stable per-barcode `identifier`), and reports additions / updates / removals via `BarcodeBatchListener.didUpdateSession`. There is no scan loop to re-trigger — the session updates fire on their own.

---

## Remove

- The third-party plugin (`cordova plugin remove phonegap-plugin-barcodescanner` / the ML Kit plugin).
- The scanner call (`cordova.plugins.barcodeScanner.scan(...)`, `window.cordova.plugins.mlkit.barcodeScanner.scan(...)`) and any loop that re-triggers it.
- The numeric / string format constants used by the old plugin and the format-filtering array.
- The old plugin's per-result or per-frame callback shape (`result.text` / `result.format`, `results.barcodes`).
- Any UI specific to the old scanner (its viewfinder, manually-drawn highlight). The Scandit `DataCaptureView` + `BarcodeBatchBasicOverlay` (or `BarcodeBatchAdvancedOverlay`) replace it.

---

## Integrate MatrixScan Batch

Follow `references/integration.md`. The shape of the rewrite:

1. **Set up the Scandit pipeline inside the `deviceready` handler**: `Scandit.DataCaptureContext.initialize(key)`, camera via `Scandit.BarcodeBatch.createRecommendedCameraSettings()` + `Scandit.Camera.withSettings(...)` + `context.setFrameSource(camera)`.
2. **Replace the format list with `BarcodeBatchSettings`**: `new Scandit.BarcodeBatchSettings()` + `settings.enableSymbologies([...])`. Use the symbology mapping table below.
3. **Construct the mode**: `new Scandit.BarcodeBatch(settings)` then `context.setMode(barcodeBatch)`.
4. **Replace the scanner callback with `barcodeBatch.addListener({ didUpdateSession })`**. Use the result-pattern mapping table below.
5. **Render the preview**: `Scandit.DataCaptureView.forContext(context)` + `view.connectToElement(document.getElementById('data-capture-view'))`, and add `new Scandit.BarcodeBatchBasicOverlay(barcodeBatch, Scandit.BarcodeBatchBasicOverlayStyle.Frame)` via `view.addOverlay(overlay)`.
6. **Start scanning**: `camera.switchToDesiredState(Scandit.FrameSourceState.On)` and `barcodeBatch.isEnabled = true`.

**Do not guess or derive Scandit symbology names from the old library's names** — they differ. Map them with the table below.

### Symbology mapping

| `phonegap-plugin-barcodescanner` `format` | ML Kit `format` constant | Scandit `Scandit.Symbology.*` |
|---|---|---|
| `QR_CODE` | `256` (`FORMAT_QR_CODE`) | `Scandit.Symbology.QR` |
| `EAN_13` | `32` (`FORMAT_EAN_13`) | `Scandit.Symbology.EAN13UPCA` |
| `EAN_8` | `64` (`FORMAT_EAN_8`) | `Scandit.Symbology.EAN8` |
| `UPC_A` | `512` (`FORMAT_UPC_A`) | `Scandit.Symbology.EAN13UPCA` (UPC-A is part of the EAN-13/UPC-A symbology in Scandit) |
| `UPC_E` | `1024` (`FORMAT_UPC_E`) | `Scandit.Symbology.UPCE` |
| `CODE_39` | `2` (`FORMAT_CODE_39`) | `Scandit.Symbology.Code39` |
| `CODE_93` | `4` (`FORMAT_CODE_93`) | `Scandit.Symbology.Code93` |
| `CODE_128` | `1` (`FORMAT_CODE_128`) | `Scandit.Symbology.Code128` |
| `ITF` | `128` (`FORMAT_ITF`) | `Scandit.Symbology.InterleavedTwoOfFive` |
| `CODABAR` | `8` (`FORMAT_CODABAR`) | `Scandit.Symbology.Codabar` |
| `DATA_MATRIX` | `16` (`FORMAT_DATA_MATRIX`) | `Scandit.Symbology.DataMatrix` |
| `AZTEC` | `4096` (`FORMAT_AZTEC`) | `Scandit.Symbology.Aztec` |
| `PDF_417` | `2048` (`FORMAT_PDF417`) | `Scandit.Symbology.PDF417` |

> Note: the Scandit symbology for QR is `Scandit.Symbology.QR` (not `QrCode`). If you encounter a format not in this table, fetch the [BarcodeBatch API index](https://docs.scandit.com/data-capture-sdk/cordova/barcode-capture/api.html) for the correct `Symbology` value before writing code.

### Result-pattern mapping

| Old scanner concept | MatrixScan Batch equivalent |
|---|---|
| "I got a result, restart the scanner" (`phonegap-plugin-barcodescanner` loop) | Nothing — `didUpdateSession` fires for every processed frame, and `session.addedTrackedBarcodes` reports the new entries since the last frame. Remove the re-trigger. |
| `result.text` / `barcode.displayValue` | `trackedBarcode.barcode.data` |
| `result.format` / `barcode.format` | `trackedBarcode.barcode.symbology` (a `Scandit.Symbology` value) |
| Per-result bounding box | `trackedBarcode.location` (a `Quadrilateral` in image-space; the basic overlay draws the highlight for you — requires the MatrixScan AR add-on) |
| "Have I seen this code yet?" (manual `Set` dedupe by value) | `trackedBarcode.identifier` is the stable per-barcode tracking ID. New barcodes appear in `session.addedTrackedBarcodes`; the same physical code keeps the same identifier across frames until it leaves the view. Keep a `Set` of identifiers for a "ever seen" set, or accumulate `barcode.data` from `addedTrackedBarcodes`. |
| "Which barcodes are currently visible?" | `session.trackedBarcodes` — a map from identifier string to `TrackedBarcode`. |
| Per-frame ML Kit `results.barcodes` array | `session.addedTrackedBarcodes` + `session.updatedTrackedBarcodes` + `session.removedTrackedBarcodes` (identifier strings) on every frame. |

---

## Preserve

- Custom data models and the accumulation list / `Set` — keep them.
- Deduplication logic — move it into `didUpdateSession`. Either keep the original value-based dedup, or upgrade to tracking-identifier-based dedup: iterate `session.addedTrackedBarcodes`, add `trackedBarcode.identifier` to a `Set`, and append only the genuinely new ones.
- Any downstream business logic triggered on a new barcode (network lookup, list render).
- **Session safety**: do not hold a reference to `session` or its arrays outside the `didUpdateSession` callback. Copy what you need before the callback returns.

---

## Putting it all together

A typical "ML Kit batch callback replaced with MatrixScan Batch" shape:

```javascript
document.addEventListener('deviceready', () => {
  const context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const cameraSettings = Scandit.BarcodeBatch.createRecommendedCameraSettings();
  window.camera = Scandit.Camera.withSettings(cameraSettings);
  context.setFrameSource(window.camera);

  const settings = new Scandit.BarcodeBatchSettings();
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA, // from ML Kit FORMAT_EAN_13
    Scandit.Symbology.Code128,   // from ML Kit FORMAT_CODE_128
    Scandit.Symbology.QR,        // from ML Kit FORMAT_QR_CODE
  ]);

  window.barcodeBatch = new Scandit.BarcodeBatch(settings);
  context.setMode(window.barcodeBatch);

  // Same dedupe-and-accumulate as the old loop, but driven by per-frame deltas.
  const seenIdentifiers = new Set();
  const scannedBarcodes = [];

  window.barcodeBatch.addListener({
    didUpdateSession: (barcodeBatch, session) => {
      session.addedTrackedBarcodes.forEach(trackedBarcode => {
        if (seenIdentifiers.has(trackedBarcode.identifier)) return;
        seenIdentifiers.add(trackedBarcode.identifier);
        scannedBarcodes.push({
          value: trackedBarcode.barcode.data,
          symbology: trackedBarcode.barcode.symbology,
        });
      });
      // Schedule UI render from the copied data, not from the session.
      renderList(scannedBarcodes.slice());
    },
  });

  window.view = Scandit.DataCaptureView.forContext(context);
  window.view.connectToElement(document.getElementById('data-capture-view'));

  window.basicOverlay = new Scandit.BarcodeBatchBasicOverlay(
    window.barcodeBatch,
    Scandit.BarcodeBatchBasicOverlayStyle.Frame,
  );
  window.view.addOverlay(window.basicOverlay);

  window.camera.switchToDesiredState(Scandit.FrameSourceState.On);
  window.barcodeBatch.isEnabled = true;
}, false);
```

---

When done, show only what changed (what was removed from the old plugin flow, what was added for MatrixScan Batch). Include the setup checklist from `references/integration.md` so the user knows to install `scandit-cordova-datacapture-core` and `scandit-cordova-datacapture-barcode`, run `cordova prepare`, add the `<div id="data-capture-view">`, set the license key, and that camera permissions are auto-configured by the plugins.
