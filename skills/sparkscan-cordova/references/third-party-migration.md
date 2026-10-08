# Third-Party Scanner → SparkScan Migration (Cordova)

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm. Replacing the plugin's full-screen scanner with SparkScan's trigger button and mini preview is always one of them.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and replace only the third-party scanner calls underneath with Scandit ones.
- **Preserve, never invent.** Keep the app's own model, list, dedupe, clear and navigation logic. Do not add symbologies, controls or filters the original did not have; do not silently drop a feature (flag it instead).

This guide replaces **`phonegap-plugin-barcodescanner`** (and its forks `cordova-plugin-barcodescanner` and `@red-mobile/cordova-plugin-barcodescanner`, same API: `cordova.plugins.barcodeScanner.scan(success, error, options)`) with Scandit **SparkScan**. For the full SparkScan API read `references/integration.md`; this guide is the delta.

> **Language note**: Examples use plain JavaScript on the global `Scandit.*` namespace, gated on `deviceready`. Do not emit `import` from `scandit-cordova-datacapture-*` in WebView runtime code.

**Shared with `barcode-capture-cordova`.** The `formats` → symbology table and the `result` field mapping are the same for SparkScan. Read them in that skill's `references/third-party-migration.md` (sections **Symbology mapping** and **Result mapping**). If that skill is not installed, fetch it from <https://github.com/Scandit/skills/blob/main/skills/barcode-capture-cordova/references/third-party-migration.md>. The short form for the common formats: `QR_CODE` → `Scandit.Symbology.QR` (never `QRCode`), `EAN_13` and `UPC_A` → `EAN13UPCA`, `CODE_128` → `Code128`, `DATA_MATRIX` → `DataMatrix`.

## Step 1: Decide whether SparkScan fits

Read the existing code first; do not ask the user to describe it. Find every `cordova.plugins.barcodeScanner.scan(success, error, options)` call, its `options` (`formats`, `preferFrontCamera`, `showFlipCameraButton`, `showTorchButton`, `torchOn`, `saveHistory`, `orientation`, `prompt`, `resultDisplayDuration`, `disableSuccessBeep`, `disableAnimations`) and what `success` / `error` do. Then decide:

- **SparkScan fits** a screen that scans one code at a time and either keeps going ("scan, add to a list, keep scanning") or stops once, and whose camera UI is just the preview plus a few buttons (torch, flip camera).
- **Use `barcode-capture-cordova` instead** (its `references/third-party-migration.md`) when the camera view must stay as it is: your own `prompt` text over a full-screen preview, a viewfinder, region-of-interest logic, or a one-shot `scan()` wrapper that must open and close a full-screen scanner. Say so in one line and continue with that skill.
- **Several codes per frame genuinely needed?** Use `matrixscan-batch-cordova`. SparkScan reports one `session.newlyRecognizedBarcode` per callback.

## Step 2: Remove the third-party scanner

- The plugin: `cordova plugin remove phonegap-plugin-barcodescanner` (or the fork in use).
- The `scan(...)` call and its `options` object, and the `result.cancelled` / `result.text` / `result.format` handling.
- `cordova.plugins.barcodeScanner.encode(...)` (QR generation) has no Scandit equivalent: flag it in the summary rather than dropping it silently.
- Keep the app's list, summary, clear and navigation UI.

## Step 3: Map formats to symbologies

Use the `barcode-capture-cordova` **Symbology mapping** table. Map **only** the formats in `options.formats` (a comma-separated string). With no `formats` option, enable what the app really consumes, or its stated default set plus a summary line "symbologies were not narrowed by the original; confirm this list". Symbologies go on `SparkScanSettings`:

```javascript
const settings = new Scandit.SparkScanSettings();
settings.enableSymbologies([Scandit.Symbology.EAN13UPCA, Scandit.Symbology.Code128]);
const sparkScan = new Scandit.SparkScan(settings);
```

`settings.codeDuplicateFilter` is in milliseconds (`-1` = report each code once). Leave it at the default unless the old code throttled repeats; any value you set is a judgment call.

## Step 4: Replace the callback with `SparkScanListener.didScan`

| `scan()` | SparkScan |
|---|---|
| `success(result)` | `sparkScan.addListener({ didScan: async (mode, session) => ... })`, reading `session.newlyRecognizedBarcode` (a single `Barcode \| null`) |
| `result.text` | `barcode.data` (`string \| null`; keep a null guard) |
| `result.format` | `barcode.symbology`; `new Scandit.SymbologyDescription(barcode.symbology).readableName` for display only. If the app stores or compares the old format string (`'QR_CODE'`), keep that contract with a small `Symbology` → old-string lookup. |
| `result.cancelled` | No equivalent: the user closes SparkScan's preview, and nothing is reported. |
| `error(message)` | A rejected `sparkScanView.startScanning()` or `prepareScanning()`; call the old error handler from the `catch`. |

`didScan` returns a `Promise<void>`; declare it `async`. Move the old `success` body in unchanged apart from the field names: dedupe, list state, lookups. Copy `data` and `symbology` out; do not keep `session` outside the callback.

Flow shapes:

- **Scan and continue** (running list, dedupe, clear): nothing else; SparkScan keeps scanning.
- **Scan once** (the old code stopped after one result): keep a `scanned` guard at the top of `didScan` and call `sparkScanView.pauseScanning()` after storing the result; "Scan again" clears the guard and calls `startScanning()`.
- **Scan once, then navigate away:** `pauseScanning()` first, then navigate, so a second callback cannot navigate twice. A promise-returning `scan()` wrapper becomes: resolve in `didScan`, then `pauseScanning()`.

## Step 5: Create the `SparkScanView`

`SparkScanView` is a native overlay on top of the WebView: no DOM element is needed, and the page's own list stays where it is. The working shape for a stock-count screen that keeps scanning, verified against 8.6.1 (keep the app's own list UI):

```javascript
const scannedItems = [];
let context, sparkScan, sparkScanView;

function renderItems() { /* unchanged */ }

function setupSparkScan() {
  context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const settings = new Scandit.SparkScanSettings();
  settings.enableSymbologies([Scandit.Symbology.EAN13UPCA, Scandit.Symbology.Code128]);
  sparkScan = new Scandit.SparkScan(settings);

  sparkScan.addListener({
    didScan: async (_sparkScan, session) => {
      const barcode = session.newlyRecognizedBarcode;
      if (!barcode || barcode.data == null) return;
      const existing = scannedItems.find((item) => item.text === barcode.data);
      if (existing) {
        existing.quantity += 1;
      } else {
        const format = new Scandit.SymbologyDescription(barcode.symbology).readableName;
        scannedItems.push({ text: barcode.data, format, quantity: 1 });
      }
      renderItems();
    },
  });

  sparkScanView = Scandit.SparkScanView.forContext(context, sparkScan, new Scandit.SparkScanViewSettings());
  sparkScanView.torchControlVisible = true;
}

async function teardownSparkScan() {
  await context.removeMode(sparkScan);
  await sparkScanView.hide();
  await sparkScanView.dispose();
  sparkScan = null;
  sparkScanView = null;
}

document.addEventListener('deviceready', setupSparkScan, false);
```

`SparkScanView.forContext(context, sparkScan, settings)` takes the view settings as its third argument (`null` for defaults). Call `setupSparkScan` once and `teardownSparkScan` when the screen goes away. The scan button of the old screen disappears: SparkScan's trigger button starts scanning. List that as a judgment call, and delete the old button and its click handler instead of leaving it dead.

## Step 6: Torch, facing, orientation, feedback

- **Torch** (`showTorchButton: true`) → `sparkScanView.torchControlVisible = true`. SparkScan owns the camera, so there is no `Camera` object to set a torch state on. **Only set it if the original had the button.** `torchOn: true` → `viewSettings.defaultTorchState = Scandit.TorchState.On`.
- **Flip camera** (`showFlipCameraButton: true`) → `sparkScanView.cameraSwitchButtonVisible = true`. **Only if the original had it.**
- **Front camera** (`preferFrontCamera: true`) → `viewSettings.defaultCameraPosition = Scandit.CameraPosition.UserFacing` on the `SparkScanViewSettings` you pass to `forContext`.
- **`orientation`** has no Scandit option; keep it in `config.xml` (`<preference name="Orientation" value="portrait" />`).
- **`prompt`, `resultDisplayDuration`, `disableAnimations`, `saveHistory`** have no equivalent; say they were dropped.
- **`disableSuccessBeep`** → `viewSettings.soundEnabled = false` on the `SparkScanViewSettings` (haptics stay on unless `hapticEnabled = false`). Flag it.
- **Permission.** The Scandit plugins declare the camera permission. The old plugin handled the first-run prompt and the denied case itself, so test both on a device.

## Step 7: Verify

Run `node --check` on the migrated file and confirm every Scandit symbol exists. The usual mistakes: `Scandit.Symbology.QR_CODE` / `QRCode` (it is `QR`), `Scandit.DataCaptureContext.forLicenseKey(` or `Scandit.SparkScan.forContext(` (v7 API), a non-`async` `didScan`, `barcode.data` used without the null guard, `SparkScanView.forContext` called with two arguments. No `cordova.plugins.barcodeScanner` call may remain.

## Step 8: Setup checklist and summary

**Setup checklist:**
1. `cordova plugin remove phonegap-plugin-barcodescanner` (or the fork in use), then `cordova plugin add scandit-cordova-datacapture-core` and `cordova plugin add scandit-cordova-datacapture-barcode`.
2. Run `cordova prepare` after the plugin changes.
3. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key (see **Licence key** in `SKILL.md`).
4. No DOM element is needed for SparkScan; camera permissions are declared by the plugins.

**Summary:** list what was removed and added, the format → symbology mapping, and every judgment call (new scanning UI with trigger button and mini preview, the scan button gone, torch / camera-switch controls moved to the SparkScan toolbar, `prompt`, `resultDisplayDuration`, `disableAnimations` and `saveHistory` dropped, `disableSuccessBeep` mapped to `soundEnabled = false`, `orientation` kept in `config.xml`, duplicate filter, symbologies not narrowed, no `cancelled` result). Do not list code that was already correct.

## API reference

- SparkScan API: https://docs.scandit.com/data-capture-sdk/cordova/barcode-capture/api.html
- Get Started: https://docs.scandit.com/sdks/cordova/sparkscan/get-started/
