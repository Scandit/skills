# BarcodeCapture Capacitor Integration Guide

BarcodeCapture is a single-barcode scanning capture mode. In Capacitor it renders through a `DataCaptureView` connected to a DOM element. A `BarcodeCaptureOverlay` is attached to the view to visualize recognized barcodes (frame, brush, optional viewfinder). A `BarcodeCaptureListener` receives `didScan` callbacks with the newly recognized barcode.

> **Language note**: Examples below use JavaScript (ES modules). The same API works identically with TypeScript — adapt imports and add type annotations to match the user's project.

## Prerequisites

- Scandit Capacitor packages installed:
  - `scandit-capacitor-datacapture-core`
  - `scandit-capacitor-datacapture-barcode`
- After installing, run `npx cap sync` to sync the native projects.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- **Minimum SDK version**: BarcodeCapture on Capacitor: **6.8**. Modern constructors (`new BarcodeCapture(settings)`, `new BarcodeCaptureOverlay(mode)`, `BarcodeCapture.createRecommendedCameraSettings()`) require **7.6+**.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/App/App/Info.plist`.
  - Android: handled automatically by the plugin.
- BarcodeCapture runs on iOS and Android only. Guard with `Capacitor.isNativePlatform()` if your app also targets web.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which file they'd like to integrate BarcodeCapture into (typically the app entry point or a page module, e.g. `www/js/app.js`). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Install packages: `npm install scandit-capacitor-datacapture-core scandit-capacitor-datacapture-barcode`
2. Run `npx cap sync` to apply native changes.
3. Add `NSCameraUsageDescription` to `ios/App/App/Info.plist`. Android camera permission is declared automatically by the Scandit plugin — no manifest edit needed.
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key from https://ssl.scandit.com.
5. Add `<div id="data-capture-view">` to the scanning screen in your HTML and size it to fill the camera area.
6. Store references to `barcodeCapture`, `view`, `camera`, and the overlay on `window` or at module scope to prevent garbage collection.

## Step 1 — Initialize Plugins and Create DataCaptureContext

Plugin initialization **must** happen before any other Scandit API call. It discovers all installed Scandit Capacitor plugins, fetches native defaults, and wires up the bridge.

```javascript
import {
  DataCaptureContext,
  ScanditCaptureCorePlugin,
} from 'scandit-capacitor-datacapture-core';

// Must be called first — sets up all Scandit plugins.
await ScanditCaptureCorePlugin.initializePlugins();

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';
const context = DataCaptureContext.initialize(licenseKey);
```

> **Important**: Always call `ScanditCaptureCorePlugin.initializePlugins()` before `DataCaptureContext.initialize()` or any other Scandit API. Skipping this step causes undefined behavior.

## Step 2 — Configure BarcodeCaptureSettings

Choose which barcode symbologies to scan. Only enable what you need — each extra symbology adds processing time.

```javascript
import {
  BarcodeCaptureSettings,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

const settings = new BarcodeCaptureSettings();

settings.enableSymbologies([
  Symbology.EAN13UPCA,
  Symbology.EAN8,
  Symbology.UPCE,
  Symbology.Code39,
  Symbology.Code128,
  Symbology.InterleavedTwoOfFive,
]);

// Optional: adjust active symbol counts for variable-length symbologies.
const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];
```

### BarcodeCaptureSettings Key Members

| Member | Available | Description |
|--------|-----------|-------------|
| `new BarcodeCaptureSettings()` | capacitor=6.8 | All symbologies disabled by default. |
| `enableSymbologies(symbologies)` | capacitor=6.8 | Enable multiple symbologies at once. |
| `enableSymbology(symbology, enabled)` | capacitor=6.8 | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | capacitor=6.8 | Get per-symbology settings (e.g. `activeSymbolCounts`). |
| `enabledSymbologies` | capacitor=6.8 | Read-only array of currently enabled symbologies. |
| `enableSymbologiesForCompositeTypes(compositeTypes)` | capacitor=6.8 | Enable symbologies needed for composite codes. |
| `enabledCompositeTypes` | capacitor=6.8 | The enabled `CompositeType[]`. |
| `codeDuplicateFilter` | capacitor=6.8 | `number` (ms) — duplicate suppression interval. |
| `locationSelection` | capacitor=6.8 | `LocationSelection \| null` — restrict the scan area. |
| `scanIntention` | capacitor=6.24 | `ScanIntention.Smart \| ScanIntention.Manual`. |
| `batterySaving` | capacitor=6.26 | `BatterySavingMode.Auto \| .On \| .Off`. |
| `setProperty(name, value)` / `getProperty(name)` | capacitor=6.8 | Advanced property access by name. |

## Step 3 — Set Up the Camera

```javascript
import {
  Camera,
  FrameSourceState,
} from 'scandit-capacitor-datacapture-core';

