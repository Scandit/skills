# BarcodeCapture Cordova Integration Guide

## Integration flow

Before writing any code, align with the user:

1. **Which symbologies do they need to scan?** Retail typically uses EAN-13/UPC-A, EAN-8, UPC-E, Code 128, Code 39, ITF. Logistics often adds Data Matrix, QR, PDF417. Only enable what the user asks for — each extra symbology costs processing time.
2. **Which file should BarcodeCapture be wired into?** If the user hasn't told you, ask for the path of the JS/TS file that owns the scanning screen (e.g. `www/js/app.js`, `www/index.js`). Also confirm the HTML element id that should host the camera preview (e.g. `<div id="data-capture-view">`).
3. **Write the code directly into that file.** Do not dump a giant snippet and tell the user to copy/paste — open the file with the edit tools and make the changes in place. Preserve existing code (DOM wiring, event listeners, state) alongside the new BarcodeCapture integration.
4. **After the code is in place, show a setup checklist** (packages, camera permissions, CSP, iOS/Android prerequisites) so the user can verify the runtime prerequisites.

BarcodeCapture is a single-barcode capture mode that renders the camera preview into a `DataCaptureView` mounted in your HTML. A `BarcodeCaptureOverlay` is added on top of the view to highlight recognized codes. Unlike SparkScan, there is no pre-built UI — the host page is responsible for layout, lifecycle, and result display.

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
  setupBarcodeCapture();
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

## Step 3 — Configure BarcodeCaptureSettings

Choose which barcode symbologies to scan. Only enable what the user asked for.

```javascript
const settings = new Scandit.BarcodeCaptureSettings();

settings.enableSymbologies([
  Scandit.Symbology.EAN13UPCA,
  Scandit.Symbology.EAN8,
  Scandit.Symbology.UPCE,
  Scandit.Symbology.Code39,
  Scandit.Symbology.Code128,
  Scandit.Symbology.InterleavedTwoOfFive,
]);

// Optional: adjust active symbol counts for variable-length symbologies
const code39Settings = settings.settingsForSymbology(Scandit.Symbology.Code39);
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];
```

### BarcodeCaptureSettings properties

| Property | Type | Description |
|----------|------|-------------|
| `codeDuplicateFilter` | `number` | Milliseconds between accepted scans of the same code. `0` = report every detection, `-1` = report each code only once until scanning stops, `-2` = Smart duplicate filtering (default in 7.1+). |
| `scanIntention` | `ScanIntention` | Scanning intent algorithm. `Scandit.ScanIntention.Smart` (default), `Scandit.ScanIntention.Manual`. |
| `batterySaving` | `BatterySavingMode` | Battery optimization. `Scandit.BatterySavingMode.Auto` (default), `.On`, `.Off`. |
| `locationSelection` | `LocationSelection \| null` | Restrict the scan area. `null` = full-frame. |
| `enabledCompositeTypes` | `CompositeType[]` | Composite codes to enable (GS1 Composite A/B/C). |

### BarcodeCaptureSettings methods

| Method | Description |
|--------|-------------|
| `enableSymbologies(symbologies)` | Enable multiple symbologies at once. |
| `enableSymbology(symbology, enabled)` | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | Get per-symbology settings. |
| `enableSymbologiesForCompositeTypes(compositeTypes)` | Enable all symbologies needed for the given composite types. |
| `setProperty(name, value)` / `getProperty(name)` | Advanced properties by name. |

## Step 4 — Configure the camera

```javascript
const cameraSettings = Scandit.BarcodeCapture.recommendedCameraSettings;
const camera = Scandit.Camera.default;
camera.applySettings(cameraSettings);
context.setFrameSource(camera);
```

`Scandit.BarcodeCapture.recommendedCameraSettings` returns the camera settings tuned for barcode capture. `context.setFrameSource(camera)` binds the camera to the context — frames will start flowing once the camera is switched on (Step 8).

