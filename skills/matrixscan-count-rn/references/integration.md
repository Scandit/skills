# MatrixScan Count React Native Integration Guide

MatrixScan Count (API name: `BarcodeCount*`) is a multi-barcode scan-and-count mode that scans all barcodes in view simultaneously when the user taps the shutter button, and tracks the running total. In React Native it is rendered through a `<BarcodeCountView>` component that provides a full-featured counting UI out of the box: shutter button, progress bar, list button, exit button, hint overlays, and optional status icons.

> **Language note**: Examples below use TypeScript (`.tsx`) because it is the default for React Native templates. For plain JavaScript projects, drop the type annotations and keep the same imports and structure.

## Prerequisites

- Scandit React Native packages installed:
  - `scandit-react-native-datacapture-core`
  - `scandit-react-native-datacapture-barcode`
- After installing, run `npx pod-install@1.2.1` (or `cd ios && pod install`) for iOS. Android auto-links via Gradle — no manual step.
- Minimum SDK version: **6.17** for core BarcodeCount classes on React Native. `new BarcodeCount(settings)` constructor requires 7.6+. `tapToUncountEnabled` requires 7.0+. `BarcodeCountNotInListActionSettings` requires 7.1+. `BarcodeCountStatusProvider` and status-mode APIs require 8.3+.
- React Native `>=0.70`. The New Architecture (Fabric / TurboModules) is supported — no additional setup required beyond the standard RN template.
- A valid Scandit license key — see **Licence key** in this skill's `SKILL.md`.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/<App>/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request at runtime via `PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.CAMERA)` before rendering the count screen.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which file they'd like to integrate MatrixScan Count into (typically the count screen component, e.g. `App.tsx`, `ScanPage.tsx`, or a screen module). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Install packages: `npm install scandit-react-native-datacapture-core scandit-react-native-datacapture-barcode`
2. Run `npx pod-install@1.2.1` (iOS). Android auto-links.
3. Add `NSCameraUsageDescription` to `ios/<App>/Info.plist`.
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key (see **Licence key** in `SKILL.md`).
5. If Metro was running, restart it with `--reset-cache` so the new package is picked up.

## Step 1 — Initialize DataCaptureContext (singleton module)

Create a small module that initializes the context exactly once at import time and re-exports the singleton for the rest of the app:

```typescript
// CaptureContext.ts
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

export default DataCaptureContext.sharedInstance;
```

- `DataCaptureContext.initialize(licenseKey)` is the v8 API. It is idempotent per process — call it once.
- `DataCaptureContext.sharedInstance` is the singleton accessor used everywhere else in the app.
- Do **not** create additional `DataCaptureContext` instances — there is only one per app.

> **Important**: Put the `initialize(...)` call at the top of a dedicated module so it runs on first import and before any component that uses `sharedInstance` mounts.

## Step 2 — Configure BarcodeCountSettings

Choose which barcode symbologies to scan. Only enable what you need — each extra symbology adds processing time.

```typescript
import {
  BarcodeCountSettings,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';

const settings = new BarcodeCountSettings();

settings.enableSymbologies([
  Symbology.EAN13UPCA,
  Symbology.EAN8,
  Symbology.UPCE,
  Symbology.Code39,
  Symbology.Code128,
  Symbology.QR,
  Symbology.DataMatrix,
]);

// Optional: adjust active symbol counts for variable-length symbologies
const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];

// Optional: declare whether all barcodes are expected to be unique (improves performance)
settings.expectsOnlyUniqueBarcodes = true;
```

### BarcodeCountSettings Properties and Methods

| Member | Description |
|--------|-------------|
| `enableSymbologies(symbologies)` | Enable multiple symbologies at once. |
| `enableSymbology(symbology, enabled)` | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | Get per-symbology settings (e.g. `activeSymbolCounts`). |
| `enabledSymbologies` | Read-only array of currently enabled symbologies. |
| `expectsOnlyUniqueBarcodes` | `boolean` — optimize for unique-barcode scenarios. Do not enable if multiple identical barcodes are expected. |
| `disableModeWhenCaptureListCompleted` | `boolean` (RN 8.3+) — auto-disable mode when capture list is completed. |
| `clusteringMode` | `ClusteringMode` (RN 8.3+) — `Disabled` (default), `Auto`, `Manual`, or `AutoWithManualCorrection`. |
| `filterSettings` | Read-only `BarcodeFilterSettings` getter — mutate it in place to exclude barcodes from counting. |
| `setProperty(name, value)` / `getProperty(name)` | Advanced property access by name. |

### Filtering — excluding barcodes from the count (Step 2 add-on)

When several barcode types appear in the scene but you only want to count some of them, exclude the
rest with `BarcodeCountSettings.filterSettings`. This is a **read-only getter** that returns a
`BarcodeFilterSettings` instance — mutate it in place; do **not** construct a new `BarcodeFilterSettings`
and assign it back. Filtering applies at the settings level (which barcodes are counted), separately
from how filtered barcodes are highlighted on the view (see section 5j, `BarcodeFilterHighlightSettings`).