import { BarcodeCapture } from 'scandit-capacitor-datacapture-barcode';

// Recommended camera settings for BarcodeCapture (SDK ≥7.6).
const cameraSettings = BarcodeCapture.createRecommendedCameraSettings();
window.camera = Camera.withSettings(cameraSettings);
context.setFrameSource(window.camera);
```

> **SDK <7.6 fallback**: `BarcodeCapture.createRecommendedCameraSettings()` is available from capacitor=7.6. On older SDKs, use `Camera.default` or construct `CameraSettings` manually.

## Step 4 — Construct BarcodeCapture

```javascript
import {
  BarcodeCapture,
} from 'scandit-capacitor-datacapture-barcode';

// SDK ≥7.6 constructor — no context argument.
window.barcodeCapture = new BarcodeCapture(settings);

// Register the mode with the context.
context.setMode(window.barcodeCapture);
```

> **SDK <7.6 fallback**: If targeting earlier SDK versions, use `BarcodeCapture.forContext(context, settings)` which both constructs the mode and adds it to the context.

### BarcodeCapture Key Members

| Member | Available | Description |
|--------|-----------|-------------|
| `new BarcodeCapture(settings)` | capacitor=7.6 | Constructs a new instance. |
| `BarcodeCapture.forContext(context, settings)` | capacitor=6.8 | Legacy factory; constructs and adds the mode to the context. Deprecated in v8. |
| `BarcodeCapture.createRecommendedCameraSettings()` | capacitor=7.6 | Returns camera settings optimized for BarcodeCapture. |
| `addListener(listener)` / `removeListener(listener)` | capacitor=6.8 | Register/remove a `BarcodeCaptureListener`. |
| `applySettings(settings)` | capacitor=6.8 | Update settings at runtime (returns `Promise<void>`). |
| `isEnabled` | capacitor=6.8 | `boolean` — pause/resume scanning without removing the mode. |
| `feedback` | capacitor=6.8 | The `BarcodeCaptureFeedback` instance for success sounds/vibration. |
| `context` | capacitor=6.8 | Read-only reference to the associated `DataCaptureContext`. |

## Step 5 — Mount DataCaptureView and Add the Overlay

`DataCaptureView.forContext(context)` creates the view. Then attach it to a DOM element with `connectToElement`. Add a `BarcodeCaptureOverlay` so that recognized barcodes are visualized.

```javascript
import { DataCaptureView } from 'scandit-capacitor-datacapture-core';
import { BarcodeCaptureOverlay } from 'scandit-capacitor-datacapture-barcode';

// Create the view for the context.
window.view = DataCaptureView.forContext(context);

// Connect to a DOM element — the view mirrors its size and position.
window.view.connectToElement(document.getElementById('data-capture-view'));

