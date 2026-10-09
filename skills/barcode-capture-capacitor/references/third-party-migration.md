# Third-Party Barcode Scanner → BarcodeCapture Migration (Capacitor)

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and replace only the third-party scanner calls underneath with Scandit ones.

This guide covers replacing Capawesome's `@capacitor-mlkit/barcode-scanning` plugin (`startScan()` + the `barcodesScanned` event) with Scandit BarcodeCapture (`BarcodeCapture`). It is a **replacement**, not a rename: the structure of the app's scanner screen — a transparent WebView over a native camera, the app's own close button, its permission flow — must survive.

> **Language note**: Examples are TypeScript with imports from `scandit-capacitor-datacapture-core` and `scandit-capacitor-datacapture-barcode`. In a plain-JS project keep the same calls and drop the types.

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- The `BarcodeScanner` calls in use: `startScan` / `stopScan`, `addListener('barcodesScanned', …)`, `scan()`, `readBarcodesFromImage`, `enableTorch` / `disableTorch` / `toggleTorch`, `setZoomRatio`, `checkPermissions` / `requestPermissions`, `openSettings`, `isSupported`, `installGoogleBarcodeScannerModule`.
- The `formats` passed to `startScan`. **No `formats` means ML Kit scanned every format** — enable the recommended default set below, never just QR, and list that choice as a judgment call.
- The result handling: which `Barcode` fields are read (`rawValue`, `displayValue`, `format`), whether the app counts consecutive reads of the same code, whether it collects multi-part QR codes (for example animated UR fragments), what it does after the first result.
- The CSS that made the page transparent while ML Kit's camera ran behind the WebView (typically a class on `body` such as `scanner-active` or `scan-active`), and the app's own HTML shown over the camera (close/stop button, progress, title). **All of it stays.**
- The permission flow: `checkPermissions()` / `requestPermissions()` or `@capacitor/camera`, and the screen shown when permission is denied.
- Whether the app also ships a plain web build (`Capacitor.getPlatform() === 'web'`).