```typescript
import {
  BarcodeCountSettings,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';

const settings = new BarcodeCountSettings();
settings.enableSymbologies([Symbology.Code128, Symbology.PDF417]);

const filterSettings = settings.filterSettings;
// Exclude an entire symbology — e.g. count Code 128 but never PDF417
filterSettings.excludedSymbologies = [Symbology.PDF417];
// Exclude by data content — e.g. any barcode whose data starts with 1234
filterSettings.excludedCodesRegex = '^1234.*';
```

`BarcodeFilterSettings` members:

| Member | Type | Description |
|--------|------|-------------|
| `excludedSymbologies` | `Symbology[]` | Symbologies that are recognized but not counted. |
| `excludedCodesRegex` | `string` | Barcodes whose data matches this regex are excluded. |
| `excludeEan13` | `boolean` | Convenience flag to exclude EAN-13 barcodes. |
| `excludeUpca` | `boolean` | Convenience flag to exclude UPC-A barcodes. |
| `setExcludedSymbolCounts(counts, symbology)` | method | Exclude specific symbol counts for a symbology. |

## Step 3 — Construct BarcodeCount and attach camera

Hold the `BarcodeCount` instance and camera in a `useRef` so they survive re-renders without being recreated.

```tsx
import React, { useEffect, useRef } from 'react';
import {
  BarcodeCount,
  BarcodeCountSettings,
  BarcodeCountSession,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';
import {
  Camera,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';
import dataCaptureContext from './CaptureContext';

function setupCamera(): Camera {
  const camera = Camera.withSettings(BarcodeCount.createRecommendedCameraSettings());
  if (!camera) throw new Error('Failed to create camera');
  dataCaptureContext.setFrameSource(camera);
  return camera;
}

function setupBarcodeCount(setCodes: (codes: string[]) => void): BarcodeCount {
  const settings = new BarcodeCountSettings();
  settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);

  const barcodeCount = new BarcodeCount(settings);

  barcodeCount.addListener({
    didScan: async (_: BarcodeCount, session: BarcodeCountSession) => {
      // session.recognizedBarcodes is an array of Barcode (RN 7.0+)
      const barcodeData = session.recognizedBarcodes
        .map(b => b.data)
        .filter((d): d is string => d !== null);
      setCodes(barcodeData);
    },
  });

  return barcodeCount;
}
```

### BarcodeCount Methods

| Method | Description |
|--------|-------------|
| `new BarcodeCount(settings)` | Constructs a new instance. Available from react-native=7.6. |
| `addListener(listener)` / `removeListener(listener)` | Register/remove a session listener. |
| `applySettings(settings)` | Update settings at runtime (returns `Promise<void>`). |
| `reset()` | Resets the session — clears the history of tracked barcodes (`Promise<void>`). |
| `startScanningPhase()` | Starts the capture session programmatically. |
| `endScanningPhase()` | Disables the mode and switches off the frame source. |
| `setBarcodeCountCaptureList(list)` | Activates "scan against a list" mode with a `BarcodeCountCaptureList`. |
| `setAdditionalBarcodes(barcodes)` | Inject barcodes as partial scanning results (`Promise<void>`). |
| `clearAdditionalBarcodes()` | Remove previously injected additional barcodes (`Promise<void>`). |
| `BarcodeCount.createRecommendedCameraSettings()` | Returns camera settings optimized for BarcodeCount. RN 7.6+. |
| `feedback` | Read/write `BarcodeCountFeedback` property — see Step 7. |
| `isEnabled` | `boolean` — enable/disable the mode without removing it from the context. |

## Step 4 — BarcodeCountView (JSX and props)

`<BarcodeCountView>` is a React component that provides the full counting UI. Pass `barcodeCount`, `context`, and optionally `viewStyle` as props. Listeners are wired imperatively via the `ref` callback.

```tsx
import {
  BarcodeCountView,
  BarcodeCountViewStyle,
  BarcodeCountViewListener,
  BarcodeCountViewUiListener,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';
import dataCaptureContext from './CaptureContext';

export const CountScreen = () => {
  const barcodeCountRef = useRef<BarcodeCount>(null!);
  // ... (initialize barcodeCountRef as shown in Step 3)

  const viewListenerRef = useRef<BarcodeCountViewListener | null>(null);
  if (!viewListenerRef.current) {
    viewListenerRef.current = {
      didTapRecognizedBarcode: (_, trackedBarcode: TrackedBarcode) => {
        console.log('Tapped recognized barcode:', trackedBarcode.barcode.data);
      },
      didTapRecognizedBarcodeNotInList: (_, trackedBarcode: TrackedBarcode) => {
        console.log('Tapped not-in-list barcode:', trackedBarcode.barcode.data);
      },
      didCompleteCaptureList: (_) => {
        console.log('Capture list completed');
      },
    };
  }

  const viewUiListenerRef = useRef<BarcodeCountViewUiListener | null>(null);
  if (!viewUiListenerRef.current) {
    viewUiListenerRef.current = {
      didTapListButton: (_: BarcodeCountView) => {
        // Navigate to results page
      },
      didTapExitButton: (_: BarcodeCountView) => {
        // Complete the counting session
      },
    };
  }

  return (
    <BarcodeCountView
      style={{ flex: 1 }}
      barcodeCount={barcodeCountRef.current}
      context={dataCaptureContext}
      viewStyle={BarcodeCountViewStyle.Icon}
      ref={view => {
        if (view) {
          view.listener = viewListenerRef.current;
          view.uiListener = viewUiListenerRef.current;
        }
      }}
    />
  );
};
```

