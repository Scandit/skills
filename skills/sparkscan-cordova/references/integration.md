# SparkScan Cordova Integration Guide

## Integration flow

Before writing any code, align with the user:

1. **Which symbologies do they need to scan?** Retail typically uses EAN-13/UPC-A, EAN-8, UPC-E, Code 128, Code 39, ITF. Logistics often adds Data Matrix, QR, PDF417. Only enable what the user asks for — each extra symbology costs processing time.
2. **Which file should SparkScan be wired into?** If the user hasn't told you, ask for the path of the JS/TS file that owns the scanning screen (e.g. `www/js/app.js`, `www/js/scan.js`).
3. **Write the code directly into that file.** Do not dump a giant snippet and tell the user to copy/paste — open the file with the edit tools and make the changes in place. Preserve existing code (DOM wiring, event listeners, state) alongside the new SparkScan integration.
4. **After the code is in place, show a setup checklist** (packages, camera permissions, CSP, iOS/Android prerequisites) so the user can verify the runtime prerequisites.

SparkScan is a pre-built scanning UI for high-volume single-scanning workflows. It renders as a native overlay on top of the webview — no DOM mount point is needed for the scanning UI itself. Users tap a floating trigger button to scan barcodes without leaving their current screen.

## Prerequisites

- **Cordova plugins installed**:
  - `scandit-cordova-datacapture-core`
  - `scandit-cordova-datacapture-barcode`
- Install with:
  ```bash
  cordova plugin add scandit-cordova-datacapture-core
  cordova plugin add scandit-cordova-datacapture-barcode
  ```
