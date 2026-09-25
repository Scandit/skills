# MatrixScan Batch React Native Integration Guide

MatrixScan Batch (API name: `BarcodeBatch*`) is a multi-barcode tracking mode that continuously tracks all barcodes visible in the camera feed simultaneously, reporting additions, updates, and removals on every frame. In React Native it renders through a `<DataCaptureView>` with one or more overlays attached — `BarcodeBatchBasicOverlay` for simple per-barcode highlights, and `BarcodeBatchAdvancedOverlay` for fully custom AR bubble views.

> **Language note**: Examples below use TypeScript (`.tsx`) because it is the default for React Native templates. For plain JavaScript projects, drop the type annotations and keep the same imports and structure.

> **TrackedObject (RN 8.2+)**: In SDK 8.2+, a `TrackedObject` base class was introduced that `TrackedBarcode` extends. No recipe is needed for this — the `TrackedBarcode` API you use day-to-day is unchanged.

## Prerequisites

- Scandit React Native packages installed:
  - `scandit-react-native-datacapture-core`
  - `scandit-react-native-datacapture-barcode`
- After installing, run `npx pod-install` (or `cd ios && pod install`) for iOS. Android auto-links via Gradle — no manual step.
- Minimum SDK version for BarcodeBatch on React Native: **6.5**. The modern constructors (`new BarcodeBatch(settings)`, `new BarcodeBatchBasicOverlay(mode, style)`, `new BarcodeBatchAdvancedOverlay(mode)`, `BarcodeBatch.createRecommendedCameraSettings()`) require **7.6+**.
- React Native `>=0.70`. The New Architecture (Fabric / TurboModules) is supported.
- **New Architecture caveat (iOS, RN ≥ 0.79)**: When using `BarcodeBatchAdvancedOverlay` with the new React Native architecture on iOS, your `AppDelegate` must implement the `ScanditReactNativeFactoryContainer` protocol (available in the `scandit-react-native-datacapture-core` module). If you followed the [React Native 0.79 upgrade guide](https://raw.githubusercontent.com/react-native-community/rn-diff-purge/release/0.79.2/RnDiffApp/ios/RnDiffApp/AppDelegate.swift) you should already have the required property.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/<App>/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request at runtime via `PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.CAMERA)` before rendering the scan screen.

## Integration flow

Ask the user which barcode symbologies they need to scan. Only enable the symbologies actually required — each extra symbology adds processing time.

Once the user responds, ask them which file they'd like to integrate MatrixScan Batch into (typically the scan screen component, e.g. `App.tsx`, `ScanPage.tsx`). Then write the integration code directly into that file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Install packages: `npm install scandit-react-native-datacapture-core scandit-react-native-datacapture-barcode`
2. Run `npx pod-install` (iOS). Android auto-links.
3. Add `NSCameraUsageDescription` to `ios/<App>/Info.plist`.
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key from https://ssl.scandit.com.
5. If Metro was running, restart it with `--reset-cache` so the new package is picked up.

## Step 1 — Initialize DataCaptureContext (singleton module)

Create a small module that initializes the context exactly once at import time:

```typescript
// CaptureContext.ts
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

export default DataCaptureContext.sharedInstance;
```

- `DataCaptureContext.initialize(licenseKey)` is the v8 API. It is idempotent per process — call it once.
- `DataCaptureContext.sharedInstance` is the singleton accessor used everywhere else.
- Do **not** create additional `DataCaptureContext` instances.

## Step 2 — Configure BarcodeBatchSettings and construct BarcodeBatch

```typescript
import {
  BarcodeBatch,
  BarcodeBatchSettings,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';
import dataCaptureContext from './CaptureContext';

function setupBarcodeBatch(): BarcodeBatch {
  const settings = new BarcodeBatchSettings();

  // Only enable the symbologies your app actually needs.
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.EAN8,
    Symbology.UPCE,
    Symbology.Code39,
    Symbology.Code128,
  ]);

  // Optional: adjust active symbol counts for variable-length symbologies
  const code39Settings = settings.settingsForSymbology(Symbology.Code39);
  code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];

  // Construct the mode (RN 7.6+ constructor)
  const barcodeBatch = new BarcodeBatch(settings);

  // Register the mode with the context
  dataCaptureContext.setMode(barcodeBatch);

  return barcodeBatch;
}
```

### BarcodeBatchSettings Members

| Member | Description |
|--------|-------------|
| `new BarcodeBatchSettings()` | Creates a new settings instance. All symbologies disabled by default. |
| `enableSymbologies(symbologies)` | Enable multiple symbologies at once. |
| `enableSymbology(symbology, enabled)` | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | Get per-symbology settings (e.g. `activeSymbolCounts`). |
| `enabledSymbologies` | Read-only array of currently enabled symbologies. |
| `setProperty(name, value)` / `getProperty(name)` | Advanced property access by name. |

### BarcodeBatch Members (RN-relevant)

| Member | Available | Description |
|--------|-----------|-------------|
| `new BarcodeBatch(settings)` | react-native=7.6 | Constructs a new instance. |
| `addListener(listener)` / `removeListener(listener)` | react-native=7.0 | Register/remove a `BarcodeBatchListener`. |
| `applySettings(settings)` | react-native=7.0 | Update settings at runtime (returns `Promise<void>`). |
| `isEnabled` | react-native=7.0 | `boolean` — enable/disable without removing from context. |
| `reset()` | react-native=7.0 | Resets the object tracker (`Promise<void>`). |
| `BarcodeBatch.createRecommendedCameraSettings()` | react-native=7.6 | Returns camera settings optimized for BarcodeBatch. |

## Step 3 — Receive tracked barcodes via BarcodeBatchListener

`BarcodeBatchListener.didUpdateSession` is called after every frame where the tracked barcode state changes. The session provides the full current state plus the per-frame deltas.

```typescript
import {
  BarcodeBatch,
  BarcodeBatchSession,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';

const listener = {
  didUpdateSession: async (
    _barcodeBatch: BarcodeBatch,
    session: BarcodeBatchSession,
    _getFrameData: () => Promise<any>,
  ) => {
    // All currently tracked barcodes (snapshot for this frame)
    const allTracked = Object.values(session.trackedBarcodes);

    // Newly appeared barcodes this frame
    const added: TrackedBarcode[] = session.addedTrackedBarcodes;

    // Barcodes whose position changed this frame
    const updated: TrackedBarcode[] = session.updatedTrackedBarcodes;

    // Identifiers of barcodes that left the frame
    const removedIds: string[] = session.removedTrackedBarcodes;

    allTracked.forEach(trackedBarcode => {
      const { data, symbology } = trackedBarcode.barcode;
      console.log(`Tracking [${symbology}]: ${data}`);
    });

    // IMPORTANT: do not hold a reference to session or its arrays outside this callback.
    // Copy the data you need before the callback returns.
  },
};

barcodeBatch.addListener(listener);
```

### BarcodeBatchSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `trackedBarcodes` | `{ [key: string]: TrackedBarcode }` | All currently tracked barcodes (map from identifier to TrackedBarcode). |
| `addedTrackedBarcodes` | `TrackedBarcode[]` | Barcodes newly tracked this frame. |
| `updatedTrackedBarcodes` | `TrackedBarcode[]` | Barcodes with updated location this frame. |
| `removedTrackedBarcodes` | `string[]` | Identifiers of barcodes that were lost. |
| `frameSequenceID` | `number` | Identifier of the current frame sequence. |
| `reset()` | `Promise<void>` | Resets the session (call only inside the listener). |

> **Important**: Do not hold references to the session object or its arrays outside the `didUpdateSession` callback — they may be concurrently modified. Copy any data you need.

### TrackedBarcode Properties

| Property | Type | Description |
|----------|------|-------------|
| `barcode` | `Barcode` | The barcode associated with this track. |
| `identifier` | `number` | Unique identifier for this track. Reused after the barcode is lost. |
| `location` | `Quadrilateral` | Location of the barcode in image-space (requires MatrixScan AR add-on). |

### Reading data off a tracked barcode

Each `TrackedBarcode` exposes the per-track fields you need to build your own list, dedupe, or render labels. Read them inside `didUpdateSession` (the only place the session is safe to touch) and copy out what you keep:

```typescript
Object.values(session.trackedBarcodes).forEach((trackedBarcode: TrackedBarcode) => {
  // Stable identifier for this track. Use it as a dedupe key — the same physical
  // barcode keeps the same identifier across frames. (Reused after the track is lost.)
  const id: number = trackedBarcode.identifier;

  // The decoded barcode. `data` is the string payload; it is `string | null`.
  const data: string | null = trackedBarcode.barcode.data;
  const symbology: Symbology = trackedBarcode.barcode.symbology;

  // Corner positions of the barcode. `location` is a Quadrilateral with
  // topLeft / topRight / bottomRight / bottomLeft Points.
  const location: Quadrilateral = trackedBarcode.location;
  console.log(`#${id} [${symbology}] ${data}`, location.topLeft, location.bottomRight);
});
```

- `identifier` is the right dedupe key. Do **not** dedupe on `barcode.data` if two different physical labels can share a value — use the track id.
- `barcode.data` is `string | null`. Guard for `null` before using it (a code can be tracked before it is fully decoded).
- `location` is in **image-space** (pixel coordinates of the camera frame) and **requires the MatrixScan AR add-on** — without the add-on it returns a quadrilateral with all corners at `(0, 0)`. To position your own UI over the barcode, convert the corners to view coordinates with the `DataCaptureView` method `view.viewQuadrilateralForFrameQuadrilateral(location)` (returns `Promise<Quadrilateral>`); do not assume the raw `location` corners are screen pixels.

## Step 4 — BarcodeBatchBasicOverlay: per-barcode brushes

`BarcodeBatchBasicOverlay` renders a highlight frame or dot over each tracked barcode. Set a `listener` with `brushForTrackedBarcode` to return different brushes based on the tracked barcode's data or symbology.

> **Note**: Using `brushForTrackedBarcode` (and `setBrushForTrackedBarcode`) requires the **MatrixScan AR add-on**.

```typescript
import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';
import { Brush, Color } from 'scandit-react-native-datacapture-core';