## Step 5 — Create the BarcodeCapture mode

```javascript
const barcodeCapture = new Scandit.BarcodeCapture(settings);
context.setMode(barcodeCapture);
```

`new Scandit.BarcodeCapture(settings)` is the v8 constructor. After construction, register the mode with the context via `context.setMode(barcodeCapture)`. (In v7 you would have called `Scandit.BarcodeCapture.forContext(context, settings)`; see `references/migration.md`.)

## Step 6 — Create the DataCaptureView and BarcodeCaptureOverlay

`DataCaptureView` renders the camera preview. It mounts into an HTML element you provide. `BarcodeCaptureOverlay` draws recognized barcodes on top of the view.

```javascript
const view = Scandit.DataCaptureView.forContext(context);
view.connectToElement(document.getElementById('data-capture-view'));

const overlay = new Scandit.BarcodeCaptureOverlay(barcodeCapture);
overlay.viewfinder = new Scandit.RectangularViewfinder(
  Scandit.RectangularViewfinderStyle.Square,
  Scandit.RectangularViewfinderLineStyle.Light,
);
view.addOverlay(overlay);
```

The HTML side needs a sized container:

```html
<div id="data-capture-view" style="width: 100vw; height: 100vh; z-index: -1;"></div>
```

The `z-index: -1` lets HTML controls on the page sit above the camera preview. Adjust the size and stacking to match your layout.

## Step 7 — Add a BarcodeCaptureListener

Listeners are JS object literals — implement only the callbacks you need.

```javascript
barcodeCapture.addListener({
  didScan: (barcodeCapture, session, _getFrameData) => {
    const barcode = session.newlyRecognizedBarcode;
    if (!barcode) return;

    // Disable the mode while you process the result. The listener blocks
    // further frame processing — keep it short, or pause scanning.
    barcodeCapture.isEnabled = false;

    const symbology = new Scandit.SymbologyDescription(barcode.symbology);
    showResult(`Scanned: ${barcode.data} (${symbology.readableName})`);
  },
});
```

### BarcodeCaptureListener

Both callbacks are optional.

| Callback | Signature | Description |
|----------|-----------|-------------|
| `didScan` | `(barcodeCapture, session, getFrameData) => Promise<void>` | A barcode was successfully scanned. |
| `didUpdateSession` | `(barcodeCapture, session, getFrameData) => Promise<void>` | Called every frame, regardless of detection. |

### BarcodeCaptureSession

| Member | Type | Description |
|--------|------|-------------|
| `newlyRecognizedBarcode` | `Barcode \| null` | The barcode just scanned, or `null`. |
| `newlyLocalizedBarcodes` | `LocalizedOnlyBarcode[]` | Codes localized but not decoded in the current frame. |
| `frameSequenceID` | `number` | Frame counter. |
| `reset()` | `Promise<void>` | Clears the session state (call only inside the listener callbacks). |

> **Important:** the `session` reference is only valid inside the listener callback. Do not store it or read its arrays outside the callback — they may be modified concurrently.

## Step 8 — Camera lifecycle (turn on / pause / resume / off)

The camera is **off** by default. Switch it on once the listener is wired:

```javascript
camera.switchToDesiredState(Scandit.FrameSourceState.On);
barcodeCapture.isEnabled = true;
```

To **pause** scanning while keeping the camera running (cheap, instant resume):

```javascript
barcodeCapture.isEnabled = false;
// later:
barcodeCapture.isEnabled = true;
```

To **stop** scanning (release the camera, e.g. when navigating away):

```javascript
barcodeCapture.isEnabled = false;
camera.switchToDesiredState(Scandit.FrameSourceState.Off);
```

A typical teardown when leaving the scan page:

```javascript
const teardownBarcodeCapture = () => {
  if (barcodeCapture) {
    barcodeCapture.isEnabled = false;
  }
  if (camera) {
    camera.switchToDesiredState(Scandit.FrameSourceState.Off);
  }
};
```