// Create the overlay and add it to the view.
// SDK ≥7.6: `new BarcodeCaptureOverlay(mode)` then `view.addOverlay(overlay)`.
window.overlay = new BarcodeCaptureOverlay(window.barcodeCapture);
window.view.addOverlay(window.overlay);
```

> **SDK <7.6 fallback**: Use the static factory `BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view)` which both constructs the overlay and adds it to the view.

The HTML must contain a container element, sized to fill the camera area:

```html
<div id="data-capture-view" style="width: 100%; height: 100%;"></div>
```

### BarcodeCaptureOverlay Key Members

| Member | Available | Description |
|--------|-----------|-------------|
| `new BarcodeCaptureOverlay(mode)` | capacitor=7.6 | Constructs the overlay. Add it to a view via `view.addOverlay`. |
| `BarcodeCaptureOverlay.withBarcodeCaptureForView(mode, view)` | capacitor=6.8 | Legacy factory; constructs and adds the overlay to the view. |
| `brush` | capacitor=6.8 | `Brush` — visual style for recognized barcodes. Set to a fully transparent brush to hide the highlight. |
| `viewfinder` | capacitor=6.8 | `IViewfinder \| null` — optional viewfinder (e.g. `RectangularViewfinder`, `LaserlineViewfinder`). Default `null`. |
| `shouldShowScanAreaGuides` | capacitor=6.8 | Debug: show the active scan area. Default `false`. |

## Step 6 — Implement BarcodeCaptureListener

```javascript
import { SymbologyDescription } from 'scandit-capacitor-datacapture-barcode';

window.barcodeCapture.addListener({
  didScan: async (barcodeCapture, session, getFrameData) => {
    const barcode = session.newlyRecognizedBarcode;
    if (barcode == null) return;

    // Disable the mode while you handle the scan — the callback blocks
    // further frame processing on Capacitor until it returns.
    barcodeCapture.isEnabled = false;

    const symbology = new SymbologyDescription(barcode.symbology);
    console.log(`Scanned: ${barcode.data} (${symbology.readableName})`);

    // ... do your work (navigation, lookup, store result) ...

    // Re-enable when you are ready to scan again.
    barcodeCapture.isEnabled = true;
  },

  didUpdateSession: async (barcodeCapture, session, getFrameData) => {
    // Called on every frame, regardless of whether a barcode was recognized.
    // Keep the body short — it blocks further frame processing.
  },
});
```

### BarcodeCaptureListener Callbacks

All callbacks are optional. Implement only what you need.

| Callback | Signature | Description |
|----------|-----------|-------------|
| `didScan` | `(barcodeCapture, session, getFrameData) => Promise<void>` | Invoked when a barcode is recognized. The newly scanned barcode is at `session.newlyRecognizedBarcode`. |
| `didUpdateSession` | `(barcodeCapture, session, getFrameData) => Promise<void>` | Invoked after every processed frame, regardless of recognition. |

> **Capacitor-specific behavior**: Both callbacks block further frame processing until they return. Keep them short. If you need to do meaningful work after a scan, set `barcodeCapture.isEnabled = false` first, perform the work, and re-enable when ready.

### BarcodeCaptureSession Properties

| Property | Type | Available | Description |
|----------|------|-----------|-------------|
| `newlyRecognizedBarcode` | `Barcode \| null` | capacitor=6.26 | The barcode just recognized in the last processed frame. |
| `newlyLocalizedBarcodes` | `LocalizedOnlyBarcode[]` | capacitor=6.8 | Codes localized but not recognized in the last frame. |
| `frameSequenceID` | `number` | capacitor=6.8 | Identifier of the current frame sequence. |
| `reset()` | `Promise<void>` | capacitor=6.12 | Clears the session's duplicate-filter history. Call only inside the listener. |

> **Important**: Do not hold references to `session` or its arrays outside the listener callbacks — they may be concurrently modified. Copy any data you need before the callback returns.

## Step 7 — Lifecycle: Start, Pause, Resume, and Cleanup

### Start scanning

```javascript
// Switch the camera on to start streaming frames.
await window.camera.switchToDesiredState(FrameSourceState.On);

