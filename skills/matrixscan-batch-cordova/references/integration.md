# MatrixScan Batch Cordova Integration Guide

MatrixScan Batch (API name: `BarcodeBatch*`) is a multi-barcode tracking mode that continuously tracks all barcodes visible in the camera feed simultaneously, reporting additions, updates, and removals on every frame. In Cordova it renders through a `DataCaptureView` (connected to a DOM element) with one or more overlays attached — `BarcodeBatchBasicOverlay` for simple per-barcode highlights, and `BarcodeBatchAdvancedOverlay` for fully custom AR bubble views using the serialized `TrackedBarcodeView` pattern from the Bubbles sample.

> **Source note**: Integration is anchored to the Cordova samples (`MatrixScanSimpleSample` and `MatrixScanBubblesSample`) at `frameworks/cordova/samples/03_Advanced_Batch_Scanning_Samples/`. All API shown here is verified against those samples and the RST API docs (`docs/source/barcode-capture/api/`).

> **Language note**: Examples below use plain JavaScript, matching the Cordova samples. The same APIs are available in TypeScript — add a `global.d.ts` that re-exports `Scandit.*` types and adapt syntax accordingly.

> **TrackedObject (Cordova 8.2+)**: In SDK 8.2+, a `TrackedObject` base class was introduced that `TrackedBarcode` extends. No recipe is needed — the `TrackedBarcode` API you use day-to-day is unchanged.

## Prerequisites

- Cordova plugins installed:
  - `scandit-cordova-datacapture-core`
  - `scandit-cordova-datacapture-barcode`
- Install with:
  ```bash
  cordova plugin add scandit-cordova-datacapture-core
  cordova plugin add scandit-cordova-datacapture-barcode
  ```
