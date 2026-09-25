# SparkScan Capacitor Integration Guide

SparkScan is a pre-built scanning UI for high-volume single-scanning workflows. It renders as a native overlay on top of the webview — no DOM mount point is needed for the scanning UI itself. Users tap a floating trigger button to scan barcodes without leaving their current screen.

> **Language note**: Examples below use JavaScript. The same API works identically with TypeScript — adapt imports and add type annotations to match the user's project.

## Prerequisites

- Scandit Capacitor packages installed:
  - `scandit-capacitor-datacapture-core`
  - `scandit-capacitor-datacapture-barcode`
- After installing, run `npx cap sync` to sync the native projects.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test
- Camera permissions configured by the app:
  - iOS: `NSCameraUsageDescription` in `Info.plist`
  - Android: handled automatically by the plugin

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which file they'd like to integrate SparkScan into (typically the app entry point, e.g. `app.js`, `main.ts`, or a page module). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Install packages: `npm install scandit-capacitor-datacapture-core scandit-capacitor-datacapture-barcode`
2. Run `npx cap sync` to apply native changes.
3. Add `NSCameraUsageDescription` to `ios/App/App/Info.plist`.
4. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.
5. Store references to `sparkScan` and `sparkScanView` on `window` or at module scope to prevent garbage collection.

## Step 1 — Initialize Plugins and Create DataCaptureContext

Plugin initialization **must** happen before any other Scandit API call. It discovers all installed Scandit Capacitor plugins, fetches native defaults, and wires up the bridge.

```javascript
import {
  DataCaptureContext,
  ScanditCaptureCorePlugin,
} from 'scandit-capacitor-datacapture-core';

// Must be called first — sets up all Scandit plugins
await ScanditCaptureCorePlugin.initializePlugins();

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';
const context = DataCaptureContext.initialize(licenseKey);
```

> **Important**: Always call `ScanditCaptureCorePlugin.initializePlugins()` before `DataCaptureContext.initialize()` or any other Scandit API. Skipping this step causes undefined behavior.

## Step 2 — Configure SparkScanSettings

Choose which barcode symbologies to scan. Only enable what you need — each extra symbology adds processing time.

```javascript
import {
  SparkScanSettings,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

const settings = new SparkScanSettings();

settings.enableSymbologies([
  Symbology.EAN13UPCA,
  Symbology.EAN8,
  Symbology.UPCE,
  Symbology.Code39,
  Symbology.Code128,
  Symbology.InterleavedTwoOfFive,
]);

// Optional: adjust active symbol counts for variable-length symbologies
const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];
```

### SparkScanSettings Properties

| Property | Type | Description |
|----------|------|-------------|
| `codeDuplicateFilter` | `number` | Milliseconds to suppress duplicate scans of the same code. |
| `scanIntention` | `ScanIntention` | Scanning intent mode. Values: `ScanIntention.Smart`, `ScanIntention.Manual`. |
| `batterySaving` | `BatterySavingMode` | Battery optimization level. Values: `BatterySavingMode.Auto`, `BatterySavingMode.On`, `BatterySavingMode.Off`. |
| `locationSelection` | `LocationSelection \| null` | Restrict the scan area. `null` = full frame. |
| `enabledCompositeTypes` | `CompositeType[]` | Composite barcode types. |
| `itemDefinitions` | `ScanItemDefinition[] \| null` | For item-based (USI) scanning. |

### SparkScanSettings Methods

| Method | Description |
|--------|-------------|
| `enableSymbologies(symbologies)` | Enable multiple symbologies. |
| `enableSymbology(symbology, enabled)` | Enable or disable one. |
| `settingsForSymbology(symbology)` | Get per-symbology settings (e.g., `activeSymbolCounts`). |
| `enableSymbologiesForCompositeTypes(compositeTypes)` | Enable symbologies required for composite types. |
| `setProperty(name, value)` / `getProperty(name)` | Advanced property access by name. |

## Step 3 — Create SparkScan Mode and Add a Listener

```javascript
import {
  SparkScan,
  SymbologyDescription,
} from 'scandit-capacitor-datacapture-barcode';

const sparkScan = new SparkScan(settings);

sparkScan.addListener({
  didScan: async (sparkScan, session) => {
    const barcode = session.newlyRecognizedBarcode;
    if (barcode == null) return;

    const symbology = new SymbologyDescription(barcode.symbology);
    console.log(`Scanned: ${barcode.data} (${symbology.readableName})`);
  },
});
```

### SparkScanListener Interface

All callbacks are optional. Implement only what you need.