### BarcodeCountView JSX Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `barcodeCount` | `BarcodeCount` | Yes | The BarcodeCount mode instance. |
| `context` | `DataCaptureContext` | Yes | The shared DataCaptureContext singleton. |
| `viewStyle` | `BarcodeCountViewStyle` | No | `Icon` (default animated icons) or `Dot` (dot highlights). |
| `style` | `ViewStyle` | Yes | React Native style — typically `{ flex: 1 }`. |

> **Note**: `listener` and `uiListener` are **not** JSX props — they are set imperatively in the `ref` callback.

> **Note**: `BarcodeCountView` does not require an explicit `start()` call. Scanning starts automatically when the view mounts and the camera is on.

## Step 5 — BarcodeCountView Customization

`BarcodeCountView` exposes many properties that control the appearance and behavior of the built-in UI. Set them imperatively in the `ref` callback.

For visibility toggles and the exit, shutter, list and toolbar buttons, see [View controls and toolbar](toolbar.md).

### 5b — Brushes (Dot Style Only)

Brushes are used when `viewStyle` is `BarcodeCountViewStyle.Dot`. They color the dot highlight for each barcode category.

```typescript
import { Brush, Color } from 'scandit-react-native-datacapture-core';

ref={view => {
  if (view) {
    // Global brush for all recognized barcodes (in list)
    view.recognizedBrush = new Brush(
      Color.fromHex('#4CAF50'),  // fill — green
      Color.fromHex('#4CAF50'),  // stroke
      1,
    );
    // Barcodes not in the capture list
    view.notInListBrush = new Brush(
      Color.fromHex('#F44336'),  // fill — red
      Color.fromHex('#F44336'),
      1,
    );
    // Barcodes accepted via the not-in-list action popup (RN 7.1+)
    view.acceptedBrush = new Brush(Color.fromHex('#2196F3'), Color.fromHex('#2196F3'), 1);
    // Barcodes rejected via the not-in-list action popup (RN 7.1+)
    view.rejectedBrush = new Brush(Color.fromHex('#FF9800'), Color.fromHex('#FF9800'), 1);
  }
}}
```

**Static defaults** (read-only, accessible before the view mounts):

```typescript
const defaultRecognizedBrush = BarcodeCountView.defaultRecognizedBrush;
const defaultNotInListBrush = BarcodeCountView.defaultNotInListBrush;
const defaultAcceptedBrush = BarcodeCountView.defaultAcceptedBrush;   // RN 7.1+
const defaultRejectedBrush = BarcodeCountView.defaultRejectedBrush;   // RN 7.1+
```

**Per-barcode brush setters** (override per tracked barcode, RN 7.1+):

```typescript
// Call these from inside viewListener.brushForRecognizedBarcode etc., or imperatively:
await view.setBrushForRecognizedBarcode(trackedBarcode, new Brush(Color.fromHex('#00FF00'), Color.fromHex('#00FF00'), 1));
await view.setBrushForRecognizedBarcodeNotInList(trackedBarcode, new Brush(Color.fromHex('#FF0000'), Color.fromHex('#FF0000'), 1));
await view.setBrushForAcceptedBarcode(trackedBarcode, new Brush(Color.fromHex('#2196F3'), Color.fromHex('#2196F3'), 1));
await view.setBrushForRejectedBarcode(trackedBarcode, new Brush(Color.fromHex('#FF9800'), Color.fromHex('#FF9800'), 1));
```

Note: Per-barcode brushes can also be returned from `BarcodeCountViewListener` callbacks (`brushForRecognizedBarcode`, `brushForRecognizedBarcodeNotInList`, `brushForAcceptedBarcode`, `brushForRejectedBarcode`).

### 5c — Button Text Customization

```typescript
ref={view => {
  if (view) {
    view.exitButtonText = 'Done';
    view.clearHighlightsButtonText = 'Clear';
  }
}}
```

| Property | Type | Description |
|----------|------|-------------|
| `exitButtonText` | `string` | Label for the exit button. |
| `clearHighlightsButtonText` | `string` | Label for the clear highlights button. |

Android uses content-description properties for Android TalkBack on buttons:

| Property | Platform | Description |
|----------|----------|-------------|
| `listButtonContentDescription` | Android | Content description for the list button. |
| `exitButtonContentDescription` | Android | Content description for the exit button. |
| `shutterButtonContentDescription` | Android | Content description for the shutter button. |
| `clearHighlightsButtonContentDescription` | Android | Content description for the clear highlights button. |
| `singleScanButtonContentDescription` | Android | Content description for the single scan button. |
| `floatingShutterButtonContentDescription` | Android | Content description for the floating shutter button. |
| `statusModeButtonContentDescription` | Android | Content description for the status mode button (RN 8.3+). |

