# BarcodeCapture React Native Integration Guide

BarcodeCapture is the single-scan capture mode in the Scandit Data Capture SDK. Unlike SparkScan, it does **not** ship a pre-built UI — you wire up a `DataCaptureView`, attach a `BarcodeCaptureOverlay` for the recognized-barcode highlight, and drive the camera (frame source) yourself. Use BarcodeCapture when you need full control over the scanning surface (custom layouts, custom viewfinders, location selection, etc.).

> **Language note**: Examples below use TypeScript (`.tsx`) because it is the default for React Native templates. For plain JavaScript projects, drop the type annotations and keep the same imports and structure.

## Prerequisites

- Scandit React Native packages installed:
  - `scandit-react-native-datacapture-core`
  - `scandit-react-native-datacapture-barcode`
- After installing, run `npx pod-install` (or `cd ios && pod install`) for iOS. Android auto-links via Gradle — no manual step.
- React Native `>=0.70`. The New Architecture (Fabric / TurboModules) is supported — no additional setup required beyond the standard RN template.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/<App>/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request at runtime via `PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.CAMERA)` before rendering the scan screen.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which file they'd like to integrate BarcodeCapture into (typically the scan screen component, e.g. `App.tsx`, `ScanScreen.tsx`, or a page module). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Install packages: `npm install scandit-react-native-datacapture-core scandit-react-native-datacapture-barcode`
2. Run `npx pod-install` (iOS). Android auto-links.
3. Add `NSCameraUsageDescription` to `ios/<App>/Info.plist`.
4. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with your key from https://ssl.scandit.com.
5. If Metro was running, restart it with `--reset-cache` so the new package is picked up.

## Step 1 — Initialize DataCaptureContext (singleton module)

Create a small module that initializes the context exactly once at import time and re-exports the singleton for the rest of the app:

```typescript
// CaptureContext.ts
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

DataCaptureContext.initialize(licenseKey);

export default DataCaptureContext.sharedInstance;
```

- `DataCaptureContext.initialize(licenseKey)` is the v8 API. It is idempotent per process — call it once.
- `DataCaptureContext.sharedInstance` is the singleton accessor used everywhere else in the app.
- Do **not** create additional `DataCaptureContext` instances — there is only one per app.

> **Important**: Put the `initialize(...)` call at the top of a dedicated module so it runs on first import and before any component that uses `sharedInstance` mounts.

## Step 2 — Configure BarcodeCaptureSettings + symbologies

Choose which barcode symbologies to scan. Only enable what you need — each extra symbology adds processing time. By default all symbologies are disabled.

```typescript
import {
  BarcodeCaptureSettings,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';

const settings = new BarcodeCaptureSettings();

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

### Per-symbology settings (`settingsForSymbology`)

`settings.settingsForSymbology(Symbology.X)` returns the mutable `SymbologySettings` for one symbology. Mutating it updates the parent `BarcodeCaptureSettings`. Apply the result with `barcodeCapture.applySettings(settings)` (or pass `settings` into the constructor before the mode is added). Common per-symbology configuration:

```typescript
const code39Settings = settings.settingsForSymbology(Symbology.Code39);

// Extensions — symbology-specific feature flags (string keys).
code39Settings.setExtensionEnabled('full_ascii', true);

// Checksums — array of Checksum values. The code is accepted if any matches.
code39Settings.checksums = [Checksum.Mod43];

// Active symbol counts — allowed code lengths (in symbols) for variable-length codes.
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];

