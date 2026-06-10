# MatrixScan Count React Native Integration Guide

MatrixScan Count (API name: `BarcodeCount*`) is a multi-barcode scan-and-count mode that scans all barcodes in view simultaneously when the user taps the shutter button, and tracks the running total. In React Native it is rendered through a `<BarcodeCountView>` component that provides a full-featured counting UI out of the box: shutter button, progress bar, list button, exit button, hint overlays, and optional status icons.

> **Language note**: Examples below use TypeScript (`.tsx`) because it is the default for React Native templates. For plain JavaScript projects, drop the type annotations and keep the same imports and structure.

## Prerequisites

- Scandit React Native packages installed:
  - `scandit-react-native-datacapture-core`
  - `scandit-react-native-datacapture-barcode`
- After installing, run `npx pod-install` (or `cd ios && pod install`) for iOS. Android auto-links via Gradle — no manual step.
- Minimum SDK version: **6.17** for core BarcodeCount classes on React Native. `new BarcodeCount(settings)` constructor requires 7.6+. `tapToUncountEnabled` requires 7.0+. `BarcodeCountNotInListActionSettings` requires 7.1+. `BarcodeCountStatusProvider` and status-mode APIs require 8.3+.
- React Native `>=0.70`. The New Architecture (Fabric / TurboModules) is supported — no additional setup required beyond the standard RN template.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/<App>/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request at runtime via `PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.CAMERA)` before rendering the count screen.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which file they'd like to integrate MatrixScan Count into (typically the count screen component, e.g. `App.tsx`, `ScanPage.tsx`, or a screen module). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Install packages: `npm install scandit-react-native-datacapture-core scandit-react-native-datacapture-barcode`
2. Run `npx pod-install` (iOS). Android auto-links.
3. Add `NSCameraUsageDescription` to `ios/<App>/Info.plist`.
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key from https://ssl.scandit.com.
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

### 5a — Visibility Toggles

All properties are `boolean`. Set them in the `ref` callback.

| Property | Default | Description |
|----------|---------|-------------|
| `shouldShowUserGuidanceView` | `true` | Show the user guidance / loading view. |
| `shouldShowListProgressBar` | `true` | Show progress bar when a capture list is active. |
| `shouldShowListButton` | `true` | Show the list button (lower-left). |
| `shouldShowExitButton` | `true` | Show the exit button (lower-right). |
| `shouldShowShutterButton` | `true` | Show the center shutter button. |
| `shouldShowHints` | `true` | Show on-screen hints. |
| `shouldShowClearHighlightsButton` | `false` | Show the "clear highlights" button above the shutter. |
| `shouldShowSingleScanButton` | `false` | Show a single-scan button (lower-left). |
| `shouldShowStatusModeButton` | `false` | Show status mode toggle button (RN 8.3+). |
| `shouldShowFloatingShutterButton` | `false` | Show a draggable floating shutter button. |
| `shouldShowToolbar` | `true` | Show the collapsible toolbar at the top. |
| `shouldShowScanAreaGuides` | `false` | Debug: visualize the active scan area. |
| `shouldShowTorchControl` | `false` | Show torch on/off button (RN 6.26+). |
| `shouldShowStatusIconsOnScan` | `false` | Auto-load status icons immediately on scan, bypassing the manual toggle (RN 8.3+). |
| `shouldDisableModeOnExitButtonTapped` | `true` | Auto-disable mode when exit is tapped (RN 6.19+). |

```tsx
ref={view => {
  if (view) {
    view.shouldShowExitButton = false;
    view.shouldShowToolbar = false;
    view.shouldShowClearHighlightsButton = true;
    view.shouldShowTorchControl = true;
    view.listener = viewListenerRef.current;
    view.uiListener = viewUiListenerRef.current;
  }
}}
```

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

```typescript
import {
  BarcodeCountToolbarSettings,
} from 'scandit-react-native-datacapture-barcode';

ref={view => {
  if (view) {
    // BarcodeCountToolbarSettings constructor requires RN 8.3+
    const toolbarSettings = new BarcodeCountToolbarSettings();

    // Customize toolbar button labels and accessibility here (see section 5l below)
    toolbarSettings.audioOnButtonText = 'Sound On';
    toolbarSettings.audioOffButtonText = 'Sound Off';

    view.setToolbarSettings(toolbarSettings);

    // Set a status provider (RN 8.3+)
    view.setStatusProvider(myStatusProvider);
  }
}}
```

