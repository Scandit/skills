# MatrixScan Batch Capacitor Integration Guide

MatrixScan Batch (API name: `BarcodeBatch*`) is a multi-barcode tracking mode that continuously tracks all barcodes visible in the camera feed simultaneously, reporting additions, updates, and removals on every frame. In Capacitor it renders through a `DataCaptureView` (connected to a DOM element) with one or more overlays attached — `BarcodeBatchBasicOverlay` for simple per-barcode highlights, and `BarcodeBatchAdvancedOverlay` for fully custom AR bubble views using the serialized `TrackedBarcodeView` pattern.

> **Language note**: Examples below use JavaScript (ES modules). The same API works identically with TypeScript — adapt imports and add type annotations to match the user's project.

> **TrackedObject (Capacitor 8.2+)**: In SDK 8.2+, a `TrackedObject` base class was introduced that `TrackedBarcode` extends. No recipe is needed for this — the `TrackedBarcode` API you use day-to-day is unchanged.

## Prerequisites

- Scandit Capacitor packages installed:
  - `scandit-capacitor-datacapture-core`
  - `scandit-capacitor-datacapture-barcode`
- After installing, run `npx cap sync` to sync the native projects.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- **Minimum SDK version**: BarcodeBatch on Capacitor: **6.8**. Modern constructors (`new BarcodeBatch(settings)`, `new BarcodeBatchBasicOverlay(mode, style)`, `new BarcodeBatchAdvancedOverlay(mode)`, `BarcodeBatch.createRecommendedCameraSettings()`) require **7.6+**.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/App/App/Info.plist`.
  - Android: handled automatically by the plugin.
- BarcodeBatch runs on iOS and Android only. Guard with `Capacitor.isNativePlatform()` if your app also targets web.

## Integration flow

Ask the user which barcode symbologies they need to scan. Only enable the symbologies actually required — each extra symbology adds processing time.

Once the user responds, ask them which file they'd like to integrate MatrixScan Batch into (typically the app entry point or a page module, e.g. `www/js/app.js`). Then write the integration code directly into that file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Install packages: `npm install scandit-capacitor-datacapture-core scandit-capacitor-datacapture-barcode`
2. Run `npx cap sync` to apply native changes.
3. Add `NSCameraUsageDescription` to `ios/App/App/Info.plist`.
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key from https://ssl.scandit.com.
5. Add `<div id="data-capture-view">` to the scanning screen in your HTML and size it to fill the camera area.
6. Store references to `barcodeBatch`, `view`, and any overlays on `window` or at module scope to prevent garbage collection.

## Step 1 — Initialize Plugins and Create DataCaptureContext

Plugin initialization **must** happen before any other Scandit API call.

```javascript
import {
  DataCaptureContext,
  ScanditCaptureCorePlugin,
} from 'scandit-capacitor-datacapture-core';

// Must be called first — sets up all Scandit plugins.
await ScanditCaptureCorePlugin.initializePlugins();

const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
```

> **Important**: Always call `ScanditCaptureCorePlugin.initializePlugins()` before `DataCaptureContext.initialize()` or any other Scandit API. Skipping this step causes undefined behavior.

## Step 2 — Set Up the Camera

```javascript
import {
  Camera,
  FrameSourceState,
} from 'scandit-capacitor-datacapture-core';

import { BarcodeBatch } from 'scandit-capacitor-datacapture-barcode';

// Use the recommended camera settings for BarcodeBatch (SDK ≥7.6).
const cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
window.camera = Camera.withSettings(cameraSettings);
context.setFrameSource(window.camera);
```

> **Note**: `BarcodeBatch.createRecommendedCameraSettings()` is available from capacitor=7.6. On older SDKs, use `Camera.default` or construct `CameraSettings` manually.

## Step 3 — Configure BarcodeBatchSettings and Construct BarcodeBatch

```javascript
import {
  BarcodeBatch,
  BarcodeBatchSettings,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

const settings = new BarcodeBatchSettings();

// Only enable the symbologies your app actually needs.
settings.enableSymbologies([
  Symbology.EAN13UPCA,
  Symbology.EAN8,
  Symbology.UPCE,
  Symbology.Code39,
  Symbology.Code128,
]);

// Optional: adjust active symbol counts for variable-length symbologies.
const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];

