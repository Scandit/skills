# Third-Party Scanner → BarcodeCapture Migration (Cordova)

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and replace only the third-party scanner calls underneath with Scandit ones.

This guide replaces **`phonegap-plugin-barcodescanner`** (and its forks `cordova-plugin-barcodescanner` and `@red-mobile/cordova-plugin-barcodescanner`, same API) with Scandit **BarcodeCapture**. For the full BarcodeCapture API read `references/integration.md`; this guide is the delta.

> **Language note**: Examples use plain JavaScript on the global `Scandit.*` namespace, gated on `deviceready`. Do not emit `import` from `scandit-cordova-datacapture-*` in WebView runtime code.

## Before anything else

Read the existing code. Do not ask the user to describe what their scanner does. Identify:

- Every `cordova.plugins.barcodeScanner.scan(success, error, options)` call and its `options` (`formats`, `preferFrontCamera`, `showFlipCameraButton`, `showTorchButton`, `torchOn`, `saveHistory`, `orientation`, `prompt`, `resultDisplayDuration`, `disableSuccessBeep`, `disableAnimations`).
- What `success` does with the result (`text`, `format`, `cancelled`): dedupe, list, navigation, lookups. What `error` does.
- Whether the app treats `scan()` as one-shot (one call, one result, scanner closes) or re-calls it for each code.

`scan()` opens a full-screen native scanner and closes it after one result. BarcodeCapture runs inside your page and keeps scanning until you stop it, so the **one-shot** behaviour is something you rebuild (below). Decide per call site; if the app only ever scans one code per call, use the one-shot pattern, otherwise the continuous one.

If the screen scans several codes per frame at once, use `matrixscan-batch-cordova`. If you want Scandit's pre-built scanning UI instead of a camera view you lay out, use `sparkscan-cordova` (its `references/third-party-migration.md`).

## Remove

- The plugin: `cordova plugin remove phonegap-plugin-barcodescanner` (or the fork in use).
- The `cordova.plugins.barcodeScanner.scan(...)` call and its `options` object, and the `result.cancelled` / `result.text` / `result.format` handling.
- `cordova.plugins.barcodeScanner.encode(...)` (QR generation) has no Scandit equivalent: keep it only if you keep the plugin, otherwise flag it in the summary instead of dropping it silently.
- Keep the app's own list, dedupe, summary and navigation code.

## Integrate BarcodeCapture

Follow `references/integration.md`. The shape of the rewrite:

1. In the `deviceready` handler: `Scandit.DataCaptureContext.initialize(key)` once.
2. `new Scandit.BarcodeCaptureSettings()` + `settings.enableSymbologies([...])` from the table below, then `new Scandit.BarcodeCapture(settings)` and `context.setMode(barcodeCapture)`.
3. Camera: `Scandit.Camera.withSettings(Scandit.BarcodeCapture.createRecommendedCameraSettings())` (world-facing) and `context.setFrameSource(camera)`.
4. `Scandit.DataCaptureView.forContext(context)` + `await view.connectToElement(<sized element>)`, then `view.addOverlay(new Scandit.BarcodeCaptureOverlay(barcodeCapture))`.
5. The `success` callback becomes `barcodeCapture.addListener({ didScan })`.
6. Start with `camera.switchToDesiredState(Scandit.FrameSourceState.On)`.

### Symbology mapping

Map **only** the formats the app passed in `options.formats` (a comma-separated string); fewer symbologies scan faster and more accurately. Do not derive Scandit names from the plugin's names.