### 5l — BarcodeCountToolbarSettings (RN 8.3+)

`BarcodeCountToolbarSettings` controls the text labels and accessibility strings for the four toggle buttons in the collapsible toolbar: **audio**, **vibration**, **strap mode**, and **color scheme**. The constructor is available from react-native=8.3; all individual properties are available from react-native=6.17 but are only meaningful once the constructor is accessible.

#### Audio button

| Property | Platform | Description |
|----------|----------|-------------|
| `audioOnButtonText` | both | Label for the audio toggle when audio is **on**. |
| `audioOffButtonText` | both | Label for the audio toggle when audio is **off**. |
| `audioButtonAccessibilityHint` | iOS | VoiceOver hint for the audio toggle button. |
| `audioButtonAccessibilityLabel` | iOS | VoiceOver label for the audio toggle button. |
| `audioButtonContentDescription` | Android | TalkBack content description for the audio toggle button. |

```typescript
const toolbarSettings = new BarcodeCountToolbarSettings();

toolbarSettings.audioOnButtonText = 'Sound On';
toolbarSettings.audioOffButtonText = 'Sound Off';
toolbarSettings.audioButtonAccessibilityHint = 'Toggles scan sound';       // iOS VoiceOver
toolbarSettings.audioButtonAccessibilityLabel = 'Audio';                    // iOS VoiceOver
toolbarSettings.audioButtonContentDescription = 'Toggle scan audio';        // Android TalkBack

view.setToolbarSettings(toolbarSettings);
```

#### Vibration button

| Property | Platform | Description |
|----------|----------|-------------|
| `vibrationOnButtonText` | both | Label for the vibration toggle when vibration is **on**. |
| `vibrationOffButtonText` | both | Label for the vibration toggle when vibration is **off**. |
| `vibrationButtonAccessibilityHint` | iOS | VoiceOver hint for the vibration toggle button. |
| `vibrationButtonAccessibilityLabel` | iOS | VoiceOver label for the vibration toggle button. |
| `vibrationButtonContentDescription` | Android | TalkBack content description for the vibration toggle button. |

```typescript
const toolbarSettings = new BarcodeCountToolbarSettings();

toolbarSettings.vibrationOnButtonText = 'Vibration On';
toolbarSettings.vibrationOffButtonText = 'Vibration Off';
toolbarSettings.vibrationButtonAccessibilityHint = 'Toggles scan vibration'; // iOS VoiceOver
toolbarSettings.vibrationButtonAccessibilityLabel = 'Vibration';              // iOS VoiceOver
toolbarSettings.vibrationButtonContentDescription = 'Toggle vibration';       // Android TalkBack

view.setToolbarSettings(toolbarSettings);
```

#### Strap mode button

| Property | Platform | Description |
|----------|----------|-------------|
| `strapModeOnButtonText` | both | Label for the strap-mode toggle when strap mode is **on**. |
| `strapModeOffButtonText` | both | Label for the strap-mode toggle when strap mode is **off**. |
| `strapModeButtonAccessibilityHint` | iOS | VoiceOver hint for the strap-mode toggle button. |
| `strapModeButtonAccessibilityLabel` | iOS | VoiceOver label for the strap-mode toggle button. |
| `strapModeButtonContentDescription` | Android | TalkBack content description for the strap-mode toggle button. |

```typescript
const toolbarSettings = new BarcodeCountToolbarSettings();

toolbarSettings.strapModeOnButtonText = 'Strap Mode On';
toolbarSettings.strapModeOffButtonText = 'Strap Mode Off';
toolbarSettings.strapModeButtonAccessibilityHint = 'Toggles strap mode';    // iOS VoiceOver
toolbarSettings.strapModeButtonAccessibilityLabel = 'Strap Mode';            // iOS VoiceOver
toolbarSettings.strapModeButtonContentDescription = 'Toggle strap mode';     // Android TalkBack

view.setToolbarSettings(toolbarSettings);
```