// Color-inverted codes — read bright codes on a dark background.
code39Settings.isColorInvertedEnabled = true;
```

| Member | Type | Description |
|--------|------|-------------|
| `setExtensionEnabled(extension, enabled)` | method | Enable/disable a symbology extension by string key (e.g. `'full_ascii'`, `'remove_leading_zero'`). |
| `isExtensionEnabled(extension)` | method | Whether an extension is enabled. |
| `checksums` | `Checksum[]` | Optional checksums (e.g. `Checksum.Mod43`). Imported from `scandit-react-native-datacapture-barcode`. |
| `activeSymbolCounts` | `number[]` | Allowed lengths in symbols for variable-length symbologies. |
| `isColorInvertedEnabled` | `boolean` | Enable decoding of color-inverted (bright-on-dark) codes for this symbology. |

`Checksum` is imported from `scandit-react-native-datacapture-barcode`.

### BarcodeCaptureSettings Properties

| Property | Type | Description |
|----------|------|-------------|
| `codeDuplicateFilter` | `number` | Milliseconds to suppress duplicate scans of the same code. `0` = report every detection, `-1` = report each code only once until the mode is disabled. |
| `scanIntention` | `ScanIntention` | Scanning intent mode. Values: `ScanIntention.Smart` (default in v7+), `ScanIntention.Manual`. |
| `batterySaving` | `BatterySavingMode` | Battery optimization. `Auto`, `On`, or `Off`. |
| `locationSelection` | `LocationSelection \| null` | Restrict the scan area. `null` = full frame. |
| `enabledCompositeTypes` | `CompositeType[]` | Composite barcode types. |
| `enabledSymbologies` | `Symbology[]` | Read-only set of currently enabled symbologies. |

### BarcodeCaptureSettings Methods

| Method | Description |
|--------|-------------|
| `enableSymbologies(symbologies)` | Enable multiple symbologies. |
| `enableSymbology(symbology, enabled)` | Enable or disable one. |
| `settingsForSymbology(symbology)` | Get per-symbology settings (e.g., `activeSymbolCounts`). |
| `enableSymbologiesForCompositeTypes(compositeTypes)` | Enable symbologies required for composite types. |
| `setProperty(name, value)` / `getProperty(name)` | Advanced property access by name. |

## Step 3 — Create the Camera and set it as the frame source

BarcodeCapture has no built-in camera. Create a `Camera`, apply the recommended camera settings for barcode capture, and set it as the context's frame source.

```typescript
import {
  Camera,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';
import { BarcodeCapture } from 'scandit-react-native-datacapture-barcode';

const camera = Camera.default;
camera?.applySettings(BarcodeCapture.recommendedCameraSettings);
await dataCaptureContext.setFrameSource(camera);
```

`Camera.default` returns the world-facing camera. `BarcodeCapture.recommendedCameraSettings` is a static getter that returns a `CameraSettings` tuned for barcode scanning. The camera is started later by switching it to `FrameSourceState.On` (Step 7).

## Step 4 — Create the BarcodeCapture mode

```typescript
import {
  BarcodeCapture,
  BarcodeCaptureSettings,
} from 'scandit-react-native-datacapture-barcode';

// v8 (preferred from 7.6+)
const barcodeCapture = new BarcodeCapture(settings);
dataCaptureContext.addMode(barcodeCapture);

// v7 / v6 — still supported in v8 but discouraged in new code
// const barcodeCapture = BarcodeCapture.forContext(dataCaptureContext, settings);
```

`new BarcodeCapture(settings)` does not bind to a context; you must call `dataCaptureContext.addMode(barcodeCapture)` (or `setMode(...)`) to attach it. `BarcodeCapture.forContext(context, settings)` is the older factory that auto-attaches when `context` is non-null.

### BarcodeCapture Methods and Properties

| Member | Type | Description |
|---|---|---|
| `isEnabled` | `boolean` | Pause / resume scanning without stopping the camera. Set to `false` inside `didScan` while you process the result. |
| `feedback` | `BarcodeCaptureFeedback` | Sound + vibration feedback. See Step 8. |
| `applySettings(settings)` | `Promise<void>` | Update settings at runtime. |
| `addListener(listener)` / `removeListener(listener)` | — | Register or remove a `BarcodeCaptureListener`. |
| `BarcodeCapture.recommendedCameraSettings` | `CameraSettings` | Static — recommended camera settings for barcode capture. |

## Step 5 — Render `<DataCaptureView>` and add a `BarcodeCaptureOverlay`

The `DataCaptureView` renders the camera preview. The `BarcodeCaptureOverlay` draws the recognized-barcode highlight on top.

```tsx
import React, { useEffect, useRef } from 'react';
import {
  DataCaptureView,
} from 'scandit-react-native-datacapture-core';
import {
  BarcodeCaptureOverlay,
} from 'scandit-react-native-datacapture-barcode';

const viewRef = useRef<DataCaptureView | null>(null);

useEffect(() => {
  // v8 constructor
  const overlay = new BarcodeCaptureOverlay(barcodeCapture);
  viewRef.current?.addOverlay(overlay);

  return () => {
    viewRef.current?.removeOverlay(overlay);
  };
}, []);

return (
  <DataCaptureView
    style={{ flex: 1 }}
    context={dataCaptureContext}
    ref={view => { viewRef.current = view; }}
  />
);
```

The legacy factory `BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, view)` is still available — passing a non-null `view` adds the overlay automatically.

### BarcodeCaptureOverlay Properties

| Property | Type | Description |
|----------|------|-------------|
| `viewfinder` | `Viewfinder \| null` | The viewfinder drawn over the preview. `null` = no viewfinder. See Step 9. |
| `brush` | `Brush` | The brush used to highlight recognized barcodes. Default: transparent fill, Scandit-blue stroke, width 1. |
| `shouldShowScanAreaGuides` | `boolean` | Development aid — shows the scan area outline. Default `false`. Do not use in production. |

## Step 6 — Implement BarcodeCaptureListener

The listener delivers barcode results. On React Native, both methods are async and receive a `getFrameData` thunk you can `await` to retrieve frame bytes if needed.

```typescript
import {
  BarcodeCapture,
  BarcodeCaptureSession,
} from 'scandit-react-native-datacapture-barcode';
import { FrameData } from 'scandit-react-native-datacapture-core';