> `scan()` (ML Kit's full-screen one-shot scanner with its own UI) is not what this guide covers. For a one-shot flow, read `sparkscan-capacitor` (ready-made scan UI) and use this guide only for the continuous `startScan()` flow.

---

## Remove

- `import { BarcodeScanner, BarcodeFormat, LensFacing } from '@capacitor-mlkit/barcode-scanning';` and every use of the ML Kit enums and `Barcode` type.
- `BarcodeScanner.addListener('barcodesScanned', …)` and the `PluginListenerHandle` it returns (and its `remove()` call), `removeAllListeners()`.
- `BarcodeScanner.startScan(…)` / `BarcodeScanner.stopScan()`.
- `isSupported()` and `installGoogleBarcodeScannerModule()` (and its install-progress listener): Scandit needs no Google module.
- The plugin itself (`npm uninstall @capacitor-mlkit/barcode-scanning`, then `npx cap sync`) once nothing references it.

Keep: the app's own permission check and denied screen (see **Permissions**), its transparent-background CSS, its close/stop button and any other HTML over the camera.

---

## Integrate BarcodeCapture

Follow `references/integration.md`. The shape of the rewrite:

1. **Guard the web platform first**: `Capacitor.getPlatform() === 'web'` ⇒ do not call any Scandit API (see **Web platform**).
2. **Initialize once**: `await ScanditCaptureCorePlugin.initializePlugins()`, then `DataCaptureContext.initialize(licenseKey)`. Create **one** `DataCaptureContext` and one `BarcodeCapture` per app and reuse them for every scan; never re-initialise per scan.
3. **Replace `formats` with `BarcodeCaptureSettings`**: `new BarcodeCaptureSettings()` + `settings.enableSymbologies([...])` using the mapping table below.
4. **Camera**: `BarcodeCapture.createRecommendedCameraSettings()` + `Camera.withSettings(...)`. It returns `null` when no camera is available — handle it before `context.setFrameSource(camera)`.
5. **Mode**: `new BarcodeCapture(settings)` then `await context.setMode(barcodeCapture)`.
6. **Replace the `barcodesScanned` listener** with `barcodeCapture.addListener({ didScan })` (see **Result mapping**).
7. **Preview**: `DataCaptureView.forContext(context)` + `view.connectToElement(element)` on an element with `z-index: -1`, and `view.addOverlay(new BarcodeCaptureOverlay(barcodeCapture))`.
8. **Start**: `barcodeCapture.isEnabled = true` and `await camera.switchToDesiredState(FrameSourceState.On)`. **Stop** (the `stopScan()` equivalent): `barcodeCapture.isEnabled = false`, remove the listener (or clear the callback a permanent listener calls), `await camera.switchToDesiredState(FrameSourceState.Off)`, `view.detachFromElement()`. A stop can arrive while a start is still awaiting setup: bump a counter in stop, and have start bail out after each `await` when the counter changed, so a closed screen never turns the camera on.

### Preview placement: keep the app's HTML on top

ML Kit runs its camera behind a transparent WebView, so the app's close button, progress UI and lists stay visible over the preview. Keep that layout: give the element you connect the view to a **negative z-index**. When the element's `z-index` is below zero the plugin places the native capture view **under** the WebView; with `z-index: 0` or higher the native view covers the app's HTML and the user cannot reach the close button.

```html
<div id="data-capture-view" style="position: fixed; inset: 0; z-index: -1;"></div>
```

- The page's own CSS still paints over the native view. Keep the transparent-background rule the ML Kit screen already used (the `body` class) while scanning, or the preview is hidden behind the page.
- Call `connectToElement` only after the element exists in the DOM: in `useEffect` (React, keyed on the state that renders the element), `ngAfterViewInit` (Angular), `onMounted` (Vue), after `load` in plain JS.
- Tear down on unmount (`useEffect` cleanup, `ngOnDestroy`, `onBeforeUnmount`): stop the scan and call `view.detachFromElement()`.
- No element to connect to (the scanner lives in a service or wrapper whose `start()` takes no element)? Create it there: a `div` with the style above appended to `document.body` before `connectToElement`, removed after `detachFromElement()`. Keep the wrapper's signature.

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

> Never narrow below what the original scanned: no `formats` ⇒ the recommended default set above, not QR only. Code that compared `barcode.format` against ML Kit strings must compare `barcode.symbology` against `Symbology` values. For a format not in this table, fetch the [BarcodeCapture API reference](https://docs.scandit.com/data-capture-sdk/capacitor/barcode-capture/api.html) before writing code.

### Result mapping

| ML Kit concept | BarcodeCapture equivalent |
|---|---|
| `barcodesScanned` event, `event.barcodes` | `didScan(barcodeCapture, session)`: `session.newlyRecognizedBarcode` (one barcode per callback, or `null`) |
| `barcode.rawValue` / `barcode.displayValue` | `barcode.data` (`string \| null` — skip `null`) |
| `barcode.format` | `barcode.symbology` |
| `valueType`, `wifi`, `contactInfo`, … (ML Kit's parsed content) | No equivalent — parse `barcode.data` yourself and name each dropped field in the summary |
| Remove the listener after the first result | `barcodeCapture.isEnabled = false` and `barcodeCapture.removeListener(listener)` |

**Duplicate filter.** BarcodeCapture filters repeats of the same code by default, so identical reads never reach `didScan`. When the app counts consecutive reads of one code (for example "accept after 10 identical reads") or collects multi-part QR codes (animated UR fragments), set `settings.codeDuplicateFilter = 0` so every read reaches `didScan`. Otherwise leave the default.

**Callback blocks frames.** On Capacitor `didScan` blocks frame processing. Do slow work (navigation, network) after setting `barcodeCapture.isEnabled = false`, as `references/integration.md` explains.

**Session safety**: do not keep `session` outside the callback; copy what you need.

### Other `BarcodeScanner` calls

| ML Kit call | Scandit equivalent |
|---|---|
| `readBarcodesFromImage({ path })` | `ImageFrameSource.create(base64Image)`: `await context.setFrameSource(imageSource)` + `barcodeCapture.isEnabled = true` + `await imageSource.switchToDesiredState(FrameSourceState.On)`; the result arrives in the same `didScan`. Read the file as base64 first (e.g. `@capacitor/filesystem`). Afterwards restore the camera with `context.setFrameSource(camera)` and the previous `isEnabled` value. |
| `enableTorch()` / `disableTorch()` / `toggleTorch()` | `camera.desiredTorchState = TorchState.On` / `TorchState.Off` |
| `isTorchAvailable()` | `await camera.getIsTorchAvailable()` |
| `setZoomRatio({ zoomRatio })` | `cameraSettings.zoomFactor = zoomRatio; await camera.applySettings(cameraSettings)` |
| `startScan({ lensFacing })` | `Camera.atPosition(CameraPosition.UserFacing)` for `LensFacing.Front`, `CameraPosition.WorldFacing` for `LensFacing.Back`; to keep the recommended settings use `Camera.asPositionWithSettings(position, cameraSettings)`. Keep the app's camera-direction prop and map its type at the edge so callers do not change. A direction change needs a new camera: stop, then start again. |
| `openSettings()` | No Scandit equivalent — keep the app's own mechanism (a settings plugin or the existing handler) |
| `isSupported()` / `installGoogleBarcodeScannerModule()` | Remove; not needed |

### Permissions

Scandit has no permission API. The OS prompts for camera access when the camera first starts (`switchToDesiredState(FrameSourceState.On)`). Keep the app's own permission check and its denied screen: if it used `BarcodeScanner.checkPermissions()` / `requestPermissions()`, back it with `@capacitor/camera` (`Camera.checkPermissions()` / `Camera.requestPermissions({ permissions: ['camera'] })`) or the app's existing flow, and only then start the scan. `@capacitor/camera` is a separate package: add it (`npm install @capacitor/camera`) when the app does not have it. Both calls resolve `{ camera: 'granted' | 'denied' | 'prompt' | … }`; treat anything but `'granted'` as denied. **Never fake `granted`.** iOS needs `NSCameraUsageDescription` in `Info.plist`; Android's camera permission is added by the plugin.

### Web platform

The Scandit Capacitor plugins do not run in a browser; on web `initializePlugins()` throws. Check `Capacitor.getPlatform() === 'web'` **before** `initializePlugins()` and keep whatever the app already shows on web (a disabled button, a message, another scanner). Do not call any Scandit API on web.

---

## Preserve

- The app's close/stop/progress/paste HTML, its transparent-background `body` class and its permission-denied screen.
- Result routing: whatever the `barcodesScanned` handler did with the value (emit, resolve, navigate) happens in `didScan` instead.
- A stop after the first result when the original stopped after the first result (camera Off, mode disabled, listener removed or its callback cleared, class removed). A scanner that keeps running behind the app drains the battery and keeps the native view up.
- Public signatures of any scanner wrapper (camera-direction prop, `start`/`stop` functions, callbacks).

---

## Putting it all together

A framework-neutral scanner module with continuous reads, the web guard, a reused context, front/back camera and torch, plus a React screen that keeps the app's own Stop button. The module:

```typescript
import { Capacitor } from '@capacitor/core';
import {
  Camera,
  CameraPosition,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
  ScanditCaptureCorePlugin,
  TorchState,
} from 'scandit-capacitor-datacapture-core';
import {
  BarcodeCapture,
  BarcodeCaptureOverlay,
  BarcodeCaptureSettings,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

export interface ScanResult {
  rawValue: string;
  format: string;
}

interface Scanner {
  context: DataCaptureContext;
  barcodeCapture: BarcodeCapture;
  view: DataCaptureView;
}

// Context, mode, view, overlay and listener are created once, on first use, and reused by every scan.
let scannerPromise: Promise<Scanner> | null = null;
let camera: Camera | null = null;
let cameraPosition: CameraPosition | null = null;
let onScanCb: ((result: ScanResult) => void) | null = null;
let generation = 0; // bumped by stopScan(): a startScan() still setting up then bails out

function getScanner(): Promise<Scanner> {
  if (!scannerPromise) {
    scannerPromise = (async () => {
      await ScanditCaptureCorePlugin.initializePlugins();
      const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

      const settings = new BarcodeCaptureSettings();
      settings.enableSymbologies([
        Symbology.QR,
        Symbology.EAN13UPCA,
        Symbology.Code128,
      ]);
      settings.codeDuplicateFilter = 0; // the app counts consecutive reads of one code

      const barcodeCapture = new BarcodeCapture(settings);
      barcodeCapture.isEnabled = false;
      await context.setMode(barcodeCapture);
      barcodeCapture.addListener({
        didScan: async (_mode, session) => {
          const barcode = session.newlyRecognizedBarcode;
          if (barcode?.data) {
            onScanCb?.({ rawValue: barcode.data, format: barcode.symbology });
          }
        },
      });

      const view = DataCaptureView.forContext(context);
      await view.addOverlay(new BarcodeCaptureOverlay(barcodeCapture));
      return { context, barcodeCapture, view };
    })();
  }
  return scannerPromise;
}

export function isScanningSupported(): boolean {
  return Capacitor.getPlatform() !== 'web';
}

// `element` must already be in the DOM and carry `z-index: -1`.
export async function startScan(
  element: HTMLElement,
  onScan: (result: ScanResult) => void,
  position: CameraPosition = CameraPosition.WorldFacing,
): Promise<void> {
  if (!isScanningSupported()) {
    throw new Error('Scanning is not available in a browser');
  }
  const mine = ++generation;
  const { context, barcodeCapture, view } = await getScanner();
  if (mine !== generation) return; // stopped while setting up

  // A camera is bound to one position: create a new one only when the position changes.
  let active = camera;
  if (!active || cameraPosition !== position) {
    active = Camera.asPositionWithSettings(position, BarcodeCapture.createRecommendedCameraSettings());
    if (!active) {
      throw new Error('No camera available');
    }
    await context.setFrameSource(active);
    camera = active;
    cameraPosition = position;
    if (mine !== generation) return;
  }

  onScanCb = onScan;
  view.connectToElement(element);
  barcodeCapture.isEnabled = true;
  await active.switchToDesiredState(FrameSourceState.On); // the OS camera prompt fires here
}

export function setTorch(on: boolean): void {
  if (camera) {
    camera.desiredTorchState = on ? TorchState.On : TorchState.Off;
  }
}

export async function stopScan(): Promise<void> {
  generation++;
  if (!scannerPromise) return;
  const { barcodeCapture, view } = await scannerPromise;
  barcodeCapture.isEnabled = false;
  await camera?.switchToDesiredState(FrameSourceState.Off);
  view.detachFromElement();
  onScanCb = null;
}
```

The screen. The container exists only after `scanning` becomes true, so the scan starts in an effect; the cleanup stops it on unmount:

```tsx
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { startScan, stopScan, isScanningSupported, ScanResult } from './scanner';

export function ScanButton({ onResult }: { onResult: (value: string) => void }) {
  const viewRef = useRef<HTMLDivElement>(null);
  const [scanning, setScanning] = useState(false);
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  const close = useCallback(async () => {
    await stopScan();
    document.body.classList.remove('scanner-active');
    setScanning(false);
  }, []);

  // The container exists only after the render with `scanning === true`, so start in an effect.
  useEffect(() => {
    if (!scanning || !viewRef.current) return;
    document.body.classList.add('scanner-active');
    startScan(viewRef.current, (result: ScanResult) => {
      void close();
      onResultRef.current(result.rawValue);
    }).catch((error: unknown) => {
      console.error('Scanner failed to start', error); // e.g. no camera, plugin init failed
      void close();
    });
    return () => {
      void stopScan();
    };
  }, [scanning, close]);

  if (!isScanningSupported()) {
    return <p>QR scanning requires a mobile device</p>;
  }

  if (scanning) {
    return (
      <>
        <div ref={viewRef} style={{ position: 'fixed', inset: 0, zIndex: -1 }} />
        <button style={{ position: 'fixed', top: 16, right: 16 }} onClick={close}>
          Stop
        </button>
      </>
    );
  }
  return <button onClick={() => setScanning(true)}>Scan QR code</button>;
}
```

> The same structure applies in Angular (`ngAfterViewInit` calls `startScan`, `ngOnDestroy` calls `stopScan`) and Vue (`onMounted` / `onBeforeUnmount`).
>
> `BarcodeCaptureOverlay` draws a highlight on each recognised code — a visual change from ML Kit, which drew nothing. Name it in the summary.

---

## After applying changes

1. `npm uninstall @capacitor-mlkit/barcode-scanning`, `npm install scandit-capacitor-datacapture-core scandit-capacitor-datacapture-barcode`, then `npx cap sync`.
2. Type-check (`npx tsc --noEmit`) and fix every error before finishing; an ML Kit `rawValue` is `string | undefined` while `barcode.data` is `string | null`, so adjust types that carried it.
3. iOS: keep (or add) `NSCameraUsageDescription` in `Info.plist`. Android: nothing to add.
4. Set the license key, and confirm the connected element has a negative `z-index`.
5. Show only what changed: what was removed from the ML Kit flow, what was added for BarcodeCapture, and each judgment call (enabled symbologies, duplicate filter, overlay, dropped typed fields).