// SDK ≥7.6 constructor — no context argument.
window.barcodeBatch = new BarcodeBatch(settings);

// Register the mode with the context.
context.setMode(window.barcodeBatch);
```

> **SDK <7.6 fallback**: If targeting earlier SDK versions, the context-less constructor is not available. Instead, create the context first and call `context.setMode(barcodeBatch)` after constructing settings.

### BarcodeBatchSettings Key Members

| Member | Available | Description |
|--------|-----------|-------------|
| `new BarcodeBatchSettings()` | capacitor=7.0 | All symbologies disabled by default. |
| `enableSymbologies(symbologies)` | capacitor=7.0 | Enable multiple symbologies at once. |
| `enableSymbology(symbology, enabled)` | capacitor=7.0 | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | capacitor=7.0 | Get per-symbology settings (e.g. `activeSymbolCounts`). |
| `enabledSymbologies` | capacitor=7.0 | Read-only array of currently enabled symbologies. |
| `setProperty(name, value)` / `getProperty(name)` | capacitor=7.0 | Advanced property access by name. |

### BarcodeBatch Key Members

| Member | Available | Description |
|--------|-----------|-------------|
| `new BarcodeBatch(settings)` | capacitor=7.6 | Constructs a new instance. |
| `BarcodeBatch.createRecommendedCameraSettings()` | capacitor=7.6 | Returns camera settings optimized for BarcodeBatch. |
| `addListener(listener)` / `removeListener(listener)` | capacitor=7.0 | Register/remove a `BarcodeBatchListener`. |
| `applySettings(settings)` | capacitor=7.0 | Update settings at runtime (returns `Promise<void>`). |
| `isEnabled` | capacitor=7.0 | `boolean` — enable/disable without removing from context. |
| `reset()` | capacitor=7.0 | Resets the object tracker (`Promise<void>`). |
| `context` | capacitor=7.0 | Read-only reference to the associated `DataCaptureContext`. |

## Step 4 — Receive Tracked Barcodes via BarcodeBatchListener

`BarcodeBatchListener.didUpdateSession` is called after every frame where the tracked barcode state changes.

```javascript
window.barcodeBatch.addListener({
  // Called on every frame where tracked barcode state changes.
  didUpdateSession: async (barcodeBatch, session, getFrameData) => {
    // All currently tracked barcodes (map from identifier to TrackedBarcode).
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
| `trackedBarcodes` | `{ [key: string]: TrackedBarcode }` | capacitor=7.0 | All currently tracked barcodes. |
| `addedTrackedBarcodes` | `TrackedBarcode[]` | capacitor=7.0 | Barcodes newly tracked this frame. |
| `updatedTrackedBarcodes` | `TrackedBarcode[]` | capacitor=7.0 | Barcodes with updated location this frame. |
| `removedTrackedBarcodes` | `string[]` | capacitor=7.0 | Identifiers of barcodes that were lost. |
| `frameSequenceID` | `number` | capacitor=7.0 | Identifier of the current frame sequence. |
| `reset()` | `Promise<void>` | capacitor=7.0 | Resets the session (call only inside the listener). |

> **Important**: Do not hold references to the session object or its arrays outside the `didUpdateSession` callback — they may be concurrently modified. Copy any data you need.

#### Reacting to lost barcodes with `removedTrackedBarcodes`

`session.removedTrackedBarcodes` is the array of tracking identifiers for barcodes that **left the
frame this frame**. Use it to prune any app-level state you keep keyed by tracking identifier (a
per-barcode map, AR views, list rows, etc.) so it doesn't grow unbounded:

```javascript
// App-level state keyed by tracking identifier.
const trackedState = new Map();

window.barcodeBatch.addListener({
  didUpdateSession: async (barcodeBatch, session) => {
    // Add / update entries for currently tracked barcodes.
    Object.values(session.trackedBarcodes).forEach(trackedBarcode => {
      trackedState.set(trackedBarcode.identifier, trackedBarcode.barcode.data);
    });

    // Remove entries for barcodes that were lost this frame.
    session.removedTrackedBarcodes.forEach(identifier => {
      trackedState.delete(identifier);
    });
  },
});
```

> **Note**: `removedTrackedBarcodes` is an array of identifiers, not `TrackedBarcode` objects — the
> barcode is already gone, so only its `identifier` is reported. On Capacitor the session reports
> these identifiers as strings (`string[]`), while a live `TrackedBarcode.identifier` is a `number`;
> when you key your own map, store and look up with a consistent type. As with every session array,
> consume it inside the callback — do not retain `session` or `removedTrackedBarcodes` after the
> callback returns.

### TrackedBarcode Properties

| Property | Type | Available | Description |
|----------|------|-----------|-------------|
| `barcode` | `Barcode` | capacitor=6.8 | The barcode associated with this track. |
| `identifier` | `number` | capacitor=6.8 | Unique identifier for this track. May be reused after a barcode is lost. |
| `location` | `Quadrilateral` | capacitor=6.8 | Location of the barcode in image-space. Requires MatrixScan AR add-on. |

## Step 5 — Set Up DataCaptureView

`DataCaptureView.forContext(context)` creates the view. Then attach it to a DOM element with `connectToElement`.

```javascript
import { DataCaptureView } from 'scandit-capacitor-datacapture-core';

// Create the view for the context.
window.view = DataCaptureView.forContext(context);

// Connect to a DOM element — the view mirrors its size and position.
window.view.connectToElement(document.getElementById('data-capture-view'));
```

The HTML must contain a container element, sized to fill the camera area:

```html
<div id="data-capture-view" style="width: 100%; height: 100%;"></div>
```

## Step 6 — BarcodeBatchBasicOverlay: Per-Barcode Brushes

`BarcodeBatchBasicOverlay` renders a highlight frame or dot over each tracked barcode. Set a `listener` with `brushForTrackedBarcode` to return different brushes based on symbology or data.

> **Note**: Using `brushForTrackedBarcode` (and `setBrushForTrackedBarcode`) requires the **MatrixScan AR add-on**.

> **Brush fallback semantics**: `brushForTrackedBarcode` must return a `Brush` — returning `null` **hides** that barcode (no highlight). To "keep the default highlight" for barcodes that don't match a custom rule, return either `basicOverlay.brush` (the overlay's current default brush, capacitor=7.0) or a non-null `Brush` you constructed yourself. Use `null`/transparent only when you actually want to hide.

```javascript
import {
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

import { Brush, Color } from 'scandit-capacitor-datacapture-core';

// Brushes for different conditions.
const greenBrush = new Brush(
  Color.fromRGBA(0, 204, 0, 0.3),  // semi-transparent green fill
  Color.fromHex('#00CC00'),          // solid green stroke
  2,
);
const redBrush = new Brush(
  Color.fromRGBA(204, 0, 0, 0.3),
  Color.fromHex('#CC0000'),
  2,
);
// Transparent brush — hides the highlight for this barcode entirely.
const transparentBrush = new Brush(
  Color.fromRGBA(0, 0, 0, 0),
  Color.fromRGBA(0, 0, 0, 0),
  0,
);

// SDK ≥7.6 constructor.
const basicOverlay = new BarcodeBatchBasicOverlay(
  window.barcodeBatch,
  BarcodeBatchBasicOverlayStyle.Frame,
);

// Set a listener to return a brush per tracked barcode.
// Called from the rendering thread whenever a new tracked barcode appears.
basicOverlay.listener = {
  brushForTrackedBarcode: (overlay, trackedBarcode) => {
    const data = trackedBarcode.barcode.data ?? '';

    // Hide barcodes starting with '0' (return null also hides the barcode).
    if (data.startsWith('0')) {
      return transparentBrush;
    }

    // Different colors by symbology.
    if (trackedBarcode.barcode.symbology === Symbology.EAN13UPCA) {
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
| `new BarcodeBatchBasicOverlay(mode, style)` | capacitor=7.6 | Constructs the overlay. |
| `listener` | capacitor=7.0 | Set an `IBarcodeBatchBasicOverlayListener`. Requires MatrixScan AR add-on. |
| `brush` | capacitor=7.0 | Default brush when no listener is set. |
| `setBrushForTrackedBarcode(brush, trackedBarcode)` | capacitor=7.0 | Imperatively set a brush for a specific tracked barcode. Returns `Promise<void>`. Requires AR add-on. |
| `clearTrackedBarcodeBrushes()` | capacitor=7.0 | Clear all custom brushes. Returns `Promise<void>`. |
| `shouldShowScanAreaGuides` | capacitor=7.0 | Debug: show the active scan area. Default `false`. |
| `style` | capacitor=7.0 | The overlay style (`Frame` or `Dot`). |

### BarcodeBatchBasicOverlayStyle Values

| Value | Description |
|-------|-------------|
| `BarcodeBatchBasicOverlayStyle.Frame` | Rectangular frame highlight with appear animation. Default. |
| `BarcodeBatchBasicOverlayStyle.Dot` | Dot highlight with appear animation. |

#### Choosing or switching the overlay style

The style is the **second argument** of the `new BarcodeBatchBasicOverlay(mode, style)` constructor.
There are exactly two values — `BarcodeBatchBasicOverlayStyle.Frame` (rectangular outline, the
default) and `BarcodeBatchBasicOverlayStyle.Dot` (a small dot at the barcode center). To switch
from frames to dots, change only that argument — nothing else about the overlay setup changes:

```javascript
// Dot highlights instead of the default frame.
const basicOverlay = new BarcodeBatchBasicOverlay(
  window.barcodeBatch,
  BarcodeBatchBasicOverlayStyle.Dot,
);
window.view.addOverlay(basicOverlay);
```

> **Note**: The style is fixed at construction. To change it at runtime, remove the existing
> overlay (`view.removeOverlay`) and add a new one with the desired style. Re-applying brushes is
> not needed for a plain style switch.

### IBarcodeBatchBasicOverlayListener Callbacks

| Callback | Description |
|----------|-------------|
| `brushForTrackedBarcode(overlay, trackedBarcode)` | Return a `Brush` (or `null` to hide) for a newly tracked barcode. Called from the rendering thread. Requires MatrixScan AR add-on. |
| `didTapTrackedBarcode(overlay, trackedBarcode)` | Called when the user taps a tracked barcode highlight. Called from the main thread. |

#### Handling taps on a tracked-barcode highlight

Set `didTapTrackedBarcode` on the basic-overlay listener to react when the user taps a highlight
(for example to open a detail view for that code). The callback receives the overlay and the
`TrackedBarcode` that was tapped:

```javascript
basicOverlay.listener = {
  didTapTrackedBarcode: (overlay, trackedBarcode) => {
    console.log('Tapped barcode:', trackedBarcode.barcode.data);
    // e.g. navigate to a detail screen for trackedBarcode.barcode.data
  },
};
```

> **Note**: The `BarcodeBatchBasicOverlay` listener (including `didTapTrackedBarcode` and
> `brushForTrackedBarcode`) requires the **MatrixScan AR add-on**. `didTapTrackedBarcode` is the
> basic-overlay tap callback; the advanced overlay uses `didTapViewForTrackedBarcode` instead
> (see Step 7).

## Step 7 — BarcodeBatchAdvancedOverlay: AR Annotations

`BarcodeBatchAdvancedOverlay` lets you anchor a custom view to each tracked barcode. On Capacitor, the view must be a **serialized `TrackedBarcodeView`** constructed from a DOM element via `TrackedBarcodeView.withHTMLElement`.

> **Important**: Using `BarcodeBatchAdvancedOverlay` requires the **MatrixScan AR add-on**.

The anchor and offset are set via the overlay listener, which positions each bubble relative to its tracked barcode.

```javascript
import {
  BarcodeBatchAdvancedOverlay,
  TrackedBarcodeView,
} from 'scandit-capacitor-datacapture-barcode';

import {
  Anchor,
  MeasureUnit,
  NumberWithUnit,
  PointWithUnit,
} from 'scandit-capacitor-datacapture-core';

// SDK ≥7.6 constructor.
window.advancedOverlay = new BarcodeBatchAdvancedOverlay(window.barcodeBatch);

window.advancedOverlay.listener = {
  // Position the bubble above the center of the barcode.
  anchorForTrackedBarcode: (overlay, trackedBarcode) => {
    return Anchor.TopCenter;
  },

  // Shift the bubble up by 100% of its own height so it sits above the barcode.
  offsetForTrackedBarcode: (overlay, trackedBarcode) => {
    return new PointWithUnit(
      new NumberWithUnit(0, MeasureUnit.Fraction),
      new NumberWithUnit(-1, MeasureUnit.Fraction),
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

In `BarcodeBatchListener.didUpdateSession`, call `overlay.setViewForTrackedBarcode` for each barcode you want an AR bubble on. The view must be a `TrackedBarcodeView` built from a DOM element.

```javascript
window.barcodeBatch.addListener({
  didUpdateSession: async (barcodeBatch, session) => {
    // Remove views for lost barcodes (the overlay handles cleanup automatically,
    // but explicitly nulling them prevents stale data in your own state).
    session.removedTrackedBarcodes.forEach(identifier => {
      // Optional: clear any app-level state for this identifier.
    });

    // Set or update the AR view for each currently tracked barcode.
    Object.values(session.trackedBarcodes).forEach(trackedBarcode => {
      const barcodeData = trackedBarcode.barcode.data;
      if (!barcodeData) return;

      // Build the DOM element for the bubble.
      const bubbleElement = createBubble(barcodeData);

      // Wrap the DOM element in a TrackedBarcodeView.
      // The scale option compensates for device pixel ratio for crisp rendering.
      const bubble = TrackedBarcodeView.withHTMLElement(
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

> **Pixel density note**: Scale down the bubble by `1 / window.devicePixelRatio` in the `TrackedBarcodeView.withHTMLElement` options to get crisp rendering on high-DPI screens. The DOM element itself should be constructed at physical pixels (`width * devicePixelRatio`).

### Advanced Overlay Key Members

| Member | Available | Description |
|--------|-----------|-------------|
| `new BarcodeBatchAdvancedOverlay(mode)` | capacitor=7.6 | Constructs the overlay. |
| `listener` | capacitor=7.0 | Set an `IBarcodeBatchAdvancedOverlayListener`. |
| `setViewForTrackedBarcode(view, trackedBarcode)` | capacitor=7.0 | Set the `TrackedBarcodeView` for a tracked barcode. Pass `null` to remove. Returns `Promise<void>`. |
| `setAnchorForTrackedBarcode(anchor, trackedBarcode)` | capacitor=7.0 | Override the anchor imperatively. Returns `Promise<void>`. |
| `setOffsetForTrackedBarcode(offset, trackedBarcode)` | capacitor=7.0 | Override the offset imperatively. Returns `Promise<void>`. |
| `clearTrackedBarcodeViews()` | capacitor=7.0 | Remove all AR views. Returns `Promise<void>`. |
| `shouldShowScanAreaGuides` | capacitor=7.0 | Debug: show the active scan area. Default `false`. |

### IBarcodeBatchAdvancedOverlayListener Callbacks

| Callback | Description |
|----------|-------------|
| `viewForTrackedBarcode(overlay, trackedBarcode)` | Return a `TrackedBarcodeView` (or `null`) for a newly tracked barcode. Ignored if `setViewForTrackedBarcode` was already called for this barcode. |
| `anchorForTrackedBarcode(overlay, trackedBarcode)` | Return an `Anchor` for the view. |
| `offsetForTrackedBarcode(overlay, trackedBarcode)` | Return a `PointWithUnit` offset. |
| `didTapViewForTrackedBarcode(overlay, trackedBarcode)` | Called when the user taps the AR view. |

#### Handling taps on an AR bubble

To react when the user taps a bubble rendered by the advanced overlay, add
`didTapViewForTrackedBarcode` to the advanced-overlay listener. The callback receives the overlay
and the tapped `TrackedBarcode`:

```javascript
window.advancedOverlay.listener = {
  anchorForTrackedBarcode: (overlay, trackedBarcode) => Anchor.TopCenter,
  offsetForTrackedBarcode: (overlay, trackedBarcode) =>
    new PointWithUnit(
      new NumberWithUnit(0, MeasureUnit.Fraction),
      new NumberWithUnit(-1, MeasureUnit.Fraction),
    ),

  // Tap callback for the advanced (AR) overlay.
  didTapViewForTrackedBarcode: (overlay, trackedBarcode) => {
    console.log('Tapped AR bubble:', trackedBarcode.barcode.data);
    // e.g. open a detail view for trackedBarcode.barcode.data
  },
};
```

> **Important**: For the advanced overlay use `didTapViewForTrackedBarcode` — **not**
> `didTapTrackedBarcode` (that callback belongs to the `BarcodeBatchBasicOverlay` listener, Step 6).
> Like the rest of `BarcodeBatchAdvancedOverlay`, it requires the **MatrixScan AR add-on**.

### TrackedBarcodeView

`TrackedBarcodeView` is the serialized view type used by Capacitor's advanced overlay. It wraps a DOM element for transmission to the native layer.

| Member | Available | Description |
|--------|-----------|-------------|
| `TrackedBarcodeView.withHTMLElement(element, options?)` | capacitor=7.0 | Create from a DOM element. `options.scale` adjusts for device pixel ratio. |

## Step 8 — Start Camera and Enable Mode

```javascript
// Switch camera on to start streaming frames.
await window.camera.switchToDesiredState(FrameSourceState.On);

// Enable the mode to start tracking.
window.barcodeBatch.isEnabled = true;
```

## Step 8b — Feedback (Sound / Vibration)

Unlike `BarcodeCapture` (single-scan), **`BarcodeBatch` has no built-in feedback** — there is no
`barcodeBatch.feedback` property, and the SDK does **not** automatically beep or vibrate when a
barcode is tracked. MatrixScan tracks many barcodes continuously, so emitting feedback per frame
would be constant noise. If you want a sound/vibration cue, you must construct a `Feedback` object
yourself and call `emit()` from your listener, deciding when it makes sense (typically once per
newly tracked barcode).

`Feedback`, `Sound`, and `Vibration` come from `scandit-capacitor-datacapture-core`:

```javascript
import {
  Feedback,
  Sound,
  Vibration,
} from 'scandit-capacitor-datacapture-core';

// Construct ONCE — outside the listener — so it isn't rebuilt on every frame.
// new Feedback(vibration, sound): either argument may be null.
const successFeedback = new Feedback(
  Vibration.defaultVibration,
  Sound.defaultSound,
);
// Alternatively: const successFeedback = Feedback.defaultFeedback;

window.barcodeBatch.addListener({
  didUpdateSession: async (barcodeBatch, session) => {
    // Emit only for barcodes that appeared this frame — not for every tracked
    // barcode on every frame.
    if (session.addedTrackedBarcodes.length > 0) {
      successFeedback.emit();
    }
  },
});
```

### Feedback Key Members

| Member | Available | Description |
|--------|-----------|-------------|
| `new Feedback(vibration, sound)` | capacitor=6.8 | Construct with a `Vibration?` and a `Sound?` (either may be `null`). |
| `Feedback.defaultFeedback` | capacitor=6.8 | A ready-made feedback with the default sound and vibration. |
| `feedback.emit()` | capacitor=6.8 | Emits the configured sound and/or vibration. Subject to the device ring mode / volume. |
| `Vibration.defaultVibration` | capacitor=6.8 | The default system vibration. |
| `Sound.defaultSound` | capacitor=6.8 | The default beep. Pass a custom `Sound` for a different tone. |

> **Note**: `emit()` is influenced by the device's ring mode and volume settings — a correctly
> configured `Feedback` may still play nothing if the device is muted. On some browsers/web targets
> vibration is unsupported and only the sound (if any) is played.

## Step 9 — Lifecycle: Enable/Disable and Cleanup

### Enable/disable without removing the mode

```javascript
// Pause scanning (e.g. app goes to background or user navigates away).
window.barcodeBatch.isEnabled = false;
await window.camera.switchToDesiredState(FrameSourceState.Off);

// Resume scanning (e.g. app returns to foreground).
window.barcodeBatch.isEnabled = true;
await window.camera.switchToDesiredState(FrameSourceState.On);
```

### Handle Capacitor app lifecycle events

```javascript
import { App } from '@capacitor/app';

App.addListener('appStateChange', async ({ isActive }) => {
  if (!isActive) {
    window.barcodeBatch.isEnabled = false;
    await window.camera.switchToDesiredState(FrameSourceState.Off);
  } else {
    window.barcodeBatch.isEnabled = true;
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

> **Note**: Call `view.detachFromElement()` when the scanning screen is torn down to release resources. This is the Capacitor equivalent of removing the native view.

## Step 10 — Camera Permissions

### iOS

Add to `ios/App/App/Info.plist`:

```xml
<key>NSCameraUsageDescription</key>
<string>We need camera access to scan barcodes</string>
```

### Android

The camera permission (`android.permission.CAMERA`) is declared automatically by the Scandit plugin in its manifest. No manual step is required for the manifest entry. The runtime permission request is handled by the operating system when the camera is first activated.

## Step 11 — Complete Example

```javascript
import {
  Anchor,
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
  MeasureUnit,
  NumberWithUnit,
  PointWithUnit,
  ScanditCaptureCorePlugin,
  Brush,
  Color,
} from 'scandit-capacitor-datacapture-core';

import {
  BarcodeBatch,
  BarcodeBatchAdvancedOverlay,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchSettings,
  Symbology,
  TrackedBarcodeView,
} from 'scandit-capacitor-datacapture-barcode';

async function runApp() {
  // 1. Initialize plugins — must be first.
  await ScanditCaptureCorePlugin.initializePlugins();

  // 2. Create context.
  const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  // 3. Set up camera.
  const cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
  window.camera = Camera.withSettings(cameraSettings);
  context.setFrameSource(window.camera);

  // 4. Configure BarcodeBatchSettings.
  const settings = new BarcodeBatchSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.EAN8,
    Symbology.Code128,
  ]);

  // 5. Create BarcodeBatch mode and register with context.
  window.barcodeBatch = new BarcodeBatch(settings);
  context.setMode(window.barcodeBatch);

  // 6. Register the session listener.
  window.barcodeBatch.addListener({
    didUpdateSession: async (barcodeBatch, session) => {
      Object.values(session.trackedBarcodes).forEach(trackedBarcode => {
        console.log(`Tracking: ${trackedBarcode.barcode.data}`);
      });
    },
  });

  // 7. Create and connect the DataCaptureView.
  window.view = DataCaptureView.forContext(context);
  window.view.connectToElement(document.getElementById('data-capture-view'));

  // 8. Add BasicOverlay with per-barcode brushes (MatrixScan AR add-on required).
  const basicOverlay = new BarcodeBatchBasicOverlay(
    window.barcodeBatch,
    BarcodeBatchBasicOverlayStyle.Frame,
  );
  basicOverlay.listener = {
    brushForTrackedBarcode: (overlay, trackedBarcode) => {
      if (trackedBarcode.barcode.symbology === Symbology.EAN13UPCA) {
        return new Brush(Color.fromRGBA(0, 204, 0, 0.3), Color.fromHex('#00CC00'), 2);
      }
      return new Brush(Color.fromRGBA(0, 100, 255, 0.3), Color.fromHex('#0064FF'), 2);
    },
  };
  window.view.addOverlay(basicOverlay);

  // 9. Start camera and enable mode.
  await window.camera.switchToDesiredState(FrameSourceState.On);
  window.barcodeBatch.isEnabled = true;
}

async function uninitialize() {
  if (window.camera) {
    await window.camera.switchToDesiredState(FrameSourceState.Off);
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

window.addEventListener('load', () => {
  runApp();
});
```

## Key Rules

1. **Initialize plugins first** — `await ScanditCaptureCorePlugin.initializePlugins()` must be called before any other Scandit API. Capacitor-specific requirement.
2. **`context.setMode(barcodeBatch)`** — This is the Capacitor method to register the mode with the context. Replaces any previously active mode.
3. **`DataCaptureView.forContext(context)` + `connectToElement`** — The Capacitor view pattern. Connect to a DOM element; the view mirrors its size and position.
4. **Modern constructors ≥7.6** — `new BarcodeBatch(settings)`, `new BarcodeBatchBasicOverlay(mode, style)`, `new BarcodeBatchAdvancedOverlay(mode)`, and `BarcodeBatch.createRecommendedCameraSettings()` all require capacitor=7.6.
5. **Add overlays to the view** — `view.addOverlay(overlay)` must be called after creating both the view and the overlay.
6. **AR add-on required** — `brushForTrackedBarcode`, `setBrushForTrackedBarcode`, and all `BarcodeBatchAdvancedOverlay` APIs require the MatrixScan AR add-on license.
7. **AdvancedOverlay uses `TrackedBarcodeView`** — On Capacitor, views passed to `setViewForTrackedBarcode` must be `TrackedBarcodeView` instances created via `TrackedBarcodeView.withHTMLElement(domElement, options)`. This is NOT the same as React Native (which uses `BarcodeBatchAdvancedOverlayView` subclasses).
8. **Prevent garbage collection** — Store `barcodeBatch`, `view`, `camera`, and overlays on `window` or at module scope.
9. **Camera permissions** — iOS: `NSCameraUsageDescription` in `Info.plist`. Android: handled automatically by the plugin.
10. **Cap sync** — Run `npx cap sync` after installing or updating Scandit packages.
11. **Session data safety** — Do not hold references to `session`, `session.trackedBarcodes`, `session.addedTrackedBarcodes`, etc. outside the `didUpdateSession` callback. Copy values you need.
12. **Teardown** — Call `view.detachFromElement()` and `camera.switchToDesiredState(FrameSourceState.Off)` when leaving the scanning screen.

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Nothing scans when the page loads | `ScanditCaptureCorePlugin.initializePlugins()` was not called or not awaited before other Scandit calls. |
| Camera not streaming | `camera.switchToDesiredState(FrameSourceState.On)` was not called, or `context.setFrameSource(camera)` was skipped. |
| Overlays not visible | `view.addOverlay(overlay)` was not called after creating the overlay. |
| Brushes not showing | `brushForTrackedBarcode` requires the MatrixScan AR add-on. Verify the license. |
| AR bubbles not rendering | `TrackedBarcodeView.withHTMLElement` not used — a plain DOM element was passed directly instead. |
| Bubbles blurry on high-DPI screens | `scale: 1 / window.devicePixelRatio` was not set in `TrackedBarcodeView.withHTMLElement` options. |
| `new BarcodeBatch(settings)` not found | Requires capacitor=7.6. |
| `BarcodeBatch.createRecommendedCameraSettings()` not found | Requires capacitor=7.6. |
| Session data accessed outside callback | Copy `addedTrackedBarcodes`, `updatedTrackedBarcodes`, etc. before the callback returns. |
| Native/web version mismatch at runtime | Run `npx cap sync` after installing or updating packages. |