### 5d — Hint Text Customization

Set hint text directly as properties on the view (no setter methods needed in RN):

```typescript
ref={view => {
  if (view) {
    view.textForTapShutterToScanHint = 'Tap button to scan';
    view.textForScanningHint = 'Scanning in progress...';
    view.textForMoveCloserAndRescanHint = 'Move closer and rescan';
    view.textForMoveFurtherAndRescanHint = 'Move further and rescan';
    view.textForBarcodesNotInListDetectedHint = 'Unknown item detected';  // RN 8.3+
    view.textForScreenCleanedUpHint = 'Screen cleared';                   // RN 8.3+
    view.textForTapToUncountHint = 'Tap to remove from count';
    view.textForClusteringGestureHint = 'Swipe to group codes';           // RN 8.3+
  }
}}
```

| Property | RN Version | Description |
|----------|-----------|-------------|
| `textForTapShutterToScanHint` | 6.17+ | Hint prompting the user to tap the shutter. |
| `textForScanningHint` | 6.17+ | Hint shown while scanning is in progress. |
| `textForMoveCloserAndRescanHint` | 6.17+ | Hint when the camera should move closer. |
| `textForMoveFurtherAndRescanHint` | 6.17+ | Hint when the camera should move further. |
| `textForBarcodesNotInListDetectedHint` | 8.3+ | Hint when a barcode not in list is scanned. |
| `textForScreenCleanedUpHint` | 8.3+ | Hint when the screen is cleared. |
| `textForTapToUncountHint` | 7.0+ | Hint when the user deselects a barcode. |
| `textForClusteringGestureHint` | 8.3+ | Hint for the clustering gesture. |

### 5e — Accessibility Labels and Hints (iOS)

Accessibility properties affect iOS VoiceOver and have no effect on Android.

```typescript
ref={view => {
  if (view) {
    view.listButtonAccessibilityLabel = 'View scan list';
    view.listButtonAccessibilityHint = 'Opens the list of scanned items';

    view.exitButtonAccessibilityLabel = 'Finish scanning';
    view.exitButtonAccessibilityHint = 'Completes the counting session';

    view.shutterButtonAccessibilityLabel = 'Scan barcodes';
    view.shutterButtonAccessibilityHint = 'Tap to scan all visible barcodes';

    view.floatingShutterButtonAccessibilityLabel = 'Scan';
    view.floatingShutterButtonAccessibilityHint = 'Tap to scan';

    view.singleScanButtonAccessibilityLabel = 'Single scan';
    view.singleScanButtonAccessibilityHint = 'Scan one barcode';

    view.clearHighlightsButtonAccessibilityLabel = 'Clear highlights';
    view.clearHighlightsButtonAccessibilityHint = 'Removes all barcode highlights from screen';

    view.statusModeButtonAccessibilityLabel = 'Toggle status';     // RN 8.3+
    view.statusModeButtonAccessibilityHint = 'Shows item statuses'; // RN 8.3+
  }
}}
```

### 5f — Hardware Trigger

```typescript
ref={view => {
  if (view) {
    // iOS: enable volume button as trigger (RN 7.1+)
    view.hardwareTriggerEnabled = true;

    // Android: enable a specific hardware key (RN 7.1+, device API ≥28)
    // Pass null to use the default key (XCover HW button or KEYCODE_VOLUME_DOWN)
    view.enableHardwareTrigger(null);

    // Check if the Android device supports hardware trigger:
    if (BarcodeCountView.hardwareTriggerSupported) {
      view.enableHardwareTrigger(null);
    }
  }
}}
```

### 5g — Tap-to-Uncount (RN 7.0+)

```typescript
ref={view => {
  if (view) {
    view.tapToUncountEnabled = true;
    view.textForTapToUncountHint = 'Tap barcode to remove';
  }
}}
```

### 5h — Torch Control Position (RN 6.26+)

```typescript
import { Anchor } from 'scandit-react-native-datacapture-core';

ref={view => {
  if (view) {
    view.shouldShowTorchControl = true;
    view.torchControlPosition = Anchor.TopRight;  // TopLeft | TopRight | BottomLeft | BottomRight
  }
}}
```

### 5i — Not-in-List Action Settings (RN 7.1+)

When scanning against a list, tapping a "not in list" barcode can show an action popup allowing the user to accept or reject it.

```typescript
ref={view => {
  if (view) {
    const notInListSettings = view.barcodeNotInListActionSettings;
    notInListSettings.enabled = true;
    notInListSettings.acceptButtonText = 'Accept';
    notInListSettings.rejectButtonText = 'Reject';
    notInListSettings.cancelButtonText = 'Cancel';
    notInListSettings.barcodeAcceptedHint = 'Item added to list';
    notInListSettings.barcodeRejectedHint = 'Item rejected';
  }
}}
```

### 5j — Filter Settings