| Callback | Signature | Description |
|----------|-----------|-------------|
| `didScan` | `(sparkScan, session, getFrameData?) => Promise<void>` | Called when a barcode is scanned. |
| `didUpdateSession` | `(sparkScan, session, getFrameData?) => Promise<void>` | Called on every frame processed. |

### SparkScanSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `newlyRecognizedBarcode` | `Barcode \| null` | The barcode just scanned. |
| `frameSequenceID` | `number` | Frame identifier. |
| `allScannedItems` / `newlyRecognizedItems` | `ScannedItem[]` | For USI / item-based scanning. |
| `reset()` | `Promise<void>` | Clear session state. |

### SparkScan Methods

| Method | Description |
|--------|-------------|
| `addListener(listener)` / `removeListener(listener)` | Register/remove a listener. |
| `applySettings(settings)` | Update settings at runtime. |

## Step 4 — Create SparkScanView

`SparkScanView` is a native overlay that renders the scanning UI (trigger button, viewfinder, toasts) on top of the webview. No DOM element or container is needed.

```javascript
import { SparkScanView } from 'scandit-capacitor-datacapture-barcode';

const sparkScanView = SparkScanView.forContext(context, sparkScan);
```

> The third parameter `SparkScanViewSettings | null` is optional. Pass `null` or omit it for defaults.

## Step 5 — SparkScanView Lifecycle

| Method | Description |
|--------|-------------|
| `prepareScanning()` | Initialize the camera. Called automatically on view creation. |
| `startScanning()` | Begin barcode capture. |
| `pauseScanning()` | Pause (resume with `startScanning()`). |
| `stopScanning()` | Stop and release camera. |
| `show()` / `hide()` | Show/hide the overlay. |
| `dispose()` | Release native resources. **Always call when done.** (Async in v8+.) |
| `showToast(text)` | Display a temporary toast on the overlay. |

## Step 6 — SparkScanView Properties

### Visibility Controls (boolean)

| Property | Description |
|----------|-------------|
| `previewSizeControlVisible` | Preview size toggle (mini vs. full). |
| `scanningBehaviorButtonVisible` | Single-scan / continuous-scan toggle. |
| `barcodeCountButtonVisible` | Barcode Count mode button. |
| `barcodeFindButtonVisible` | Barcode Find mode button. |
| `targetModeButtonVisible` | Target mode button. |
| `labelCaptureButtonVisible` | Label Capture mode button. |
| `cameraSwitchButtonVisible` | Front/back camera switch. |
| `torchControlVisible` | Torch (flashlight) toggle. |
| `zoomSwitchControlVisible` | Zoom level control. |
| `previewCloseControlVisible` | Close button on camera preview. |
| `triggerButtonVisible` | Floating trigger button. |

### Color Properties (`Color | null`)

All colors use `Color.fromHex('#RRGGBB')` from `scandit-capacitor-datacapture-core`.

| Property | Description |
|----------|-------------|
| `toolbarBackgroundColor` | Toolbar background. |
| `toolbarIconActiveTintColor` / `toolbarIconInactiveTintColor` | Toolbar icon tints. |
| `triggerButtonAnimationColor` | Animation ring color. |
| `triggerButtonExpandedColor` / `triggerButtonCollapsedColor` | Trigger button state colors. |
| `triggerButtonTintColor` | Trigger button icon tint. |

### Other Properties

| Property | Type | Description |
|----------|------|-------------|
| `triggerButtonImage` | `string \| null` | Custom image for the trigger button. |
| `SparkScanView.defaultBrush` | `Brush` (static) | Default highlight brush. |

## Step 7 — Custom Feedback

By default SparkScan provides visual and haptic feedback on each scan. To customize feedback per-barcode (e.g., reject invalid codes), set a `feedbackDelegate` on the view.

```javascript
import {
  SparkScanBarcodeSuccessFeedback,
  SparkScanBarcodeErrorFeedback,
} from 'scandit-capacitor-datacapture-barcode';
import { Color, Brush } from 'scandit-capacitor-datacapture-core';

const isValidBarcode = (barcode) => barcode.data != null && barcode.data !== '';

sparkScanView.feedbackDelegate = {
  feedbackForBarcode: (barcode) => {
    if (isValidBarcode(barcode)) {
      return new SparkScanBarcodeSuccessFeedback();
    }
    return new SparkScanBarcodeErrorFeedback(
      'Invalid barcode',                 // message on overlay
      60,                                // resumeCapturingDelay (ms)
      Color.fromHex('#FF0000'),          // visualFeedbackColor
      new Brush(Color.fromHex('#FF0000'), Color.fromHex('#FF0000'), 1),
      null,                              // sound/haptic (null = default)
    );
  },
};
```

