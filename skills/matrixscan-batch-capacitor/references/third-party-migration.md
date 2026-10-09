# Third-Party Multi-Barcode Scanner → MatrixScan Batch Migration (Capacitor)

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and replace only the third-party scanner calls underneath with Scandit ones.

This guide covers replacing Capawesome's `@capacitor-mlkit/barcode-scanning` plugin, used for continuous multi-barcode scanning (`startScan()` + the `barcodesScanned` event), with Scandit MatrixScan Batch (`BarcodeBatch`). It is a **replacement**, not a rename: ML Kit reports raw detections per frame; BarcodeBatch tracks each barcode across frames with a stable identifier.

> **Language note**: Examples use plain JavaScript (ES modules) with imports from `scandit-capacitor-datacapture-core` and `scandit-capacitor-datacapture-barcode`. In a TypeScript project keep the same calls and add types.

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- The `BarcodeScanner` calls in use: `startScan` / `stopScan`, `addListener('barcodesScanned', …)`, `readBarcodesFromImage`, `enableTorch` / `disableTorch` / `toggleTorch`, `setZoomRatio`, `checkPermissions` / `requestPermissions`, `scan()`.
- The `formats` passed to `startScan` (an array of `BarcodeFormat` members). No `formats` means ML Kit scanned every format — enable only what the app really reads, and list that choice as a judgment call.
- The result handling: dedup by `rawValue` (usually a `Set`), the accumulated list, which `Barcode` fields are read (`rawValue`, `displayValue`, `format`, `cornerPoints`, typed fields like `valueType` / `wifi`).
- The CSS that made the page transparent while ML Kit's camera ran behind the WebView (typically a class such as `barcode-scanner-active` on `body` that clears backgrounds and hides the page).
- Whether the app also runs as a plain web build (`Capacitor.getPlatform() === 'web'`).