```typescript
// BarcodeFilterHighlightSettings can be set to control how filtered barcodes appear.
// Access via view.filterSettings (type: BarcodeFilterHighlightSettings | null).
ref={view => {
  if (view) {
    // view.filterSettings = myFilterHighlightSettings;
  }
}}
```

### 5k — Methods on BarcodeCountView

| Method | Returns | Description |
|--------|---------|-------------|
| `clearHighlights()` | `Promise<void>` | Clear all barcode highlights. Does not affect the session. |
| `setToolbarSettings(settings)` | `void` | Configure the collapsible toolbar (pass a `BarcodeCountToolbarSettings` instance). |
| `setStatusProvider(provider)` | `void` | Set a `BarcodeCountStatusProvider` (RN 8.3+). |

For the toolbar settings example and button labels and accessibility strings, see [View controls and toolbar](toolbar.md).

**prepareScanning and stopScanning** are iOS-only native methods. In React Native, camera lifecycle is managed via `camera.switchToDesiredState(FrameSourceState.On/Off)` and `dataCaptureContext.setFrameSource(null)` — not via these iOS-specific view methods.

## Step 6 — BarcodeCountListener

`BarcodeCountListener` receives session callbacks. Register it on the `BarcodeCount` instance with `addListener`.

```tsx
import {
  BarcodeCount,
  BarcodeCountSession,
} from 'scandit-react-native-datacapture-barcode';

const listener = {
  didScan: async (_: BarcodeCount, session: BarcodeCountSession) => {
    // Called once per scanning phase (after shutter is tapped)
    // session.recognizedBarcodes: Barcode[] — all currently recognized barcodes (RN 7.0+)
    const allBarcodes = session.recognizedBarcodes;
    console.log('Recognized barcodes:', allBarcodes.map(b => b.data));
  },

  // onSessionUpdated: called each frame while scanning (RN 8.3+)
  onSessionUpdated: async (_: BarcodeCount, session: BarcodeCountSession) => {
    // Use for real-time per-frame updates
  },
};

barcodeCount.addListener(listener);
```

### BarcodeCountSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `recognizedBarcodes` | `Barcode[]` | All currently recognized barcodes. RN 7.0+. |
| `frameSequenceID` | `number` | Identifier of the current frame sequence. |
| `additionalBarcodes` | `Barcode[]` | Injected barcodes from `setAdditionalBarcodes`. |
| `reset()` | `Promise<void>` | Reset the session (call only inside the listener callback). |
| `getSpatialMap()` | `Promise<BarcodeSpatialGrid \| null>` | Compute the spatial map (requires `mappingEnabled`). |
| `getSpatialMapWithHints(rows, cols)` | `Promise<BarcodeSpatialGrid \| null>` | Compute the spatial map with size hints. |

## Step 7 — BarcodeCountViewListener

`BarcodeCountViewListener` receives tap events on barcode highlights and list completion events. Set it on the view via the `ref` callback: `view.listener = myListener`.

```typescript
import {
  BarcodeCountViewListener,
  BarcodeCountView,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';

const viewListener: BarcodeCountViewListener = {
  // Dot style only — return brush for a recognized barcode
  brushForRecognizedBarcode: (view, trackedBarcode) => {
    return new Brush(Color.fromHex('#4CAF50'), Color.fromHex('#4CAF50'), 1);
  },
  // Dot style only — return brush for a not-in-list barcode
  brushForRecognizedBarcodeNotInList: (view, trackedBarcode) => {
    return new Brush(Color.fromHex('#F44336'), Color.fromHex('#F44336'), 1);
  },
  // RN 7.1+: return brush for an accepted barcode
  brushForAcceptedBarcode: (view, trackedBarcode) => {
    return new Brush(Color.fromHex('#2196F3'), Color.fromHex('#2196F3'), 1);
  },
  // RN 7.1+: return brush for a rejected barcode
  brushForRejectedBarcode: (view, trackedBarcode) => {
    return new Brush(Color.fromHex('#FF9800'), Color.fromHex('#FF9800'), 1);
  },
  didTapRecognizedBarcode: (view, trackedBarcode: TrackedBarcode) => {
    console.log('Tapped recognized barcode:', trackedBarcode.barcode.data);
  },
  didTapFilteredBarcode: (view, filteredBarcode: TrackedBarcode) => {
    console.log('Tapped filtered barcode:', filteredBarcode.barcode.data);
  },
  didTapRecognizedBarcodeNotInList: (view, trackedBarcode: TrackedBarcode) => {
    console.log('Tapped not-in-list barcode:', trackedBarcode.barcode.data);
  },
  // RN 7.1+
  didTapAcceptedBarcode: (view, trackedBarcode: TrackedBarcode) => {
    console.log('Tapped accepted barcode:', trackedBarcode.barcode.data);
  },
  // RN 7.1+
  didTapRejectedBarcode: (view, trackedBarcode: TrackedBarcode) => {
    console.log('Tapped rejected barcode:', trackedBarcode.barcode.data);
  },
  // Called when all items in the capture list have been scanned
  didCompleteCaptureList: (view: BarcodeCountView) => {
    console.log('Capture list completed!');
  },
};
```