<!-- BEGIN GENERATED symbology-table sources=phonegap style=js namespace=Scandit.Symbology -->
| `phonegap-plugin-barcodescanner` `formats` string | Scandit `Scandit.Symbology` |
|---|---|
| `QR_CODE` | `Scandit.Symbology.QR` (**not** `QRCode`) |
| `EAN_13` | `Scandit.Symbology.EAN13UPCA` |
| `EAN_8` | `Scandit.Symbology.EAN8` |
| `UPC_A` | `Scandit.Symbology.EAN13UPCA` (UPC-A is read by the EAN-13/UPC-A symbology) |
| `UPC_E` | `Scandit.Symbology.UPCE` |
| `CODE_39` | `Scandit.Symbology.Code39` |
| `CODE_93` | `Scandit.Symbology.Code93` |
| `CODE_128` | `Scandit.Symbology.Code128` |
| `ITF` | `Scandit.Symbology.InterleavedTwoOfFive` (no ITF-14 symbology; ITF-14 is a 14-digit Interleaved 2 of 5) |
| `CODABAR` | `Scandit.Symbology.Codabar` |
| `DATA_MATRIX` | `Scandit.Symbology.DataMatrix` |
| `AZTEC` | `Scandit.Symbology.Aztec` |
| `PDF_417` | `Scandit.Symbology.PDF417` |
| `MSI` | `Scandit.Symbology.MSIPlessey` |
| `RSS14` | `Scandit.Symbology.GS1Databar` |
| `RSS_EXPANDED` | `Scandit.Symbology.GS1DatabarExpanded` |
| `MAXICODE` (not in the plugin's documented list; Android passes it through to ZXing, iOS ignores it) | `Scandit.Symbology.MaxiCode` |
| `UPC_EAN_EXTENSION` (not in the plugin's documented list; Android accepts it but it enables no reader on its own, iOS ignores it) | No symbology of its own: the 2/5-digit add-on arrives as `barcode.addOnData` on the EAN/UPC result. Look up how to enable add-ons in the API reference before writing it. |

**Recommended default set** when the source scanned every format and nothing in the app narrows it: `Scandit.Symbology.QR`, `Scandit.Symbology.EAN13UPCA`, `Scandit.Symbology.EAN8`, `Scandit.Symbology.UPCE`, `Scandit.Symbology.Code39`, `Scandit.Symbology.Code93`, `Scandit.Symbology.Code128`, `Scandit.Symbology.InterleavedTwoOfFive`, `Scandit.Symbology.Codabar`, `Scandit.Symbology.DataMatrix`, `Scandit.Symbology.Aztec`, `Scandit.Symbology.PDF417`.
<!-- END GENERATED symbology-table -->

**No `formats` option** means the plugin scanned every format it supports. Never guess one symbology: search the project for what the app really consumes and enable exactly that. If nothing narrows it, enable the recommended default set under the table and add a summary line "symbologies were not narrowed by the original; confirm this list". If a format is not in the table, look it up in the API reference before writing it.

## Options mapping

| `options` | BarcodeCapture |
|---|---|
| `formats` | `settings.enableSymbologies([...])` (table above) |
| `preferFrontCamera` | `Scandit.Camera.atPosition(Scandit.CameraPosition.UserFacing)` (`WorldFacing` for back); the positional factory uses default settings, so call `camera.applySettings(Scandit.BarcodeCapture.createRecommendedCameraSettings())`. It returns `null` when the device has no such camera. |
| `showTorchButton` | `view.addControl(new Scandit.TorchSwitchControl())` on the `DataCaptureView`: Scandit's own button, so flag the look as a UI change. **Only add it if the original set `showTorchButton: true`.** |
| `torchOn` | `camera.desiredTorchState = Scandit.TorchState.On` |
| `showFlipCameraButton` | `view.addControl(new Scandit.CameraSwitchControl(worldCamera, userCamera))` with the two `Camera.atPosition(...)` cameras; the first is the one set as frame source. **Only add it if the original set `showFlipCameraButton: true`.** |
| `orientation` | No Scandit option. Keep it in `config.xml`: `<preference name="Orientation" value="portrait" />` (or `landscape`). |
| `prompt` | No equivalent. Show the text in your own HTML element next to the preview and flag it as a judgment call. |
| `resultDisplayDuration`, `disableAnimations`, `saveHistory` | No equivalent; say they were dropped. |
| `disableSuccessBeep` | `const feedback = Scandit.BarcodeCaptureFeedback.default; feedback.success = new Scandit.Feedback(Scandit.Vibration.defaultVibration, null); barcodeCapture.feedback = feedback;` (drops the sound, keeps the vibration). Without it, BarcodeCapture beeps and vibrates by default. |

## Result mapping

| `scan()` | BarcodeCapture |
|---|---|
| `success(result)` | `didScan: async (mode, session) => ...` reading `session.newlyRecognizedBarcode` (a single `Barcode \| null`) |
| `result.text` | `barcode.data` (`string \| null`; keep a null guard) |
| `result.format` (e.g. `'QR_CODE'`) | `barcode.symbology` (a `Scandit.Symbology` value); `new Scandit.SymbologyDescription(barcode.symbology).readableName` for display only. If the app stores or compares the old format string, keep that contract with a small `Symbology` → old-string lookup. |
| `result.cancelled` | No equivalent: nothing is "cancelled" unless your page offers a Close button. Add one only where the old flow had a cancel path, and call the same teardown. |
| `error(message)` | A rejected `camera.switchToDesiredState(...)` or a `null` camera. Call the old error handler from the `catch`. |

Move the body of the old `success` callback into `didScan` unchanged, apart from the field names. Do not keep `session` outside the callback; copy `data` and `symbology` out.

## Continuous pattern (scan, add, keep scanning)

For a screen that scans repeatedly (a button opens the scanner, each new code is added to a list). The app's list, dedupe and `renderItems` stay as they were; only the scanner call changes. Verified against 8.6.1:

```javascript
const scannedItems = [];
let context, camera, barcodeCapture, view;

function renderItems() { /* unchanged */ }

async function setupScanner() {
  context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const settings = new Scandit.BarcodeCaptureSettings();
  settings.enableSymbologies([
    Scandit.Symbology.QR,
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.Code128,
  ]);
  barcodeCapture = new Scandit.BarcodeCapture(settings);
  barcodeCapture.isEnabled = false;
  await context.setMode(barcodeCapture);

  const cameraSettings = Scandit.BarcodeCapture.createRecommendedCameraSettings();
  camera = Scandit.Camera.withSettings(cameraSettings);
  if (!camera) { alert('Scanning failed: no camera'); return false; }
  const frontCamera = Scandit.Camera.atPosition(Scandit.CameraPosition.UserFacing);
  await context.setFrameSource(camera);

  barcodeCapture.addListener({
    didScan: async (_mode, session) => {
      const barcode = session.newlyRecognizedBarcode;
      if (!barcode || barcode.data == null) return;
      const alreadyScanned = scannedItems.some((item) => item.text === barcode.data);
      if (alreadyScanned) return;
      const format = new Scandit.SymbologyDescription(barcode.symbology).readableName;
      scannedItems.push({ text: barcode.data, format });
      renderItems();
    },
  });

  view = Scandit.DataCaptureView.forContext(context);
  await view.connectToElement(document.getElementById('data-capture-view'));
  await view.addOverlay(new Scandit.BarcodeCaptureOverlay(barcodeCapture));
  await view.addControl(new Scandit.TorchSwitchControl());
  if (frontCamera) {
    frontCamera.applySettings(cameraSettings);
    await view.addControl(new Scandit.CameraSwitchControl(camera, frontCamera));
  }
  await view.hide();
  return true;
}

async function startScan() {
  try {
    await view.show();
    barcodeCapture.isEnabled = true;
    await camera.switchToDesiredState(Scandit.FrameSourceState.On);
  } catch (error) {
    alert('Scanning failed: ' + error);
  }
}

async function stopScan() {
  barcodeCapture.isEnabled = false;
  await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
  await view.hide();
}

document.addEventListener('deviceready', async () => {
  // Wire the buttons only once setup finished, so a tap cannot reach an undefined view.
  if (!(await setupScanner())) return;
  document.getElementById('scan-button').addEventListener('click', startScan);
  document.getElementById('close-button').addEventListener('click', stopScan);
}, false);
```

The HTML needs a sized element for the preview and, in place of the plugin's own back button, a Close control that calls `stopScan()`:

```html
<div id="data-capture-view" style="position: fixed; inset: 0; z-index: -1;"></div>
<button id="close-button">Close</button>
```

Keep the element laid out (do not use `display: none` on it): the native preview takes its position and size from the element, and `view.hide()` / `view.show()` toggle the preview itself. The torch and flip controls above come from `showTorchButton: true` and `showFlipCameraButton: true` in this fixture; drop each line whose option the original lacked.

## One-shot pattern (a promise per `scan()` call)

For code that wraps `scan()` in a function or promise and expects one result, then the scanner to close. This helper keeps that contract; the rest of the app calls it exactly as before. Create the context once at `deviceready` and pass it in:

```javascript
async function scanBarcode(context) {
  const settings = new Scandit.BarcodeCaptureSettings();
  settings.enableSymbologies([Scandit.Symbology.QR, Scandit.Symbology.EAN13UPCA]);
  const barcodeCapture = new Scandit.BarcodeCapture(settings);
  const camera = Scandit.Camera.withSettings(Scandit.BarcodeCapture.createRecommendedCameraSettings());
  if (!camera) throw new Error('no camera');
  const view = Scandit.DataCaptureView.forContext(context);

  let listener;
  const finish = async () => {
    barcodeCapture.removeListener(listener);
    barcodeCapture.isEnabled = false;
    await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
    await context.removeMode(barcodeCapture);
    view.detachFromElement();
  };
  const scanned = new Promise((resolve) => {
    listener = {
      didScan: async (_mode, session) => {
        const barcode = session.newlyRecognizedBarcode;
        if (!barcode) return;
        barcodeCapture.isEnabled = false;
        resolve({
          text: barcode.data,
          format: new Scandit.SymbologyDescription(barcode.symbology).readableName,
          cancelled: false,
        });
      },
    };
  });

  try {
    await context.setMode(barcodeCapture);
    await context.setFrameSource(camera);
    barcodeCapture.addListener(listener);
    await view.connectToElement(document.getElementById('data-capture-view'));
    await view.addOverlay(new Scandit.BarcodeCaptureOverlay(barcodeCapture));
    barcodeCapture.isEnabled = true;
    await camera.switchToDesiredState(Scandit.FrameSourceState.On);
    return await scanned;
  } finally {
    await finish();
  }
}
```

Disable the mode at the top of `didScan` so a second code in the same frame cannot resolve twice. Teardown order is: `removeListener`, `isEnabled = false`, camera off, `removeMode`, then detach the view. Never call `context.dispose()`. If the old code returned `{ cancelled: true }` on back-press, keep the `resolve` of `scanned` in a variable and call it from a Close button with `{ cancelled: true }`; the `finally` tears down either way.

## Preserve and verify

Keep the app's data models, list state, dedupe, summary and navigation code, and its error handling. Add nothing the original lacked; flag anything you could not carry over.

Run `node --check` on the migrated file. Then confirm each Scandit symbol you wrote exists: the usual mistakes are `Scandit.Symbology.QR_CODE` / `QRCode` (it is `QR`), `Scandit.DataCaptureContext.forLicenseKey(` or `Scandit.BarcodeCapture.forContext(` (v7 API), and `barcode.data` used without the null guard. No `cordova.plugins.barcodeScanner` call may remain.

## Setup checklist and summary

**Setup checklist:**
1. `cordova plugin remove phonegap-plugin-barcodescanner` (or the fork in use), then `cordova plugin add scandit-cordova-datacapture-core` and `cordova plugin add scandit-cordova-datacapture-barcode`.
2. Run `cordova prepare` after the plugin changes.
3. Add a sized DOM element for the camera preview, for example `<div id="data-capture-view">`, and make it visible to layout.
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key (see **Licence key** in `SKILL.md`).
5. Camera permissions are declared by the Scandit plugins; test the first-run prompt and the denied case on a device, since the old plugin handled both itself.

**Summary:** list what was removed and added, the format → symbology mapping, and every judgment call (scanner now lives in your page instead of a full-screen native screen, Scandit torch and flip buttons replace the plugin's, `prompt` text, `resultDisplayDuration`, `disableAnimations` and `saveHistory` dropped, `orientation` kept in `config.xml`, symbologies not narrowed, no `cancelled` result). Do not list code that was already correct.

## API reference

- BarcodeCapture API: https://docs.scandit.com/data-capture-sdk/cordova/barcode-capture/api.html
- Get Started: https://docs.scandit.com/sdks/cordova/barcode-capture/get-started/