#### Color scheme button

| Property | Platform | Description |
|----------|----------|-------------|
| `colorSchemeOnButtonText` | both | Label for the color-scheme toggle when the alternate color scheme is **on**. |
| `colorSchemeOffButtonText` | both | Label for the color-scheme toggle when the alternate color scheme is **off**. |
| `colorSchemeButtonAccessibilityHint` | iOS | VoiceOver hint for the color-scheme toggle button. |
| `colorSchemeButtonAccessibilityLabel` | iOS | VoiceOver label for the color-scheme toggle button. |
| `colorSchemeButtonContentDescription` | Android | TalkBack content description for the color-scheme toggle button. |

```typescript
const toolbarSettings = new BarcodeCountToolbarSettings();

toolbarSettings.colorSchemeOnButtonText = 'High Contrast On';
toolbarSettings.colorSchemeOffButtonText = 'High Contrast Off';
toolbarSettings.colorSchemeButtonAccessibilityHint = 'Toggles color scheme';  // iOS VoiceOver
toolbarSettings.colorSchemeButtonAccessibilityLabel = 'Color Scheme';          // iOS VoiceOver
toolbarSettings.colorSchemeButtonContentDescription = 'Toggle color scheme';   // Android TalkBack

view.setToolbarSettings(toolbarSettings);
```

#### All toolbar properties at once

```typescript
ref={view => {
  if (view) {
    const toolbarSettings = new BarcodeCountToolbarSettings();

    // Audio toggle labels
    toolbarSettings.audioOnButtonText = 'Sound On';
    toolbarSettings.audioOffButtonText = 'Sound Off';
    toolbarSettings.audioButtonAccessibilityLabel = 'Audio';
    toolbarSettings.audioButtonAccessibilityHint = 'Toggles scan audio feedback';
    toolbarSettings.audioButtonContentDescription = 'Toggle scan audio';

    // Vibration toggle labels
    toolbarSettings.vibrationOnButtonText = 'Vibration On';
    toolbarSettings.vibrationOffButtonText = 'Vibration Off';
    toolbarSettings.vibrationButtonAccessibilityLabel = 'Vibration';
    toolbarSettings.vibrationButtonAccessibilityHint = 'Toggles scan vibration feedback';
    toolbarSettings.vibrationButtonContentDescription = 'Toggle vibration';

    // Strap mode toggle labels
    toolbarSettings.strapModeOnButtonText = 'Strap Mode On';
    toolbarSettings.strapModeOffButtonText = 'Strap Mode Off';
    toolbarSettings.strapModeButtonAccessibilityLabel = 'Strap Mode';
    toolbarSettings.strapModeButtonAccessibilityHint = 'Enables scanning in strap mode';
    toolbarSettings.strapModeButtonContentDescription = 'Toggle strap mode';

    // Color scheme toggle labels
    toolbarSettings.colorSchemeOnButtonText = 'High Contrast On';
    toolbarSettings.colorSchemeOffButtonText = 'High Contrast Off';
    toolbarSettings.colorSchemeButtonAccessibilityLabel = 'Color Scheme';
    toolbarSettings.colorSchemeButtonAccessibilityHint = 'Toggles high-contrast color scheme';
    toolbarSettings.colorSchemeButtonContentDescription = 'Toggle color scheme';

    view.setToolbarSettings(toolbarSettings);

    view.listener = viewListenerRef.current;
    view.uiListener = viewUiListenerRef.current;
  }
}}
```

> **Note**: `BarcodeCountToolbarSettings` constructor is available from react-native=8.3. All individual string properties are present from react-native=6.17 but the class cannot be instantiated on earlier SDK versions. Accessibility hint/label properties apply only on iOS; content description properties apply only on Android. Leaving any property unset causes the SDK to use its built-in default string.

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

> **This is the canonical way to validate scans against a picklist, packing slip, or backend order.**
> Do NOT compare scanned data against a plain JavaScript array. `BarcodeCountCaptureList` is the only
> mechanism that produces correct `correctBarcodes` / `wrongBarcodes` / `missingBarcodes` session data
> and drives the built-in progress bar. A JS array comparison will miss quantity tracking, will not
> drive the view's visual states, and will not trigger `didCompleteCaptureList`.