// The mode is enabled by default; this line is a no-op unless you disabled it.
window.barcodeCapture.isEnabled = true;
```

### Pause / resume

```javascript
// Pause scanning (e.g. user navigates away from the scanning screen).
window.barcodeCapture.isEnabled = false;
await window.camera.switchToDesiredState(FrameSourceState.Off);

// Resume.
window.barcodeCapture.isEnabled = true;
await window.camera.switchToDesiredState(FrameSourceState.On);
```

### Stop scanning correctly

To stop completely, both disable the mode and stop the frame source — disabling only the camera while keeping the mode enabled may produce additional scan events:

```javascript
// No more didScan callbacks will be invoked after this call.
window.barcodeCapture.isEnabled = false;
// Asynchronously turn off the camera.
window.barcodeCapture.context.frameSource.switchToDesiredState(FrameSourceState.Off);
```

### Handle Capacitor app lifecycle events

```javascript
import { App } from '@capacitor/app';

App.addListener('appStateChange', async ({ isActive }) => {
  if (!isActive) {
    window.barcodeCapture.isEnabled = false;
    await window.camera.switchToDesiredState(FrameSourceState.Off);
  } else {
    window.barcodeCapture.isEnabled = true;
    await window.camera.switchToDesiredState(FrameSourceState.On);
  }
});
```

### Full teardown

```javascript
async function uninitialize() {
  if (window.camera) {
    await window.camera.switchToDesiredState(FrameSourceState.Off);
    window.camera = null;
  }
  if (window.barcodeCapture) {
    window.barcodeCapture.isEnabled = false;
    window.barcodeCapture = null;
  }
  if (window.view) {
    window.view.detachFromElement();
    window.view = null;
  }
}
```

## Step 8 — Camera Permissions

### iOS

Add to `ios/App/App/Info.plist`:

```xml
<key>NSCameraUsageDescription</key>
<string>We need camera access to scan barcodes</string>
```

### Android

The camera permission (`android.permission.CAMERA`) is declared automatically by the Scandit plugin in its manifest. The runtime permission request is handled by the operating system when the camera is first activated.

## Optional — Custom Feedback

The default `BarcodeCaptureFeedback` plays a beep and vibrates on a successful scan. To customize:

```javascript
import {
  BarcodeCaptureFeedback,
} from 'scandit-capacitor-datacapture-barcode';
import {
  Feedback,
  Sound,
  Vibration,
} from 'scandit-capacitor-datacapture-core';

const feedback = BarcodeCaptureFeedback.defaultFeedback;
// Vibration only, no sound.
feedback.success = new Feedback(Vibration.defaultVibration, null);
window.barcodeCapture.feedback = feedback;
```

## Optional — Viewfinders

Attach a viewfinder to the overlay to show users where to aim. Set `overlay.viewfinder` to one of the viewfinder types below (or `null` for no viewfinder).

### RectangularViewfinder

```javascript
import { RectangularViewfinder, RectangularViewfinderStyle, RectangularViewfinderLineStyle } from 'scandit-capacitor-datacapture-core';

window.overlay.viewfinder = new RectangularViewfinder(
  RectangularViewfinderStyle.Square,
  RectangularViewfinderLineStyle.Light,
);
```

### AimerViewfinder

An aimer viewfinder draws a frame plus a central dot. It is the recommended viewfinder when pairing with a `RadiusLocationSelection`. Construct it with no arguments and assign it to the overlay; tune the optional `frameColor` / `dotColor` properties if needed.

```javascript
import { AimerViewfinder } from 'scandit-capacitor-datacapture-core';

window.overlay.viewfinder = new AimerViewfinder();
```

`AimerViewfinder` is available from capacitor=6.8.

### LaserlineViewfinder

A horizontal laser line with a Scandit logo underneath. The line toggles color depending on whether the capture mode is enabled. Construct it with no arguments and assign it to the overlay.

```javascript
import { LaserlineViewfinder } from 'scandit-capacitor-datacapture-core';