> `scan()` (ML Kit's full-screen one-shot scanner) is a single-barcode flow — it maps to SparkScan or BarcodeCapture, not to MatrixScan Batch. This guide covers the continuous `startScan()` flow.

---

## Remove

- `import { BarcodeScanner, BarcodeFormat } from '@capacitor-mlkit/barcode-scanning';`
- `BarcodeScanner.addListener('barcodesScanned', …)` and the `PluginListenerHandle` it returns (and its `remove()` call).
- `BarcodeScanner.startScan(…)` / `BarcodeScanner.stopScan()`.
- Every use of the ML Kit `BarcodeFormat` enum.
- `BarcodeScanner.checkPermissions()` / `requestPermissions()` gating the camera start (see **Permissions** below).
- The plugin itself (`npm uninstall @capacitor-mlkit/barcode-scanning`, then `npx cap sync`) once nothing references it.

---

## Integrate MatrixScan Batch

Follow `references/integration.md`. The shape of the rewrite:

1. **Initialize first**: `await ScanditCaptureCorePlugin.initializePlugins()` before any other Scandit call.
2. **Context and camera**: `DataCaptureContext.initialize(licenseKey)`, then `BarcodeBatch.createRecommendedCameraSettings()` + `Camera.withSettings(cameraSettings)` + `context.setFrameSource(camera)`. `Camera.withSettings` returns `null` when no camera is available — handle it.
3. **Replace `formats` with `BarcodeBatchSettings`**: `new BarcodeBatchSettings()` + `settings.enableSymbologies([...])`, using the mapping table below.
4. **Construct the mode with the v8 constructor**: `new BarcodeBatch(settings)` then `context.setMode(barcodeBatch)`. `BarcodeBatch.forContext` was removed in 8.0 — never emit it.
5. **Replace the `barcodesScanned` listener with `barcodeBatch.addListener({ didUpdateSession })`** and move the dedup / summary logic into it (see **Result mapping**).
6. **Render the preview** with `DataCaptureView.forContext(context)` + `view.connectToElement(element)` on an element with a **negative z-index** (see **Preview placement**).
7. **Start**: `await camera.switchToDesiredState(FrameSourceState.On)` and `barcodeBatch.isEnabled = true`. The `stopScan()` equivalent is `barcodeBatch.isEnabled = false` + `camera.switchToDesiredState(FrameSourceState.Off)`.

### Preview placement: keep the app's HTML on top

ML Kit runs its camera behind a transparent WebView, so the app's buttons and lists stay visible over the preview. Keep that layout: give the element you connect the view to a negative z-index. When the element's `z-index` is below zero, the Capacitor plugin places the native capture view **under** the WebView, and the HTML above it stays interactive.

```html
<div id="data-capture-view" style="position: fixed; inset: 0; z-index: -1;"></div>
```

- The plugin clears the native WebView background, but the page's own CSS still paints. Keep the transparent-background rule the ML Kit screen already needed (e.g. the `barcode-scanner-active` class on `body`) while scanning, or the preview is hidden behind it.
- Call `connectToElement` only after the element exists in the DOM: after `load` in plain JS, in `useEffect` (React), `ngAfterViewInit` (Angular) or `onMounted` (Vue).
- `view.webViewContentOnTop = true` forces the same placement regardless of z-index.
- Tear down with `view.detachFromElement()` when leaving the screen.

### Symbology mapping

**Do not guess or derive Scandit symbology names from ML Kit names** — they differ. ML Kit's `BarcodeFormat` is a string enum; map each member:

<!-- BEGIN GENERATED symbology-table sources=capacitor-mlkit style=js -->
| `@capacitor-mlkit/barcode-scanning` `BarcodeFormat` (value) | Scandit `Symbology` |
|---|---|
| `BarcodeFormat.QrCode` (`'QR_CODE'`) | `Symbology.QR` (**not** `QRCode`) |
| `BarcodeFormat.Ean13` (`'EAN_13'`) | `Symbology.EAN13UPCA` |
| `BarcodeFormat.Ean8` (`'EAN_8'`) | `Symbology.EAN8` |
| `BarcodeFormat.UpcA` (`'UPC_A'`) | `Symbology.EAN13UPCA` (UPC-A is read by the EAN-13/UPC-A symbology) |
| `BarcodeFormat.UpcE` (`'UPC_E'`) | `Symbology.UPCE` |
| `BarcodeFormat.Code39` (`'CODE_39'`) | `Symbology.Code39` |
| `BarcodeFormat.Code93` (`'CODE_93'`) | `Symbology.Code93` |
| `BarcodeFormat.Code128` (`'CODE_128'`) | `Symbology.Code128` |
| `BarcodeFormat.Itf` (`'ITF'`) | `Symbology.InterleavedTwoOfFive` (no ITF-14 symbology; ITF-14 is a 14-digit Interleaved 2 of 5) |
| `BarcodeFormat.Codabar` (`'CODABAR'`) | `Symbology.Codabar` |
| `BarcodeFormat.DataMatrix` (`'DATA_MATRIX'`) | `Symbology.DataMatrix` |
| `BarcodeFormat.Aztec` (`'AZTEC'`) | `Symbology.Aztec` |
| `BarcodeFormat.Pdf417` (`'PDF_417'`) | `Symbology.PDF417` |

**Recommended default set** when the source scanned every format and nothing in the app narrows it: `Symbology.QR`, `Symbology.EAN13UPCA`, `Symbology.EAN8`, `Symbology.UPCE`, `Symbology.Code39`, `Symbology.Code93`, `Symbology.Code128`, `Symbology.InterleavedTwoOfFive`, `Symbology.Codabar`, `Symbology.DataMatrix`, `Symbology.Aztec`, `Symbology.PDF417`.
<!-- END GENERATED symbology-table -->

> The Scandit symbology for QR is `Symbology.QR` (not `QrCode`). Code that compared `barcode.format` against these strings must compare `trackedBarcode.barcode.symbology` against `Symbology` values instead. For a format not in this table, fetch the [BarcodeBatch API reference](https://docs.scandit.com/data-capture-sdk/capacitor/barcode-capture/api.html) before writing code.

### Result mapping

| ML Kit concept | MatrixScan Batch equivalent |
|---|---|
| `barcodesScanned` event, `event.barcodes` per frame | `didUpdateSession(barcodeBatch, session)`: `session.addedTrackedBarcodes` (new this frame), `session.updatedTrackedBarcodes`, `session.removedTrackedBarcodes` (identifier strings), `session.trackedBarcodes` (all currently visible, keyed by identifier) |
| `barcode.rawValue` / `barcode.displayValue` | `trackedBarcode.barcode.data` |
| `barcode.format` | `trackedBarcode.barcode.symbology` |
| `barcode.cornerPoints` | `trackedBarcode.location` (a `Quadrilateral`) — **requires the MatrixScan AR add-on**; without it every corner is `(0, 0)`. If the app reads the corners, name the add-on as a prerequisite in the summary. `BarcodeBatchBasicOverlay` draws the highlight without the add-on |
| (none — no tracking) | `trackedBarcode.identifier` (a `number`), stable while the barcode stays in view, and reusable for another barcode once it is lost. `removedTrackedBarcodes` and the `trackedBarcodes` keys are strings — compare with `String(trackedBarcode.identifier)` |
| `Set` of seen `rawValue`s | Keep it, fed from `session.trackedBarcodes` on every callback (see **Preserve** for per-track counting) |
| `valueType`, `wifi`, `contactInfo`, `driverLicense`, … (ML Kit's parsed content) | No BarcodeBatch equivalent — parse `barcode.data` yourself. Name each dropped field in the summary. |

**Session safety**: do not keep `session` or its arrays outside `didUpdateSession`. Copy what you need before the callback returns.

### Other `BarcodeScanner` calls

| ML Kit call | Scandit equivalent |
|---|---|
| `readBarcodesFromImage({ path })` / `({ blob })` | `ImageFrameSource.create(base64Image)` set as the frame source: `context.setFrameSource(imageSource)` + `barcodeBatch.isEnabled = true` + `await imageSource.switchToDesiredState(FrameSourceState.On)`; results arrive in the same `didUpdateSession`. Read the file as a base64 string first (e.g. `@capacitor/filesystem` `readFile`). Afterwards restore the previous `isEnabled` value and switch back with `context.setFrameSource(camera)`. |
| `enableTorch()` / `disableTorch()` / `toggleTorch()` | `camera.desiredTorchState = TorchState.On` / `TorchState.Off`; or add a `TorchSwitchControl` to the view with `view.addControl(new TorchSwitchControl())` |
| `isTorchAvailable()` | `await camera.getIsTorchAvailable()` |
| `setZoomRatio({ zoomRatio })` | `cameraSettings.zoomFactor = zoomRatio; await camera.applySettings(cameraSettings)` |
| `startScan({ lensFacing: LensFacing.Front })` | `Camera.atPosition(CameraPosition.UserFacing)` |
| `openSettings()` | No Scandit API — keep a separate settings/permissions plugin if the app needs it |

### Permissions

Scandit has no permission API. The OS prompts for camera access when the camera first starts (`switchToDesiredState(FrameSourceState.On)`). iOS needs `NSCameraUsageDescription` in `Info.plist`; Android's camera permission is added by the plugin. If the app had a "permission denied" screen built on `BarcodeScanner.checkPermissions()`, keep that screen and back it with a dedicated permissions plugin instead.

### Web platform

The Scandit Capacitor plugins do not scan in a browser. If the app also ships a web build, guard the scanner setup with `Capacitor.getPlatform() === 'web'` (from `@capacitor/core`), as the full example below does, and hide the scan UI or route web users to the Scandit Web SDK.

---

## Preserve

- The data model and the accumulated list — keep them.
- Dedup — move it into `didUpdateSession` and iterate `Object.values(session.trackedBarcodes)` on every callback: a track can arrive with `data === null` and decode later, which an `addedTrackedBarcodes`-only loop misses. Keep value-based dedup (`trackedBarcode.barcode.data`) when the summary means "unique values". For per-track counting, add `String(trackedBarcode.identifier)` to a `Set` only once `data` is non-null, and delete every `session.removedTrackedBarcodes` id from it, because identifiers are reused after a track is lost. Per-track counting counts two physical copies, or one barcode that leaves and comes back, as separate items; value dedup counts them once.
- The render function and any downstream logic on a new barcode (network lookup, list update).
- Start/stop entry points (button handlers, page lifecycle) — rewire them to the Scandit start/stop.

---

## Putting it all together

`startScan()` + `barcodesScanned` with value dedup and a summary list, migrated:

```javascript
import { Capacitor } from '@capacitor/core';
import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
  ScanditCaptureCorePlugin,
} from 'scandit-capacitor-datacapture-core';
import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchSettings,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

// Accumulated unique scans, deduplicated by value.
const seen = new Set();
const scanned = [];

async function setUpScanner() {
  await ScanditCaptureCorePlugin.initializePlugins();

  const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
  const camera = Camera.withSettings(cameraSettings);
  if (!camera) {
    throw new Error('No camera available');
  }
  context.setFrameSource(camera);

  const settings = new BarcodeBatchSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA, // was ML Kit Ean13
    Symbology.Code128,   // was ML Kit Code128
    Symbology.QR,        // was ML Kit QrCode
  ]);

  const barcodeBatch = new BarcodeBatch(settings);
  context.setMode(barcodeBatch);
  barcodeBatch.isEnabled = false;

  barcodeBatch.addListener({
    didUpdateSession: async (_barcodeBatch, session) => {
      // Value dedup scans every visible barcode, so one first reported without data is not lost.
      for (const trackedBarcode of Object.values(session.trackedBarcodes)) {
        const value = trackedBarcode.barcode.data;
        if (value === null || seen.has(value)) {
          continue;
        }
        seen.add(value);
        scanned.push({ value, format: trackedBarcode.barcode.symbology });
      }
      renderSummary();
    },
  });

  // The element has z-index: -1, so the app's HTML stays on top of the preview.
  const view = DataCaptureView.forContext(context);
  const element = document.getElementById('data-capture-view');
  if (element) {
    view.connectToElement(element);
  }
  view.addOverlay(new BarcodeBatchBasicOverlay(barcodeBatch, BarcodeBatchBasicOverlayStyle.Frame));

  const startScanning = async () => {
    await camera.switchToDesiredState(FrameSourceState.On);
    barcodeBatch.isEnabled = true;
  };

  const stopScanning = async () => {
    barcodeBatch.isEnabled = false;
    await camera.switchToDesiredState(FrameSourceState.Off);
  };

  document.getElementById('start-btn')?.addEventListener('click', startScanning);
  document.getElementById('stop-btn')?.addEventListener('click', stopScanning);
}

function renderSummary() {
  const list = document.getElementById('scanned-list');
  if (!list) return;
  list.innerHTML = '';
  for (const item of scanned) {
    const li = document.createElement('li');
    li.textContent = `${item.value} (${item.format})`;
    list.appendChild(li);
  }
}

window.addEventListener('load', async () => {
  if (Capacitor.getPlatform() === 'web') {
    return; // The Scandit Capacitor plugins do not scan in a browser.
  }
  await setUpScanner();
});
```

> `BarcodeBatchBasicOverlay` draws a frame on each tracked barcode — a visual change from ML Kit, which drew nothing. Name it in the summary; drop the overlay if the user wants the old look. Per-barcode brushes need the MatrixScan AR add-on.

---

## After applying changes

1. `npm uninstall @capacitor-mlkit/barcode-scanning`, `npm install scandit-capacitor-datacapture-core scandit-capacitor-datacapture-barcode`, then `npx cap sync`.
2. iOS: keep (or add) `NSCameraUsageDescription` in `Info.plist`. Android: nothing to add.
3. Add the `<div id="data-capture-view">` with a negative z-index, and set the license key.
4. Show only what changed: what was removed from the ML Kit flow, what was added for MatrixScan Batch, and each judgment call (enabled symbologies, dedup key, overlay, dropped typed fields).