### SparkScanFeedbackDelegate Interface

| Callback | Signature | Description |
|----------|-----------|-------------|
| `feedbackForBarcode` | `(barcode) => SparkScanBarcodeFeedback \| null` | Return success/error feedback per scanned barcode. `null` = default. |
| `feedbackForScannedItem` | `(item) => Promise<SparkScanBarcodeFeedback \| null>` | For USI/item-based scanning. |

### SparkScanBarcodeSuccessFeedback

| Constructor / Factory | Description |
|-----------------------|-------------|
| `new SparkScanBarcodeSuccessFeedback()` | Default success visuals. |
| `SparkScanBarcodeSuccessFeedback.fromVisualFeedbackColor(color, brush, feedback)` | Custom color, brush, sound. |

### SparkScanBarcodeErrorFeedback

| Constructor / Factory | Description |
|-----------------------|-------------|
| `new SparkScanBarcodeErrorFeedback(message, resumeCapturingDelay, visualFeedbackColor, brush, feedback)` | Full constructor. |
| `SparkScanBarcodeErrorFeedback.fromMessage(message, resumeCapturingDelay)` | Convenience factory with defaults. |

## Step 8 — SparkScanViewUiListener

Listen for user interactions with the SparkScan overlay buttons:

```javascript
sparkScanView.uiListener = {
  didTapBarcodeCountButton: (view) => { /* navigate to count screen */ },
  didTapBarcodeFindButton: (view) => { /* navigate to find screen */ },
  didTapLabelCaptureButton: (view) => { /* navigate to label screen */ },
  didChangeViewState: (newState) => { /* expanded/collapsed */ },
  didChangeScanningMode: (newScanningMode) => { /* single vs continuous */ },
};
```

All callbacks are optional.

## Step 9 — HTML Setup

SparkScan renders as a native overlay — it does **not** need a DOM container. Your app content (results list, buttons, etc.) renders in the webview **behind** the overlay.

### Minimal HTML

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SparkScan</title>
  <meta name="viewport" content="viewport-fit=cover, width=device-width, initial-scale=1.0,
    minimum-scale=1.0, maximum-scale=1.0, user-scalable=no">
</head>
<body style="margin: 0; padding: 0;">
  <div id="results">
    <div id="list" class="top"></div>
    <div class="bottom">
      <button id="clear-list">CLEAR LIST</button>
    </div>
  </div>
</body>
</html>
```

### Key CSS considerations

Use `env(safe-area-inset-*)` to account for device notches and the home indicator. The SparkScan trigger button floats at the bottom, so position any bottom-anchored UI above the safe-area inset so it doesn't overlap.

```css
html, body { padding: 0; margin: 0; }
body {
  width: 100vw; height: 100vh; overflow: hidden;
  position: absolute; font-family: Arial, Helvetica, sans-serif;
}
#list {
  width: 100vw;
  height: calc(100vh - env(safe-area-inset-top, 20px)
    - calc(env(safe-area-inset-bottom, 0px) + 40px) - 20px - 60px);
  padding-top: env(safe-area-inset-top, 20px);
  overflow: scroll;
}
.bottom {
  position: fixed;
  bottom: calc(env(safe-area-inset-bottom, 0px) + 40px);
  width: 100vw; display: flex; justify-content: center; align-items: center;
}
.result { padding: 10px; border-bottom: 1px solid lightgrey; }
```

## Step 10 — Complete Example

A full working app: scan, validate, display in a list.

### index.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SparkScan List Building</title>
  <meta name="viewport" content="viewport-fit=cover, width=device-width, initial-scale=1.0,
    minimum-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <style>
    html, body { padding: 0; margin: 0; }
    body { width: 100vw; height: 100vh; overflow: hidden;
           position: absolute; font-family: Arial, Helvetica, sans-serif; }
    #results { height: 100vh; width: 100vw; background: #fff; }
    #list { width: 100vw;
            height: calc(100vh - env(safe-area-inset-top, 20px)
              - calc(env(safe-area-inset-bottom, 0px) + 40px) - 20px - 60px);
            padding-top: env(safe-area-inset-top, 20px);
            overflow: scroll; }
    .bottom { position: fixed;
              bottom: calc(env(safe-area-inset-bottom, 0px) + 40px);
              width: 100vw; display: flex; justify-content: center; }
    button { width: 90vw; height: 60px; background: #2EC1CE;
             border: none; color: white; font-size: 1em; font-weight: bold; }
    .result { padding: 10px; border-bottom: 1px solid lightgrey; }
    .result p { margin: 0; }
    .symbology { color: #2EC1CE; font-size: 0.9em; }
  </style>
</head>
<body style="margin: 0; padding: 0;">
  <div id="results">
    <div id="list" class="top"></div>
    <div class="bottom">
      <button id="clear-list">CLEAR LIST</button>
    </div>
  </div>
</body>
</html>
```