const listener = {
  didScan: async (
    mode: BarcodeCapture,
    session: BarcodeCaptureSession,
    _getFrameData: () => Promise<FrameData>,
  ) => {
    const barcode = session.newlyRecognizedBarcode;
    if (barcode == null) return;

    // Pause scanning while we process this result.
    mode.isEnabled = false;

    // ... handle the barcode (navigate, network call, UI update)

    // Re-enable when ready for the next scan, or leave disabled to stop.
    mode.isEnabled = true;
  },

  didUpdateSession: async (
    _mode: BarcodeCapture,
    _session: BarcodeCaptureSession,
    _getFrameData: () => Promise<FrameData>,
  ) => {
    // Called every processed frame, regardless of whether a code was scanned.
  },
};

barcodeCapture.addListener(listener);
```

### BarcodeCaptureListener Interface

All callbacks are optional. Implement only what you need.

| Callback | Signature (React Native) | Description |
|---|---|---|
| `didScan` | `(barcodeCapture, session, getFrameData) => Promise<void>` | Called when a barcode is scanned. |
| `didUpdateSession` | `(barcodeCapture, session, getFrameData) => Promise<void>` | Called on every frame processed. |

### BarcodeCaptureSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `newlyRecognizedBarcode` | `Barcode \| null` | The barcode just scanned in the current frame. |
| `newlyLocalizedBarcodes` | `LocalizedOnlyBarcode[]` | Barcodes that were localized but not decoded this frame. |
| `frameSequenceID` | `number` | Frame sequence identifier; stays the same as long as frames flow without interruption. |
| `reset()` | `Promise<void>` | Clear session history (resets duplicate filtering). Only call inside a listener callback. |

> **Important**: Do not retain references to `session.newlyRecognizedBarcode` or `session.newlyLocalizedBarcodes` outside the listener callback — the session is mutated concurrently.

## Step 7 — Lifecycle: switch the camera on / off

The camera is not started by mounting `<DataCaptureView>`. You drive it explicitly via `FrameSourceState`. The recommended pattern with React Navigation is `useFocusEffect`:

```tsx
import { useFocusEffect } from '@react-navigation/native';
import { useCallback } from 'react';
import { Camera, FrameSourceState } from 'scandit-react-native-datacapture-core';

