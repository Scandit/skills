# SparkScan React Native Integration Guide

SparkScan is a pre-built scanning UI for high-volume single-scanning workflows. In React Native it is a component (`<SparkScanView>`) that wraps your screen. The scanning controls (floating trigger button, toolbar, mini preview, toasts) render as a native view on top of the children, so users scan barcodes without leaving the current screen.

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

Once the user responds, ask them which file they'd like to integrate SparkScan into (typically the scan screen component, e.g. `App.tsx`, `ScanScreen.tsx`, or a page module). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

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

## Step 2 — Configure SparkScanSettings

Choose which barcode symbologies to scan. Only enable what you need — each extra symbology adds processing time.

```typescript
import {
  SparkScanSettings,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';

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

## Step 3 — Create the SparkScan mode and register a listener

The recommended pattern is to hold the `SparkScan` instance in a `useRef` so it survives re-renders without being recreated, and to register the listener inside `useEffect`.

```tsx
import React, { useEffect, useRef, useState } from 'react';
import {
  SparkScan,
  SparkScanSession,
  SparkScanSettings,
  Symbology,
  SymbologyDescription,
} from 'scandit-react-native-datacapture-barcode';
import dataCaptureContext from './CaptureContext';

function createSparkScan(): SparkScan {
  const settings = new SparkScanSettings();
  settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);
  return new SparkScan(settings);
}

export const ScanScreen = () => {
  const [codes, setCodes] = useState<{ data: string | null; symbology: string }[]>([]);

  // Create the mode once — persist across re-renders.
  const sparkScanMode = useRef<SparkScan>(null!);
  if (!sparkScanMode.current) {
    sparkScanMode.current = createSparkScan();
  }

  useEffect(() => {
    const listener = {
      didScan: async (_: SparkScan, session: SparkScanSession) => {
        const barcode = session.newlyRecognizedBarcode;
        if (barcode == null) return;
        const symbology = new SymbologyDescription(barcode.symbology);
        setCodes(prev => [...prev, { data: barcode.data, symbology: symbology.readableName }]);
      },
    };
    sparkScanMode.current.addListener(listener);

    // Cleanup: unbind the mode from the context on unmount.
    return () => {
      dataCaptureContext.removeMode(sparkScanMode.current);
    };
  }, []);

  // ...render (Step 5)
};
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

## Step 4 — Render `<SparkScanView>`

`<SparkScanView>` is a React component that hosts a native platform view. Pass the context, the SparkScan mode, and `SparkScanViewSettings` as props. Children render **under** the native scanning overlay.

```tsx
import { View, Text } from 'react-native';
import {
  SparkScanView,
  SparkScanViewSettings,
} from 'scandit-react-native-datacapture-barcode';

return (
  <SparkScanView
    style={{ flex: 1 }}
    context={dataCaptureContext}
    sparkScan={sparkScanMode.current}
    sparkScanViewSettings={new SparkScanViewSettings()}
  >
    {/* Your screen content — renders under the scanning overlay */}
    <View style={{ flex: 1, padding: 16 }}>
      <Text>Scanned items appear here</Text>
    </View>
  </SparkScanView>
);
```

> Props `context`, `sparkScan`, and `style` are required. `sparkScanViewSettings` is optional — pass a default `new SparkScanViewSettings()` if you don't need to tweak view-level config.

## Step 5 — SparkScanView Lifecycle and Cleanup

The native view is created when the component mounts and torn down when it unmounts. Camera startup is automatic — you do **not** need to call a separate `prepareScanning()` / `startScanning()` in typical flows.

Cleanup responsibilities when the scan screen unmounts:

| What | How |
|---|---|
| Unbind the SparkScan mode from the context | `dataCaptureContext.removeMode(sparkScanMode.current)` in the `useEffect` cleanup. |
| Remove listeners (if you stored them) | `sparkScanMode.current.removeListener(listener)` before `removeMode`. |

You do **not** need to dispose the view explicitly — React unmount handles the native view.

| Runtime method | Description |
|---|---|
| `startScanning()` / `pauseScanning()` | Manually control scanning when replacing the built-in trigger button with a custom one. |
| `stopScanning()` | Stop scanning and release the camera. |
| `showToast(text)` | Display a temporary toast on the overlay. |

## Step 6 — SparkScanView Properties

Most properties are set imperatively on the view instance via the `ref` callback (they are not React props):