// Brushes for different conditions
const greenBrush = new Brush(Color.fromRGBA(0, 255, 0, 0.3), Color.fromHex('#00FF00'), 2);
const redBrush = new Brush(Color.fromRGBA(255, 0, 0, 0.3), Color.fromHex('#FF0000'), 2);
const transparentBrush = new Brush(Color.fromRGBA(0, 0, 0, 0), Color.fromRGBA(0, 0, 0, 0), 0);

function setupBasicOverlay(barcodeBatch: BarcodeBatch): BarcodeBatchBasicOverlay {
  const overlay = new BarcodeBatchBasicOverlay(barcodeBatch, BarcodeBatchBasicOverlayStyle.Frame);

  // Set a listener to return a brush per tracked barcode.
  // Called from the rendering thread whenever a new tracked barcode appears.
  overlay.listener = {
    brushForTrackedBarcode: (_overlay, trackedBarcode: TrackedBarcode) => {
      const data = trackedBarcode.barcode.data ?? '';

      // Example: hide barcodes that start with '0' (return transparent brush)
      if (data.startsWith('0')) {
        return transparentBrush;  // null also hides the barcode
      }

      // Example: different colors by symbology
      if (trackedBarcode.barcode.symbology === Symbology.EAN13UPCA) {
        return greenBrush;
      }

      return redBrush;
    },

    didTapTrackedBarcode: (_overlay, trackedBarcode: TrackedBarcode) => {
      console.log('Tapped:', trackedBarcode.barcode.data);
    },
  };

  return overlay;
}
```

The overlay must be added to the `DataCaptureView` via `view.addOverlay(overlay)` in the view's `ref` callback (see Step 6).

#### Handling taps on a highlight (`didTapTrackedBarcode`)

The basic overlay listener has a second callback, `didTapTrackedBarcode`, called on the main thread when the user taps a tracked barcode's highlight. Use it to react to a tap — e.g. show the barcode's data or open a detail screen:

```typescript
overlay.listener = {
  brushForTrackedBarcode: (_overlay, _trackedBarcode: TrackedBarcode) => greenBrush,

  // Called from the main thread when a highlight is tapped.
  didTapTrackedBarcode: (_overlay, trackedBarcode: TrackedBarcode) => {
    console.log('Tapped highlight for', trackedBarcode.barcode.data);
    // e.g. navigation.navigate('Detail', { code: trackedBarcode.barcode.data });
  },
};
```

> **Note**: `didTapTrackedBarcode` requires the **MatrixScan AR add-on** (same as the rest of `IBarcodeBatchBasicOverlayListener`). A barcode whose `brushForTrackedBarcode` returned `null` draws no highlight and therefore **cannot be tapped** — the tap callback will not fire for it.

### BarcodeBatchBasicOverlay Members

| Member | Available | Description |
|--------|-----------|-------------|
| `new BarcodeBatchBasicOverlay(mode, style)` | react-native=7.6 | Constructs the overlay. |
| `listener` | react-native=7.0 | Set an `IBarcodeBatchBasicOverlayListener`. |
| `brush` | react-native=7.0 | Default brush for all tracked barcodes when no listener is set. |
| `setBrushForTrackedBarcode(brush, trackedBarcode)` | react-native=7.0 | Imperatively set the brush for a specific tracked barcode. Returns `Promise<void>`. |
| `clearTrackedBarcodeBrushes()` | react-native=7.0 | Clear all custom brushes. Returns `Promise<void>`. |
| `shouldShowScanAreaGuides` | react-native=7.0 | Debug: show the active scan area. Default `false`. |
| `style` | react-native=7.0 | The overlay style (`Frame` or `Dot`). |

### BarcodeBatchBasicOverlayStyle values

| Value | Description |
|-------|-------------|
| `BarcodeBatchBasicOverlayStyle.Frame` | Rectangular frame highlight with appear animation. Default. |
| `BarcodeBatchBasicOverlayStyle.Dot` | Dot highlight with appear animation. |

### IBarcodeBatchBasicOverlayListener callbacks

| Callback | Description |
|----------|-------------|
| `brushForTrackedBarcode(overlay, trackedBarcode)` | Return a `Brush` (or `null` to hide) for a newly tracked barcode. Called from the rendering thread. |
| `didTapTrackedBarcode(overlay, trackedBarcode)` | Called when the user taps a tracked barcode highlight. Called from the main thread. |

## Step 5 — BarcodeBatchAdvancedOverlay: AR annotations

`BarcodeBatchAdvancedOverlay` lets you anchor a custom React Native view to each tracked barcode. The view must be a subclass of `BarcodeBatchAdvancedOverlayView` and must be registered with `AppRegistry`.

> **Important**: Using `BarcodeBatchAdvancedOverlay` requires the **MatrixScan AR add-on**.

> **New Architecture (iOS, RN ≥ 0.79)**: Your `AppDelegate` must implement the `ScanditReactNativeFactoryContainer` protocol. See the prerequisites section.

### 5a — Define the BarcodeBatchAdvancedOverlayView subclass

```tsx
// ARBubble.tsx
import React from 'react';
import { Text, View, StyleSheet } from 'react-native';
import { BarcodeBatchAdvancedOverlayView } from 'scandit-react-native-datacapture-barcode';