- After any plugin change: `cordova prepare` (or re-add the platform) so the native side is re-synced.
- A valid **Scandit license key** (get one at [scandit.com](https://www.scandit.com)).
- **Camera permissions** are configured automatically by the plugins:
  - iOS: `NSCameraUsageDescription` is added to `Info.plist` via `plugin.xml`.
  - Android: `CAMERA` and `VIBRATE` permissions are added to `AndroidManifest.xml`.
- **iOS deployment target**: 15.0 or higher (`<preference name="deployment-target" value="15.0"/>` in `config.xml`).
- **Android minSdkVersion**: 24 or higher.
- **Swift support**: `cordova-plugin-add-swift-support` must be installed for iOS builds.

## Step 1 — Load the SDK and wait for `deviceready`

The Scandit SDK is exposed on the global `window.Scandit` object. Both plugins auto-register at app startup (via Cordova channels in `plugin.xml`). You **must** wait for the `deviceready` event before using any Scandit API — otherwise the native bridge is not available yet.

```javascript
document.addEventListener('deviceready', () => {
  // Safe to call Scandit APIs here
  setupSparkScan();
}, false);
```

If the project is TypeScript, declare the global type in a `global.d.ts` next to your entry file:

```typescript
import type * as ScanditCore from 'scandit-cordova-datacapture-core';
import type * as ScanditBarcode from 'scandit-cordova-datacapture-barcode';

declare global {
  const Scandit: typeof ScanditCore & typeof ScanditBarcode;
}
```

Reference it from your TS file with `/// <reference path="./global.d.ts" />`.

> **Do not** import from `scandit-cordova-datacapture-*` at runtime in a plain-Cordova project — those are plugin manifests, not ES modules, and bundling them in a webview without Webpack/Rollup will fail. Use `Scandit.X` at runtime.

## Step 2 — Create the DataCaptureContext

```javascript
const context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
```

`DataCaptureContext.initialize(key)` is the v8 entry point. It both stores the license and sets up the shared context singleton used by the rest of the SDK. Call this exactly once, after `deviceready`.

## Step 3 — Configure SparkScanSettings

Choose which barcode symbologies to scan. Only enable what the user asked for.

```javascript
const sparkScanSettings = new Scandit.SparkScanSettings();

sparkScanSettings.enableSymbologies([
  Scandit.Symbology.EAN13UPCA,
  Scandit.Symbology.EAN8,
  Scandit.Symbology.UPCE,
  Scandit.Symbology.Code39,
  Scandit.Symbology.Code128,
  Scandit.Symbology.InterleavedTwoOfFive,
]);

// Optional: adjust active symbol counts for variable-length symbologies
const code39Settings = sparkScanSettings.settingsForSymbology(Scandit.Symbology.Code39);
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];
```

### SparkScanSettings properties

| Property | Type | Description |
|----------|------|-------------|
| `codeDuplicateFilter` | `number` | Milliseconds to suppress duplicate scans of the same code. |
| `scanIntention` | `ScanIntention` | Controls scanning intent mode. `Scandit.ScanIntention.Smart` (default), `Scandit.ScanIntention.Manual`. |
| `batterySaving` | `BatterySavingMode` | Battery optimization level. `Scandit.BatterySavingMode.Auto`, `.On`, `.Off`. |
| `locationSelection` | `LocationSelection \| null` | Restrict the scan area. `null` = full-frame. |

### SparkScanSettings methods

| Method | Description |
|--------|-------------|
| `enableSymbologies(symbologies)` | Enable multiple symbologies at once. |
| `enableSymbology(symbology, enabled)` | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | Get per-symbology settings. |
| `setProperty(name, value)` / `getProperty(name)` | Advanced properties by name. |

## Step 4 — Create the SparkScan mode and add a listener

```javascript
const sparkScan = new Scandit.SparkScan(sparkScanSettings);

sparkScan.addListener({
  didScan: async (_sparkScan, session) => {
    const barcode = session.newlyRecognizedBarcode;
    if (!barcode) return;
    const symbology = new Scandit.SymbologyDescription(barcode.symbology);
    console.log(`Scanned: ${barcode.data} (${symbology.readableName})`);
  },
});
```

### SparkScanListener

Both callbacks are optional — implement only what you need.

| Callback | Signature | Description |
|----------|-----------|-------------|
| `didScan` | `(sparkScan, session, getFrameData?) => Promise<void>` | A barcode was successfully scanned. |
| `didUpdateSession` | `(sparkScan, session, getFrameData?) => Promise<void>` | Called every frame, regardless of detection. |

### SparkScanSession

| Property | Type | Description |
|----------|------|-------------|
| `newlyRecognizedBarcode` | `Barcode \| null` | The barcode just scanned, or `null`. |
| `frameSequenceID` | `number` | Frame counter. |
| `reset()` | `Promise<void>` | Clears the session state. |

## Step 5 — Create the SparkScanView

`SparkScanView` is a native overlay. No DOM element or container is needed — it floats above the webview automatically.

```javascript
const sparkScanViewSettings = new Scandit.SparkScanViewSettings();
const sparkScanView = Scandit.SparkScanView.forContext(context, sparkScan, sparkScanViewSettings);
```

The third argument (`SparkScanViewSettings | null`) is optional — pass `null` to use defaults.

## Step 6 — SparkScanView lifecycle

The view manages the camera and scanning lifecycle. Use these methods to control it:

| Method | Description |
|--------|-------------|
| `prepareScanning()` | Initialize the camera and prepare for scanning. |
| `startScanning()` | Begin capture. |
| `pauseScanning()` | Pause (resumable with `startScanning()`). |
| `stopScanning()` | Stop and release camera resources. |
| `show()` / `hide()` | Show/hide the overlay. |
| `dispose()` | Release native resources. **Always call this when done** — returns a `Promise<void>` in v8. |
| `showToast(text)` | Display a temporary toast on the overlay. |

**Typical teardown** when navigating away from the scan screen:

```javascript
const teardownSparkScan = async () => {
  if (context && sparkScan) {
    context.removeMode(sparkScan);
  }
  if (sparkScanView) {
    sparkScanView.hide();
    await sparkScanView.dispose();
    sparkScan = null;
    sparkScanView = null;
  }
};
```

## Step 7 — SparkScanView properties

All properties are get/set. Use them to customize the overlay appearance and controls.

### Visibility controls (boolean)

| Property | Description |
|----------|-------------|
| `previewSizeControlVisible` | Preview size toggle (mini vs. full preview). |
| `scanningBehaviorButtonVisible` | Single-scan / continuous-scan toggle. |
| `barcodeCountButtonVisible` | Barcode Count mode button. |
| `barcodeFindButtonVisible` | Barcode Find mode button. |
| `targetModeButtonVisible` | Target mode button. |
| `labelCaptureButtonVisible` | Label Capture mode button. |
| `cameraSwitchButtonVisible` | Front/back camera switch. |
| `torchControlVisible` | Torch (flashlight) toggle. |
| `zoomSwitchControlVisible` | Zoom level control. |
| `previewCloseControlVisible` | Preview-close button. |
| `triggerButtonVisible` | Floating trigger button. |

### Color properties (`Color | null`)

Use `Scandit.Color.fromHex('#RRGGBB')` or `Scandit.Color.fromHex('#AARRGGBB')`.

| Property | Description |
|----------|-------------|
| `toolbarBackgroundColor` | Toolbar background. |
| `toolbarIconActiveTintColor` / `toolbarIconInactiveTintColor` | Toolbar icon tints. |
| `triggerButtonCollapsedColor` / `triggerButtonExpandedColor` / `triggerButtonAnimationColor` | Trigger-button states. |
| `triggerButtonTintColor` | Trigger-button icon tint. |

### Other properties

| Property | Type | Description |
|----------|------|-------------|
| `triggerButtonImage` | `string \| null` | Custom trigger-button image. |
| `uiListener` | `SparkScanViewUiListener \| null` | Callbacks for user interactions (Step 9). |
| `feedbackDelegate` | `SparkScanFeedbackDelegate \| null` | Custom per-barcode feedback (Step 8). |
| `defaultBrush` (static) | `Brush` | Default highlight brush. `Scandit.SparkScanView.defaultBrush`. |

## Step 8 — Custom feedback

By default SparkScan provides visual + haptic feedback on each scan. To customize feedback per barcode, set `feedbackDelegate`:

```javascript
sparkScanView.feedbackDelegate = {
  feedbackForBarcode: (barcode) => {
    if (isValidBarcode(barcode)) {
      return new Scandit.SparkScanBarcodeSuccessFeedback();
    }
    return new Scandit.SparkScanBarcodeErrorFeedback(
      'Wrong barcode',                        // message
      60,                                     // resumeCapturingDelay (ms)
      Scandit.Color.fromHex('#FF0000'),       // visualFeedbackColor
      new Scandit.Brush(
        Scandit.Color.fromHex('#FF0000'),
        Scandit.Color.fromHex('#FF0000'),
        1,
      ),
      null,                                   // feedback sound (null = default)
    );
  },
};
```

### SparkScanFeedbackDelegate

| Callback | Signature | Description |
|----------|-----------|-------------|
| `feedbackForBarcode` | `(barcode) => SparkScanBarcodeFeedback \| null` | Per-barcode feedback. Return `null` for default. |
| `feedbackForScannedItem` | `(item) => Promise<SparkScanBarcodeFeedback \| null>` | For USI/item-based scanning. |

### SparkScanBarcodeSuccessFeedback

| Constructor / factory | Description |
|-----------------------|-------------|
| `new Scandit.SparkScanBarcodeSuccessFeedback()` | Default success visuals. |
| `Scandit.SparkScanBarcodeSuccessFeedback.fromVisualFeedbackColor(color, brush, feedback)` | Custom color/brush/sound. |

### SparkScanBarcodeErrorFeedback

| Constructor / factory | Description |
|-----------------------|-------------|
| `new Scandit.SparkScanBarcodeErrorFeedback(message, resumeCapturingDelay, visualFeedbackColor, brush, feedback)` | Full constructor. |
| `Scandit.SparkScanBarcodeErrorFeedback.fromMessage(message, resumeCapturingDelay)` | Convenience factory with default visuals. |

## Step 9 — SparkScanViewUiListener

Listen for user interactions with overlay buttons:

```javascript
sparkScanView.uiListener = {
  didTapBarcodeCountButton: (view) => { /* navigate to Barcode Count */ },
  didTapBarcodeFindButton: (view) => { /* navigate to Barcode Find */ },
  didTapLabelCaptureButton: (view) => { /* handle Label Capture */ },
  didChangeViewState: (newState) => { /* expanded/collapsed */ },
  didChangeScanningMode: (newScanningMode) => { /* single vs continuous toggle */ },
};
```

All callbacks are optional.

## Step 10 — HTML setup

SparkScan renders as a native overlay — it does **not** need a DOM container. Your app content (results list, buttons, etc.) renders in the webview **behind** the overlay.

### Content-Security-Policy

Cordova requires a CSP meta tag. Use the standard Cordova CSP:

```html
<meta http-equiv="Content-Security-Policy"
  content="default-src 'self' 'unsafe-inline' data: gap: https://ssl.gstatic.com 'unsafe-eval';
           style-src 'self' 'unsafe-inline';
           media-src *;
           img-src 'self' data: content:;" />
```

### Touch pass-through

The SparkScanView native overlay sits at z-index 0. HTML content sits on top. Use `pointer-events: none` on the scan overlay root and `pointer-events: auto` on interactive areas so touches pass through to the native scanner in empty regions:

```css
.scan-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  pointer-events: none;   /* Allow touches through to native overlay */
  z-index: 1;             /* Above native SparkScanView (z-index 0) */
}

.scan-header, .list-container {
  pointer-events: auto;   /* Re-enable for interactive areas */
}

body {
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
}
```

## Step 11 — Complete example

Full working app, based on the official ListBuildingSample.

### `www/index.html`

```html
<!doctype html>
<html>
  <head>
    <meta http-equiv="Content-Security-Policy"
      content="default-src 'self' 'unsafe-inline' data: gap: https://ssl.gstatic.com 'unsafe-eval';
               style-src 'self' 'unsafe-inline';
               media-src *;
               img-src 'self' data: content:;" />
    <meta name="viewport" content="width=device-width, user-scalable=no, viewport-fit=cover" />
    <title>List Building Sample</title>
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <div id="home-page">
      <div class="content-container"><h1>ListBuilding</h1></div>
      <button class="start-button" id="start-scan-button">Start new scan</button>
    </div>

    <div id="scan-page">
      <div class="scan-overlay">
        <div class="scan-header">
          <button class="back-button" id="back-button">Back</button>
          <span class="header-title">Scan</span>
        </div>
        <div class="list-container">
          <div class="scan-count" id="scan-count">0 items</div>
          <div class="results-list" id="results-list"></div>
          <button class="clear-button" id="clear-button">CLEAR LIST</button>
        </div>
      </div>
    </div>

    <script type="text/javascript" src="cordova.js"></script>
    <script type="text/javascript" src="index.js"></script>
  </body>
</html>
```

### `www/index.js`

```javascript
// @ts-check

const Elements = {
  homePage: document.getElementById('home-page'),
  scanPage: document.getElementById('scan-page'),
  startScanButton: document.getElementById('start-scan-button'),
  backButton: document.getElementById('back-button'),
  scanCount: document.getElementById('scan-count'),
  resultsList: document.getElementById('results-list'),
  clearButton: document.getElementById('clear-button'),
};

let context;
let sparkScan = null;
let sparkScanView = null;
let scannedItems = [];

document.addEventListener('deviceready', () => {
  setupEventListeners();
}, false);

const setupSparkScan = () => {
  if (sparkScan && sparkScanView) return;

  context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const sparkScanSettings = new Scandit.SparkScanSettings();
  sparkScanSettings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.EAN8,
    Scandit.Symbology.UPCE,
    Scandit.Symbology.Code39,
    Scandit.Symbology.Code128,
    Scandit.Symbology.InterleavedTwoOfFive,
  ]);

  const code39Settings = sparkScanSettings.settingsForSymbology(Scandit.Symbology.Code39);
  code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];

  sparkScan = new Scandit.SparkScan(sparkScanSettings);

  sparkScan.addListener({
    didScan: async (_sparkScan, session) => {
      const barcode = session.newlyRecognizedBarcode;
      if (barcode && isValidBarcode(barcode)) {
        const symbologyDescription = new Scandit.SymbologyDescription(barcode.symbology);
        scannedItems.push({ data: barcode.data, symbology: symbologyDescription.readableName });
        updateScanList();
      }
    },
  });

  const sparkScanViewSettings = new Scandit.SparkScanViewSettings();
  sparkScanView = Scandit.SparkScanView.forContext(context, sparkScan, sparkScanViewSettings);

  sparkScanView.feedbackDelegate = {
    feedbackForBarcode: (barcode) => {
      if (isValidBarcode(barcode)) {
        return new Scandit.SparkScanBarcodeSuccessFeedback();
      }
      return new Scandit.SparkScanBarcodeErrorFeedback(
        'Wrong barcode',
        60,
        Scandit.Color.fromHex('#FF0000'),
        new Scandit.Brush(Scandit.Color.fromHex('#FF0000'), Scandit.Color.fromHex('#FF0000'), 1),
        null,
      );
    },
  };
};

const teardownSparkScan = async () => {
  if (context && sparkScan) {
    context.removeMode(sparkScan);
  }
  if (sparkScanView) {
    sparkScanView.hide();
    await sparkScanView.dispose();
    sparkScan = null;
    sparkScanView = null;
  }
};

const isValidBarcode = (barcode) => barcode.data != null && barcode.data !== '123456789';

const setupEventListeners = () => {
  Elements.startScanButton.addEventListener('click', showScanPage);
  Elements.backButton.addEventListener('click', showHomePage);
  Elements.clearButton.addEventListener('click', clearList);
};

const showScanPage = () => {
  setupSparkScan();
  Elements.homePage.classList.add('hidden');
  Elements.scanPage.classList.add('active');
  if (sparkScanView) sparkScanView.show();
};

const showHomePage = async () => {
  await teardownSparkScan();
  Elements.scanPage.classList.remove('active');
  Elements.homePage.classList.remove('hidden');
  clearList();
};

const updateScanList = () => {
  const count = scannedItems.length;
  Elements.scanCount.textContent = `${count} ${count === 1 ? 'item' : 'items'}`;
  Elements.resultsList.innerHTML = '';
  scannedItems.forEach((item) => {
    const resultItem = document.createElement('div');
    resultItem.className = 'result-item';
    resultItem.innerHTML = `
      <div class="result-data">
        <p class="result-barcode">${item.data}</p>
        <p class="result-symbology">${item.symbology}</p>
      </div>`;
    Elements.resultsList.appendChild(resultItem);
  });
  Elements.resultsList.scrollTop = Elements.resultsList.scrollHeight;
};

const clearList = () => {
  scannedItems = [];
  updateScanList();
};
```

## Key rules

1. **Always wait for `deviceready`** before calling any `Scandit.*` API. Never call at module load time.
2. **Use the `Scandit.*` global at runtime** in plain Cordova projects. `scandit-cordova-datacapture-*` are plugin manifests, not runtime modules.
3. **`DataCaptureContext.initialize(key)`** — the v8 entry point. Not `.forLicenseKey()` and not `.sharedInstance`.
4. **`new Scandit.SparkScan(settings)`** — v8 constructor. Not `SparkScan.forSettings()`.
5. **`SparkScanView.forContext(context, sparkScan, settings)`** — `settings` may be `null`. Do not call `new SparkScanView(...)` directly.
6. **SparkScanView is a native overlay** — no DOM container is needed for the scanning UI.
7. **Always `await dispose()`** when tearing down the view. It returns a promise in v8.
8. **`feedbackDelegate` is set on the view**, not on the SparkScan mode.
9. **Run `cordova prepare`** after installing/updating plugins.
10. **Touch pass-through via CSS** is required whenever HTML overlays sit above the scan overlay — use `pointer-events: none` on the overlay root and `pointer-events: auto` on interactive elements.