useFocusEffect(
  useCallback(() => {
    barcodeCapture.isEnabled = true;
    Camera.default?.switchToDesiredState(FrameSourceState.On);

    return () => {
      barcodeCapture.isEnabled = false;
      Camera.default?.switchToDesiredState(FrameSourceState.Off);
    };
  }, []),
);
```

Cleanup responsibilities when the scan screen unmounts:

| What | How |
|---|---|
| Stop the camera | `camera.switchToDesiredState(FrameSourceState.Off)` |
| Disable the mode | `barcodeCapture.isEnabled = false` |
| Remove the overlay | `dataCaptureView.removeOverlay(overlay)` |
| Unbind the mode from the context | `dataCaptureContext.removeMode(barcodeCapture)` |
| Remove the listener | `barcodeCapture.removeListener(listener)` |

> ### ⚠️ Never call `dataCaptureContext.dispose()`
>
> The context is a process-wide **singleton** (`DataCaptureContext.sharedInstance`). Disposing it tears down every Scandit screen in the entire app, not just the one being unmounted, and leaves the app unable to scan again until the JS bundle is reloaded.
>
> **Do not** include `dataCaptureContext.dispose()` in `useEffect` cleanup, `useFocusEffect` cleanup, `componentWillUnmount`, or anywhere else — even if your training data or other React Native libraries follow that convention. The complete and correct unmount cleanup is exactly the five rows in the table above (camera off, mode disabled, overlay removed, mode removed, listener removed). Stop after `removeMode` and `removeListener`. Adding `dispose()` is always a bug.

## Step 8 — Feedback customization

By default `BarcodeCapture` plays a beep and vibrates on every successful scan. The feedback object is mutable on the mode:

```typescript
import { Feedback, Vibration } from 'scandit-react-native-datacapture-core';
import { BarcodeCaptureFeedback } from 'scandit-react-native-datacapture-barcode';

const feedback = BarcodeCaptureFeedback.defaultFeedback;
// Vibration only, no sound:
feedback.success = new Feedback(Vibration.defaultVibration, null);
barcodeCapture.feedback = feedback;
```

`BarcodeCaptureFeedback.success` is a `Feedback` with optional `Vibration` and `Sound` components. Passing `null` for either disables that channel.

## Step 9 — Viewfinder (optional)

A viewfinder is a visual cue painted by `BarcodeCaptureOverlay`. It is purely cosmetic and does not affect what is scanned. Set it on the overlay:

```typescript
import {
  RectangularViewfinder,
  RectangularViewfinderStyle,
  RectangularViewfinderLineStyle,
  LaserlineViewfinder,
} from 'scandit-react-native-datacapture-core';

// Rectangular viewfinder
overlay.viewfinder = new RectangularViewfinder(
  RectangularViewfinderStyle.Square,
  RectangularViewfinderLineStyle.Light,
);

// Or a laserline viewfinder (no constructor arguments)
// overlay.viewfinder = new LaserlineViewfinder();

// Or an aimer viewfinder (a crosshair-style dot + frame, good for single-code aiming)
// const aimer = new AimerViewfinder();
// aimer.frameColor = Color.fromHex('#FFFFFF');
// aimer.dotColor = Color.fromHex('#FF0000');
// overlay.viewfinder = aimer;
```

`AimerViewfinder` is imported from `scandit-react-native-datacapture-core`. It has no constructor arguments; customize it through its `frameColor` and `dotColor` properties (both `Color`). `LaserlineViewfinder` also takes no constructor arguments; customize via its `width` (`NumberWithUnit`), `enabledColor`, and `disabledColor` properties.

To restrict where barcodes are accepted (not just where the viewfinder is drawn), see Step 10.

## Step 9b — Overlay brush (highlight color)

The `brush` property of `BarcodeCaptureOverlay` controls how recognized barcodes are highlighted. Construct a `Brush(fillColor, strokeColor, strokeWidth)`:

```typescript
import { Brush, Color } from 'scandit-react-native-datacapture-core';

overlay.brush = new Brush(
  Color.fromRGBA(0, 255, 0, 0.2), // fill
  Color.fromHex('#00FF00'),       // stroke
  2,                              // stroke width
);
```

`Brush`, `Color` are imported from `scandit-react-native-datacapture-core`. `Brush.transparent` is a static that returns a fully transparent brush (no fill, no stroke) — useful to hide a highlight (see "Rejecting barcodes" below).

## Step 9c — Rejecting barcodes (visually mark unwanted codes)

To reject a scanned barcode — accept only codes that match a rule — handle the rejection inside `didScan`. The pattern: in `didScan`, inspect `barcode.data`; if it does not match your rule, set the overlay's `brush` to `Brush.transparent` so the rejected code is not highlighted, and `return` early without processing it. Acceptable codes get the normal brush.

```typescript
const listener = {
  didScan: async (mode, session) => {
    const barcode = session.newlyRecognizedBarcode;
    if (barcode == null) return;

    // Reject anything that is not an internal SKU.
    if (!barcode.data?.startsWith('SKU-')) {
      overlay.brush = Brush.transparent;
      return; // do not process the rejected code
    }

    overlay.brush = new Brush(
      Color.fromRGBA(0, 255, 0, 0.2),
      Color.fromHex('#00FF00'),
      2,
    );
    // ... process the accepted barcode
  },
};
```

## Step 10 — Location selection (optional)

`locationSelection` on `BarcodeCaptureSettings` filters which barcodes are accepted by where they appear in the frame. Apply it via `barcodeCapture.applySettings(settings)`.

```typescript
import {
  RadiusLocationSelection,
  NumberWithUnit,
  MeasureUnit,
} from 'scandit-react-native-datacapture-core';

