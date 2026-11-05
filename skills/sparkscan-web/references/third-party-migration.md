# Third-Party Scanner → SparkScan Migration (Web)

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behavior change (new default, different overlay look, changed feedback, changed scan timing, changed scanned value) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm. Replacing the library's camera box or `<video>` preview with SparkScan's trigger button and mini preview is always one of them.
- **Compatibility layer.** When the scanning code sits behind a shared scanner module or wrapper that other code calls, keep that module's public API frozen (same types, function names, callbacks) and replace only the third-party scanner calls underneath with Scandit ones.
- **Preserve, never invent.** Keep the app's own model, list, dedupe, totals, clear and network logic. Do not add symbologies or filters the original did not have; do not silently drop a feature (flag it instead).

This guide replaces **ZXing-js** (`@zxing/browser`, `@zxing/library`), **html5-qrcode** and the **`BarcodeDetector` API** (native, or the `barcode-detector` polyfill) with Scandit **SparkScan**. For the full SparkScan API read `references/integration.md`, and `references/react.md` when the page is a React component; this guide is the delta.

## Step 1: Identify the library and decide whether SparkScan fits

Read the existing code first; do not ask the user to describe it. Identify the library by its imports and `package.json`:

- **ZXing-js** — `BrowserMultiFormatReader` (or `BrowserQRCodeReader`) with `decodeFromVideoDevice` / `decodeFromConstraints` / `decodeOnceFromVideoDevice`, format hints via `DecodeHintType.POSSIBLE_FORMATS` and `BarcodeFormat`, `IScannerControls.stop()` / `switchTorch()`, or the older `@zxing/library`-only `reader.reset()`.
- **html5-qrcode** — `new Html5Qrcode(elementId, { formatsToSupport })` with `start(camera, { fps, qrbox }, onSuccess, onError)` / `stop()` / `pause()` / `resume()`, or the ready-made `Html5QrcodeScanner(...).render(onSuccess, onError)` / `clear()`; `Html5QrcodeSupportedFormats`, `getRunningTrackCameraCapabilities().torchFeature()`, `scanFile()`.
- **`BarcodeDetector`** — `new BarcodeDetector({ formats })`, `BarcodeDetector.getSupportedFormats()`, `await detector.detect(video)` inside a `requestAnimationFrame` or `setInterval` loop over a `getUserMedia` stream, often with `import "barcode-detector/polyfill"` (or `barcode-detector/ponyfill`) for browsers without it.

Then decide:

- **SparkScan fits** a page that scans one code at a time and either keeps going ("scan, add to a list, keep scanning") or stops once, and whose camera UI is just the preview plus a few buttons (torch, camera switch).
- **Use `barcode-capture-web` instead** when the camera UI must stay as it is: a hand-drawn highlight from `getResultPoints()` / `bounds` / `cornerPoints` / `boundingBox`, region-of-interest logic, a bespoke preview layout, or a camera owned by a shared component. Say so in one line, build on that skill's `references/integration.md`, and carry over Steps 2 and 3 of this guide.
- **Several codes per frame genuinely needed** (the code loops over every `detect()` result or accumulates a frame's codes together, live highlights on each)? Use `matrixscan-batch-web`. SparkScan reports one `session.newlyRecognizedBarcode` per callback.

Also read the installed Scandit SDK version (`@scandit/web-datacapture-*` in `package.json`; none yet means the latest). This guide's code compiles against 8.6.1; on 7.x, upgrade first with `references/migration.md`.

## Step 2: Remove the third-party scanner

- The packages from `package.json` once nothing imports them: `@zxing/browser`, `@zxing/library`, `html5-qrcode`, `barcode-detector`.
- The imports, the reader / scanner / detector instance, its start, decode and stop calls (`decodeFromVideoDevice`, `start`, `render`, `detect`, `controls.stop()`, `reset()`, `clear()`), the hints / `formatsToSupport` / `formats` configuration and any `getSupportedFormats()` filtering.
- The `<video>` element (or the `<div>` html5-qrcode rendered into) and everything that fed it: `navigator.mediaDevices.getUserMedia`, `video.srcObject`, `video.play()`, stopping the stream's tracks. SparkScan opens and closes the camera itself.
- The decode loop and its throttles: `requestAnimationFrame` / `setInterval` ticks, scan-interval delays, `fps`, ZXing's `delayBetweenScanAttempts` and `delayBetweenScanSuccess`. SparkScan runs its own frame loop, so there is nothing to throttle: say so in the summary.
- `visibilitychange` / `pagehide` handlers that only stop or restart the camera: `SparkScanView` already goes idle when the page is hidden. Do not port them to `stopScanning()`.
- The app's own torch and camera-switch buttons, any hand-drawn highlight canvas, and success beeps or `navigator.vibrate` calls: SparkScan's toolbar and feedback replace them (Step 6).

Keep the rest of the page: lists, totals, clear and "Scan again" buttons, result panels, network calls.

## Step 3: Map formats to symbologies

Map **only** the formats the app scanned, from the hint list, `formatsToSupport` or `formats`. Several source formats can map to one Scandit symbology (EAN-13 and UPC-A are both `Symbology.EAN13UPCA`): enable it once. **Do not derive Scandit names from the source names** — `qr_code` / `QR_CODE` is `Symbology.QR`, never `QRCode`, and there is no `EAN8UPCE` (EAN-8 is `Symbology.EAN8`, UPC-E is `Symbology.UPCE`).

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

For a format not in the table (`MICRO_QR_CODE`, the polyfill's `micro_qr_code`, `code_32`, …), check the `Symbology` API reference before mapping it. "All formats" (no `POSSIBLE_FORMATS` hint, no `formatsToSupport`, no `formats`, the polyfill's `'any'`, or every value `getSupportedFormats()` returned): enable what the app really consumes, or the recommended default set above, and add a summary line "symbologies were not narrowed by the original; confirm this list". A polyfill group value narrows that to the default-set members of its group: `'linear_codes'` is EAN13UPCA, EAN8, UPCE, Code39, Code93, Code128, InterleavedTwoOfFive and Codabar; `'matrix_codes'` is QR, DataMatrix, Aztec and PDF417.

**UPC-A values.** These libraries return a UPC-A code as 12 digits when UPC-A is among the formats; `Symbology.EAN13UPCA` returns it as 13 digits with a leading `0`. When the app scanned UPC-A, keep the 12-digit values with `settings.settingsForSymbology(Symbology.EAN13UPCA).setExtensionEnabled("remove_leading_upca_zero", true)`, or flag the changed value as a judgment call.

Symbologies go on `SparkScanSettings` (`settings.enableSymbologies([...])`, Step 5). `settings.codeDuplicateFilter` is the time in milliseconds before the same code is reported again; leave it at the default unless the old code skipped repeats of the same code, and list any value you set as a judgment call. A manual same-code cooldown (a `lastCode` / `lastScanAt` check) becomes `codeDuplicateFilter` with that many milliseconds, and the manual check goes. The two differ: the cooldown only skipped a repeat of the last code, while `codeDuplicateFilter` holds back every code seen within the window, so A, B, A inside it now reports A once. Where the page counts quantities, list that as a judgment call. A `Set` that never adds a code twice is the app's own list logic: keep it as it is.

## Step 4: Replace the callback with `didScan`

| Old | SparkScan |
|---|---|
| ZXing `decodeFromVideoDevice(…, (result, error, controls) => …)`, html5-qrcode `start(…, onSuccess, onError)` / `render(onSuccess, onError)`, `BarcodeDetector` `await detector.detect(video)` in a loop | `sparkScan.addListener({ didScan: (sparkScan, session) => … })`: read `session.newlyRecognizedBarcode` (one `Barcode \| null`); never loop over an array |
| `result.getText()` / `decodedText` / `barcode.rawValue` | `barcode.data` (`string \| null`; keep or add the null guard) |
| `result.getBarcodeFormat()` / `decodedResult.result.format.formatName` / `barcode.format` | `barcode.symbology`. When the app shows, stores or compares the old format string, keep it with a small `Symbology` → old-string lookup (EAN-13 and UPC-A share `Symbology.EAN13UPCA`; with `remove_leading_upca_zero` on, 12-digit data is UPC-A), or use `new SymbologyDescription(barcode.symbology).readableName` and flag the changed names (`EAN-13/UPC-A`, not `EAN_13`). |
| `getResultPoints()` / `result.bounds` / `cornerPoints` / `boundingBox` | `barcode.location`; SparkScan draws no app overlay, so a page that needs them belongs on `barcode-capture-web` (Step 1). |
| The error callback, `NotFoundException` checks, empty `detect()` results | Delete them: there is no per-frame "nothing found" callback. |

Move the old callback's body in unchanged: dedupe, list state, totals, lookups, navigation. Copy `data` and `symbology` out; do not keep `session` outside the callback.

Flow shapes:

- **Scan and continue** (the decode loop kept running and the page adds each code to a list): set `viewSettings.scanningBehavior = SparkScanScanningBehavior.Continuous` (Step 5). SparkScan's default is single scanning: one code per trigger press. Even in continuous scanning the user starts it with the trigger button, and it stops after 10 seconds without a scan (`viewSettings.inactiveStateTimeout`); the old loop ran until the page closed it. List all three as judgment calls.
- **Scan once** (the success handler calls `stop()`, `clear()`, `controls.stop()` or used `decodeOnceFromVideoDevice`, then shows the result and a "Scan again" button): keep the default single scanning. After the code SparkScan plays its success feedback, goes inactive and pauses the camera (it keeps the stream open rather than releasing it like `stop()` did), so `stop()` needs no replacement. The trigger button and the mini preview can still start a new scan while the result is shown: keep the app's guard, so such a code is ignored (it still gets SparkScan's success feedback). List both as judgment calls. In place of Step 5's `listener`, with the `declare` lines standing for Step 5's objects and the page's own button and result code:

```typescript
import type { SparkScan, SparkScanListener, SparkScanView } from "@scandit/web-datacapture-barcode";

declare const sparkScan: SparkScan;
declare const view: SparkScanView;
declare const restartButton: HTMLButtonElement;
declare function showResult(code: string): Promise<void>;

let shownCode: string | null = null;

const listener: SparkScanListener = {
  didScan: (_sparkScan, session) => {
    const code = session.newlyRecognizedBarcode?.data;
    if (shownCode !== null || code == null) {
      return;
    }
    shownCode = code;
    restartButton.hidden = false;
    void showResult(code);
  },
};
sparkScan.addListener(listener);

restartButton.addEventListener("pointerup", (event) => event.stopPropagation());
restartButton.addEventListener("click", () => {
  shownCode = null;
  restartButton.hidden = true;
  void view.startScanning();
});
```

The `pointerup` handler keeps SparkScan's click-outside handler from sending the view to idle while the button starts it (`references/integration.md`, **Overriding the click-outside behavior**). Never call `stopScanning()` (or Step 5's teardown) inside `didScan`: SparkScan handles the same code after the app's listener, and a stopped view cannot.
- **Scan once and navigate away:** set the guard first, then navigate, so a second callback cannot navigate twice. Run Step 5's teardown from the route change, never from inside `didScan`.

## Step 5: Mount `SparkScanView`