```tsx
<SparkScanView
  ref={view => {
    if (view) {
      view.torchControlVisible = true;
      view.barcodeFindButtonVisible = true;
      view.triggerButtonTintColor = Color.fromHex('#FFFFFF');
    }
    sparkScanViewRef.current = view;
  }}
  /* ...other props */
>
```

### Visibility Controls (`boolean`)

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

All colors use `Color.fromHex('#RRGGBB')` from `scandit-react-native-datacapture-core`.

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

By default SparkScan provides visual and haptic feedback on each scan. To customize feedback per-barcode (e.g., reject invalid codes), set a `feedbackDelegate` on the view. Build the delegate with `useMemo` so the feedback objects aren't recreated on every render.

```tsx
import { useCallback, useMemo } from 'react';
import {
  Barcode,
  SparkScanBarcodeSuccessFeedback,
  SparkScanBarcodeErrorFeedback,
} from 'scandit-react-native-datacapture-barcode';
import { Color, Brush } from 'scandit-react-native-datacapture-core';

const isValidBarcode = useCallback((barcode: Barcode) => {
  return barcode.data != null && barcode.data !== '123456789';
}, []);

const feedbackDelegate = useMemo(() => {
  const success = new SparkScanBarcodeSuccessFeedback();
  const error = new SparkScanBarcodeErrorFeedback(
    'Wrong barcode',                 // message on overlay
    60,                               // resumeCapturingDelay (seconds)
    Color.fromHex('#FF0000'),         // visualFeedbackColor
    new Brush(Color.fromHex('#FF0000'), Color.fromHex('#FF0000'), 1),
    null,                             // sound/haptic (null = default)
  );
  return {
    feedbackForBarcode: (barcode: Barcode) =>
      isValidBarcode(barcode) ? success : error,
  };
}, [isValidBarcode]);

// Assign the delegate via the view ref:
<SparkScanView
  ref={view => {
    if (view) view.feedbackDelegate = feedbackDelegate;
    sparkScanViewRef.current = view;
  }}
  /* ...other props */
>
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

Listen for user interactions with the SparkScan overlay buttons. Assign via the view ref:

```tsx
<SparkScanView
  ref={view => {
    if (view) {
      view.uiListener = {
        didTapBarcodeCountButton: () => navigation.navigate('count'),
        didTapBarcodeFindButton: () => navigation.navigate('find'),
        didTapLabelCaptureButton: () => navigation.navigate('label'),
        didChangeViewState: newState => { /* expanded/collapsed */ },
        didChangeScanningMode: newMode => { /* single vs continuous */ },
      };
    }
    sparkScanViewRef.current = view;
  }}
  /* ...other props */
>
```

All callbacks are optional.

## Step 9 — Camera Permissions

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

On iOS, the permission prompt is triggered automatically by the native SparkScan view when it mounts.

## Step 10 — Complete Example

Full working screen: plugin init, context singleton, scan pipeline, list UI, and feedback delegate — mirrors the official ListBuildingSample.

### CaptureContext.ts

```typescript
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

DataCaptureContext.initialize(licenseKey);

export default DataCaptureContext.sharedInstance;
```

### ScanScreen.tsx

```tsx
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { View, ScrollView, Text, Pressable, StyleSheet } from 'react-native';

import { Color, Brush } from 'scandit-react-native-datacapture-core';
import {
  SparkScan,
  SparkScanSettings,
  SparkScanView,
  SparkScanViewSettings,
  Symbology,
  SymbologyDescription,
  SparkScanSession,
  Barcode,
  SparkScanBarcodeSuccessFeedback,
  SparkScanBarcodeErrorFeedback,
} from 'scandit-react-native-datacapture-barcode';

import dataCaptureContext from './CaptureContext';