settings.locationSelection = new RadiusLocationSelection(
  new NumberWithUnit(0.5, MeasureUnit.Fraction),
);
await barcodeCapture.applySettings(settings);
```

A rectangular location selection (`RectangularLocationSelection.withSize(...)`) is also available if you need a non-circular acceptance region.

## Step 11 — Scan intention (optional)

`ScanIntention.Smart` (default in v7+) intelligently picks the barcode the user is aiming at when several are visible. `ScanIntention.Manual` reverts to scanning whatever decodes first.

```typescript
import { ScanIntention } from 'scandit-react-native-datacapture-core';

settings.scanIntention = ScanIntention.Manual;
await barcodeCapture.applySettings(settings);
```

## Step 12 — CodeDuplicateFilter (optional)

To suppress repeated reports of the same barcode value within a time window, set `codeDuplicateFilter` (in milliseconds) on the settings before applying:

```typescript
settings.codeDuplicateFilter = 500; // 500 ms
await barcodeCapture.applySettings(settings);
```

- `0` — report every detection.
- `-1` — report each code at most once until the mode is disabled.
- positive value — minimum interval between repeated reports of the same code.

## Step 13 — Composite codes (optional)

To scan composite codes (a 1D code + a 2D component), enable both the composite types and the symbologies they require:

```typescript
import { CompositeType } from 'scandit-react-native-datacapture-barcode';

settings.enabledCompositeTypes = [CompositeType.A, CompositeType.B];
settings.enableSymbologiesForCompositeTypes(settings.enabledCompositeTypes);
```

## Step 14 — Camera Permissions

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

async function requestCameraPermission() {
  if (Platform.OS !== 'android') return true;
  const status = await PermissionsAndroid.request(
    PermissionsAndroid.PERMISSIONS.CAMERA,
  );
  return status === PermissionsAndroid.RESULTS.GRANTED;
}
```

Gate navigation to the scan screen on a successful permission:

```tsx
const handleStartScan = async () => {
  const granted = await requestCameraPermission();
  if (!granted) return;
  navigation.navigate('scan');
};
```

## Step 15 — Complete Example

Full working scan screen: context singleton, camera, mode, overlay, listener, lifecycle.

### CaptureContext.ts

```typescript
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

DataCaptureContext.initialize(licenseKey);

export default DataCaptureContext.sharedInstance;
```

### ScanScreen.tsx