interface ARBubbleProps {
  barcodeData: string;
  label?: string;
}

// Must extend BarcodeBatchAdvancedOverlayView.
// Must have a static moduleName used for AppRegistry.registerComponent.
export class ARBubble extends BarcodeBatchAdvancedOverlayView {
  render() {
    const { barcodeData, label } = this.props as ARBubbleProps;

    return (
      <View style={styles.bubble}>
        <Text style={styles.label}>{label ?? barcodeData}</Text>
      </View>
    );
  }
}

const styles = StyleSheet.create({
  bubble: {
    backgroundColor: '#2196F3',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    minWidth: 80,
    alignItems: 'center',
  },
  label: {
    color: '#FFFFFF',
    fontWeight: 'bold',
    fontSize: 13,
  },
});
```

### 5b — Register the component in index.js

The component must be registered before use:

```javascript
// index.js
import { AppRegistry } from 'react-native';
import App from './app/App';
import { ARBubble } from './app/ARBubble';
import { name as appName } from './app.json';

AppRegistry.registerComponent(appName, () => App);
AppRegistry.registerComponent(ARBubble.moduleName, () => ARBubble);
```

> **Important**: `ARBubble.moduleName` is the `ModuleName` property inherited from `BarcodeBatchAdvancedOverlayView`. Do not hardcode a string — always use `MyView.moduleName`.

### 5c — Set up the advanced overlay

```typescript
import {
  BarcodeBatch,
  BarcodeBatchAdvancedOverlay,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';
import {
  Anchor,
  MeasureUnit,
  NumberWithUnit,
  PointWithUnit,
} from 'scandit-react-native-datacapture-core';
import { ARBubble } from './ARBubble';

function setupAdvancedOverlay(barcodeBatch: BarcodeBatch): BarcodeBatchAdvancedOverlay {
  const overlay = new BarcodeBatchAdvancedOverlay(barcodeBatch);

  // Set listener for anchor and offset (called per new tracked barcode)
  overlay.listener = {
    // Position the bubble above the center of the barcode
    anchorForTrackedBarcode: (_overlay, _trackedBarcode) => Anchor.TopCenter,

    // Shift the bubble up by 100% of its own height so it sits above the barcode
    offsetForTrackedBarcode: (_overlay, _trackedBarcode) =>
      new PointWithUnit(
        new NumberWithUnit(0, MeasureUnit.Fraction),
        new NumberWithUnit(-1, MeasureUnit.Fraction),
      ),
  };

  return overlay;
}
```

### 5d — Set the view for each tracked barcode

In `BarcodeBatchListener.didUpdateSession`, call `overlay.setViewForTrackedBarcode` for each relevant tracked barcode:

```typescript
const advancedOverlayRef = useRef<BarcodeBatchAdvancedOverlay>(null!);

const barcodeBatchListenerRef = useRef({
  didUpdateSession: async (
    _barcodeBatch: BarcodeBatch,
    session: BarcodeBatchSession,
    _getFrameData: () => Promise<any>,
  ) => {
    // Remove views for lost barcodes
    session.removedTrackedBarcodes.forEach(identifier => {
      // no explicit removal needed — the overlay handles this automatically
    });

    // Set or update the view for each tracked barcode
    Object.values(session.trackedBarcodes).forEach(trackedBarcode => {
      const barcodeData = trackedBarcode.barcode.data;
      if (!barcodeData) return;

      // Construct the ARBubble view with props for this barcode
      const bubble = new ARBubble({ barcodeData, label: `SKU: ${barcodeData}` });

      advancedOverlayRef.current
        ?.setViewForTrackedBarcode(bubble, trackedBarcode)
        .catch(console.warn);
    });
  },
});
```

> The view passed to `setViewForTrackedBarcode` must be a `BarcodeBatchAdvancedOverlayView` subclass instance. Passing a plain React element is not supported on React Native.

### 5e — Handling taps on an AR view (`didTapViewForTrackedBarcode`)

The advanced overlay listener exposes `didTapViewForTrackedBarcode` — the advanced-overlay equivalent of the basic overlay's `didTapTrackedBarcode`. It is called when the user taps the AR view anchored to a tracked barcode. Add it to the same `overlay.listener` object that carries `anchorForTrackedBarcode` and `offsetForTrackedBarcode`:

```typescript
overlay.listener = {
  anchorForTrackedBarcode: (_overlay, _trackedBarcode) => Anchor.TopCenter,
  offsetForTrackedBarcode: (_overlay, _trackedBarcode) =>
    new PointWithUnit(
      new NumberWithUnit(0, MeasureUnit.Fraction),
      new NumberWithUnit(-1, MeasureUnit.Fraction),
    ),

  // Called when the AR view for a tracked barcode is tapped.
  didTapViewForTrackedBarcode: (_overlay, trackedBarcode: TrackedBarcode) => {
    console.log('Tapped AR bubble for', trackedBarcode.barcode.data, trackedBarcode.identifier);
    // e.g. navigation.navigate('Detail', { code: trackedBarcode.barcode.data });
  },
};
```

> **Note**: `didTapViewForTrackedBarcode` requires the **MatrixScan AR add-on**. Use it for the custom AR views; for the simple frame/dot highlights use the basic overlay's `didTapTrackedBarcode` instead (see Step 4).

### Advanced Overlay Members

| Member | Available | Description |
|--------|-----------|-------------|
| `new BarcodeBatchAdvancedOverlay(mode)` | react-native=7.6 | Constructs the overlay. |
| `listener` | react-native=7.0 | Set an `IBarcodeBatchAdvancedOverlayListener`. |
| `setViewForTrackedBarcode(view, trackedBarcode)` | react-native=7.0 | Set the view for a tracked barcode. `view` must be a `BarcodeBatchAdvancedOverlayView` instance. Returns `Promise<void>`. |
| `setAnchorForTrackedBarcode(anchor, trackedBarcode)` | react-native=7.0 | Override the anchor imperatively. Returns `Promise<void>`. |
| `setOffsetForTrackedBarcode(offset, trackedBarcode)` | react-native=7.0 | Override the offset imperatively. Returns `Promise<void>`. |
| `clearTrackedBarcodeViews()` | react-native=7.0 | Remove all AR views. Returns `Promise<void>`. |
| `updateSizeOfTrackedBarcodeView(identifier, width, height)` | react-native=7.4 | Resize an existing view. |
| `shouldShowScanAreaGuides` | react-native=7.0 | Debug: show the active scan area. Default `false`. |

### IBarcodeBatchAdvancedOverlayListener callbacks

| Callback | Description |
|----------|-------------|
| `viewForTrackedBarcode(overlay, trackedBarcode)` | Return a `BarcodeBatchAdvancedOverlayView` instance (or `null`) for a newly tracked barcode. Called from the main thread. Ignored if `setViewForTrackedBarcode` was already called for this barcode. |
| `anchorForTrackedBarcode(overlay, trackedBarcode)` | Return an `Anchor` for the view. Called after `viewForTrackedBarcode`. |
| `offsetForTrackedBarcode(overlay, trackedBarcode)` | Return a `PointWithUnit` offset. Called after `anchorForTrackedBarcode`. |
| `didTapViewForTrackedBarcode(overlay, trackedBarcode)` | Called when the user taps the AR view. Available from react-native=7.0. |

## Step 6 — Render DataCaptureView and attach overlays

```tsx
import React, { useEffect, useRef } from 'react';
import {
  DataCaptureView,
  Camera,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';
import dataCaptureContext from './CaptureContext';

export const ScanPage = () => {
  const viewRef = useRef<DataCaptureView>(null);
  const cameraRef = useRef<Camera | null>(null);

  const barcodeBatchRef = useRef<BarcodeBatch>(null!);
  if (!barcodeBatchRef.current) {
    barcodeBatchRef.current = setupBarcodeBatch();
  }

  const overlayRef = useRef<BarcodeBatchBasicOverlay>(null!);
  if (!overlayRef.current) {
    overlayRef.current = setupBasicOverlay(barcodeBatchRef.current);
  }

  useEffect(() => {
    const initCamera = async () => {
      if (!cameraRef.current) {
        const cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
        const camera = Camera.withSettings(cameraSettings);
        if (!camera) throw new Error('No camera available');
        await dataCaptureContext.setFrameSource(camera);
        await camera.switchToDesiredState(FrameSourceState.On);
        cameraRef.current = camera;
      }
    };

    initCamera();

    return () => {
      barcodeBatchRef.current.isEnabled = false;
      dataCaptureContext.removeMode(barcodeBatchRef.current);
    };
  }, []);

  return (
    <DataCaptureView
      style={{ flex: 1 }}
      context={dataCaptureContext}
      ref={view => {
        if (view && !viewRef.current) {
          view.addOverlay(overlayRef.current);
          viewRef.current = view;
        }
      }}
    />
  );
};
```

> The `DataCaptureView` `ref` callback pattern (`if (view && !viewRef.current)`) ensures overlays are only added once and not on every re-render.

## Step 7 — Lifecycle: enable/disable, cleanup on unmount

### Enable/disable without removing the mode

```typescript
// Pause scanning (e.g. app goes to background)
barcodeBatchRef.current.isEnabled = false;
cameraRef.current?.switchToDesiredState(FrameSourceState.Off);

// Resume scanning (e.g. app returns to foreground)
barcodeBatchRef.current.isEnabled = true;
cameraRef.current?.switchToDesiredState(FrameSourceState.On);
```

### Handle app state changes

```typescript
import { AppState, AppStateStatus } from 'react-native';

useEffect(() => {
  const subscription = AppState.addEventListener('change', (nextAppState: AppStateStatus) => {
    if (nextAppState.match(/inactive|background/)) {
      barcodeBatchRef.current.isEnabled = false;
      cameraRef.current?.switchToDesiredState(FrameSourceState.Off);
    } else if (nextAppState === 'active') {
      barcodeBatchRef.current.isEnabled = true;
      cameraRef.current?.switchToDesiredState(FrameSourceState.On);
    }
  });

  return () => subscription.remove();
}, []);
```

### Cleanup on unmount

```typescript
useEffect(() => {
  // ... camera setup ...

  return () => {
    // Disable and unregister the mode
    barcodeBatchRef.current.isEnabled = false;
    dataCaptureContext.removeMode(barcodeBatchRef.current);
  };
}, []);
```

> Use `dataCaptureContext.removeMode(barcodeBatch)` for cleanup, **not** `setFrameSource(null)`. The BarcodeBatch mode is removed from the context so it stops processing frames.

## Step 7b — Feedback (beep / vibration)

Unlike single-barcode `BarcodeCapture` (which has a `BarcodeCaptureFeedback` and beeps automatically on every scan), **`BarcodeBatch` has no automatic feedback** — there is no `BarcodeBatchFeedback` class, and the mode never beeps or vibrates on its own. If you want audible/haptic feedback when a barcode starts being tracked, you must construct a `Feedback` and call `emit()` yourself.

```typescript
import { Feedback, Vibration, Sound } from 'scandit-react-native-datacapture-core';

// Build the feedback once (default beep + default vibration).
// Pass null for either channel to disable it, e.g. new Feedback(Vibration.defaultVibration, null).
const scanFeedback = new Feedback(Vibration.defaultVibration, Sound.defaultSound);
// Alternatively: const scanFeedback = Feedback.defaultFeedback;

// Track which barcodes have already triggered feedback so each one beeps only once.
const seenIdentifiers = new Set<number>();

const listener = {
  didUpdateSession: async (_batch: BarcodeBatch, session: BarcodeBatchSession) => {
    // Emit only for barcodes that started being tracked this frame…
    session.addedTrackedBarcodes.forEach(trackedBarcode => {
      // …and dedupe by the stable track identifier so the same barcode does not
      // re-beep on later frames.
      if (!seenIdentifiers.has(trackedBarcode.identifier)) {
        seenIdentifiers.add(trackedBarcode.identifier);
        scanFeedback.emit();
      }
    });
  },
};

barcodeBatch.addListener(listener);
```

- Iterate `session.addedTrackedBarcodes` (not all `trackedBarcodes`) so you emit once per new barcode rather than on every frame.
- Dedupe on `trackedBarcode.identifier` — emitting per `addedTrackedBarcodes` entry is usually enough, but keeping a `Set` guards against a track being briefly lost and re-added.
- `Feedback`, `Vibration`, and `Sound` are imported from `scandit-react-native-datacapture-core`. `Vibration.defaultVibration` and `Sound.defaultSound` are the standard success cues; emission is still subject to the device's ring mode and volume.

### Feedback API (core)

| Member | Available | Description |
|--------|-----------|-------------|
| `new Feedback(vibration, sound)` | react-native=6.5 | Construct a feedback from a `Vibration` (or `null`) and a `Sound` (or `null`). |
| `Feedback.defaultFeedback` | react-native=6.5 | Static getter: default sound + default vibration. |
| `feedback.emit()` | react-native=6.5 | Emit the configured sound and vibration. |
| `Vibration.defaultVibration` | react-native=6.5 | Static getter for the default success vibration. |
| `Sound.defaultSound` | react-native=6.5 | Static getter for the default success beep. |

## Step 8 — Camera Permissions

### iOS

Add to `ios/<App>/Info.plist`:

```xml
<key>NSCameraUsageDescription</key>
<string>We need camera access to scan barcodes</string>
```

### Android

Request at runtime before the scan screen mounts:

```tsx
import { Platform, PermissionsAndroid } from 'react-native';

async function requestCameraPermission(): Promise<boolean> {
  if (Platform.OS !== 'android') return true;
  const status = await PermissionsAndroid.request(
    PermissionsAndroid.PERMISSIONS.CAMERA,
  );
  return status === PermissionsAndroid.RESULTS.GRANTED;
}
```

## Step 9 — Complete Example

### CaptureContext.ts

```typescript
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

export default DataCaptureContext.sharedInstance;
```

### ScanPage.tsx

```tsx
import React, { useEffect, useRef } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchSession,
  BarcodeBatchSettings,
  Symbology,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';
import {
  Brush,
  Camera,
  Color,
  DataCaptureView,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';
import dataCaptureContext from './CaptureContext';

export const ScanPage = () => {
  const viewRef = useRef<DataCaptureView>(null);
  const cameraRef = useRef<Camera | null>(null);

  const barcodeBatchRef = useRef<BarcodeBatch>(null!);
  if (!barcodeBatchRef.current) {
    const settings = new BarcodeBatchSettings();
    settings.enableSymbologies([
      Symbology.EAN13UPCA,
      Symbology.EAN8,
      Symbology.Code128,
    ]);

    const batch = new BarcodeBatch(settings);
    batch.addListener({
      didUpdateSession: async (_batch: BarcodeBatch, session: BarcodeBatchSession) => {
        const added: TrackedBarcode[] = session.addedTrackedBarcodes;
        const updated: TrackedBarcode[] = session.updatedTrackedBarcodes;
        const removedIds: string[] = session.removedTrackedBarcodes;

        console.log(
          `Frame: +${added.length} added, ~${updated.length} updated, -${removedIds.length} removed`
        );

        Object.values(session.trackedBarcodes).forEach(tracked => {
          console.log(`Tracking: ${tracked.barcode.data}`);
        });
      },
    });

    dataCaptureContext.setMode(batch);
    barcodeBatchRef.current = batch;
  }

  const overlayRef = useRef<BarcodeBatchBasicOverlay>(null!);
  if (!overlayRef.current) {
    const overlay = new BarcodeBatchBasicOverlay(
      barcodeBatchRef.current,
      BarcodeBatchBasicOverlayStyle.Frame,
    );

    overlay.listener = {
      brushForTrackedBarcode: (_overlay, trackedBarcode: TrackedBarcode) => {
        // Example: different brush per symbology
        if (trackedBarcode.barcode.symbology === Symbology.EAN13UPCA) {
          return new Brush(Color.fromRGBA(0, 200, 0, 0.3), Color.fromHex('#00C800'), 2);
        }
        return new Brush(Color.fromRGBA(0, 100, 255, 0.3), Color.fromHex('#0064FF'), 2);
      },
    };

    overlayRef.current = overlay;
  }

  useEffect(() => {
    const initCamera = async () => {
      if (!cameraRef.current) {
        const settings = BarcodeBatch.createRecommendedCameraSettings();
        const camera = Camera.withSettings(settings);
        if (!camera) throw new Error('No camera available');
        await dataCaptureContext.setFrameSource(camera);
        await camera.switchToDesiredState(FrameSourceState.On);
        cameraRef.current = camera;
      }
    };

    void initCamera();

    const subscription = AppState.addEventListener('change', (nextAppState: AppStateStatus) => {
      if (nextAppState.match(/inactive|background/)) {
        barcodeBatchRef.current.isEnabled = false;
        cameraRef.current?.switchToDesiredState(FrameSourceState.Off);
      } else if (nextAppState === 'active') {
        barcodeBatchRef.current.isEnabled = true;
        cameraRef.current?.switchToDesiredState(FrameSourceState.On);
      }
    });

    return () => {
      subscription.remove();
      barcodeBatchRef.current.isEnabled = false;
      dataCaptureContext.removeMode(barcodeBatchRef.current);
    };
  }, []);

  return (
    <DataCaptureView
      style={{ flex: 1 }}
      context={dataCaptureContext}
      ref={view => {
        if (view && !viewRef.current) {
          view.addOverlay(overlayRef.current);
          viewRef.current = view;
        }
      }}
    />
  );
};
```

## Key Rules

1. **Singleton context** — Call `DataCaptureContext.initialize(licenseKey)` once in a dedicated module and export `DataCaptureContext.sharedInstance`. Never construct another context anywhere else.
2. **Function components with hooks** — Hold `BarcodeBatch`, camera, and overlays in `useRef`. Initialize them once using the `if (!ref.current)` guard.
3. **setMode for registration** — Call `dataCaptureContext.setMode(barcodeBatch)` after constructing the mode. Call `dataCaptureContext.removeMode(barcodeBatch)` in the cleanup function.
4. **Overlays via addOverlay** — Add overlays to the `DataCaptureView` using `view.addOverlay(overlay)` inside the `ref` callback. Use the `if (view && !viewRef.current)` guard to call it only once.
5. **Session data** — The session object is only safe to access inside the `didUpdateSession` callback. Copy arrays before using them outside.
6. **AR add-on required** — `brushForTrackedBarcode`, `setBrushForTrackedBarcode`, and all `BarcodeBatchAdvancedOverlay` APIs require the MatrixScan AR add-on license.
7. **BarcodeBatchAdvancedOverlayView subclass** — Views passed to `setViewForTrackedBarcode` must be instances of a `BarcodeBatchAdvancedOverlayView` subclass, and the subclass must be registered via `AppRegistry.registerComponent(MyView.moduleName, () => MyView)` in `index.js`.
8. **New Architecture (iOS ≥ 0.79)** — If using the new RN architecture with `BarcodeBatchAdvancedOverlay`, the `AppDelegate` must implement `ScanditReactNativeFactoryContainer`.
9. **Camera permissions** — iOS: `NSCameraUsageDescription` in `Info.plist`. Android: runtime request via `PermissionsAndroid`.
10. **Metro cache** — If a package upgrade appears to have no effect at runtime, restart Metro with `npm start -- --reset-cache`.

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Nothing scans when the view mounts | Camera not started. `await camera.switchToDesiredState(FrameSourceState.On)` in `useEffect`. |
| Overlays not visible | `addOverlay` was not called or was called outside the `ref` callback guard. |
| Brushes not showing | `brushForTrackedBarcode` requires the MatrixScan AR add-on. Verify the license. |
| AR bubbles not rendering | `AppRegistry.registerComponent(ARBubble.moduleName, () => ARBubble)` was not called in `index.js`. |
| AR overlay crashes on iOS (new architecture) | `AppDelegate` does not implement `ScanditReactNativeFactoryContainer`. See prerequisites. |
| App crashes on iOS after install | Run `npx pod-install` and rebuild. |
| `new BarcodeBatch(settings)` not found | Requires react-native=7.6. Use `BarcodeBatch.forDataCaptureContext(context, settings)` on older versions. |
| `BarcodeBatch.createRecommendedCameraSettings()` not found | Requires react-native=7.6. |
| Session data accessed outside callback | Copy `addedTrackedBarcodes`, `updatedTrackedBarcodes`, etc. before the callback returns. |
| Mode not cleaning up after navigation | Call `dataCaptureContext.removeMode(barcodeBatch)` in the `useEffect` cleanup. |
