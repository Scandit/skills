# Third-Party One-Shot Scanner → SparkScan Migration (Capacitor)

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different scanning UI, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and replace only the third-party scanner calls underneath with Scandit ones.

This guide covers replacing Capawesome's `@capacitor-mlkit/barcode-scanning` plugin, used as a one-shot scanner (`await BarcodeScanner.scan()` returning `{ barcodes }`), with Scandit SparkScan (`SparkScanView`). It is a **replacement**, not a rename: ML Kit's `scan()` opens a full-screen scanner and returns a promise; SparkScan is a native overlay driven by listeners, so the promise has to be built around it.

> **Language note**: Examples use TypeScript with imports from `scandit-capacitor-datacapture-core` and `scandit-capacitor-datacapture-barcode`. In a plain-JS project keep the same calls and drop the types.

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- The `BarcodeScanner` calls in use: `scan()`, `requestPermissions` / `checkPermissions`, `isSupported`, `isGoogleBarcodeScannerModuleAvailable` / `installGoogleBarcodeScannerModule`. The plugin may be imported dynamically (`await import('@capacitor-mlkit/barcode-scanning')`) — search for the package name, not only `import … from`.
- The `formats` passed to `scan({ formats })`. No `formats` means ML Kit scanned every format — enable the recommended default set below, never fewer than the app needs.
- What the caller does with the result: usually only `barcodes[0].rawValue`; whether an empty `barcodes` array means "user cancelled" (ML Kit resolves with an empty array on cancel, and some versions reject with a message matching `/cancel/i`).
- The permission handling around `scan()`: the denied-permission message or screen, and any "scanning…" state that disables a button until the promise settles.
- Whether the app also runs as a plain web build (`Capacitor.getPlatform() === 'web'`).

> If the app uses the continuous `startScan()` + `barcodesScanned` flow instead of `scan()`, this is the wrong guide: that flow maps to MatrixScan Batch (`matrixscan-batch-capacitor`) or BarcodeCapture (`barcode-capture-capacitor`).

---

## Remove

- `import { BarcodeScanner, BarcodeFormat } from '@capacitor-mlkit/barcode-scanning';` (or the dynamic `import()` form) and every use of the ML Kit `BarcodeFormat` enum.
- `BarcodeScanner.scan(…)`.
- `BarcodeScanner.isSupported()`, `isGoogleBarcodeScannerModuleAvailable()` and `installGoogleBarcodeScannerModule()` — and any polling loop or start-up call that waits for the Google module. Scandit ships its own decoder: there is no module to install. Replace `isSupported` with `Capacitor.isNativePlatform()` if the app hides the scan entry point on web.
- `BarcodeScanner.checkPermissions()` / `requestPermissions()` as the camera gate (see **Permissions** below).
- The plugin itself (`npm uninstall @capacitor-mlkit/barcode-scanning`, then `npx cap sync`) once nothing references it.

---

## Integrate SparkScan

Follow `references/integration.md`. The shape of the rewrite:

1. **Initialize first**: `await ScanditCaptureCorePlugin.initializePlugins()` before any other Scandit call.
2. **One context, one mode, one view for the whole app.** Create `DataCaptureContext.initialize(licenseKey)`, `SparkScan` and `SparkScanView.forContext(context, sparkScan, null)` the first time `scan()` is called and reuse them for every later call. Never re-initialise the context per scan: it is wasteful and leaves a second native view behind.
3. **Replace `formats` with `SparkScanSettings`**: `settings.enableSymbologies([...])`, using the mapping table below. Apply a different set on a later call with `await sparkScan.applySettings(settings)`.
4. **Wrap the listener in a promise.** `sparkScan.addListener({ didScan })` is registered once; each `scan()` call stores a resolver. The first `didScan` stops and hides the view, then resolves it with `{ barcodes: [...] }` (see **Result mapping**). Allow one scan at a time: reject a `scan()` call while another is running. If `show()` or `startScanning()` throws, clear the resolver, stop and hide the view, then rethrow.
5. **Show and start** per call: `await view.show()` then `await view.startScanning()`. Stop and hide: `await view.stopScanning()` then `await view.hide()`. Release everything with `await view.dispose()` only when the whole screen or app is torn down.

### Cancel: resolve, never hang

ML Kit's scanner has a close button; leaving it resolves `scan()` with an empty `barcodes` array. SparkScan has no such promise, so a wrapper that only resolves in `didScan` hangs forever when the user dismisses the scanner — the caller's "scanning…" state never clears.