## Step 9 — Optional: customize feedback

By default each scan emits a beep and a vibration. To customize, replace the feedback on the mode:

```javascript
const feedback = Scandit.BarcodeCaptureFeedback.defaultFeedback;
feedback.success = new Scandit.Feedback(Scandit.Vibration.defaultVibration, null);
barcodeCapture.feedback = feedback;
```

| Property / member | Description |
|---|---|
| `Scandit.BarcodeCaptureFeedback.defaultFeedback` | A new feedback instance with default values. |
| `feedback.success` | The `Feedback` (sound + vibration) emitted on a successful scan. |
| `barcodeCapture.feedback` | Assigning replaces the feedback used by the mode. |

## Step 10 — Optional: viewfinders, location selection, scan intention

### Viewfinder

A viewfinder is a visual guide drawn inside the `BarcodeCaptureOverlay`. The most common is a rectangular viewfinder:

```javascript
overlay.viewfinder = new Scandit.RectangularViewfinder(
  Scandit.RectangularViewfinderStyle.Square,
  Scandit.RectangularViewfinderLineStyle.Light,
);
```

Set `overlay.viewfinder = null` to remove it.

Two other viewfinder styles are available; both take **no constructor arguments** and expose color properties you can tweak:

```javascript
// Aimer viewfinder — a crosshair-style aimer with a frame and a centre dot.
const aimer = new Scandit.AimerViewfinder();
aimer.frameColor = Scandit.Color.fromHex('FFFFFF');
aimer.dotColor = Scandit.Color.fromHex('FF0000');
overlay.viewfinder = aimer;

// Laserline viewfinder — a horizontal line, good for single-line 1D scanning.
const laserline = new Scandit.LaserlineViewfinder();
laserline.width = new Scandit.NumberWithUnit(0.9, Scandit.MeasureUnit.Fraction);
laserline.enabledColor = Scandit.Color.fromHex('FFFFFF');
laserline.disabledColor = Scandit.Color.fromHex('808080');
overlay.viewfinder = laserline;
```

| Viewfinder | Constructor | Key properties |
|---|---|---|
| `Scandit.RectangularViewfinder` | `(style, lineStyle)` | `dimensions`, `color` |
| `Scandit.AimerViewfinder` | `()` | `frameColor`, `dotColor` |
| `Scandit.LaserlineViewfinder` | `()` | `width`, `enabledColor`, `disabledColor` |

### Highlight brush (recognized-barcode appearance)

`BarcodeCaptureOverlay` draws a brush over each recognized barcode. The default brush has a transparent fill and a Scandit-blue stroke. Replace `overlay.brush` to change it, or set it to `Scandit.Brush.transparent` to draw nothing:

```javascript
// A custom highlight: semi-transparent green fill, solid green 3px stroke.
overlay.brush = new Scandit.Brush(
  Scandit.Color.fromHex('8800FF00'), // fillColor (ARGB hex)
  Scandit.Color.fromHex('FF00FF00'), // strokeColor
  3,                                  // strokeWidth
);

// Draw no highlight at all.
overlay.brush = Scandit.Brush.transparent;
```

`new Scandit.Brush(fillColor, strokeColor, strokeWidth)` takes two `Scandit.Color` instances and a numeric stroke width. `Scandit.Color.fromHex(...)` accepts `RRGGBB` or `AARRGGBB` hex strings.

### Reject (filter) unwanted barcodes