window.overlay.viewfinder = new LaserlineViewfinder();
```

`LaserlineViewfinder` is available from capacitor=7.4. Optional properties: `width` (`FloatWithUnit`), `enabledColor` (`Color`), `disabledColor` (`Color`).

## Optional — Location Selection

Restrict where in the frame barcodes are accepted:

```javascript
import {
  RadiusLocationSelection,
  NumberWithUnit,
  MeasureUnit,
} from 'scandit-capacitor-datacapture-core';

settings.locationSelection = new RadiusLocationSelection(
  new NumberWithUnit(0.1, MeasureUnit.Fraction),
);
```

`RectangularLocationSelection.withSize(...)` is also available.

## Optional — Scan Intention

Smart scan intention is the default on Capacitor (from 7.0). To opt out:

```javascript
import { ScanIntention } from 'scandit-capacitor-datacapture-core';

settings.scanIntention = ScanIntention.Manual;
```

## Optional — Code Duplicate Filter

Suppress duplicate scans of the same data within a time window:

```javascript
// Suppress duplicates within 500 ms.
settings.codeDuplicateFilter = 500;
```

Set to `0` to report every detection, or `-1` to never report the same code twice until scanning is stopped. The filter is reset whenever the mode is disabled.

## Optional — Composite Codes

Composite codes pair a 1D barcode with a 2D component (e.g. GS1 DataBar + MicroPDF417). Enable them in two steps — the symbologies that make up the composite, plus the composite types themselves:

```javascript
import { CompositeType } from 'scandit-capacitor-datacapture-barcode';

settings.enableSymbologiesForCompositeTypes([
  CompositeType.A,
  CompositeType.B,
]);
settings.enabledCompositeTypes = [CompositeType.A, CompositeType.B];
```

## Optional — Overlay Brush (highlight color)

The `BarcodeCaptureOverlay.brush` controls how recognized barcodes are highlighted in the view. Assign a `Brush` built from a fill `Color`, a stroke `Color`, and a stroke width. Use `Color.fromHex(...)` to build colors from a hex string.

```javascript
import { Brush, Color } from 'scandit-capacitor-datacapture-core';

// Semi-transparent green fill with a solid green 2px stroke.
window.overlay.brush = new Brush(
  Color.fromHex('#8800FF00'),
  Color.fromHex('#00FF00'),
  2,
);
```

To hide the highlight entirely, assign a fully transparent brush:

```javascript
import { Brush } from 'scandit-capacitor-datacapture-core';

window.overlay.brush = Brush.transparent;
```

## Optional — Rejecting Barcodes (reject pattern)

To accept some scanned codes but reject others (e.g. codes that do not match an expected prefix), inspect the barcode inside `didScan`. When a code should be rejected, set the overlay brush to a transparent brush so it is not highlighted, and `return` early without acting on it. Accepted codes are processed normally.

```javascript
import { Brush } from 'scandit-capacitor-datacapture-core';

window.barcodeCapture.addListener({
  didScan: async (barcodeCapture, session) => {
    const barcode = session.newlyRecognizedBarcode;
    if (barcode == null) return;

    // Reject anything that does not start with the expected prefix.
    if (!barcode.data?.startsWith('ABC')) {
      window.overlay.brush = Brush.transparent;
      return;
    }

    // Accept: highlight with the default brush and handle the scan.
    barcodeCapture.isEnabled = false;
    // ... handle accepted barcode ...
    barcodeCapture.isEnabled = true;
  },
});
```

## Optional — Symbology Extensions

Some symbologies expose extensions that toggle symbology-specific behavior (for example, decoding the full ASCII character set for Code 39). Get the per-symbology settings with `settingsForSymbology` and call `setExtensionEnabled(extension, enabled)`. Apply the change to the `BarcodeCaptureSettings` before constructing the mode.

```javascript
const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.setExtensionEnabled('full_ascii', true);
```

`setExtensionEnabled` is available from capacitor=6.8. Extension names are strings (e.g. `'full_ascii'`, `'relaxed_sharp_quiet_zone_check'`); see the Symbology Properties reference for the list per symbology.

## Optional — Symbology Checksums

Set optional checksum algorithms for a symbology via the per-symbology `checksums` property. For example, Code 39 supports the Mod 43 checksum:

```javascript
import { Checksum } from 'scandit-capacitor-datacapture-barcode';