```tsx
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';

import {
  Camera,
  DataCaptureView,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';
import {
  BarcodeCapture,
  BarcodeCaptureOverlay,
  BarcodeCaptureSession,
  BarcodeCaptureSettings,
  Symbology,
  SymbologyDescription,
} from 'scandit-react-native-datacapture-barcode';

import dataCaptureContext from './CaptureContext';

export const ScanScreen = () => {
  const [lastScan, setLastScan] = useState<string | null>(null);

  const viewRef = useRef<DataCaptureView | null>(null);
  const cameraRef = useRef<Camera | null>(null);
  const barcodeCaptureRef = useRef<BarcodeCapture | null>(null);

  if (cameraRef.current === null) {
    const camera = Camera.default;
    camera?.applySettings(BarcodeCapture.recommendedCameraSettings);
    dataCaptureContext.setFrameSource(camera);
    cameraRef.current = camera;
  }

  if (barcodeCaptureRef.current === null) {
    const settings = new BarcodeCaptureSettings();
    settings.enableSymbologies([
      Symbology.EAN13UPCA,
      Symbology.EAN8,
      Symbology.UPCE,
      Symbology.Code39,
      Symbology.Code128,
      Symbology.InterleavedTwoOfFive,
    ]);
    const barcodeCapture = new BarcodeCapture(settings);
    dataCaptureContext.addMode(barcodeCapture);
    barcodeCaptureRef.current = barcodeCapture;
  }

  useEffect(() => {
    const barcodeCapture = barcodeCaptureRef.current!;

    const listener = {
      didScan: async (
        mode: BarcodeCapture,
        session: BarcodeCaptureSession,
      ) => {
        const barcode = session.newlyRecognizedBarcode;
        if (barcode == null) return;
        mode.isEnabled = false;
        const symbology = new SymbologyDescription(barcode.symbology);
        setLastScan(`${barcode.data} (${symbology.readableName})`);
        mode.isEnabled = true;
      },
    };
    barcodeCapture.addListener(listener);

    const overlay = new BarcodeCaptureOverlay(barcodeCapture);
    viewRef.current?.addOverlay(overlay);

    return () => {
      viewRef.current?.removeOverlay(overlay);
      barcodeCapture.removeListener(listener);
      dataCaptureContext.removeMode(barcodeCapture);
    };
  }, []);

  useFocusEffect(
    useCallback(() => {
      const barcodeCapture = barcodeCaptureRef.current!;
      const camera = cameraRef.current;
      barcodeCapture.isEnabled = true;
      camera?.switchToDesiredState(FrameSourceState.On);
      return () => {
        barcodeCapture.isEnabled = false;
        camera?.switchToDesiredState(FrameSourceState.Off);
      };
    }, []),
  );

  return (
    <View style={styles.container}>
      <DataCaptureView
        style={styles.preview}
        context={dataCaptureContext}
        ref={view => { viewRef.current = view; }}
      />
      <View style={styles.results}>
        <Text>{lastScan ?? 'Waiting for scan...'}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  preview: { flex: 1 },
  results: { padding: 16, backgroundColor: '#fff' },
});
```

## Key Rules

1. **Singleton context** — Call `DataCaptureContext.initialize(licenseKey)` once in a dedicated module and export `DataCaptureContext.sharedInstance`. Never construct another context anywhere else.
2. **Function components with hooks** — Hold the camera, mode, and view in `useRef`. Register listeners and overlays inside `useEffect`. Drive the camera on/off through `useFocusEffect`. Do not use class components for new BarcodeCapture code.
3. **Camera is not automatic** — `Camera.default` + `dataCaptureContext.setFrameSource(camera)` + `camera.switchToDesiredState(FrameSourceState.On)` are all required. The native view does not start the camera for you.
4. **Disable the mode in `didScan`** — Set `barcodeCapture.isEnabled = false` before doing per-scan work to avoid duplicate callbacks. Re-enable when ready for the next code.
5. **Cleanup on unmount** — Stop the camera, remove the overlay, remove the listener, and call `dataCaptureContext.removeMode(barcodeCapture)`. Do not call `dataCaptureContext.dispose()`.
6. **Construction in v8** — Prefer `new BarcodeCapture(settings)` + `context.addMode(...)`. The `BarcodeCapture.forContext(context, settings)` factory is older but still works.
7. **Imports** — Core types (`DataCaptureContext`, `DataCaptureView`, `Camera`, `FrameSourceState`, `Color`, `Brush`, viewfinders) from `scandit-react-native-datacapture-core`; barcode types (`BarcodeCapture`, `BarcodeCaptureSettings`, `BarcodeCaptureOverlay`, `Symbology`, `SymbologyDescription`, `BarcodeCaptureFeedback`) from `scandit-react-native-datacapture-barcode`.
8. **Pod install** — Run `npx pod-install` (or `cd ios && pod install`) after installing or updating Scandit packages. Android auto-links.
9. **Camera permissions** — iOS: `NSCameraUsageDescription` in `Info.plist`. Android: runtime request via `PermissionsAndroid` before navigating to the scan screen.
10. **Metro cache** — If a package upgrade appears to have no effect at runtime, restart Metro with `npm start -- --reset-cache`.

For the full API surface (every property, every overload), see the [BarcodeCapture API reference](https://docs.scandit.com/data-capture-sdk/react-native/barcode-capture/api.html).