There is no dedicated "reject" API. To accept only barcodes matching a rule, inspect `barcode.data` inside `didScan`: for a rejected code, set the overlay brush to transparent (so it isn't highlighted) and `return` without acting; for an accepted code, draw a highlight brush and process it.

```javascript
barcodeCapture.addListener({
  didScan: (barcodeCapture, session, _getFrameData) => {
    const barcode = session.newlyRecognizedBarcode;
    if (!barcode) return;

    // Reject codes whose data does not start with the expected prefix.
    if (!barcode.data || !barcode.data.startsWith('09:')) {
      overlay.brush = Scandit.Brush.transparent;
      return;
    }

    // Accept: highlight and handle the result.
    overlay.brush = new Scandit.Brush(
      Scandit.Color.fromHex('8800FF00'),
      Scandit.Color.fromHex('FF00FF00'),
      3,
    );
    barcodeCapture.isEnabled = false;
    showResult(`Scanned: ${barcode.data}`);
  },
});
```

### Per-symbology settings: extensions, checksums, active symbol counts, color inversion

`settings.settingsForSymbology(symbology)` returns a mutable `SymbologySettings` object. Mutating it updates the parent `BarcodeCaptureSettings`; re-apply with `barcodeCapture.applySettings(settings)`.

```javascript
const code39Settings = settings.settingsForSymbology(Scandit.Symbology.Code39);

// Extension: enable a symbology-specific feature by name (e.g. full ASCII for Code 39).
code39Settings.setExtensionEnabled('full_ascii', true);

// Checksums: require/accept an optional checksum (e.g. Mod 43 for Code 39).
code39Settings.checksums = [Scandit.Checksum.Mod43];

// Active symbol counts: the set of barcode lengths to decode for variable-length symbologies.
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12];

// Color inversion: also decode light-on-dark (inverted) barcodes.
code39Settings.isColorInvertedEnabled = true;

barcodeCapture.applySettings(settings);
```

| Member | Type | Description |
|---|---|---|
| `setExtensionEnabled(name, enabled)` | method | Activate/deactivate a symbology-specific extension (e.g. `'full_ascii'`). |
| `checksums` | `Checksum[]` | Optional checksums to accept, e.g. `[Scandit.Checksum.Mod43]`. |
| `activeSymbolCounts` | `number[]` | Barcode lengths to decode (ignored for fixed-size/2D symbologies). |
| `isColorInvertedEnabled` | `boolean` | When `true`, also decode color-inverted (light-on-dark) codes. |

### Location selection

Restrict scanning to a specific region of the frame:

```javascript
settings.locationSelection = Scandit.RadiusLocationSelection.withRadius(
  new Scandit.NumberWithUnit(0, Scandit.MeasureUnit.Fraction),
);
barcodeCapture.applySettings(settings);
```

### Scan intention

`Smart` (default) auto-picks the barcode the user is aiming at. Switch to `Manual` if you need to scan whatever is in frame without intent disambiguation:

```javascript
settings.scanIntention = Scandit.ScanIntention.Manual;
barcodeCapture.applySettings(settings);
```

### Code duplicate filter

```javascript
settings.codeDuplicateFilter = 500; // ignore the same code for 500 ms
barcodeCapture.applySettings(settings);
```

### Composite codes (GS1 Composite A/B/C)

```javascript
const composite = [Scandit.CompositeType.A, Scandit.CompositeType.B];
settings.enableSymbologiesForCompositeTypes(composite);
settings.enabledCompositeTypes = composite;
barcodeCapture.applySettings(settings);
```

## Step 11 — HTML setup

BarcodeCapture **needs** a DOM element to render the camera preview. The minimum HTML is:

```html
<!doctype html>
<html>
  <head>
    <meta http-equiv="Content-Security-Policy"
      content="default-src 'self' data: gap: https://ssl.gstatic.com 'unsafe-eval' 'unsafe-inline';
               style-src 'self' 'unsafe-inline';
               media-src *;
               img-src 'self' data: content:;" />
    <meta name="viewport" content="width=device-width, user-scalable=no, viewport-fit=cover" />
    <title>BarcodeCapture Sample</title>
  </head>
  <body style="margin: 0; padding: 0;">
    <div id="data-capture-view" style="width: 100vw; height: 100vh; z-index: -1;"></div>
    <script type="text/javascript" src="cordova.js"></script>
    <script type="text/javascript" src="index.js"></script>
  </body>
</html>
```

## Step 12 — Complete example

Full working app, based on the official BarcodeCaptureSimpleSample.

### `www/index.js`

```javascript
// @ts-check

document.addEventListener('deviceready', () => {
  const context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const camera = Scandit.Camera.default;
  camera.applySettings(Scandit.BarcodeCapture.recommendedCameraSettings);
  context.setFrameSource(camera);

  const settings = new Scandit.BarcodeCaptureSettings();
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.EAN8,
    Scandit.Symbology.UPCE,
    Scandit.Symbology.QR,
    Scandit.Symbology.DataMatrix,
    Scandit.Symbology.Code39,
    Scandit.Symbology.Code128,
    Scandit.Symbology.InterleavedTwoOfFive,
  ]);

  const code39Settings = settings.settingsForSymbology(Scandit.Symbology.Code39);
  code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];

  const barcodeCapture = new Scandit.BarcodeCapture(settings);
  context.setMode(barcodeCapture);

  barcodeCapture.addListener({
    didScan: (_barcodeCapture, session, _getFrameData) => {
      const barcode = session.newlyRecognizedBarcode;
      if (!barcode) return;

      const symbology = new Scandit.SymbologyDescription(barcode.symbology);
      showResult(`Scanned: ${barcode.data} (${symbology.readableName})`);
      barcodeCapture.isEnabled = false;
    },
  });

  const view = Scandit.DataCaptureView.forContext(context);
  view.connectToElement(document.getElementById('data-capture-view'));

  const overlay = new Scandit.BarcodeCaptureOverlay(barcodeCapture);
  overlay.viewfinder = new Scandit.RectangularViewfinder(
    Scandit.RectangularViewfinderStyle.Square,
    Scandit.RectangularViewfinderLineStyle.Light,
  );
  view.addOverlay(overlay);

  camera.switchToDesiredState(Scandit.FrameSourceState.On);
  barcodeCapture.isEnabled = true;

  window.barcodeCapture = barcodeCapture;
}, false);

function showResult(text) {
  const el = document.createElement('div');
  el.id = 'result';
  el.className = 'result';
  el.innerHTML = `<p>${text}</p><button onclick="continueScanning()">OK</button>`;
  document.querySelector('#data-capture-view').appendChild(el);
}

function continueScanning() {
  const el = document.querySelector('#result');
  if (el) el.parentElement.removeChild(el);
  window.barcodeCapture.isEnabled = true;
}
```

## Key rules

1. **Always wait for `deviceready`** before calling any `Scandit.*` API. Never call at module load time.
2. **Use the `Scandit.*` global at runtime** in plain Cordova projects. `scandit-cordova-datacapture-*` are plugin manifests, not runtime modules.
3. **`DataCaptureContext.initialize(key)`** — the v8 entry point. Not `.forLicenseKey()` and not `.sharedInstance`.
4. **`new Scandit.BarcodeCapture(settings)` + `context.setMode(...)`** — v8 pattern. Not `BarcodeCapture.forContext(context, settings)` (v7).
5. **`new Scandit.BarcodeCaptureOverlay(barcodeCapture)` + `view.addOverlay(overlay)`** — v8 pattern for attaching the overlay.
6. **Mount the `DataCaptureView` to a sized DOM element** with `view.connectToElement(...)`. Without a sized container the camera preview is invisible.
7. **Camera is off by default** — call `camera.switchToDesiredState(Scandit.FrameSourceState.On)` once the listener is wired, and `barcodeCapture.isEnabled = true` to start receiving frames.
8. **Disable the mode (`barcodeCapture.isEnabled = false`) before doing any non-trivial work in `didScan`** — the listener blocks frame processing while it runs.
9. **Do not retain the `session`** outside the listener callback. Read what you need and copy it.
10. **Run `cordova prepare`** after installing/updating plugins.