const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.checksums = [Checksum.Mod43];
```

`Checksum` is available from capacitor=6.8. Other values include `Checksum.Mod10`, `Checksum.Mod11`, `Checksum.Mod16`, `Checksum.Mod47`, `Checksum.Mod103`. The code is accepted if any of the listed checksums matches.

## Optional — Active Symbol Counts

Variable-length symbologies (Code 39, Code 128, Interleaved 2 of 5, etc.) accept a range of symbol counts. Narrowing the range improves accuracy when you know the expected length. Set the per-symbology `activeSymbolCounts` to an array of integers:

```javascript
const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];
```

`activeSymbolCounts` is available from capacitor=6.8.

## Optional — Color-Inverted Codes

By default a symbology only decodes dark codes on a bright background. To also decode color-inverted (bright code on a dark background) codes, set the per-symbology `isColorInvertedEnabled` to `true`:

```javascript
const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.isColorInvertedEnabled = true;
```

`isColorInvertedEnabled` is available from capacitor=6.8.

## Complete Example

A full working app: scan, log, render the barcode in a list.

### index.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>BarcodeCapture</title>
  <meta name="viewport" content="viewport-fit=cover, width=device-width, initial-scale=1.0,
    minimum-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <style>
    html, body { margin: 0; padding: 0; width: 100%; height: 100%; }
    #data-capture-view { width: 100vw; height: 60vh; }
    #list { width: 100vw; height: 40vh; overflow: scroll; padding: 10px; box-sizing: border-box; }
    .result { padding: 8px; border-bottom: 1px solid lightgrey; }
    .symbology { color: #2EC1CE; font-size: 0.9em; }
  </style>
</head>
<body>
  <div id="data-capture-view"></div>
  <div id="list"></div>
</body>
</html>
```

### app.js

```javascript
import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
  ScanditCaptureCorePlugin,
} from 'scandit-capacitor-datacapture-core';

import {
  BarcodeCapture,
  BarcodeCaptureOverlay,
  BarcodeCaptureSettings,
  Symbology,
  SymbologyDescription,
} from 'scandit-capacitor-datacapture-barcode';

async function runApp() {
  // 1. Initialize plugins — must be first.
  await ScanditCaptureCorePlugin.initializePlugins();

  // 2. Create the data capture context with your license key.
  const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  // 3. Set up the camera.
  const cameraSettings = BarcodeCapture.createRecommendedCameraSettings();
  window.camera = Camera.withSettings(cameraSettings);
  context.setFrameSource(window.camera);

  // 4. Configure BarcodeCaptureSettings.
  const settings = new BarcodeCaptureSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.EAN8,
    Symbology.UPCE,
    Symbology.Code39,
    Symbology.Code128,
    Symbology.InterleavedTwoOfFive,
  ]);

  // 5. Construct the BarcodeCapture mode and register it with the context.
  window.barcodeCapture = new BarcodeCapture(settings);
  context.setMode(window.barcodeCapture);

  // 6. Register a scan listener.
  window.barcodeCapture.addListener({
    didScan: async (barcodeCapture, session) => {
      const barcode = session.newlyRecognizedBarcode;
      if (barcode == null) return;

      // Disable while we update the UI — the callback blocks frame processing.
      barcodeCapture.isEnabled = false;

      const symbology = new SymbologyDescription(barcode.symbology);
      const list = document.getElementById('list');
      const entry = document.createElement('div');
      entry.className = 'result';
      entry.innerHTML = `<p>${barcode.data}</p><p class="symbology">${symbology.readableName}</p>`;
      list.appendChild(entry);

      barcodeCapture.isEnabled = true;
    },
  });

  // 7. Mount the DataCaptureView and add the overlay.
  window.view = DataCaptureView.forContext(context);
  window.view.connectToElement(document.getElementById('data-capture-view'));
  window.overlay = new BarcodeCaptureOverlay(window.barcodeCapture);
  window.view.addOverlay(window.overlay);

  // 8. Start the camera.
  await window.camera.switchToDesiredState(FrameSourceState.On);
}

document.addEventListener('DOMContentLoaded', () => {
  runApp();
});
```