## Step 8 — BarcodeCountViewUiListener

`BarcodeCountViewUiListener` receives button tap events. Set it via `view.uiListener = myUiListener` in the `ref` callback.

```typescript
import { BarcodeCountViewUiListener, BarcodeCountView } from 'scandit-react-native-datacapture-barcode';

const viewUiListener: BarcodeCountViewUiListener = {
  didTapListButton: (view: BarcodeCountView) => {
    // Show current scan progress / navigate to results
    navigation.navigate('Results', { source: 'listButton' });
  },
  didTapExitButton: (view: BarcodeCountView) => {
    // Session complete — stop camera and navigate
    camera.switchToDesiredState(FrameSourceState.Off);
    navigation.navigate('Results', { source: 'finishButton' });
  },
  didTapSingleScanButton: (view: BarcodeCountView) => {
    // Handle single-scan button tap
  },
};
```

## Step 9 — Scanning Against a List (BarcodeCountCaptureList)

For expected quantities, completion callbacks, and the correct, wrong and missing barcodes in a session, see [Scanning against a capture list](capture-list.md).

## Step 10 — BarcodeCountFeedback

`BarcodeCountFeedback` controls sound and vibration when barcodes are detected. It is a property on the `BarcodeCount` instance.

```typescript
import {
  BarcodeCountFeedback,
} from 'scandit-react-native-datacapture-barcode';
import { Feedback, Sound, Vibration } from 'scandit-react-native-datacapture-core';

// Use the built-in default feedback (sound + vibration for success and failure)
barcodeCount.feedback = BarcodeCountFeedback.default;

// Disable all feedback
const silent = BarcodeCountFeedback.emptyFeedback;
barcodeCount.feedback = silent;

// Custom: vibrate on success, silent on failure
const custom = new BarcodeCountFeedback();
custom.success = new Feedback(Vibration.defaultVibration, null);
custom.failure = new Feedback(null, null);
barcodeCount.feedback = custom;
```

### BarcodeCountFeedback Properties

| Property | Type | Description |
|----------|------|-------------|
| `BarcodeCountFeedback.default` | `BarcodeCountFeedback` (static) | Default feedback: sound + vibration for both success and failure. |
| `BarcodeCountFeedback.emptyFeedback` | `BarcodeCountFeedback` (static) | Silent feedback — no sound or vibration. RN 7.1+. |
| `success` | `Feedback` | Feedback for a successful scan event. |
| `failure` | `Feedback` | Feedback for a failure event. |

## Step 11 — BarcodeCountStatusProvider (RN 8.3+)

`BarcodeCountStatusProvider` lets you attach per-barcode status icons (stock status, quality flags, etc.) that appear when status mode is activated. This API requires react-native=8.3+.

There are two modes:
1. **Button-activated**: Set `shouldShowStatusModeButton = true`. The user taps the button to enter status mode.
2. **Auto on scan**: Set `shouldShowStatusIconsOnScan = true`. Status icons load immediately after each scan.

```typescript
import {
  BarcodeCountStatusProvider,
  BarcodeCountStatusProviderCallback,
  BarcodeCountStatusItem,
  BarcodeCountStatusResultSuccess,
  BarcodeCountStatusResultError,
  BarcodeCountStatus,
} from 'scandit-react-native-datacapture-barcode';
import { TrackedBarcode } from 'scandit-react-native-datacapture-barcode';

const statusProvider: BarcodeCountStatusProvider = {
  onStatusRequested: (
    barcodes: TrackedBarcode[],
    callback: BarcodeCountStatusProviderCallback,
  ) => {
    // Build status items — look up each barcode's status from your data source
    const statusItems = barcodes.map(trackedBarcode => {
      const data = trackedBarcode.barcode.data ?? '';
      // Example: look up stock status
      const status = getStockStatus(data);  // returns BarcodeCountStatus value
      return BarcodeCountStatusItem.create(trackedBarcode, status);
    });

    // Deliver the result via the callback — do NOT await, use the callback pattern
    callback.onStatusReady(
      BarcodeCountStatusResultSuccess.create(
        statusItems,
        'Status mode enabled',   // shown when entering status mode
        'Status mode disabled',  // shown when exiting status mode
      ),
    );
  },
};

// Wire it to the view in the ref callback:
ref={view => {
  if (view) {
    view.setStatusProvider(statusProvider);
    view.shouldShowStatusModeButton = true;
    // Or to auto-show on scan:
    // view.shouldShowStatusIconsOnScan = true;
    view.listener = viewListenerRef.current;
    view.uiListener = viewUiListenerRef.current;
  }
}}
```

### BarcodeCountStatus Values