- Set `view.uiListener = { didChangeViewState }`. `SparkScanViewState` is `Initial`, `Idle`, `Inactive`, `Active` or `Error`. Remember when the state has been `Active`; when it later becomes `Idle` while a call is still pending, resolve with `{ barcodes: [] }` and hide the view. The preview's close control and `pauseScanning()` both switch to `Idle`. Do **not** resolve on `Inactive`: releasing the trigger without a read also lands there while the user is still scanning, and a successful read reaches `Inactive` only after `didScan` has already resolved the call.
- Also expose a `cancelScan()` the app can call from its own close or back button — a collapsed SparkScan shows only its trigger button, and the user may never reach `Active`.
- **Never** use `didTapBarcodeCountButton` (or `didTapBarcodeFindButton` / `didTapLabelCaptureButton`) as a close hook: they fire when the user taps the Count / Find / Label Capture mode buttons, not on close. Hide those buttons instead (`view.barcodeCountButtonVisible = false`, `view.barcodeFindButtonVisible = false`, `view.labelCaptureButtonVisible = false`) so the user cannot reach a mode the app does not handle.

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

> The Scandit symbology for QR is `Symbology.QR` (not `QrCode`). Do not narrow the set: if `scan()` passed no `formats`, enable the recommended default set above, not just QR. For a format not in this table, fetch the [SparkScan API reference](https://docs.scandit.com/data-capture-sdk/capacitor/barcode-capture/api/ui/spark-scan-view.html) before writing code.

### Result mapping

| ML Kit concept | SparkScan equivalent |
|---|---|
| `scan()` resolving `{ barcodes }` | A promise you build: resolve on the first `didScan` with the mapped barcode |
| `barcode.rawValue` / `barcode.displayValue` | `session.newlyRecognizedBarcode.data` (nullable — skip the scan if `null`) |
| `barcode.format` | `session.newlyRecognizedBarcode.symbology` (a `Symbology` value) |
| Empty `barcodes` on cancel | Resolve `{ barcodes: [] }` from `didChangeViewState` / `cancelScan()` |
| `valueType`, `wifi`, `contactInfo`, `driverLicense`, … (ML Kit's parsed content) | No SparkScan equivalent — parse `barcode.data` yourself. Name each dropped field in the summary. |

Keep the caller's code unchanged where the wrapper returns the same shape (`{ barcodes: [{ rawValue, displayValue, format }] }`).

### Permissions

Scandit has no permission API. The OS prompts for camera access when the camera first starts (`startScanning()`). iOS needs `NSCameraUsageDescription` in `Info.plist`; Android's camera permission is added by the plugin.

- Keep the app's own permission check and its denied message or screen exactly as they are, backed by the app's existing mechanism (for example `@capacitor/camera` `checkPermissions()` / `requestPermissions()`). If ML Kit's `requestPermissions()` was the only source, replace it with such a plugin (`npm install @capacitor/camera`; `Camera.requestPermissions({ permissions: ['camera'] })` resolves `{ camera: 'granted' | 'denied' | … }`) — never stub it to always return `granted`, which silently kills the denied path.
- Run the check before calling the wrapper, as the original did, so a denial never reaches SparkScan.
- `openSettings()` has no Scandit equivalent — keep the app's own mechanism or say so in the summary.

### Behaviour changes to list

- The UI changes: ML Kit's full-screen scanner becomes SparkScan's mini preview with a trigger button (`startScanning()` begins scanning immediately; the user can still collapse it).
- SparkScan adds its own success feedback (beep, vibration, highlight).
- Torch, zoom and camera-switch controls are SparkScan's own, configured through `SparkScanView` and `SparkScanViewSettings`; there are no `enableTorch()` / `setZoomRatio()` calls.

### Web platform

The Scandit Capacitor plugins do not scan in a browser. If the app also ships a web build, guard the scanner with `Capacitor.getPlatform() === 'web'` (from `@capacitor/core`) before `initializePlugins()`, as the example below does, and hide the scan entry point or route web users to the Scandit Web SDK.

---

## Preserve

- The caller's contract: `await scan()` returns `{ barcodes }`, empty on cancel. Callers (React handlers, Vue composables) should need no change beyond the import.
- The permission gate and its denied UI, the "scanning…" / disabled-button state (it must clear on every path: result, cancel, error), and error messages.
- Everything downstream of the result (parsing, routing, state updates).

---

## Putting it all together

`BarcodeScanner.scan({ formats: [QrCode] })` with a permission gate and "empty means cancelled", migrated:

```typescript
import { Capacitor } from '@capacitor/core';
import { DataCaptureContext, ScanditCaptureCorePlugin } from 'scandit-capacitor-datacapture-core';
import {
  SparkScan,
  SparkScanSettings,
  SparkScanView,
  SparkScanViewState,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

declare function requestCameraPermission(): Promise<boolean>; // the app's existing permission flow

export interface ScannedBarcode {
  rawValue: string;
  displayValue: string;
  format: Symbology;
}

let sparkScan: SparkScan | null = null;
let view: SparkScanView | null = null;
let setUp: Promise<void> | null = null;
let pending: ((result: { barcodes: ScannedBarcode[] }) => void) | null = null;
let sawActive = false;
let busy = false;

function settingsFor(symbologies: Symbology[]): SparkScanSettings {
  const settings = new SparkScanSettings();
  settings.enableSymbologies(symbologies);
  return settings;
}

async function settle(barcodes: ScannedBarcode[]): Promise<void> {
  const resolve = pending;
  pending = null;
  if (!resolve || !view) return;
  try {
    await view.stopScanning();
    await view.hide();
  } finally {
    resolve({ barcodes }); // after cleanup, so the next scan() starts on a hidden view
  }
}

async function createOnce(symbologies: Symbology[]): Promise<void> {
  await ScanditCaptureCorePlugin.initializePlugins();
  const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  sparkScan = new SparkScan(settingsFor(symbologies));
  sparkScan.addListener({
    didScan: async (_sparkScan, session) => {
      const barcode = session.newlyRecognizedBarcode;
      if (barcode == null || barcode.data == null) return;
      await settle([{ rawValue: barcode.data, displayValue: barcode.data, format: barcode.symbology }]);
    },
  });

  view = SparkScanView.forContext(context, sparkScan, null);
  view.barcodeCountButtonVisible = false;
  view.barcodeFindButtonVisible = false;
  view.labelCaptureButtonVisible = false;
  view.uiListener = {
    didChangeViewState: (newState) => {
      if (newState === SparkScanViewState.Active) {
        sawActive = true;
      } else if (sawActive && newState === SparkScanViewState.Idle) {
        void settle([]);
      }
    },
  };
}

export function cancelScan(): Promise<void> {
  return settle([]);
}

export async function scan(
  symbologies: Symbology[] = [Symbology.QR],
): Promise<{ barcodes: ScannedBarcode[] }> {
  if (Capacitor.getPlatform() === 'web') {
    throw new Error('Scanning is not available in the browser');
  }
  if (busy) throw new Error('A scan is already in progress');
  busy = true;
  try {
    setUp ??= createOnce(symbologies).catch((error: unknown) => {
      setUp = null; // let the next scan() retry a failed initialisation
      throw error;
    });
    await setUp;
    if (!sparkScan || !view) throw new Error('Scanner failed to initialise');

    await sparkScan.applySettings(settingsFor(symbologies));
    sawActive = false;
    const result = new Promise<{ barcodes: ScannedBarcode[] }>((resolve) => {
      pending = resolve;
    });
    try {
      await view.show();
      await view.startScanning();
    } catch (error) {
      pending = null;
      await view.stopScanning().catch(() => undefined);
      await view.hide().catch(() => undefined);
      throw error;
    }
    return await result;
  } finally {
    busy = false;
  }
}

// Caller: the permission gate and the denied message stay as they were.
export async function handleScan(): Promise<string | null> {
  if (!(await requestCameraPermission())) {
    throw new Error('Camera permission is required to scan');
  }
  const { barcodes } = await scan([Symbology.QR]);
  return barcodes.length > 0 ? barcodes[0].rawValue : null; // empty = user cancelled
}
```

> `scan([Symbology.QR])` keeps the original `formats: [QrCode]`. If the original passed no `formats`, call `scan(DEFAULT_SYMBOLOGIES)` with the recommended default set instead. Wire `cancelScan()` to the app's own close or back button.

---

## After applying changes

1. `npm uninstall @capacitor-mlkit/barcode-scanning`, `npm install scandit-capacitor-datacapture-core scandit-capacitor-datacapture-barcode`, then `npx cap sync`.
2. iOS: keep (or add) `NSCameraUsageDescription` in `Info.plist`. Android: nothing to add.
3. Set the license key (see **Licence key** in `SKILL.md`).
4. Run `npx tsc --noEmit` and fix every error against the typings in `node_modules`, not from memory; repeat until clean.
5. Show only what changed: what was removed from the ML Kit flow, what was added for SparkScan, and each judgment call (enabled symbologies, cancel trigger, new scanning UI, dropped typed fields).