- After any plugin change, run `cordova prepare` to sync native projects.
- **Minimum plugin version**: BarcodeBatch on Cordova: **6.2**. Modern constructors (`new Scandit.BarcodeBatch(settings)`, `new Scandit.BarcodeBatchBasicOverlay(mode, style)`, `new Scandit.BarcodeBatchAdvancedOverlay(mode)`, `Scandit.BarcodeBatch.createRecommendedCameraSettings()`) require **7.6+**.
- A valid **Scandit license key** (get one at [scandit.com](https://www.scandit.com)).
- **Camera permissions** are configured automatically by the plugins:
  - iOS: `NSCameraUsageDescription` is added to `Info.plist` via `plugin.xml`.
  - Android: `CAMERA` permission is added to `AndroidManifest.xml`.
- **iOS deployment target**: 15.0 or higher.
- **Android minSdkVersion**: 24 or higher.
- **Web platform NOT supported**: BarcodeBatch on Cordova requires iOS or Android.

## Integration flow

Ask the user which barcode symbologies they need to scan. Only enable the symbologies actually required — each extra symbology adds processing time.

Once the user responds, ask them which file they'd like to integrate MatrixScan Batch into (typically the app entry point, e.g. `www/js/index.js`). Then write the integration code directly into that file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Install plugins: `cordova plugin add scandit-cordova-datacapture-core scandit-cordova-datacapture-barcode`
2. Run `cordova prepare` to apply native changes.
3. Add `<div id="data-capture-view">` to the scanning screen in your HTML and size it to fill the camera area.
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key from https://ssl.scandit.com.
5. Store references to `barcodeBatch`, `view`, and any overlays on `window` or at module scope to prevent garbage collection.
6. Camera permissions are auto-configured by the plugins (no manual Info.plist or manifest edit needed).

## Step 1 — Wait for `deviceready`

The Scandit SDK is exposed on the global `window.Scandit` object. Both plugins auto-register at app startup. You **must** wait for the `deviceready` event before using any Scandit API.

```javascript
document.addEventListener('deviceready', () => {
  // Safe to call Scandit APIs here
  initializeSDK();
}, false);
```

If the project is TypeScript, declare the global type in a `global.d.ts`:

```typescript
import type * as ScanditCore from 'scandit-cordova-datacapture-core';
import type * as ScanditBarcode from 'scandit-cordova-datacapture-barcode';

declare global {
  const Scandit: typeof ScanditCore & typeof ScanditBarcode;
}
```

Reference it from your TS file with `/// <reference path="./global.d.ts" />`.

> **Do not** import from `scandit-cordova-datacapture-*` at runtime in a plain-Cordova project — those are plugin manifests, not ES modules. Use `Scandit.X` at runtime.

## Step 2 — Create DataCaptureContext

```javascript
const context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
```

`DataCaptureContext.initialize(key)` is the v8 entry point. Call this exactly once, after `deviceready`.

## Step 3 — Set Up the Camera

```javascript
// Use the recommended camera settings for BarcodeBatch (cordova ≥7.6).
const cameraSettings = Scandit.BarcodeBatch.createRecommendedCameraSettings();
window.camera = Scandit.Camera.withSettings(cameraSettings);
context.setFrameSource(window.camera);
```

Start and stop the camera explicitly:

```javascript
// Start:
window.camera.switchToDesiredState(Scandit.FrameSourceState.On);

// Stop (teardown):
window.camera.switchToDesiredState(Scandit.FrameSourceState.Off);
```

> **Note**: `BarcodeBatch.createRecommendedCameraSettings()` is available from cordova=7.6. On older SDKs, use `Scandit.Camera.default` or construct `CameraSettings` manually.

## Step 4 — Configure BarcodeBatchSettings and Construct BarcodeBatch

```javascript
const settings = new Scandit.BarcodeBatchSettings();

// Only enable the symbologies your app actually needs.
settings.enableSymbologies([
  Scandit.Symbology.EAN13UPCA,
  Scandit.Symbology.EAN8,
  Scandit.Symbology.UPCE,
  Scandit.Symbology.Code39,
  Scandit.Symbology.Code128,
]);

// Optional: adjust active symbol counts for variable-length symbologies.
const code39Settings = settings.settingsForSymbology(Scandit.Symbology.Code39);
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];

// SDK ≥7.6 constructor — no context argument.
window.barcodeBatch = new Scandit.BarcodeBatch(settings);

// Register the mode with the context. This replaces any previously active mode.
context.setMode(window.barcodeBatch);
```

### BarcodeBatchSettings Key Members

| Member | Available | Description |
|--------|-----------|-------------|
| `new Scandit.BarcodeBatchSettings()` | cordova=7.0 | All symbologies disabled by default. |
| `enableSymbologies(symbologies)` | cordova=7.0 | Enable multiple symbologies at once. |
| `enableSymbology(symbology, enabled)` | cordova=7.0 | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | cordova=7.0 | Get per-symbology settings (e.g. `activeSymbolCounts`). |
| `enabledSymbologies` | cordova=7.0 | Read-only array of currently enabled symbologies. |

### BarcodeBatch Key Members

| Member | Available | Description |
|--------|-----------|-------------|
| `new Scandit.BarcodeBatch(settings)` | cordova=7.6 | Constructs a new instance. No context argument. |
| `Scandit.BarcodeBatch.createRecommendedCameraSettings()` | cordova=7.6 | Returns camera settings optimized for BarcodeBatch. |
| `addListener(listener)` / `removeListener(listener)` | cordova=7.0 | Register/remove a `BarcodeBatchListener`. |
| `applySettings(settings)` | cordova=7.0 | Update settings at runtime (returns `Promise<void>`). |
| `isEnabled` | cordova=7.0 | `boolean` — enable/disable without removing from context. |
| `reset()` | cordova=7.0 | Resets the object tracker (`Promise<void>`). |
| `context` | cordova=7.0 | Read-only reference to the associated `DataCaptureContext`. |

## Step 5 — Receive Tracked Barcodes via BarcodeBatchListener

`BarcodeBatchListener.didUpdateSession` is called after every frame where the tracked barcode state changes.

```javascript
window.barcodeBatch.addListener({
  // Called on every frame where tracked barcode state changes.
  didUpdateSession: (barcodeBatch, session) => {
    // All currently tracked barcodes (map from identifier string to TrackedBarcode).
    const allTracked = Object.values(session.trackedBarcodes);

    // Newly appeared barcodes this frame.
    const added = session.addedTrackedBarcodes;

    // Barcodes whose position changed this frame.
    const updated = session.updatedTrackedBarcodes;

    // Identifiers of barcodes that left the frame (string[]).
    const removedIds = session.removedTrackedBarcodes;

    allTracked.forEach(trackedBarcode => {
      const { data, symbology } = trackedBarcode.barcode;
      console.log(`Tracking [${symbology}]: ${data}`);
    });

    // IMPORTANT: do not hold a reference to session or its arrays outside this callback.
    // Copy the data you need before the callback returns.
  },
});
```

### BarcodeBatchSession Properties

| Property | Type | Available | Description |
|----------|------|-----------|-------------|
| `trackedBarcodes` | `{ [key: string]: TrackedBarcode }` | cordova=7.0 | All currently tracked barcodes. |
| `addedTrackedBarcodes` | `TrackedBarcode[]` | cordova=7.0 | Barcodes newly tracked this frame. |
| `updatedTrackedBarcodes` | `TrackedBarcode[]` | cordova=7.0 | Barcodes with updated location this frame. |
| `removedTrackedBarcodes` | `string[]` | cordova=7.0 | Identifiers of barcodes that were lost. |
| `frameSequenceID` | `number` | cordova=7.0 | Identifier of the current frame sequence. |
| `reset()` | `Promise<void>` | cordova=7.0 | Resets the session (call only inside the listener). |

> **Important**: Do not hold references to the session object or its arrays outside the `didUpdateSession` callback — they may be concurrently modified. Copy any data you need.

#### Reacting to removed (lost) barcodes

`session.removedTrackedBarcodes` is an **array of identifier strings** — the identifiers of barcodes that left the frame this frame. It is **not** an array of `TrackedBarcode` objects, so its entries have no `.barcode` — use them directly as keys. Iterate it inside `didUpdateSession` to clean up any app-side state you keyed by tracked-barcode identifier (e.g. a per-barcode counter map or an AR view registry), so the state does not leak as barcodes come and go.

```javascript
// App-side state keyed by tracked-barcode identifier.
const highlightCountByIdentifier = {};

window.barcodeBatch.addListener({
  didUpdateSession: (barcodeBatch, session) => {
    // Newly tracked barcodes this frame — start tracking app state.
    session.addedTrackedBarcodes.forEach(trackedBarcode => {
      highlightCountByIdentifier[trackedBarcode.identifier] = 0;
    });

    // Lost barcodes this frame — delete the corresponding app state.
    // Each entry is an identifier string, not a TrackedBarcode.
    session.removedTrackedBarcodes.forEach(identifier => {
      delete highlightCountByIdentifier[identifier];
    });
  },
});
```

> **Important**: `removedTrackedBarcodes` entries are identifier strings. Do not read `.barcode.data` from them. As always, do not hold a reference to `session` or its arrays outside the callback.

### TrackedBarcode Properties

| Property | Type | Available | Description |
|----------|------|-----------|-------------|
| `barcode` | `Barcode` | cordova=6.1 | The barcode associated with this track. |
| `identifier` | `number` | cordova=6.2 | Unique identifier for this track. May be reused after a barcode is lost. |
| `location` | `Quadrilateral` | cordova=6.5 | Location of the barcode in image-space. Requires MatrixScan AR add-on. |

## Step 6 — Set Up DataCaptureView

`DataCaptureView.forContext(context)` creates the view. Then attach it to a DOM element with `connectToElement`.

```javascript
window.view = Scandit.DataCaptureView.forContext(context);
window.view.connectToElement(document.getElementById('data-capture-view'));
```

The HTML must contain a container element sized to fill the camera area:

```html
<div id="data-capture-view" style="width: 100%; height: 100%;"></div>
```

## Step 7 — BarcodeBatchBasicOverlay: Per-Barcode Brushes

`BarcodeBatchBasicOverlay` renders a highlight frame or dot over each tracked barcode. Set a `listener` with `brushForTrackedBarcode` to return different brushes based on symbology or data. Return `null` (or a fully transparent brush) to hide the highlight for a particular barcode.

> **Note**: Using `brushForTrackedBarcode` (and `setBrushForTrackedBarcode`) requires the **MatrixScan AR add-on**.

```javascript
// SDK ≥7.6 constructor.
const basicOverlay = new Scandit.BarcodeBatchBasicOverlay(
  window.barcodeBatch,
  Scandit.BarcodeBatchBasicOverlayStyle.Dot,
);

// Brushes for different conditions.
const greenBrush = new Scandit.Brush(
  Scandit.Color.fromRGBA(0, 204, 0, 0.3),   // semi-transparent green fill
  Scandit.Color.fromHex('#00CC00'),           // solid green stroke
  2,
);
const redBrush = new Scandit.Brush(
  Scandit.Color.fromRGBA(204, 0, 0, 0.3),
  Scandit.Color.fromHex('#CC0000'),
  2,
);
// Transparent brush — hides the highlight for this barcode entirely.
const transparentBrush = new Scandit.Brush(
  Scandit.Color.fromRGBA(0, 0, 0, 0),
  Scandit.Color.fromRGBA(0, 0, 0, 0),
  0,
);

// Set a listener to return a brush per tracked barcode.
// Called from the rendering thread whenever a new tracked barcode appears.
basicOverlay.listener = {
  brushForTrackedBarcode: (overlay, trackedBarcode) => {
    const data = trackedBarcode.barcode.data || '';

    // Return transparent brush to hide barcodes starting with '0'.
    if (data.startsWith('0')) {
      return transparentBrush;
    }

    // Different colors by symbology.
    if (trackedBarcode.barcode.symbology === Scandit.Symbology.EAN13UPCA) {
      return greenBrush;
    }

    return redBrush;
  },

  didTapTrackedBarcode: (overlay, trackedBarcode) => {
    console.log('Tapped:', trackedBarcode.barcode.data);
  },
};

// Add the overlay to the view — required for it to appear on screen.
window.view.addOverlay(basicOverlay);
```

### BarcodeBatchBasicOverlay Key Members

| Member | Available | Description |
|--------|-----------|-------------|
| `new Scandit.BarcodeBatchBasicOverlay(mode, style)` | cordova=7.6 | Constructs the overlay. Must be added to the view with `view.addOverlay`. |
| `listener` | cordova=7.0 | Set an `IBarcodeBatchBasicOverlayListener`. Requires MatrixScan AR add-on. |
| `brush` | cordova=7.0 | Default brush when no listener is set. |
| `setBrushForTrackedBarcode(brush, trackedBarcode)` | cordova=7.0 | Imperatively set a brush for a specific tracked barcode. Returns `Promise<void>`. Requires AR add-on. |
| `clearTrackedBarcodeBrushes()` | cordova=7.0 | Clear all custom brushes. Returns `Promise<void>`. |
| `shouldShowScanAreaGuides` | cordova=7.0 | Debug: show the active scan area. Default `false`. |
| `style` | cordova=7.0 | The overlay style (`Frame` or `Dot`). |

### BarcodeBatchBasicOverlayStyle Values

| Value | Description |
|-------|-------------|
| `Scandit.BarcodeBatchBasicOverlayStyle.Frame` | Rectangular frame highlight with appear animation. |
| `Scandit.BarcodeBatchBasicOverlayStyle.Dot` | Dot highlight with appear animation. |

#### Choosing the overlay style

The style is the **second constructor argument** of `BarcodeBatchBasicOverlay`. There is no `style` setter to change it after construction — pick the style when you create the overlay (or remove and re-create the overlay to switch). Use `Scandit.BarcodeBatchBasicOverlayStyle.Frame` for a rectangular outline, or `Scandit.BarcodeBatchBasicOverlayStyle.Dot` for a single dot per tracked barcode.

```javascript
// Frame highlight (rectangular outline).
window.basicOverlay = new Scandit.BarcodeBatchBasicOverlay(
  window.barcodeBatch,
  Scandit.BarcodeBatchBasicOverlayStyle.Frame,
);
window.view.addOverlay(window.basicOverlay);
```

```javascript
// Dot highlight (one dot per tracked barcode).
window.basicOverlay = new Scandit.BarcodeBatchBasicOverlay(
  window.barcodeBatch,
  Scandit.BarcodeBatchBasicOverlayStyle.Dot,
);
window.view.addOverlay(window.basicOverlay);
```

> **Note**: The `style` property is read-only on Cordova. To switch styles at runtime, construct a new overlay with the desired style and add it to the view.

### IBarcodeBatchBasicOverlayListener Callbacks

| Callback | Description |
|----------|-------------|
| `brushForTrackedBarcode(overlay, trackedBarcode)` | Return a `Brush` (or `null` to hide) for a newly tracked barcode. Called from the rendering thread. Requires MatrixScan AR add-on. |
| `didTapTrackedBarcode(overlay, trackedBarcode)` | Called when the user taps a tracked barcode highlight. Called from the main thread. |

#### Handling taps on a tracked barcode highlight

To react when the user taps a tracked barcode's highlight, set `didTapTrackedBarcode` on the **basic** overlay listener. The callback receives `(overlay, trackedBarcode)`; read `trackedBarcode.barcode.data` and `trackedBarcode.barcode.symbology`.

```javascript
window.basicOverlay.listener = {
  // Called on the main thread when a tracked barcode highlight is tapped.
  didTapTrackedBarcode: (overlay, trackedBarcode) => {
    const { data, symbology } = trackedBarcode.barcode;
    console.log(`Tapped [${symbology}]: ${data}`);
  },
};
```

> **Note**: The `BarcodeBatchBasicOverlay` listener (including `didTapTrackedBarcode`) requires the MatrixScan AR add-on.
>
> **Important**: `didTapTrackedBarcode` is the **basic**-overlay tap callback. For taps on an AR bubble view rendered by `BarcodeBatchAdvancedOverlay`, use `didTapViewForTrackedBarcode` instead (see Step 8). Returning `null` from `brushForTrackedBarcode` hides a barcode's highlight and also disables its tap action.

## Step 8 — BarcodeBatchAdvancedOverlay: AR Annotations

`BarcodeBatchAdvancedOverlay` lets you anchor a custom view to each tracked barcode. On Cordova, the view must be a **serialized `TrackedBarcodeView`** constructed from a DOM element via `Scandit.TrackedBarcodeView.withHTMLElement`. This is the pattern used in the Bubbles sample.

> **Important**: Using `BarcodeBatchAdvancedOverlay` requires the **MatrixScan AR add-on**.

The anchor and offset are set via the overlay listener, positioning each bubble relative to its tracked barcode.

```javascript
// SDK ≥7.6 constructor.
window.advancedOverlay = new Scandit.BarcodeBatchAdvancedOverlay(window.barcodeBatch);

window.advancedOverlay.listener = {
  // Position the bubble above the center of the barcode.
  anchorForTrackedBarcode: (overlay, trackedBarcode) => {
    return Scandit.Anchor.TopCenter;
  },

  // Shift the bubble up by 100% of its own height so it sits above the barcode.
  offsetForTrackedBarcode: (overlay, trackedBarcode) => {
    return new Scandit.PointWithUnit(
      new Scandit.NumberWithUnit(0, Scandit.MeasureUnit.Fraction),
      new Scandit.NumberWithUnit(-1, Scandit.MeasureUnit.Fraction),
    );
  },

  didTapViewForTrackedBarcode: (overlay, trackedBarcode) => {
    console.log('Tapped AR view for:', trackedBarcode.barcode.data);
  },
};

// Add the advanced overlay to the view.
window.view.addOverlay(window.advancedOverlay);
```

### Setting the View for Each Tracked Barcode

Inside `BarcodeBatchListener.didUpdateSession`, call `advancedOverlay.setViewForTrackedBarcode` for each barcode you want an AR bubble on. The view must be a `TrackedBarcodeView` built from a DOM element.

```javascript
window.barcodeBatch.addListener({
  didUpdateSession: (barcodeBatch, session) => {
    // Clean up state for lost barcodes.
    session.removedTrackedBarcodes.forEach(identifier => {
      // Optional: clear app-level state for this identifier.
    });

    // Set or update the AR view for each currently tracked barcode.
    Object.values(session.trackedBarcodes).forEach(trackedBarcode => {
      const barcodeData = trackedBarcode.barcode.data;
      if (!barcodeData) return;

      // Build the DOM element for the bubble.
      const bubbleElement = createBubble(barcodeData);

      // Wrap the DOM element in a TrackedBarcodeView.
      // The scale option compensates for device pixel ratio for crisp rendering.
      const bubble = Scandit.TrackedBarcodeView.withHTMLElement(
        bubbleElement,
        { scale: 1 / window.devicePixelRatio },
      );

      // Set the view for this tracked barcode. Pass null to remove it.
      window.advancedOverlay
        .setViewForTrackedBarcode(bubble, trackedBarcode)
        .catch(console.warn);
    });
  },
});
```

### Building a Bubble DOM Element

This is the pattern from `MatrixScanBubblesSample`. Scale DOM dimensions by `devicePixelRatio` for crisp rendering on high-DPI screens, then pass `scale: 1 / devicePixelRatio` to `withHTMLElement` to bring it back to logical pixels.

```javascript
function createBubble(barcodeData) {
  const bubbleWidth = 200;
  const bubbleHeight = 60;
  const dpr = window.devicePixelRatio;

  const container = document.createElement('div');
  container.style.width = `${bubbleWidth * dpr}px`;
  container.style.height = `${bubbleHeight * dpr}px`;
  container.style.borderRadius = `${(bubbleHeight / 2) * dpr}px`;
  container.style.backgroundColor = 'rgba(255, 255, 255, 0.85)';
  container.style.display = 'flex';
  container.style.alignItems = 'center';
  container.style.justifyContent = 'center';
  container.style.fontFamily = 'Helvetica Neue, sans-serif';
  container.style.fontSize = `${14 * dpr}px`;
  container.style.fontWeight = 'bold';
  container.style.paddingLeft = `${10 * dpr}px`;
  container.style.paddingRight = `${10 * dpr}px`;
  container.style.boxSizing = 'border-box';

  const label = document.createElement('p');
  label.style.margin = '0';
  label.textContent = barcodeData;
  container.appendChild(label);

  return container;
}
```

> **Pixel density note**: Scale the bubble down by `1 / window.devicePixelRatio` in the `TrackedBarcodeView.withHTMLElement` options so the native layer renders it at the correct logical size.

### Setting Anchor and Offset Imperatively (Alternative Pattern)

In addition to the listener callbacks, anchor and offset can be set per-barcode from `didUpdateSession`, as shown in the Bubbles sample:

```javascript
// Inside didUpdateSession, for newly added barcodes:
session.addedTrackedBarcodes.forEach(trackedBarcode => {
  window.advancedOverlay
    .setAnchorForTrackedBarcode(Scandit.Anchor.TopCenter, trackedBarcode)
    .catch(console.warn);
  window.advancedOverlay
    .setOffsetForTrackedBarcode(
      new Scandit.PointWithUnit(
        new Scandit.NumberWithUnit(0, Scandit.MeasureUnit.Fraction),
        new Scandit.NumberWithUnit(-1, Scandit.MeasureUnit.Fraction),
      ),
      trackedBarcode,
    )
    .catch(console.warn);
});
```

### Advanced Overlay Key Members

| Member | Available | Description |
|--------|-----------|-------------|
| `new Scandit.BarcodeBatchAdvancedOverlay(mode)` | cordova=7.6 | Constructs the overlay. Must be added to the view. |
| `listener` | cordova=7.0 | Set an `IBarcodeBatchAdvancedOverlayListener`. |
| `setViewForTrackedBarcode(view, trackedBarcode)` | cordova=7.0 | Set the `TrackedBarcodeView` for a tracked barcode. Pass `null` to remove. Returns `Promise<void>`. |
| `setAnchorForTrackedBarcode(anchor, trackedBarcode)` | cordova=7.0 | Override the anchor imperatively. Returns `Promise<void>`. |
| `setOffsetForTrackedBarcode(offset, trackedBarcode)` | cordova=7.0 | Override the offset imperatively. Returns `Promise<void>`. |
| `clearTrackedBarcodeViews()` | cordova=7.0 | Remove all AR views. Returns `Promise<void>`. |
| `shouldShowScanAreaGuides` | cordova=7.0 | Debug: show the active scan area. Default `false`. |

### IBarcodeBatchAdvancedOverlayListener Callbacks

| Callback | Description |
|----------|-------------|
| `viewForTrackedBarcode(overlay, trackedBarcode)` | Return a `Promise<TrackedBarcodeView?>` for a newly tracked barcode. Ignored if `setViewForTrackedBarcode` was already called for this barcode. |
| `anchorForTrackedBarcode(overlay, trackedBarcode)` | Return an `Anchor` for the view. |
| `offsetForTrackedBarcode(overlay, trackedBarcode)` | Return a `PointWithUnit` offset. |
| `didTapViewForTrackedBarcode(overlay, trackedBarcode)` | Called when the user taps the AR view. Available on Cordova. |

#### Handling taps on an AR bubble view

When you want to react to a tap on the AR bubble rendered by `BarcodeBatchAdvancedOverlay` (e.g. open a details screen for that barcode), set `didTapViewForTrackedBarcode` on the **advanced** overlay listener. Cordova supports this callback. The callback receives `(overlay, trackedBarcode)`; read `trackedBarcode.barcode.data`.

```javascript
window.advancedOverlay.listener = {
  anchorForTrackedBarcode: (overlay, trackedBarcode) => Scandit.Anchor.TopCenter,
  offsetForTrackedBarcode: (overlay, trackedBarcode) =>
    new Scandit.PointWithUnit(
      new Scandit.NumberWithUnit(0, Scandit.MeasureUnit.Fraction),
      new Scandit.NumberWithUnit(-1, Scandit.MeasureUnit.Fraction),
    ),

  // Called when the user taps the AR bubble view for a tracked barcode.
  didTapViewForTrackedBarcode: (overlay, trackedBarcode) => {
    openDetailsScreen(trackedBarcode.barcode.data);
  },
};
```

> **Note**: `BarcodeBatchAdvancedOverlay` (including `didTapViewForTrackedBarcode`) requires the MatrixScan AR add-on.
>
> **Important**: `didTapViewForTrackedBarcode` is the **advanced**-overlay callback (taps on your custom bubble view). For taps on the simple `BarcodeBatchBasicOverlay` highlight, use `didTapTrackedBarcode` instead (see Step 7). Do not mix the two names.

### TrackedBarcodeView

`TrackedBarcodeView` is the serialized view type used by Cordova's advanced overlay. It wraps a DOM element for transmission to the native layer.

| Member | Available | Description |
|--------|-----------|-------------|
| `Scandit.TrackedBarcodeView.withHTMLElement(element, options?)` | cordova=7.0 | Create from a DOM element. `options.scale` adjusts for device pixel ratio. |

## Step 9 — Start Camera and Enable Mode

```javascript
// Switch camera on to start streaming frames.
window.camera.switchToDesiredState(Scandit.FrameSourceState.On);

// Enable the mode to start tracking.
window.barcodeBatch.isEnabled = true;
```

## Step 10 — Feedback (Sound / Vibration)

**`BarcodeBatch` has NO built-in or automatic feedback.** Unlike `BarcodeCapture` (which exposes `BarcodeCaptureFeedback`) or `BarcodeCount`, the `BarcodeBatch` mode has **no `feedback` property** and never beeps or vibrates on its own. If you want a sound and/or vibration when barcodes are tracked, you must emit a `Scandit.Feedback` **manually** from inside `didUpdateSession`.

Build the feedback once (store it at module/`window` scope), then call `.emit()` for the events you care about. To beep once per **newly tracked** barcode (rather than every frame), iterate `session.addedTrackedBarcodes`:

```javascript
// Build the feedback once. Default sound + default vibration:
window.scanFeedback = new Scandit.Feedback(
  Scandit.Vibration.defaultVibration,
  Scandit.Sound.defaultSound,
);
// Equivalent shortcut: const feedback = Scandit.Feedback.defaultFeedback;

window.barcodeBatch.addListener({
  didUpdateSession: (barcodeBatch, session) => {
    // Emit once per barcode that started being tracked this frame.
    session.addedTrackedBarcodes.forEach(() => {
      window.scanFeedback.emit();
    });
  },
});
```

> **Why `addedTrackedBarcodes`?** `didUpdateSession` fires on every frame. Emitting from `trackedBarcodes` (all currently tracked) would beep continuously. `addedTrackedBarcodes` contains only the barcodes that newly appeared this frame, so the feedback fires once per new barcode.

To customize, pass a different `Scandit.Vibration` or `Scandit.Sound` (e.g. `new Scandit.Feedback(Scandit.Vibration.defaultVibration, null)` for vibration only, or pass a `Scandit.Sound` with a custom `resource`).

### Feedback API (core)

| Member | Available | Description |
|--------|-----------|-------------|
| `new Scandit.Feedback(vibration, sound)` | cordova=6.1 | Constructs a feedback. Either argument may be `null`. |
| `Scandit.Feedback.defaultFeedback` | cordova=6.1 | A feedback with the default sound and default vibration. |
| `feedback.emit()` | cordova=6.3 | Emits the sound and vibration. Subject to device ring mode / volume. |
| `Scandit.Vibration.defaultVibration` | cordova=6.1 | The default success vibration. |
| `Scandit.Sound.defaultSound` | cordova=6.1 | The default success beep. |

## Step 11 — Lifecycle: Enable/Disable, Cleanup, and Camera Permissions

### Enable/disable without removing the mode

```javascript
// Pause scanning (e.g. user navigates away or app backgrounds).
window.barcodeBatch.isEnabled = false;
window.camera.switchToDesiredState(Scandit.FrameSourceState.Off);

// Resume scanning.
window.barcodeBatch.isEnabled = true;
window.camera.switchToDesiredState(Scandit.FrameSourceState.On);
```

### App backgrounding / resuming

Cordova fires `pause` and `resume` on the `document` object:

```javascript
document.addEventListener('pause', () => {
  if (window.barcodeBatch) window.barcodeBatch.isEnabled = false;
  if (window.camera) window.camera.switchToDesiredState(Scandit.FrameSourceState.Off);
}, false);

document.addEventListener('resume', () => {
  if (window.barcodeBatch) window.barcodeBatch.isEnabled = true;
  if (window.camera) window.camera.switchToDesiredState(Scandit.FrameSourceState.On);
}, false);
```

### Full teardown

```javascript
async function uninitialize() {
  if (window.camera) {
    await window.camera.switchToDesiredState(Scandit.FrameSourceState.Off);
    window.camera = null;
  }
  if (window.barcodeBatch) {
    window.barcodeBatch.isEnabled = false;
    window.barcodeBatch = null;
  }
  if (window.view) {
    window.view.detachFromElement();
    window.view = null;
  }
}
```

> **Note**: Call `view.detachFromElement()` when the scanning screen is torn down to release native view resources.

### Camera permissions

Both iOS and Android camera permissions are declared automatically in the plugin manifests — no manual `Info.plist` or `AndroidManifest.xml` edit is required. The Cordova plugin handles this via `plugin.xml`. At runtime, the OS presents the permission dialog when the camera is first activated.

## Step 12 — Complete Example

```javascript
// @ts-check
// MatrixScan Batch integration for Cordova.
// All Scandit APIs are accessed via the global Scandit.* namespace.

document.addEventListener('deviceready', () => {
  const context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const cameraSettings = Scandit.BarcodeBatch.createRecommendedCameraSettings();
  window.camera = Scandit.Camera.withSettings(cameraSettings);
  context.setFrameSource(window.camera);

  const settings = new Scandit.BarcodeBatchSettings();
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.EAN8,
    Scandit.Symbology.Code128,
  ]);

  window.barcodeBatch = new Scandit.BarcodeBatch(settings);
  context.setMode(window.barcodeBatch);

  window.barcodeBatch.addListener({
    didUpdateSession: (barcodeBatch, session) => {
      Object.values(session.trackedBarcodes).forEach(trackedBarcode => {
        console.log('Tracking:', trackedBarcode.barcode.data);
      });
    },
  });

  window.view = Scandit.DataCaptureView.forContext(context);
  window.view.connectToElement(document.getElementById('data-capture-view'));

  // Basic overlay — default highlight for all tracked barcodes.
  window.basicOverlay = new Scandit.BarcodeBatchBasicOverlay(
    window.barcodeBatch,
    Scandit.BarcodeBatchBasicOverlayStyle.Frame,
  );
  window.view.addOverlay(window.basicOverlay);

  window.camera.switchToDesiredState(Scandit.FrameSourceState.On);
  window.barcodeBatch.isEnabled = true;
}, false);

document.addEventListener('pause', () => {
  if (window.barcodeBatch) window.barcodeBatch.isEnabled = false;
  if (window.camera) window.camera.switchToDesiredState(Scandit.FrameSourceState.Off);
}, false);

document.addEventListener('resume', () => {
  if (window.barcodeBatch) window.barcodeBatch.isEnabled = true;
  if (window.camera) window.camera.switchToDesiredState(Scandit.FrameSourceState.On);
}, false);
```

## Key Rules

1. **Always wait for `deviceready`** before calling any `Scandit.*` API.
2. **Use the `Scandit.*` global at runtime** in plain Cordova projects — do not `import` from `scandit-cordova-datacapture-*` in WebView-executed code.
3. **`context.setMode(barcodeBatch)`** — Cordova's method to register the mode with the context. Replaces any previously active mode.
4. **`DataCaptureView.forContext(context)` + `connectToElement`** — The Cordova view pattern. Connect to a DOM element; the view mirrors its size and position.
5. **Modern constructors ≥7.6** — `new Scandit.BarcodeBatch(settings)`, `new Scandit.BarcodeBatchBasicOverlay(mode, style)`, `new Scandit.BarcodeBatchAdvancedOverlay(mode)`, and `Scandit.BarcodeBatch.createRecommendedCameraSettings()` all require cordova=7.6.
6. **Add overlays to the view** — `view.addOverlay(overlay)` must be called after creating both the view and the overlay.
7. **AR add-on required** — `brushForTrackedBarcode`, `setBrushForTrackedBarcode`, and all `BarcodeBatchAdvancedOverlay` APIs require the MatrixScan AR add-on license.
8. **AdvancedOverlay uses `TrackedBarcodeView`** — On Cordova, views passed to `setViewForTrackedBarcode` must be `TrackedBarcodeView` instances created via `Scandit.TrackedBarcodeView.withHTMLElement(domElement, options)`. This is the same serialized-view pattern as Capacitor.
9. **Prevent garbage collection** — Store `barcodeBatch`, `view`, `camera`, and overlays on `window` or at module scope.
10. **Run `cordova prepare`** after installing or updating plugins.
11. **Session data safety** — Do not hold references to `session`, `session.trackedBarcodes`, `session.addedTrackedBarcodes`, etc. outside the `didUpdateSession` callback. Copy values you need.
12. **Teardown** — Call `view.detachFromElement()` and `camera.switchToDesiredState(Scandit.FrameSourceState.Off)` when leaving the scanning screen.

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| "Scandit is not defined" at startup | Code ran before `deviceready`. Move all Scandit calls inside the `deviceready` handler. |
| Camera not streaming | `camera.switchToDesiredState(Scandit.FrameSourceState.On)` was not called, or `context.setFrameSource(camera)` was skipped. |
| Overlays not visible | `view.addOverlay(overlay)` was not called after creating the overlay. |
| Brushes not showing | `brushForTrackedBarcode` requires the MatrixScan AR add-on. Verify the license. |
| AR bubbles not rendering | A plain DOM element was passed directly to `setViewForTrackedBarcode` instead of a `TrackedBarcodeView.withHTMLElement(...)` instance. |
| Bubbles blurry on high-DPI screens | `scale: 1 / window.devicePixelRatio` was not set in `TrackedBarcodeView.withHTMLElement` options. |
| `new Scandit.BarcodeBatch(settings)` not found | Requires cordova=7.6. |
| `BarcodeBatch.createRecommendedCameraSettings()` not found | Requires cordova=7.6. |
| Session data accessed outside callback | Copy `addedTrackedBarcodes`, `updatedTrackedBarcodes`, etc. before the callback returns. |
| Native/web version mismatch at runtime | Run `cordova prepare` after installing or updating plugins. |