| Value | Description |
|-------|-------------|
| `BarcodeCountStatus.None` | No status. |
| `BarcodeCountStatus.NotAvailable` | Error retrieving status. |
| `BarcodeCountStatus.Expired` | Item is expired. |
| `BarcodeCountStatus.Fragile` | Item is fragile. |
| `BarcodeCountStatus.QualityCheck` | Quality check needed. |
| `BarcodeCountStatus.LowStock` | Low stock. |
| `BarcodeCountStatus.Wrong` | Wrong item. |
| `BarcodeCountStatus.ExpiringSoon` | Expiring soon. |

### Status Result Types

| Class | Use when |
|-------|----------|
| `BarcodeCountStatusResultSuccess.create(items, enabledMsg, disabledMsg)` | Status retrieved successfully. |
| `BarcodeCountStatusResultError.create(items, errorMsg, disabledMsg)` | Partial error — some statuses available. |
| `BarcodeCountStatusResultAbort.create(errorMsg)` | Critical failure — abort status mode immediately. |

## Step 12 — Camera and Lifecycle

### Camera setup

```typescript
import { Camera, FrameSourceState } from 'scandit-react-native-datacapture-core';

function setupCamera(): Camera {
  const camera = Camera.withSettings(BarcodeCount.createRecommendedCameraSettings());
  if (!camera) throw new Error('Failed to create camera');
  dataCaptureContext.setFrameSource(camera);
  return camera;
}

// Start camera:
camera.switchToDesiredState(FrameSourceState.On);

// Stop camera (e.g. when navigating away):
camera.switchToDesiredState(FrameSourceState.Off);
```

### Lifecycle across navigation (keeping count state)

When the user navigates to a results page and comes back to continue scanning, use `barcodeCount.reset()` and `clearAdditionalBarcodes()` to start fresh, or leave the state intact to resume counting from where they left off.

```tsx
useFocusEffect(
  useCallback(() => {
    if (shouldResetOnReturn) {
      barcodeCountRef.current.clearAdditionalBarcodes().then(() => {
        return barcodeCountRef.current.reset();
      }).then(() => {
        barcodeCountRef.current.isEnabled = true;
        cameraRef.current.switchToDesiredState(FrameSourceState.On);
      });
    }
  }, [shouldResetOnReturn]),
);
```

### Cleanup on unmount

```tsx
useEffect(() => {
  startCamera();
  return () => {
    // Release the frame source when the scan screen unmounts
    dataCaptureContext.setFrameSource(null);
  };
}, []);
```

> **Note**: Unlike BarcodeAr, BarcodeCount does not use `dataCaptureContext.removeMode(...)` for cleanup. Release the camera with `setFrameSource(null)` instead.

## Step 13 — Camera Permissions

### iOS

Add to `ios/<App>/Info.plist`:

```xml
<key>NSCameraUsageDescription</key>
<string>We need camera access to scan barcodes</string>
```

### Android

Request at runtime before the count screen mounts:

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

## Step 14 — Complete Example

### CaptureContext.ts

```typescript
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

export default DataCaptureContext.sharedInstance;
```

### ScanPage.tsx

```tsx
import React, { useCallback, useEffect, useRef } from 'react';
import {
  BarcodeCount,
  BarcodeCountSettings,
  BarcodeCountSession,
  BarcodeCountView,
  BarcodeCountViewStyle,
  BarcodeCountViewListener,
  BarcodeCountViewUiListener,
  Symbology,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';
import {
  Camera,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';
import { useFocusEffect } from '@react-navigation/native';
import dataCaptureContext from './CaptureContext';

export const ScanPage = ({ navigation }: any) => {
  const cameraRef = useRef<Camera>(null!);
  if (!cameraRef.current) {
    const camera = Camera.withSettings(BarcodeCount.createRecommendedCameraSettings());
    if (!camera) throw new Error('Camera unavailable');
    dataCaptureContext.setFrameSource(camera);
    cameraRef.current = camera;
  }

  const barcodeCountRef = useRef<BarcodeCount>(null!);
  if (!barcodeCountRef.current) {
    const settings = new BarcodeCountSettings();
    settings.enableSymbologies([
      Symbology.EAN13UPCA,
      Symbology.EAN8,
      Symbology.UPCE,
      Symbology.Code128,
      Symbology.QR,
    ]);

    const mode = new BarcodeCount(settings);
    mode.addListener({
      didScan: async (_: BarcodeCount, session: BarcodeCountSession) => {
        console.log('Scanned:', session.recognizedBarcodes.map(b => b.data));
      },
    });
    barcodeCountRef.current = mode;
  }

  const viewListenerRef = useRef<BarcodeCountViewListener | null>(null);
  if (!viewListenerRef.current) {
    viewListenerRef.current = {
      didTapRecognizedBarcode: (_, tb: TrackedBarcode) => {
        console.log('Tapped recognized:', tb.barcode.data);
      },
      didCompleteCaptureList: (_) => {
        navigation.navigate('Results', { source: 'finishButton' });
      },
    };
  }

  const viewUiListenerRef = useRef<BarcodeCountViewUiListener | null>(null);
  if (!viewUiListenerRef.current) {
    viewUiListenerRef.current = {
      didTapListButton: (_: BarcodeCountView) => {
        navigation.navigate('Results', { source: 'listButton' });
      },
      didTapExitButton: (_: BarcodeCountView) => {
        cameraRef.current.switchToDesiredState(FrameSourceState.Off);
        navigation.navigate('Results', { source: 'finishButton' });
      },
    };
  }

  useEffect(() => {
    cameraRef.current.switchToDesiredState(FrameSourceState.On);
    return () => {
      dataCaptureContext.setFrameSource(null);
    };
  }, []);

  return (
    <BarcodeCountView
      style={{ flex: 1 }}
      barcodeCount={barcodeCountRef.current}
      context={dataCaptureContext}
      viewStyle={BarcodeCountViewStyle.Icon}
      ref={view => {
        if (view) {
          view.listener = viewListenerRef.current;
          view.uiListener = viewUiListenerRef.current;
        }
      }}
    />
  );
};
```