Mount SparkScan on a container element where the `<video>` was; the rest of the page stays where it is. The scan-and-continue shape, compiled against 8.6.1 (`addCode` stands for the page's own list code):

```typescript
import {
  barcodeCaptureLoader,
  SparkScan,
  type SparkScanListener,
  SparkScanScanningBehavior,
  SparkScanSettings,
  SparkScanView,
  SparkScanViewSettings,
  Symbology,
} from "@scandit/web-datacapture-barcode";
import { BrowserHelper, DataCaptureContext } from "@scandit/web-datacapture-core";
import { showMultithreadingWarning } from "./multithreading-warning";

declare function addCode(code: string): void;

export async function startScanner(): Promise<() => Promise<void>> {
  BrowserHelper.checkMultithreadingSupport()
    .then((supported) => {
      if (!supported) {
        showMultithreadingWarning();
      }
    })
    .catch(console.error);

  const context = await DataCaptureContext.forLicenseKey("-- ENTER YOUR SCANDIT LICENSE KEY HERE --", {
    libraryLocation: new URL("self-hosted-scandit-sdc-lib", document.baseURI).toString(),
    moduleLoaders: [barcodeCaptureLoader()],
  });

  const settings = new SparkScanSettings();
  settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.QR]);
  const sparkScan = SparkScan.forSettings(settings);

  const listener: SparkScanListener = {
    didScan: (_sparkScan, session) => {
      const barcode = session.newlyRecognizedBarcode;
      if (barcode?.data == null) {
        return;
      }
      addCode(barcode.data);
    },
  };
  sparkScan.addListener(listener);

  const viewSettings = new SparkScanViewSettings();
  viewSettings.scanningBehavior = SparkScanScanningBehavior.Continuous;

  const container = document.createElement("div");
  container.style.cssText = "position: fixed; inset: 0; pointer-events: none;";
  document.body.appendChild(container);

  const view = SparkScanView.forElement(container, context, sparkScan, viewSettings);
  view.style.pointerEvents = "auto";

  const teardown = async (): Promise<void> => {
    sparkScan.removeListener(listener);
    await view.stopScanning();
    container.remove();
  };
  try {
    await view.prepareScanning();
  } catch (error) {
    await teardown();
    throw error;
  }
  return teardown;
}
```

- On a scan-once page, use Step 4's `listener` instead of this one and leave `scanningBehavior` at its default.
- The container rules (non-zero size, `pointer-events`, scoping SparkScan to part of the page) are in `references/integration.md`. Import `showMultithreadingWarning` from the `multithreading-warning` helper module in `references/integration.md`, which adds the dialog to the page itself; in React, render the dialog from component state instead (`references/react.md`). `libraryLocation` points at the self-hosted `sdc-lib` folder, or at the CDN pinned to the installed version (see **Loading the SDK from a CDN** there).
- Call the returned teardown when the page or component unmounts, not on `pagehide`. When `prepareScanning()` rejects (camera refused or missing), `startScanner()` has already cleaned up and rethrows: show the app's camera message where it is called.

## Step 6: Camera controls, feedback and lifecycle

- **Torch** (ZXing `controls.switchTorch()`, html5-qrcode `torchFeature().apply()` or `showTorchButtonIfSupported`, a `{ advanced: [{ torch: true }] }` track constraint, and the app's button) → the toolbar's torch control, which SparkScan shows whenever the camera has a torch: it sets `view.torchControlVisible` from the camera when the view prepares, so hiding it means setting `false` after `await view.prepareScanning()`. A camera switch shows it again with no event the app can catch: list hiding the torch together with `cameraSwitchButtonVisible` as a judgment call. SparkScan owns the camera, so there is no track to set a torch state on. Delete the app's torch button and its state, and list the UI change as a judgment call.
- **Camera choice** (`deviceId`, `listVideoInputDevices()`, `Html5Qrcode.getCameras()`, `rememberLastUsedCamera`, `facingMode`) → SparkScan uses the back camera. For a user-controlled switch set `view.cameraSwitchButtonVisible = true`; a fixed front camera is `viewSettings.defaultCameraPosition = CameraPosition.UserFacing` (`CameraPosition` from `@scandit/web-datacapture-core`). Flag either one.
- **Camera permission** → the browser asks when `prepareScanning()` sets up the camera, so when the view mounts. The page still needs HTTPS (or `localhost`); see `references/troubleshooting.md`. `prepareScanning()` rejects when the camera cannot be opened: show the app's own refused-camera message (the old `getUserMedia` `NotAllowedError` path) from that rejection rather than dropping it.
- **`qrbox`, `aspectRatio`, `disableFlip`, ZXing `TRY_HARDER` hints** have no SparkScan equivalent: say they were removed.
- **Feedback**: success beeps and `navigator.vibrate` → SparkScan's built-in sound and haptic feedback (`viewSettings.soundEnabled`, `viewSettings.hapticEnabled`); say that it replaces them. A code the app rejects ("not a valid ticket") can get SparkScan's error feedback through `view.feedbackDelegate` (`references/integration.md`, **SparkScan feedback API**).

## Step 7: Still images

html5-qrcode `scanFile()` / `scanFileV2()` and the file tab `Html5QrcodeScanner` shows by default (`supportedScanTypes`), ZXing `decodeFromImageUrl()` / `decodeFromImageElement()`, and `detector.detect(image)` on an uploaded photo have no SparkScan equivalent: SparkScan owns its camera and takes no other frame source. Decode the file with a `BarcodeCapture` mode fed by `await ImageFrameSource.fromFile(file)` (from `@scandit/web-datacapture-core`), set as the context's mode and frame source and switched on with `switchToDesiredState(FrameSourceState.On)`. `prepareScanning()` puts SparkScan's mode and camera on that same context, so call `await view.stopScanning()` first and `await view.prepareScanning()` when the user is back on the scanning page. Feed the result into the same list. Never drop the upload path; list the moved path as a judgment call to check in a browser. If the page's main job is decoding photos, SparkScan does not fit: use `barcode-capture-web` for the whole page.

## Step 8: Verify

Type-check the migrated file (`npx tsc --noEmit`) and fix every error. The usual ones: `Symbology.QRCode` or `Symbology.EAN8UPCE` (they do not exist), `data` used as `string` without the null guard, a missing `barcodeCaptureLoader()` in `moduleLoaders`, a leftover import of the old library. No `@zxing/*`, `html5-qrcode`, `BarcodeDetector`, `getUserMedia`, `requestAnimationFrame` decode loop or new `TODO` may remain.

## Step 9: Setup checklist and summary

Show the setup checklist from `references/integration.md`, plus:

1. Remove the old scanner packages (`@zxing/browser`, `@zxing/library`, `html5-qrcode`, `barcode-detector`) from `package.json`.
2. Delete the old `<video>` / scanner container markup.
3. The `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` headers are new: the old libraries ran without them. `require-corp` blocks cross-origin images, scripts and iframes that do not opt in, and `same-origin` cuts the page's link to cross-origin popups (sign-in, payment); see `references/troubleshooting.md`.

**Summary:** list what was removed and added, the format → symbology mapping, and every judgment call: the trigger button and mini preview instead of the camera box, the scanning behavior and its 10-second timeout, a paused rather than released camera and ignored rescans that still get success feedback (scan-once pages), the torch and camera switch on SparkScan's toolbar, the duplicate filter, UPC-A values, the removed throttles and scan box (SparkScan runs its own frame loop), SparkScan's sound and haptic feedback replacing the old beep or `navigator.vibrate`, changed format names, symbologies not narrowed, the moved still-image path, and the new headers. Do not list code that was already correct.

## API reference

- SparkScan API: https://docs.scandit.com/data-capture-sdk/web/barcode-capture/api.html#:~:text=SymbologySettings-,SparkScan,-SparkScan
- Get Started: https://docs.scandit.com/sdks/web/sparkscan/get-started/