### app.js

```javascript
import {
  DataCaptureContext,
  ScanditCaptureCorePlugin,
  Color,
  Brush,
} from 'scandit-capacitor-datacapture-core';

import {
  SparkScan,
  SparkScanSettings,
  SparkScanView,
  Symbology,
  SymbologyDescription,
  SparkScanBarcodeSuccessFeedback,
  SparkScanBarcodeErrorFeedback,
} from 'scandit-capacitor-datacapture-barcode';

async function runApp() {
  let codes = {};

  // 1. Initialize all Scandit plugins — must be called first
  await ScanditCaptureCorePlugin.initializePlugins();

  // 2. Create the data capture context with your license key
  const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  // 3. Configure SparkScan settings
  const sparkScanSettings = new SparkScanSettings();
  sparkScanSettings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.EAN8,
    Symbology.UPCE,
    Symbology.Code39,
    Symbology.Code128,
    Symbology.InterleavedTwoOfFive,
  ]);

  const code39Settings = sparkScanSettings.settingsForSymbology(Symbology.Code39);
  code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];

  // 4. Create SparkScan instance (stored on window to prevent GC)
  window.sparkScan = new SparkScan(sparkScanSettings);

  const isValidBarcode = (barcode) =>
    barcode.data != null && barcode.data !== '123456789';

  // 5. Register a scan listener
  window.sparkScan.addListener({
    didScan: async (_, session) => {
      const barcode = session.newlyRecognizedBarcode;
      if (barcode == null) return;
      if (isValidBarcode(barcode)) {
        codes[barcode.data] = barcode;
        updateResults();
      }
    },
  });

  // 6. Create SparkScanView — native overlay, no DOM element needed
  window.sparkScanView = SparkScanView.forContext(context, window.sparkScan);

  // 7. Set per-barcode feedback
  window.sparkScanView.feedbackDelegate = {
    feedbackForBarcode: (barcode) => {
      if (isValidBarcode(barcode)) {
        return new SparkScanBarcodeSuccessFeedback();
      }
      return new SparkScanBarcodeErrorFeedback(
        'Wrong barcode',
        60,
        Color.fromHex('#FF0000'),
        new Brush(Color.fromHex('#FF0000'), Color.fromHex('#FF0000'), 1),
        null,
      );
    },
  };

  // 8. Wire up the results UI
  const updateResults = () => {
    const list = document.getElementById('list');
    list.innerHTML = Object.values(codes).map((barcode) => {
      const symbology = new SymbologyDescription(barcode.symbology);
      return `<div class="result">
        <p class="barcodeData">${barcode.data}</p>
        <p class="symbology">${symbology.readableName}</p>
      </div>`;
    }).join('');
  };

  document.getElementById('clear-list').addEventListener('click', () => {
    codes = {};
    updateResults();
  });
}

runApp();
```

## Key Rules

1. **Initialize plugins first** — `await ScanditCaptureCorePlugin.initializePlugins()` must be called before any other Scandit API. Capacitor-specific, no equivalent in other frameworks.
2. **Context creation** — `DataCaptureContext.initialize(licenseKey)` is the current (v7+) API. `forLicenseKey()` still exists but is deprecated.
3. **Native overlay** — `SparkScanView` renders on top of the webview. No DOM container for the view itself.
4. **Dispose when done** — Always `await sparkScanView.dispose()` when leaving the scanning screen. In v8+ dispose returns `Promise<void>`.
5. **Imports** — Core types from `scandit-capacitor-datacapture-core`; barcode types from `scandit-capacitor-datacapture-barcode`.
6. **Cap sync** — Run `npx cap sync` after installing or updating Scandit packages.
7. **Feedback delegate goes on the view** — set on `sparkScanView.feedbackDelegate`, not on the SparkScan mode.
8. **Prevent garbage collection** — store `sparkScan` and `sparkScanView` on `window` or at module scope.
9. **Camera permissions** — iOS requires `NSCameraUsageDescription` in `Info.plist`. Android handles it automatically via the plugin.
10. **TypeScript** — Add type annotations and import type interfaces (`SparkScanListener`, `SparkScanFeedbackDelegate`, `Barcode`, `SparkScanSession`) as needed.