## Key Rules

1. **Singleton context** — Call `DataCaptureContext.initialize(licenseKey)` once in a dedicated module and export `DataCaptureContext.sharedInstance`. Never construct another context anywhere else.
2. **Function components with hooks** — Hold the `BarcodeCount` mode and camera in `useRef`. Initialize them once using the `if (!ref.current)` guard. Register listeners inside that block.
3. **No explicit start()** — Unlike `BarcodeArView`, `BarcodeCountView` starts scanning automatically when it mounts and the camera is on. You do not need to call `view.start()`.
4. **Listeners via ref callback** — Wire `view.listener` and `view.uiListener` in the `BarcodeCountView` `ref` callback. Do not pass them as JSX props.
5. **Camera cleanup** — In the `useEffect` cleanup function, call `dataCaptureContext.setFrameSource(null)` to release the camera. Unlike BarcodeAr, do not call `removeMode`.
6. **Session data in `didScan`** — Access `session.recognizedBarcodes` (array, RN 7.0+) inside the `didScan` callback for the raw total count. Keep a copy of the array if you need it outside the callback — do not hold a reference to the session object. To validate scans against a picklist, **always** use `BarcodeCountCaptureList` + `BarcodeCountCaptureListListener.didUpdateSession` (see Step 9) — never compare `recognizedBarcodes` against a plain JS array.
7. **Brushes with Dot style only** — `recognizedBrush`, `notInListBrush`, `acceptedBrush`, `rejectedBrush`, and per-barcode brush methods only take effect when `viewStyle` is `BarcodeCountViewStyle.Dot`.
8. **Status provider requires RN 8.3+** — `setStatusProvider`, `shouldShowStatusModeButton`, `shouldShowStatusIconsOnScan` all require react-native=8.3+.
9. **Status provider callback pattern** — Call `callback.onStatusReady(result)` synchronously or after an async lookup. Do NOT use `await callback.onStatusReady(...)`.
10. **Imports** — Core types from `scandit-react-native-datacapture-core`; BarcodeCount types from `scandit-react-native-datacapture-barcode`.
11. **Pod install** — Run `npx pod-install@1.2.1` after installing or updating Scandit packages. Android auto-links.
12. **Camera permissions** — iOS: `NSCameraUsageDescription` in `Info.plist`. Android: runtime request via `PermissionsAndroid`.
13. **Metro cache** — If a package upgrade appears to have no effect at runtime, restart Metro with `npm start -- --reset-cache`.

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Nothing scans when the view mounts | Camera not started. Call `camera.switchToDesiredState(FrameSourceState.On)` in `useEffect`. |
| `view.listener` / `view.uiListener` not firing | They must be set in the `ref` callback, not as JSX props. |
| Brushes have no effect | Brushes only work with `viewStyle={BarcodeCountViewStyle.Dot}`. |
| App crashes on iOS after install | Run `npx pod-install@1.2.1` and rebuild. |
| `session.recognizedBarcodes` undefined | Requires react-native=7.0+. Check your installed package version. |
| `setStatusProvider` / status APIs not found | Requires react-native=8.3+. |
| `BarcodeCount.createRecommendedCameraSettings()` not found | Requires react-native=7.6+. Use `Camera.default` on older versions. |
| `new BarcodeCount(settings)` not found | Requires react-native=7.6+. Use `BarcodeCount.forDataCaptureContext(context, settings)` on older versions. |
| Counting does not resume after navigating back | Use `barcodeCount.reset()` + `clearAdditionalBarcodes()` only when explicitly restarting. Otherwise leave state intact and just turn the camera back on. |
| Validating scans by filtering `session.recognizedBarcodes` against a JS array | This approach cannot track quantities, does not drive the progress bar, and does not fire `didCompleteCaptureList`. Use `BarcodeCountCaptureList` + `setBarcodeCountCaptureList` instead (see Step 9). |
| `correctBarcodes` / `wrongBarcodes` / `missingBarcodes` are always empty | `setBarcodeCountCaptureList` was not called, or was called after the view started scanning. Call it immediately after constructing `BarcodeCount`, before mounting `BarcodeCountView`. |
| Progress bar not showing | `view.shouldShowListProgressBar` is `true` by default only when a capture list is attached. Ensure `setBarcodeCountCaptureList` was called. |