This section is a complete, end-to-end recipe for the "scan against a list" use case.

---

### 9a — Modeling the target list

A typical packing slip or picklist arrives from a backend API as a JSON array:

```json
[
  { "symbology": "ean13Upca", "data": "4006381333931", "quantity": 2 },
  { "symbology": "ean13Upca", "data": "4006381333948", "quantity": 1 },
  { "symbology": "code128",   "data": "ITEM-ABC-001",  "quantity": 3 }
]
```

Convert each entry to a `TargetBarcode` using `TargetBarcode.create(data, quantity)`. The `data` field
is a plain string (the barcode's decoded value). Symbology is not stored on `TargetBarcode` — it is
enforced by enabling the correct symbologies in `BarcodeCountSettings` (see step 9c).

```typescript
import {
  BarcodeCountCaptureList,
  BarcodeCountCaptureListListener,
  BarcodeCountCaptureListSession,
  TargetBarcode,
} from 'scandit-react-native-datacapture-barcode';
import { useMemo, useRef } from 'react';

// Shape of a picklist item from your backend
interface PicklistItem {
  symbology: string;
  data: string;
  quantity: number;
}

// Example picklist — in practice this comes from navigation params or a React context
const PICKLIST: PicklistItem[] = [
  { symbology: 'ean13Upca', data: '4006381333931', quantity: 2 },
  { symbology: 'ean13Upca', data: '4006381333948', quantity: 1 },
  { symbology: 'code128',   data: 'ITEM-ABC-001',  quantity: 3 },
];

export const ScanPage = () => {
  // Build TargetBarcode[] once — useMemo prevents rebuild on every render
  const targetBarcodes = useMemo<TargetBarcode[]>(
    () => PICKLIST.map(item => TargetBarcode.create(item.data, item.quantity)),
    [] // static list; add PICKLIST to deps if it changes at runtime
  );

  // ...rest of component (see below)
};
```

`TargetBarcode` API:

```typescript
const target = TargetBarcode.create('4006381333931', 2);
console.log(target.data);     // '4006381333931'
console.log(target.quantity); // 2  — must be >= 1
```

---

### 9b — Wiring the list to the mode

Construct `BarcodeCountCaptureList` with `BarcodeCountCaptureList.create(listener, targetBarcodes)`,
then call `barcodeCount.setBarcodeCountCaptureList(captureList)` **immediately after** constructing
the `BarcodeCount` mode.

> **Critical**: If you skip `setBarcodeCountCaptureList`, the view renders in "free count" mode —
> no matched/not-in-list distinction, no progress bar, no `didCompleteCaptureList` callback.

```typescript
import {
  BarcodeCount,
  BarcodeCountCaptureList,
  BarcodeCountCaptureListListener,
  BarcodeCountCaptureListSession,
  BarcodeCountSettings,
  Symbology,
  TargetBarcode,
} from 'scandit-react-native-datacapture-barcode';
import dataCaptureContext from './CaptureContext';

// Inside your function component, after targetBarcodes is built with useMemo:

const barcodeCountRef = useRef<BarcodeCount>(null!);
const captureListRef = useRef<BarcodeCountCaptureList>(null!);

if (!barcodeCountRef.current) {
  const settings = new BarcodeCountSettings();
  // Enable every symbology that appears in your picklist
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.EAN8,
    Symbology.UPCE,
    Symbology.Code128,
  ]);

  const barcodeCount = new BarcodeCount(settings);

  // BarcodeCountListener — fires once per shutter tap
  barcodeCount.addListener({
    didScan: async (_: BarcodeCount, session) => {
      // session.recognizedBarcodes: Barcode[] — all barcodes seen so far
      console.log('Total recognized:', session.recognizedBarcodes.length);
    },
  });

  // Build the capture list listener (see section 9d for full implementation)
  const captureListListener: BarcodeCountCaptureListListener = {
    didUpdateSession: (list: BarcodeCountCaptureList, session: BarcodeCountCaptureListSession) => {
      console.log('Correct:', session.correctBarcodes.length);
      console.log('Wrong (not in list):', session.wrongBarcodes.length);
      console.log('Missing:', session.missingBarcodes.length);
    },
  };

  const captureList = BarcodeCountCaptureList.create(captureListListener, targetBarcodes);

  // REQUIRED: attach the list to the mode
  barcodeCount.setBarcodeCountCaptureList(captureList);

  barcodeCountRef.current = barcodeCount;
  captureListRef.current = captureList;
}
```

---

### 9c — Handling matched / not-in-list visualization

When `viewStyle` is `BarcodeCountViewStyle.Dot`, the three visual states are driven by three brush
properties on `BarcodeCountView`:

| State | Session source | Brush property | Recommended color |
|-------|---------------|----------------|-------------------|
| Scanned and in list (`correctBarcodes`) | `session.correctBarcodes` | `view.recognizedBrush` | Green `#4CAF50` |
| Scanned but not in list (`wrongBarcodes`) | `session.wrongBarcodes` | `view.notInListBrush` | Red `#F44336` |
| Accepted by user (via not-in-list popup) | `session.acceptedBarcodes` | `view.acceptedBrush` | Blue `#2196F3` |

Set global brushes in the `ref` callback:

```tsx
import { Brush, Color } from 'scandit-react-native-datacapture-core';
import { BarcodeCountViewStyle } from 'scandit-react-native-datacapture-barcode';

<BarcodeCountView
  style={{ flex: 1 }}
  barcodeCount={barcodeCountRef.current}
  context={dataCaptureContext}
  viewStyle={BarcodeCountViewStyle.Dot}
  ref={view => {
    if (view) {
      // Matched-on-list = green
      view.recognizedBrush = new Brush(
        Color.fromHex('#4CAF50'),
        Color.fromHex('#4CAF50'),
        1,
      );
      // Not-in-list = red
      view.notInListBrush = new Brush(
        Color.fromHex('#F44336'),
        Color.fromHex('#F44336'),
        1,
      );
      // Accepted via the not-in-list popup = blue (RN 7.1+)
      view.acceptedBrush = new Brush(
        Color.fromHex('#2196F3'),
        Color.fromHex('#2196F3'),
        1,
      );

      // Show the built-in progress bar
      view.shouldShowListProgressBar = true;

      view.listener = viewListenerRef.current;
      view.uiListener = viewUiListenerRef.current;
    }
  }}
/>
```

For dynamic per-barcode colors (e.g. to shade items by how close they are to their target quantity),
call `setBrushForRecognizedBarcodeNotInList` imperatively from inside `BarcodeCountViewListener`:

```typescript
const viewListener: BarcodeCountViewListener = {
  brushForRecognizedBarcodeNotInList: (view, trackedBarcode) => {
    // Return a custom brush based on the barcode's data
    const isKnownExtra = myExtraItemSet.has(trackedBarcode.barcode.data ?? '');
    return isKnownExtra
      ? new Brush(Color.fromHex('#FF9800'), Color.fromHex('#FF9800'), 1)  // orange: known extra
      : new Brush(Color.fromHex('#F44336'), Color.fromHex('#F44336'), 1); // red: unexpected
  },
};
```

---

### 9d — Wiring BarcodeCountCaptureListListener

`BarcodeCountCaptureListListener` is the primary hook for reacting to list progress. It fires
alongside (not instead of) `BarcodeCountListener.didScan` — both listeners co-exist on the same
`BarcodeCount` instance.

The JavaScript method name on `BarcodeCountCaptureListListener` is **`didUpdateSession`**
(`:available: react-native=6.17`). On RN 8.3+, `didCompleteCaptureList` is also available on the
listener (in addition to `BarcodeCountViewListener.didCompleteCaptureList`).

```typescript
import {
  BarcodeCountCaptureList,
  BarcodeCountCaptureListListener,
  BarcodeCountCaptureListSession,
  TargetBarcode,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';

// Hold derived state in a ref so it is available when navigating to results
const listSessionRef = useRef<{
  correct: TrackedBarcode[];
  wrong: TrackedBarcode[];
  missing: TargetBarcode[];
}>({ correct: [], wrong: [], missing: [] });

const captureListListener: BarcodeCountCaptureListListener = {
  /**
   * Called after each frame that changes the list state.
   *
   * session.correctBarcodes  — TrackedBarcode[] matched to a TargetBarcode
   * session.wrongBarcodes    — TrackedBarcode[] scanned but NOT in the target list
   * session.missingBarcodes  — TargetBarcode[]  not yet scanned
   */
  didUpdateSession: (
    _list: BarcodeCountCaptureList,
    session: BarcodeCountCaptureListSession,
  ) => {
    const correct = session.correctBarcodes;
    const wrong   = session.wrongBarcodes;
    const missing = session.missingBarcodes;

    // Cache for the results screen
    listSessionRef.current = { correct, wrong, missing };

    // Compute progress: how many distinct target items have been fulfilled
    const fulfilledCount = targetBarcodes.length - missing.length;
    const total = targetBarcodes.length;
    console.log(`Progress: ${fulfilledCount}/${total} items, ${wrong.length} extras`);
  },

  // RN 8.3+: fires when ALL target barcodes have been scanned at the required quantity
  didCompleteCaptureList: (_list: BarcodeCountCaptureList, _session: BarcodeCountCaptureListSession) => {
    console.log('All items scanned — capture list complete');
  },
};
```

---

### 9e — Progress UI

Surface progress to the user in two complementary ways:

**Built-in progress bar** — turn on `shouldShowListProgressBar` on the view (already shown in 9c).
The SDK drives it automatically from the capture list session.

**Custom progress text** — derive counts from the `listSessionRef` kept in 9d and display them
in your own UI:

```tsx
import React, { useState } from 'react';
import { Text, View } from 'react-native';

// State driven from the listSessionRef inside didUpdateSession:
const [progress, setProgress] = useState({ fulfilled: 0, total: 0, extras: 0 });

// Inside didUpdateSession, after computing counts:
const captureListListener: BarcodeCountCaptureListListener = {
  didUpdateSession: (_list, session) => {
    listSessionRef.current = {
      correct: session.correctBarcodes,
      wrong:   session.wrongBarcodes,
      missing: session.missingBarcodes,
    };

    const fulfilled = targetBarcodes.length - session.missingBarcodes.length;
    setProgress({
      fulfilled,
      total:  targetBarcodes.length,
      extras: session.wrongBarcodes.length,
    });
  },
};

// In JSX:
<View style={{ padding: 8 }}>
  <Text>{progress.fulfilled} of {progress.total} items scanned</Text>
  {progress.extras > 0 && (
    <Text style={{ color: '#F44336' }}>{progress.extras} unexpected item(s) detected</Text>
  )}
</View>
```

To sum quantities rather than count distinct target items, reduce over the original `targetBarcodes`
array and subtract quantities still present in `session.missingBarcodes`:

```typescript
const totalQty = targetBarcodes.reduce((sum, t) => sum + t.quantity, 0);
const missingQty = session.missingBarcodes.reduce((sum, t) => sum + t.quantity, 0);
const scannedQty = totalQty - missingQty;
// => "X of Y units scanned"
```

---

### 9f — Results screen

When the user taps the list button or the exit button, navigate to a results screen. Derive the
three lists from `listSessionRef.current`:

```tsx
// ResultsPage.tsx
import React from 'react';
import { FlatList, SectionList, Text, View } from 'react-native';
import { TargetBarcode, TrackedBarcode } from 'scandit-react-native-datacapture-barcode';

interface ResultsPageProps {
  correct: TrackedBarcode[];    // matched to target — show with checkmark
  wrong: TrackedBarcode[];      // not in list — show as unexpected
  missing: TargetBarcode[];     // never scanned — show as missing
}

export const ResultsPage = ({ correct, wrong, missing }: ResultsPageProps) => {
  const sections = [
    {
      title: `Matched (${correct.length})`,
      data: correct.map(tb => ({
        key: tb.barcode.data ?? '',
        label: `✓ ${tb.barcode.data}`,
        color: '#4CAF50',
      })),
    },
    {
      title: `Missing (${missing.length})`,
      data: missing.map(tb => ({
        key: tb.data + tb.quantity,
        label: `✗ ${tb.data}  ×${tb.quantity}`,
        color: '#9E9E9E',
      })),
    },
    {
      title: `Unexpected (${wrong.length})`,
      data: wrong.map(tb => ({
        key: tb.barcode.data ?? '',
        label: `! ${tb.barcode.data}`,
        color: '#F44336',
      })),
    },
  ];

  return (
    <SectionList
      sections={sections}
      keyExtractor={item => item.key}
      renderSectionHeader={({ section }) => (
        <Text style={{ fontWeight: 'bold', padding: 8 }}>{section.title}</Text>
      )}
      renderItem={({ item }) => (
        <Text style={{ color: item.color, paddingLeft: 16, paddingVertical: 4 }}>
          {item.label}
        </Text>
      )}
    />
  );
};
```

Wire it from `BarcodeCountViewUiListener`:

```typescript
const viewUiListener: BarcodeCountViewUiListener = {
  didTapListButton: (_: BarcodeCountView) => {
    navigation.navigate('Results', {
      correct: listSessionRef.current.correct,
      wrong:   listSessionRef.current.wrong,
      missing: listSessionRef.current.missing,
    });
  },
  didTapExitButton: (_: BarcodeCountView) => {
    camera.switchToDesiredState(FrameSourceState.Off);
    navigation.navigate('Results', {
      correct: listSessionRef.current.correct,
      wrong:   listSessionRef.current.wrong,
      missing: listSessionRef.current.missing,
    });
  },
};
```

---

### 9g — Exit / re-entry behavior

The capture list **persists across scanning phases** — navigating to a results screen and returning
does not reset it. This is intentional: the user can scan more items and the already-matched barcodes
remain matched.

To resume scanning when the user navigates back:

```typescript
useFocusEffect(
  useCallback(() => {
    // Camera was off while on the results screen — turn it back on
    cameraRef.current.switchToDesiredState(FrameSourceState.On);
    barcodeCountRef.current.isEnabled = true;
  }, [])
);
```

To **swap to a new picklist** (e.g. the user moves to the next order):

```typescript
async function loadNewPicklist(newItems: PicklistItem[]) {
  const newTargetBarcodes = newItems.map(item =>
    TargetBarcode.create(item.data, item.quantity)
  );

  // 1. Build and attach the new list
  const newList = BarcodeCountCaptureList.create(captureListListener, newTargetBarcodes);
  barcodeCountRef.current.setBarcodeCountCaptureList(newList);
  captureListRef.current = newList;

  // 2. Clear all visual highlights so the previous order's dots disappear
  await viewRef.current?.clearHighlights();

  // 3. Reset the BarcodeCount session (clears recognizedBarcodes history)
  await barcodeCountRef.current.reset();

  // 4. Reset local progress state
  listSessionRef.current = { correct: [], wrong: [], missing: [] };
}
```

> **Note**: Calling `barcodeCount.setBarcodeCountCaptureList(newList)` alone does NOT clear the
> visual highlights from the previous list — always follow it with `view.clearHighlights()` when
> switching lists mid-session.

---

### 9h — Common pitfalls

- **Do NOT compare scanned data against a plain JS array.** Only `BarcodeCountCaptureList` produces
  correct `correctBarcodes` / `wrongBarcodes` / `missingBarcodes` session data, drives the progress
  bar, and fires `didCompleteCaptureList`. A JS array comparison cannot replicate this behavior.

- **`TargetBarcode.create(data, quantity)` requires quantity ≥ 1.** Passing `0` produces
  undefined behavior. Guard against zero-quantity items in your picklist before creating
  `TargetBarcode` objects.

- **`BarcodeCountCaptureList` is symbology-agnostic.** Symbology filtering is enforced
  by `BarcodeCountSettings.enableSymbology`. If your picklist contains EAN-13 items but
  EAN-13 is not enabled in settings, those barcodes will never be recognized and will
  always appear in `missingBarcodes`. Ensure every symbology present in your picklist
  is enabled in settings.

- **`BarcodeCountCaptureListListener.didUpdateSession` fires alongside
  `BarcodeCountListener.didScan`, not instead of it.** Both listeners co-exist on the same
  `BarcodeCount` instance. Use `didScan` for the raw recognized-barcodes array and
  `didUpdateSession` for list-aware progress.

- **`setBarcodeCountCaptureList` must be called before the view mounts (or immediately
  after mode construction).** Calling it after the view is already scanning works but may
  produce a single frame with incorrect visual state.

- **The `didCompleteCaptureList` callback on `BarcodeCountCaptureListListener` requires
  react-native=8.3+.** On earlier versions, listen to `BarcodeCountViewListener.didCompleteCaptureList`
  instead (available from react-native=6.17 on the view listener).

---

### TargetBarcode quick reference

```typescript
// TargetBarcode.create(data, quantity)
// :available: react-native=6.17
const target = TargetBarcode.create('4006381333931', 2);
console.log(target.data);     // '4006381333931'
console.log(target.quantity); // 2
```

### BarcodeCountCaptureListSession property reference

| Property | Type | Description | Available |
|----------|------|-------------|-----------|
| `correctBarcodes` | `TrackedBarcode[]` | Scanned barcodes that matched a TargetBarcode in the list. | react-native=6.17 |
| `wrongBarcodes` | `TrackedBarcode[]` | Scanned barcodes that did NOT match any TargetBarcode. | react-native=6.17 |
| `missingBarcodes` | `TargetBarcode[]` | Target barcodes not yet scanned at the required quantity. | react-native=6.17 |
| `acceptedBarcodes` | `TrackedBarcode[]` | Barcodes accepted via the not-in-list action popup. | react-native=7.1 |
| `rejectedBarcodes` | `TrackedBarcode[]` | Barcodes rejected via the not-in-list action popup. | react-native=7.1 |
| `additionalBarcodes` | `Barcode[]` | Barcodes injected with `setAdditionalBarcodes`. | react-native=6.17 |

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
11. **Pod install** — Run `npx pod-install` after installing or updating Scandit packages. Android auto-links.
12. **Camera permissions** — iOS: `NSCameraUsageDescription` in `Info.plist`. Android: runtime request via `PermissionsAndroid`.
13. **Metro cache** — If a package upgrade appears to have no effect at runtime, restart Metro with `npm start -- --reset-cache`.

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Nothing scans when the view mounts | Camera not started. Call `camera.switchToDesiredState(FrameSourceState.On)` in `useEffect`. |
| `view.listener` / `view.uiListener` not firing | They must be set in the `ref` callback, not as JSX props. |
| Brushes have no effect | Brushes only work with `viewStyle={BarcodeCountViewStyle.Dot}`. |
| App crashes on iOS after install | Run `npx pod-install` and rebuild. |
| `session.recognizedBarcodes` undefined | Requires react-native=7.0+. Check your installed package version. |
| `setStatusProvider` / status APIs not found | Requires react-native=8.3+. |
| `BarcodeCount.createRecommendedCameraSettings()` not found | Requires react-native=7.6+. Use `Camera.default` on older versions. |
| `new BarcodeCount(settings)` not found | Requires react-native=7.6+. Use `BarcodeCount.forDataCaptureContext(context, settings)` on older versions. |
| Counting does not resume after navigating back | Use `barcodeCount.reset()` + `clearAdditionalBarcodes()` only when explicitly restarting. Otherwise leave state intact and just turn the camera back on. |
| Validating scans by filtering `session.recognizedBarcodes` against a JS array | This approach cannot track quantities, does not drive the progress bar, and does not fire `didCompleteCaptureList`. Use `BarcodeCountCaptureList` + `setBarcodeCountCaptureList` instead (see Step 9). |
| `correctBarcodes` / `wrongBarcodes` / `missingBarcodes` are always empty | `setBarcodeCountCaptureList` was not called, or was called after the view started scanning. Call it immediately after constructing `BarcodeCount`, before mounting `BarcodeCountView`. |
| Progress bar not showing | `view.shouldShowListProgressBar` is `true` by default only when a capture list is attached. Ensure `setBarcodeCountCaptureList` was called. |