## Key Rules

1. **Initialize plugins first** — `await ScanditCaptureCorePlugin.initializePlugins()` must be called before any other Scandit API. Capacitor-specific, no equivalent in other frameworks.
2. **Context creation** — `DataCaptureContext.initialize(licenseKey)` is the current (v8) API. `forLicenseKey()` still exists but is deprecated.
3. **Mode registration** — `context.setMode(barcodeCapture)` registers the mode with the context. Replaces any previously active mode.
4. **View + overlay wiring** — `DataCaptureView.forContext(context)` creates the view, `view.connectToElement(domEl)` attaches it, and `view.addOverlay(new BarcodeCaptureOverlay(barcodeCapture))` makes recognized barcodes visible.
5. **Camera is separate** — Use `Camera.withSettings(BarcodeCapture.createRecommendedCameraSettings())` (≥7.6) or `Camera.default`, then `context.setFrameSource(camera)` and `camera.switchToDesiredState(FrameSourceState.On)`.
6. **Disable the mode in `didScan`** — On Capacitor the callback blocks further frame processing. Set `barcodeCapture.isEnabled = false` before doing any meaningful work, then re-enable.
7. **Imports** — Core types from `scandit-capacitor-datacapture-core`; barcode types from `scandit-capacitor-datacapture-barcode`.
8. **Cap sync** — Run `npx cap sync` after installing or updating Scandit packages.
9. **Prevent garbage collection** — Store `barcodeCapture`, `view`, `camera`, and the overlay on `window` or at module scope.
10. **Camera permissions** — iOS requires `NSCameraUsageDescription` in `Info.plist`. Android handles it automatically via the plugin.
11. **Session data safety** — Do not hold references to the session or its arrays outside the listener callbacks. Copy any data you need.
12. **Teardown** — Call `view.detachFromElement()` and switch the camera off when leaving the scanning screen.

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Nothing scans when the page loads | `ScanditCaptureCorePlugin.initializePlugins()` was not called or not awaited before other Scandit calls. |
| Camera not streaming | `camera.switchToDesiredState(FrameSourceState.On)` was not called, or `context.setFrameSource(camera)` was skipped. |
| No barcode highlights visible | `BarcodeCaptureOverlay` was not created, or `view.addOverlay(overlay)` was not called. |
| Repeated scans of the same code without disabling the mode | The mode keeps firing because `didScan` does not stop frame processing — set `barcodeCapture.isEnabled = false` before doing your work. |
| `new BarcodeCapture(settings)` not found | Requires capacitor=7.6. Use `BarcodeCapture.forContext(context, settings)` on older SDKs. |
| `BarcodeCapture.createRecommendedCameraSettings()` not found | Requires capacitor=7.6. Use `Camera.default` on older SDKs. |
| Native/web version mismatch at runtime | Run `npx cap sync` after installing or updating packages. |
| App tries to scan in the web build | Guard initialization with `Capacitor.isNativePlatform()`. |