export const ScanScreen = () => {
  const [codes, setCodes] = useState<{ data: string | null; symbology: string }[]>([]);

  const sparkScanMode = useRef<SparkScan>(null!);
  if (!sparkScanMode.current) {
    sparkScanMode.current = setupScanning();
  }
  const sparkScanViewRef = useRef<SparkScanView | null>(null);

  useEffect(() => {
    return () => {
      dataCaptureContext.removeMode(sparkScanMode.current);
    };
  }, []);

  function setupScanning(): SparkScan {
    const settings = new SparkScanSettings();
    settings.enableSymbologies([
      Symbology.EAN13UPCA,
      Symbology.EAN8,
      Symbology.UPCE,
      Symbology.Code39,
      Symbology.Code128,
      Symbology.InterleavedTwoOfFive,
    ]);
    settings.settingsForSymbology(Symbology.Code39).activeSymbolCounts = [
      7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    ];

    const sparkScan = new SparkScan(settings);

    sparkScan.addListener({
      didScan: async (_: SparkScan, session: SparkScanSession) => {
        const barcode = session.newlyRecognizedBarcode;
        if (barcode == null) return;
        if (!isValidBarcode(barcode)) return;
        const symbology = new SymbologyDescription(barcode.symbology);
        setCodes(prev => [...prev, { data: barcode.data, symbology: symbology.readableName }]);
      },
    });
    return sparkScan;
  }

  const isValidBarcode = useCallback(
    (barcode: Barcode) => barcode.data != null && barcode.data !== '123456789',
    [],
  );

  const feedbackDelegate = useMemo(() => {
    const success = new SparkScanBarcodeSuccessFeedback();
    const error = new SparkScanBarcodeErrorFeedback(
      'Wrong barcode',
      60,
      Color.fromHex('#FF0000'),
      new Brush(Color.fromHex('#FF0000'), Color.fromHex('#FF0000'), 1),
      null,
    );
    return {
      feedbackForBarcode: (b: Barcode) => (isValidBarcode(b) ? success : error),
    };
  }, [isValidBarcode]);

  return (
    <SparkScanView
      style={styles.container}
      context={dataCaptureContext}
      sparkScan={sparkScanMode.current}
      sparkScanViewSettings={new SparkScanViewSettings()}
      ref={view => {
        if (view) view.feedbackDelegate = feedbackDelegate;
        sparkScanViewRef.current = view;
      }}
    >
      <View style={styles.container}>
        <Text style={styles.count}>
          {codes.length} {codes.length === 1 ? 'item' : 'items'}
        </Text>
        <ScrollView style={{ flex: 1 }}>
          {codes.map((result, index) => (
            <View key={index} style={styles.row}>
              <Text style={styles.data}>{result.data}</Text>
              <Text style={styles.symbology}>{result.symbology}</Text>
            </View>
          ))}
        </ScrollView>
        <Pressable style={styles.clearButton} onPress={() => setCodes([])}>
          <Text style={styles.clearText}>CLEAR LIST</Text>
        </Pressable>
      </View>
    </SparkScanView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  count: { fontWeight: 'bold', padding: 16, fontSize: 14 },
  row: { paddingHorizontal: 16, paddingVertical: 10, borderBottomWidth: 0.5, borderColor: '#ccc' },
  data: { fontWeight: 'bold', fontSize: 14 },
  symbology: { fontSize: 12, color: '#666', marginTop: 2 },
  clearButton: {
    alignItems: 'center', padding: 12, margin: 16,
    borderWidth: 2, borderColor: '#000', borderRadius: 4,
  },
  clearText: { fontWeight: 'bold', fontSize: 16 },
});
```

## Key Rules

1. **Singleton context** — Call `DataCaptureContext.initialize(licenseKey)` once in a dedicated module and export `DataCaptureContext.sharedInstance`. Never construct another context anywhere else.
2. **Function components with hooks** — Hold the `SparkScan` mode in a `useRef`. Register listeners in `useEffect`. Build `feedbackDelegate` in `useMemo`. Do not use class components for new SparkScan code.
3. **Imperative ref assignment** — `feedbackDelegate`, `uiListener`, and color / visibility properties are set via the `ref` callback on `<SparkScanView>` (`ref={view => { if (view) view.feedbackDelegate = ...; }}`). They are not React props.
4. **Cleanup on unmount** — In the `useEffect` cleanup function, call `dataCaptureContext.removeMode(sparkScanMode.current)`. React unmount handles the native view tear-down automatically.
5. **Children render under the overlay** — Everything inside `<SparkScanView>` renders below the native scanning controls. Use this to show results lists, forms, or any other content.
6. **Imports** — Core types from `scandit-react-native-datacapture-core`; barcode types from `scandit-react-native-datacapture-barcode`.
7. **Pod install** — Run `npx pod-install` (or `cd ios && pod install`) after installing or updating Scandit packages. Android auto-links.
8. **Camera permissions** — iOS: `NSCameraUsageDescription` in `Info.plist`. Android: runtime request via `PermissionsAndroid` before navigating to the scan screen.
9. **Metro cache** — If a package upgrade appears to have no effect at runtime, restart Metro with `npm start -- --reset-cache`.
10. **Feedback delegate goes on the view** — set `sparkScanView.feedbackDelegate`, not on the SparkScan mode.
