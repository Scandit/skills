# MatrixScan AR React Native Integration Guide

MatrixScan AR (API name: `BarcodeAr*`) is a multi-barcode AR mode that tracks all barcodes in view simultaneously and overlays highlights and annotations on each one in real time. In React Native it is rendered through a `<BarcodeArView>` component that wraps your screen content. AR overlays appear on top of the children; the children render under the native AR layer.

> **Language note**: Examples below use TypeScript (`.tsx`) because it is the default for React Native templates. For plain JavaScript projects, drop the type annotations and keep the same imports and structure.

## Prerequisites

- Scandit React Native packages installed:
  - `scandit-react-native-datacapture-core`
  - `scandit-react-native-datacapture-barcode`
- After installing, run `npx pod-install` (or `cd ios && pod install`) for iOS. Android auto-links via Gradle — no manual step.
- Minimum SDK version: **7.1** for core BarcodeAr classes. `BarcodeArCustomHighlight` requires 8.0+. `BarcodeArCustomAnnotation` requires 8.1+. `BarcodeArResponsiveAnnotation` requires 8.2+.
- React Native `>=0.70`. The New Architecture (Fabric / TurboModules) is supported — no additional setup required beyond the standard RN template.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/<App>/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request at runtime via `PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.CAMERA)` before rendering the AR screen.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which file they'd like to integrate MatrixScan AR into (typically the AR screen component, e.g. `App.tsx`, `ArScreen.tsx`, or a page module). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

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

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

DataCaptureContext.initialize(licenseKey);

export default DataCaptureContext.sharedInstance;
```

- `DataCaptureContext.initialize(licenseKey)` is the v8 API. It is idempotent per process — call it once.
- `DataCaptureContext.sharedInstance` is the singleton accessor used everywhere else in the app.
- Do **not** create additional `DataCaptureContext` instances — there is only one per app.

> **Important**: Put the `initialize(...)` call at the top of a dedicated module so it runs on first import and before any component that uses `sharedInstance` mounts.

## Step 2 — Configure BarcodeArSettings

Choose which barcode symbologies to scan. Only enable what you need — each extra symbology adds processing time.

```typescript
import {
  BarcodeArSettings,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';

const settings = new BarcodeArSettings();

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
```

### BarcodeArSettings Properties and Methods

| Member | Description |
|--------|-------------|
| `enableSymbologies(symbologies)` | Enable multiple symbologies at once. |
| `enableSymbology(symbology, enabled)` | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | Get per-symbology settings (e.g. `activeSymbolCounts`). |
| `enabledSymbologies` | Read-only array of currently enabled symbologies. |
| `setProperty(name, value)` / `getProperty(name)` | Advanced property access by name. |

## Step 3 — Construct BarcodeAr and attach to context

The recommended pattern is to hold the `BarcodeAr` instance in a `useRef` so it survives re-renders without being recreated, and to register the listener inside that same initialization block.

```tsx
import React, { useEffect, useRef } from 'react';
import {
  BarcodeAr,
  BarcodeArSettings,
  BarcodeArListener,
  BarcodeArSession,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';
import dataCaptureContext from './CaptureContext';

function createBarcodeAr(): BarcodeAr {
  const settings = new BarcodeArSettings();
  settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);
  return new BarcodeAr(settings);
}

export const ArScreen = () => {
  // Create the mode once — persist across re-renders.
  const barcodeArRef = useRef<BarcodeAr>(null!);
  if (!barcodeArRef.current) {
    const barcodeAr = createBarcodeAr();
    // Attach a listener before adding the mode to the context.
    const listener: BarcodeArListener = {
      didUpdateSession: async (_barcodeAr: BarcodeAr, session: BarcodeArSession) => {
        // session.addedTrackedBarcodes — newly tracked barcodes this frame
        // session.removedTrackedBarcodes — IDs of barcodes that left the frame
        // session.trackedBarcodes — all currently tracked barcodes
      },
    };
    barcodeAr.addListener(listener);
    // Attach the mode to the shared context.
    dataCaptureContext.addMode(barcodeAr);
    barcodeArRef.current = barcodeAr;
  }

  useEffect(() => {
    return () => {
      dataCaptureContext.removeMode(barcodeArRef.current);
    };
  }, []);

  // ...render (see Step 4)
};
```

### BarcodeAr Methods

| Method | Description |
|--------|-------------|
| `new BarcodeAr(settings)` | Constructs a new instance. Available from react-native=7.6. |
| `addListener(listener)` / `removeListener(listener)` | Register/remove a session listener. |
| `applySettings(settings)` | Update settings at runtime (async). |
| `BarcodeAr.createRecommendedCameraSettings()` | Returns camera settings optimized for BarcodeAr. Available from react-native=7.6. |
| `feedback` | Read/write `BarcodeArFeedback` property — see Step 8. |

## Step 4 — BarcodeArViewSettings and BarcodeArView

`<BarcodeArView>` is a React component that hosts a native platform view. Pass the context, the BarcodeAr mode, view settings, and optional providers and listeners as props. Children render **under** the native AR overlay.

### BarcodeArViewSettings

```typescript
import { BarcodeArViewSettings } from 'scandit-react-native-datacapture-barcode';

const viewSettings = new BarcodeArViewSettings();
viewSettings.soundEnabled = true;   // default: true
viewSettings.hapticEnabled = true;  // default: true
```

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `soundEnabled` | `boolean` | `true` | Whether sound feedback is enabled. |
| `hapticEnabled` | `boolean` | `true` | Whether haptic (vibration) feedback is enabled. |
| `defaultCameraPosition` | `CameraPosition` | `WorldFacing` | The default camera to use. |

### BarcodeArView JSX

```tsx
import { View, Text } from 'react-native';
import {
  BarcodeArView,
  BarcodeArViewSettings,
} from 'scandit-react-native-datacapture-barcode';

return (
  <BarcodeArView
    style={{ flex: 1 }}
    context={dataCaptureContext}
    barcodeAr={barcodeArRef.current}
    settings={new BarcodeArViewSettings()}
    highlightProvider={highlightProvider}
    annotationProvider={annotationProvider}
    uiListener={viewUiListener}
    ref={(view: BarcodeArView | null) => {
      if (view) {
        view.start();          // REQUIRED: start scanning explicitly
        view.shouldShowTorchControl = false;
        view.shouldShowZoomControl = false;
        view.shouldShowCameraSwitchControl = true;
      }
    }}
  >
    {/* Children render under the AR overlay */}
    <View style={{ flex: 1, padding: 16 }}>
      <Text>Content here</Text>
    </View>
  </BarcodeArView>
);
```

> **Important**: Unlike SparkScan, `BarcodeArView` does NOT start automatically on mount. You must call `view.start()` in the `ref` callback.

### BarcodeArView Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `context` | `DataCaptureContext` | Yes | The shared DataCaptureContext singleton. |
| `barcodeAr` | `BarcodeAr` | Yes | The BarcodeAr mode instance. |
| `settings` | `BarcodeArViewSettings` | No | View-level configuration. Pass `new BarcodeArViewSettings()` for defaults. |
| `highlightProvider` | `BarcodeArHighlightProvider` | No | Provider that returns a highlight for each barcode. |
| `annotationProvider` | `BarcodeArAnnotationProvider` | No | Provider that returns an annotation for each barcode. |
| `uiListener` | `BarcodeArViewUiListener` | No | Receives tap events on highlights. |
| `cameraSettings` | `CameraSettings` | No | Override camera settings. Use `BarcodeAr.createRecommendedCameraSettings()` if needed. |
| `style` | `ViewStyle` | Yes | React Native style — typically `{ flex: 1 }`. |

### BarcodeArView Imperative Properties (set via ref)

| Property | Type | Description |
|----------|------|-------------|
| `shouldShowTorchControl` | `boolean` | Show/hide torch button. Default: `false`. |
| `torchControlPosition` | `Anchor` | Position of the torch button. Default: `TopLeft`. |
| `shouldShowZoomControl` | `boolean` | Show/hide zoom button. |
| `zoomControlPosition` | `Anchor` | Position of the zoom button. Default: `BottomRight`. |
| `shouldShowCameraSwitchControl` | `boolean` | Show/hide camera switch button. |
| `cameraSwitchControlPosition` | `Anchor` | Position of the camera switch button. Default: `TopRight`. |
| `shouldShowMacroModeControl` | `boolean` | Show/hide macro mode button (iOS only). |

### BarcodeArViewUiListener

Receives tap events on barcode highlights:

```tsx
import { BarcodeArViewUiListener } from 'scandit-react-native-datacapture-barcode';

const viewUiListener: BarcodeArViewUiListener = {
  didTapHighlightForBarcode(_barcodeAr, barcode, _highlight) {
    console.log('Tapped barcode:', barcode.data);
  },
};
```

### BarcodeArView Methods (called imperatively)

| Method | Description |
|--------|-------------|
| `start()` | Starts the scanning process. Call in the ref callback. |
| `stop()` | Stops the scanning process. |
| `pause()` | Pauses the scanning process. |
| `reset()` | Clears all highlights and annotations; re-queries providers. |

## Step 5 — BarcodeArListener

`BarcodeArListener` receives session updates on every frame where the set of tracked barcodes changes. Register the listener on the `BarcodeAr` instance (not the view).

```tsx
import {
  BarcodeAr,
  BarcodeArSession,
  BarcodeArListener,
} from 'scandit-react-native-datacapture-barcode';

const listener: BarcodeArListener = {
  didUpdateSession: async (barcodeAr: BarcodeAr, session: BarcodeArSession, getFrameData) => {
    // session.addedTrackedBarcodes — TrackedBarcode[] newly added this frame
    for (const tracked of session.addedTrackedBarcodes) {
      console.log('New barcode:', tracked.barcode.data, tracked.barcode.symbology);
    }

    // session.removedTrackedBarcodes — string[] of IDs that left the frame
    // session.trackedBarcodes — { [id: string]: TrackedBarcode } all current barcodes

    // If you need the raw frame image (uncommon):
    // const frameData = await getFrameData();
  },
};

barcodeAr.addListener(listener);
```

### BarcodeArListener Interface

All callbacks are optional. Implement only what you need.

| Callback | Signature | Description |
|----------|-----------|-------------|
| `didUpdateSession` | `(barcodeAr, session, getFrameData?) => Promise<void>` | Called when the tracked barcode set is updated. |

### BarcodeArSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `addedTrackedBarcodes` | `TrackedBarcode[]` | Barcodes newly tracked this frame. |
| `removedTrackedBarcodes` | `string[]` | IDs of barcodes that left the camera view. |
| `trackedBarcodes` | `{ [id: string]: TrackedBarcode }` | All currently tracked barcodes. |
| `reset()` | `Promise<void>` | Resets the session and clears all tracked barcodes. |

> **Note**: `TrackedBarcode` wraps a `Barcode` (accessible via `tracked.barcode`) plus tracking state. Use `barcode.data` and `barcode.symbology` to read the content.

## Step 6 — Highlights

Highlights are colored shapes that appear directly over each scanned barcode. Supply them through a `BarcodeArHighlightProvider` passed as the `highlightProvider` prop on `<BarcodeArView>`.

### Provider pattern

The provider fires **once per barcode** (asynchronously) when a barcode is first detected. Return `null` to show no highlight.

```tsx
import {
  BarcodeArHighlightProvider,
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
  Barcode,
} from 'scandit-react-native-datacapture-barcode';
import { Brush, Color } from 'scandit-react-native-datacapture-core';

const highlightProvider: BarcodeArHighlightProvider = {
  highlightForBarcode: async (barcode: Barcode) => {
    // Return the desired highlight, or null for no highlight.
    const highlight = new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Dot);
    highlight.brush = new Brush(
      Color.fromHex('#4D99FF'),  // fill (ARGB hex)
      Color.fromHex('#4D99FF'),  // stroke
      1.0,                       // stroke width
    );
    return highlight;
  },
};
```

### BarcodeArCircleHighlight

Draws a circle on top of the barcode. Two presets are available.

| Preset | Description |
|--------|-------------|
| `BarcodeArCircleHighlightPreset.Dot` | Small circle, good for dense barcode grids. |
| `BarcodeArCircleHighlightPreset.Icon` | Larger circle, suitable for showing an icon inside. |

```typescript
import {
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
} from 'scandit-react-native-datacapture-barcode';
import { Brush, Color } from 'scandit-react-native-datacapture-core';

// Dot preset with custom brush
const dot = new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Dot);
dot.brush = new Brush(Color.fromHex('#4D99FF'), Color.fromHex('#0055CC'), 2);
dot.size = 30;  // diameter in device-independent pixels (min 18)

// Icon preset
const icon = new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Icon);
```

Key properties:

| Property | Type | Description |
|----------|------|-------------|
| `brush` | `Brush` | Fill color, stroke color, stroke width. |
| `size` | `number` | Circle diameter in dp. Minimum 18. |
| `icon` | `ScanditIcon \| null` | Optional icon rendered inside the circle. |

### BarcodeArRectangleHighlight

Draws a rectangle that matches the barcode bounding box.

```typescript
import { BarcodeArRectangleHighlight } from 'scandit-react-native-datacapture-barcode';
import { Brush, Color } from 'scandit-react-native-datacapture-core';

const rect = new BarcodeArRectangleHighlight(barcode);
rect.brush = new Brush(Color.fromHex('#334D99FF'), Color.fromHex('#4D99FF'), 2);
rect.icon = null; // optional ScanditIcon
```

Key properties:

| Property | Type | Description |
|----------|------|-------------|
| `brush` | `Brush` | Fill color, stroke color, stroke width. |
| `icon` | `ScanditIcon \| null` | Optional icon. |

### BarcodeArCustomHighlight (SDK 8.0+)

Attach any React component as a highlight. The component replaces the native circle or rectangle entirely.

```tsx
import { BarcodeArCustomHighlight } from 'scandit-react-native-datacapture-barcode';
import { View, Text } from 'react-native';

function MyHighlightComponent({ barcode }: { barcode: Barcode }) {
  return (
    <View
      style={{
        borderRadius: 9999,
        borderWidth: 2,
        width: 32,
        height: 32,
        backgroundColor: 'rgba(255,255,255,0.5)',
        borderColor: 'white',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <Text style={{ fontSize: 10, color: 'white' }}>AR</Text>
    </View>
  );
}

const highlightProvider: BarcodeArHighlightProvider = {
  highlightForBarcode: async (barcode: Barcode) => {
    return new BarcodeArCustomHighlight({
      renderHighlight: () => <MyHighlightComponent barcode={barcode} />,
    });
  },
};
```

`BarcodeArCustomHighlight` constructor takes a `BarcodeArCustomHighlightConfig` object with a `renderHighlight` method that returns a `ReactElement`.

## Step 7 — Annotations

Annotations display additional information anchored to a barcode — tooltips, popovers, status icons, or fully custom React components. Supply them through a `BarcodeArAnnotationProvider` passed as the `annotationProvider` prop on `<BarcodeArView>`.

### Provider pattern

Like the highlight provider, the annotation provider fires **once per barcode** (asynchronously). Return `null` to show no annotation.

```tsx
import {
  BarcodeArAnnotationProvider,
  BarcodeArInfoAnnotation,
  Barcode,
} from 'scandit-react-native-datacapture-barcode';

const annotationProvider: BarcodeArAnnotationProvider = {
  annotationForBarcode: async (barcode: Barcode) => {
    // Return the desired annotation, or null for no annotation.
    const annotation = new BarcodeArInfoAnnotation(barcode);
    annotation.body = [{ text: barcode.data ?? '' }];
    return annotation;
  },
};
```

### BarcodeArInfoAnnotation

The primary annotation type. Displays structured text with an optional header and footer.

```tsx
import {
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationHeader,
  BarcodeArInfoAnnotationFooter,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArInfoAnnotationWidthPreset,
  BarcodeArInfoAnnotationAnchor,
  BarcodeArAnnotationTrigger,
  BarcodeArInfoAnnotationListener,
} from 'scandit-react-native-datacapture-barcode';
import { Color } from 'scandit-react-native-datacapture-core';

const annotationProvider: BarcodeArAnnotationProvider = {
  annotationForBarcode: async (barcode: Barcode) => {
    // Header (optional)
    const header = new BarcodeArInfoAnnotationHeader();
    header.text = 'Product Name';
    header.backgroundColor = Color.fromHex('#FF4CAF50');  // green header

    // Footer (optional)
    const footer = new BarcodeArInfoAnnotationFooter();
    footer.text = 'Tap for details';

    // Body components — one per row
    const row1 = new BarcodeArInfoAnnotationBodyComponent();
    row1.text = `Code: ${barcode.data}`;

    const row2 = new BarcodeArInfoAnnotationBodyComponent();
    row2.text = 'In stock: 42 units';

    // Annotation listener for tap events
    const annotationListener: BarcodeArInfoAnnotationListener = {
      didTap(annotation: BarcodeArInfoAnnotation) {
        console.log('Annotation tapped for barcode:', annotation.barcode.data);
      },
      didTapHeader(annotation: BarcodeArInfoAnnotation) {
        console.log('Header tapped');
      },
    };

    // Assemble the annotation
    const annotation = new BarcodeArInfoAnnotation(barcode);
    annotation.header = header;
    annotation.footer = footer;
    annotation.body = [row1, row2];
    annotation.width = BarcodeArInfoAnnotationWidthPreset.Large;
    annotation.anchor = BarcodeArInfoAnnotationAnchor.Bottom;
    annotation.isEntireAnnotationTappable = true;
    annotation.annotationTrigger = BarcodeArAnnotationTrigger.HighlightTapAndBarcodeScan;
    annotation.backgroundColor = Color.fromHex('#CCFFFFFF');
    annotation.listener = annotationListener;

    return annotation;
  },
};
```

### BarcodeArInfoAnnotation Key Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `body` | `BarcodeArInfoAnnotationBodyComponent[]` | `[]` | Array of body rows. |
| `header` | `BarcodeArInfoAnnotationHeader \| null` | `null` | Optional header section. |
| `footer` | `BarcodeArInfoAnnotationFooter \| null` | `null` | Optional footer section. |
| `width` | `BarcodeArInfoAnnotationWidthPreset` | `Small` | Width preset: `Small`, `Medium`, `Large`. |
| `anchor` | `BarcodeArInfoAnnotationAnchor` | `Bottom` | Attachment point: `Top`, `Bottom`, `Left`, `Right`. |
| `annotationTrigger` | `BarcodeArAnnotationTrigger` | `HighlightTapAndBarcodeScan` | When to show the annotation. |
| `isEntireAnnotationTappable` | `boolean` | `false` | If `true`, tapping anywhere fires `didTap`; if `false`, individual elements are tappable. |
| `backgroundColor` | `Color` | `#CCFFFFFF` | Background color of the annotation card. |
| `hasTip` | `boolean` | `true` | Whether to show the pointer tip toward the barcode. |
| `listener` | `BarcodeArInfoAnnotationListener \| null` | `null` | Tap event handler. |

### BarcodeArAnnotationTrigger values

| Value | Description |
|-------|-------------|
| `HighlightTap` | Show only when user taps the highlight. |
| `HighlightTapAndBarcodeScan` | Show immediately on scan; hide/show on highlight tap. |

### BarcodeArPopoverAnnotation

Displays a row of icon+text buttons when the user taps a barcode highlight.

```tsx
import {
  BarcodeArPopoverAnnotation,
  BarcodeArPopoverAnnotationButton,
  BarcodeArPopoverAnnotationListener,
} from 'scandit-react-native-datacapture-barcode';
import { ScanditIconBuilder, ScanditIconType } from 'scandit-react-native-datacapture-core';

const popoverListener: BarcodeArPopoverAnnotationListener = {
  didTapButton(popover, button, buttonIndex) {
    console.log(`Button ${buttonIndex} tapped: ${button.text}`);
  },
};

const annotationProvider: BarcodeArAnnotationProvider = {
  annotationForBarcode: async (barcode: Barcode) => {
    // ScanditIcon is built via ScanditIconBuilder (there is NO single-arg
    // `new ScanditIcon(type)` constructor). Pick an icon from ScanditIconType.
    const infoIcon = new ScanditIconBuilder().withIcon(ScanditIconType.InspectItem).build();
    const addIcon = new ScanditIconBuilder().withIcon(ScanditIconType.ToPick).build();

    const infoButton = new BarcodeArPopoverAnnotationButton(infoIcon, 'Details');
    const addButton = new BarcodeArPopoverAnnotationButton(addIcon, 'Add');

    const popover = new BarcodeArPopoverAnnotation(barcode, [infoButton, addButton]);
    popover.isEntirePopoverTappable = false;
    popover.listener = popoverListener;
    return popover;
  },
};
```

The `BarcodeArPopoverAnnotationButton` constructor takes `(icon: ScanditIcon, text: string)`. The listener callback is `didTapButton(popover, button, buttonIndex)`.

### Building a ScanditIcon

`ScanditIcon` has no convenience single-argument constructor. Build one with `ScanditIconBuilder`:

```typescript
import { ScanditIconBuilder, ScanditIconType, Color } from 'scandit-react-native-datacapture-core';

const icon = new ScanditIconBuilder()
  .withIcon(ScanditIconType.ExclamationMark)
  .withIconColor(Color.fromHex('#FFFFFFFF'))
  .build();
```

`ScanditIconType` members include: `ArrowRight`, `ArrowLeft`, `ArrowUp`, `ArrowDown`, `ToPick`, `Checkmark`, `XMark`, `QuestionMark`, `ExclamationMark`, `LowStock`, `ExpiredItem`, `WrongItem`, `FragileItem`, `StarFilled`, `StarHalfFilled`, `StarOutlined`, `ChevronUp`, `ChevronDown`, `ChevronLeft`, `ChevronRight`, `InspectItem`, `Print`. There is **no** `Info` or `Plus` member.

### BarcodeArStatusIconAnnotation

A compact icon that expands to show text when tapped.

```tsx
import {
  BarcodeArStatusIconAnnotation,
} from 'scandit-react-native-datacapture-barcode';
import { ScanditIconBuilder, ScanditIconType, Color } from 'scandit-react-native-datacapture-core';

const annotationProvider: BarcodeArAnnotationProvider = {
  annotationForBarcode: async (barcode: Barcode) => {
    const statusAnnotation = new BarcodeArStatusIconAnnotation(barcode);
    statusAnnotation.icon = new ScanditIconBuilder()
      .withIcon(ScanditIconType.ExclamationMark)
      .build();
    statusAnnotation.text = 'Low stock';          // shown on tap (max 20 chars)
    statusAnnotation.backgroundColor = Color.fromHex('#FFFBC02C');
    return statusAnnotation;
  },
};
```

### BarcodeArResponsiveAnnotation (SDK 8.2+)

Switches between two `BarcodeArInfoAnnotation` variants based on barcode size relative to the screen — useful for showing dense info when close-up and minimal info when far away.

```tsx
import {
  BarcodeArResponsiveAnnotation,
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArInfoAnnotationWidthPreset,
} from 'scandit-react-native-datacapture-barcode';

const annotationProvider: BarcodeArAnnotationProvider = {
  annotationForBarcode: async (barcode: Barcode) => {
    // Close-up view: detailed annotation
    const closeUpBody = new BarcodeArInfoAnnotationBodyComponent();
    closeUpBody.text = `Code: ${barcode.data} — Full details here`;
    const closeUpAnnotation = new BarcodeArInfoAnnotation(barcode);
    closeUpAnnotation.body = [closeUpBody];
    closeUpAnnotation.width = BarcodeArInfoAnnotationWidthPreset.Large;

    // Far-away view: compact annotation
    const farBody = new BarcodeArInfoAnnotationBodyComponent();
    farBody.text = 'Get closer';
    const farAnnotation = new BarcodeArInfoAnnotation(barcode);
    farAnnotation.body = [farBody];
    farAnnotation.width = BarcodeArInfoAnnotationWidthPreset.Small;

    const responsive = new BarcodeArResponsiveAnnotation(barcode, closeUpAnnotation, farAnnotation);
    responsive.threshold = 0.05;  // 5% of screen area = close-up threshold
    return responsive;
  },
};
```

### BarcodeArCustomAnnotation (SDK 8.1+)

Attach any React component as an annotation.

```tsx
import { BarcodeArCustomAnnotation, BarcodeArAnnotationTrigger } from 'scandit-react-native-datacapture-barcode';
import { Anchor } from 'scandit-react-native-datacapture-core';
import { View, Text } from 'react-native';

function ProductInfoCard({ barcode }: { barcode: Barcode }) {
  return (
    <View
      style={{
        backgroundColor: 'rgba(0,0,0,0.75)',
        borderRadius: 8,
        padding: 12,
        minWidth: 120,
        alignItems: 'center',
      }}
    >
      <Text style={{ color: 'white', fontWeight: 'bold' }}>{barcode.data}</Text>
      <Text style={{ color: '#ccc', fontSize: 12, marginTop: 4 }}>Tap for info</Text>
    </View>
  );
}

const annotationProvider: BarcodeArAnnotationProvider = {
  annotationForBarcode: async (barcode: Barcode) => {
    return new BarcodeArCustomAnnotation({
      annotationTrigger: BarcodeArAnnotationTrigger.HighlightTapAndBarcodeScan,
      anchor: Anchor.TopCenter,
      renderAnnotation: () => <ProductInfoCard barcode={barcode} />,
    });
  },
};
```

`BarcodeArCustomAnnotation` constructor takes a `BarcodeArCustomAnnotationConfig` object with:

| Property | Type | Description |
|----------|------|-------------|
| `renderAnnotation` | `() => ReactElement` | Returns the React component to render as the annotation. |
| `annotationTrigger` | `BarcodeArAnnotationTrigger` (optional) | Default: `HighlightTapAndBarcodeScan`. |
| `anchor` | `Anchor` (optional) | Default: `Anchor.TopCenter`. |

## Step 8 — BarcodeArFeedback

`BarcodeArFeedback` controls sound and vibration when barcodes are detected. It is a property on the `BarcodeAr` instance.

```typescript
import {
  BarcodeArFeedback,
} from 'scandit-react-native-datacapture-barcode';
import { Feedback, Sound, Vibration } from 'scandit-react-native-datacapture-core';

// Use the built-in default feedback (sound + vibration enabled)
barcodeAr.feedback = BarcodeArFeedback.defaultFeedback;

// Disable all feedback
const silent = new BarcodeArFeedback();
// Leave scanned and tapped unset — they default to no feedback.
barcodeAr.feedback = silent;

// Custom feedback: vibrate on scan, no sound on tap
const custom = new BarcodeArFeedback();
custom.scanned = new Feedback(Vibration.defaultVibration, null);
custom.tapped = new Feedback(null, null);
barcodeAr.feedback = custom;
```

### BarcodeArFeedback Properties

| Property | Type | Description |
|----------|------|-------------|
| `BarcodeArFeedback.defaultFeedback` | `BarcodeArFeedback` (static) | Default feedback: sound + vibration on scan. |
| `scanned` | `Feedback` | Feedback emitted when a new barcode is detected. |
| `tapped` | `Feedback` | Feedback emitted when a barcode annotation element is tapped. |

## Step 9 — Limiting which barcodes are shown

`BarcodeArFilter` is documented for React Native at SDK **8.5**, but that version is **not yet published** in the `scandit-react-native-datacapture-*` packages (latest published is 8.4.0). Do **not** generate `BarcodeArFilter` / `barcodeAr.setBarcodeFilter(...)` code today — the API is not available to install.

To limit which barcodes are shown in the meantime, return `null` from the `highlightProvider` or `annotationProvider` for unwanted barcodes. This hides their visuals while keeping them tracked.

> **Forward-looking note (filter vs. provider)**: Once `BarcodeArFilter` ships for React Native, `setBarcodeFilter` will remove barcodes from the session entirely (no highlight, no annotation, not reported as tracked), whereas returning `null` from `highlightProvider`/`annotationProvider` keeps the barcode tracked but hides its visuals. Until the filter API is published, use the provider-`null` approach.

## Step 10 — Lifecycle and Cleanup

### Starting and stopping the view

Call `view.start()` in the ref callback when the view mounts. This is required — the view does not start automatically.

To pause/stop scanning programmatically (e.g. when navigating away):

```tsx
<BarcodeArView
  ref={(view: BarcodeArView | null) => {
    if (view) {
      view.start();
      viewRef.current = view;
    }
  }}
  // ...
/>
```

```typescript
// Pause (keep camera warm):
viewRef.current?.pause();

// Stop (release camera):
viewRef.current?.stop();

// Restart:
viewRef.current?.start();
```

### Cleanup on unmount

Unbind the BarcodeAr mode from the context when the scan screen unmounts so the camera and native resources are released:

```tsx
useEffect(() => {
  return () => {
    dataCaptureContext.removeMode(barcodeArRef.current);
  };
}, []);
```

React unmount handles the native view tear-down automatically. You do not need to dispose the view explicitly.

## Step 11 — Camera Permissions

### iOS

Add to `ios/<App>/Info.plist`:

```xml
<key>NSCameraUsageDescription</key>
<string>We need camera access to scan barcodes</string>
```

### Android

Request at runtime before the AR screen mounts:

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

Gate navigation to the AR screen on a successful permission:

```tsx
const handleStartAr = async () => {
  const granted = await requestCameraPermission();
  if (!granted) return;
  navigation.navigate('ArScreen');
};
```

On iOS, the permission prompt is triggered automatically by the native BarcodeArView when it mounts and `start()` is called.

## Step 12 — Complete Example

Full working AR screen: context singleton, BarcodeAr mode with listener, highlight provider (circle), annotation provider (info annotation), and cleanup.

### CaptureContext.ts

```typescript
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

DataCaptureContext.initialize(licenseKey);

export default DataCaptureContext.sharedInstance;
```

### ArScreen.tsx

```tsx
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';

import { Color, Brush } from 'scandit-react-native-datacapture-core';
import {
  BarcodeAr,
  BarcodeArSettings,
  BarcodeArView,
  BarcodeArViewSettings,
  BarcodeArListener,
  BarcodeArSession,
  BarcodeArHighlightProvider,
  BarcodeArAnnotationProvider,
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArInfoAnnotationWidthPreset,
  BarcodeArInfoAnnotationListener,
  BarcodeArAnnotationTrigger,
  Barcode,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';

import dataCaptureContext from './CaptureContext';

function createBarcodeAr(): BarcodeAr {
  const settings = new BarcodeArSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.EAN8,
    Symbology.UPCE,
    Symbology.Code39,
    Symbology.Code128,
  ]);
  return new BarcodeAr(settings);
}

export const ArScreen = () => {
  const [scanCount, setScanCount] = useState(0);

  const barcodeArRef = useRef<BarcodeAr>(null!);
  const viewRef = useRef<BarcodeArView | null>(null);

  if (!barcodeArRef.current) {
    const barcodeAr = createBarcodeAr();

    const listener: BarcodeArListener = {
      didUpdateSession: async (_: BarcodeAr, session: BarcodeArSession) => {
        if (session.addedTrackedBarcodes.length > 0) {
          setScanCount(prev => prev + session.addedTrackedBarcodes.length);
        }
      },
    };
    barcodeAr.addListener(listener);
    dataCaptureContext.addMode(barcodeAr);
    barcodeArRef.current = barcodeAr;
  }

  useEffect(() => {
    return () => {
      dataCaptureContext.removeMode(barcodeArRef.current);
    };
  }, []);

  const highlightProvider: BarcodeArHighlightProvider = {
    highlightForBarcode: async (barcode: Barcode) => {
      const highlight = new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Dot);
      highlight.brush = new Brush(
        Color.fromHex('#4D99FF'),
        Color.fromHex('#4D99FF'),
        1.0,
      );
      return highlight;
    },
  };

  const annotationListener: BarcodeArInfoAnnotationListener = {
    didTap(annotation: BarcodeArInfoAnnotation) {
      console.log('Annotation tapped:', annotation.barcode.data);
    },
  };

  const annotationProvider: BarcodeArAnnotationProvider = {
    annotationForBarcode: async (barcode: Barcode) => {
      const bodyRow = new BarcodeArInfoAnnotationBodyComponent();
      bodyRow.text = barcode.data ?? '(no data)';

      const annotation = new BarcodeArInfoAnnotation(barcode);
      annotation.body = [bodyRow];
      annotation.width = BarcodeArInfoAnnotationWidthPreset.Medium;
      annotation.isEntireAnnotationTappable = true;
      annotation.annotationTrigger = BarcodeArAnnotationTrigger.HighlightTapAndBarcodeScan;
      annotation.listener = annotationListener;
      return annotation;
    },
  };

  return (
    <BarcodeArView
      style={styles.container}
      context={dataCaptureContext}
      barcodeAr={barcodeArRef.current}
      settings={new BarcodeArViewSettings()}
      highlightProvider={highlightProvider}
      annotationProvider={annotationProvider}
      ref={(view: BarcodeArView | null) => {
        if (view) {
          view.start();
          view.shouldShowCameraSwitchControl = true;
          viewRef.current = view;
        }
      }}
    >
      <View style={styles.badge}>
        <Text style={styles.badgeText}>
          {scanCount} {scanCount === 1 ? 'barcode' : 'barcodes'} detected
        </Text>
      </View>
    </BarcodeArView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  badge: {
    position: 'absolute',
    top: 16,
    left: 16,
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  badgeText: { color: 'white', fontWeight: 'bold', fontSize: 13 },
});
```

## Key Rules

1. **Singleton context** — Call `DataCaptureContext.initialize(licenseKey)` once in a dedicated module and export `DataCaptureContext.sharedInstance`. Never construct another context anywhere else.
2. **Function components with hooks** — Hold the `BarcodeAr` mode in a `useRef`. Initialize it once using the `if (!ref.current)` guard. Register listeners inside that block. Build providers as plain objects (they are recreated each render — this is acceptable because the view holds its own ref to the provider identity).
3. **Explicit `view.start()`** — Unlike SparkScan, `BarcodeArView` does not start automatically. You must call `view.start()` in the `ref` callback. Forgetting this means no barcodes are ever tracked.
4. **Providers are async** — `highlightForBarcode` and `annotationForBarcode` are `async` functions returning a Promise. Never assume synchronous return. Return `null` to show nothing for a given barcode.
5. **Providers fire once per barcode** — Each provider is called once when a barcode first enters the tracked set. The return value is cached by the view for that barcode's lifetime. To force a refresh, call `viewRef.current?.reset()`.
6. **Cleanup on unmount** — In the `useEffect` cleanup function, call `dataCaptureContext.removeMode(barcodeArRef.current)`. React unmount handles the native view tear-down automatically.
7. **Children render under the overlay** — Everything inside `<BarcodeArView>` renders below the native AR layer. Use absolute positioning or safe-area insets to layer UI on top of the AR content.
8. **Imports** — Core types (`DataCaptureContext`, `Color`, `Brush`, `Feedback`, etc.) from `scandit-react-native-datacapture-core`; BarcodeAr types from `scandit-react-native-datacapture-barcode`.
9. **Pod install** — Run `npx pod-install` (or `cd ios && pod install`) after installing or updating Scandit packages. Android auto-links.
10. **Camera permissions** — iOS: `NSCameraUsageDescription` in `Info.plist`. Android: runtime request via `PermissionsAndroid` before navigating to the AR screen.
11. **Metro cache** — If a package upgrade appears to have no effect at runtime, restart Metro with `npm start -- --reset-cache`.
12. **`addMode` is required** — Call `dataCaptureContext.addMode(barcodeAr)` after constructing `BarcodeAr` and before rendering `<BarcodeArView>`. Without this, the view has no mode to drive scanning.

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Barcodes are never tracked / nothing appears | Forgot `view.start()` in the `ref` callback, or forgot `dataCaptureContext.addMode(barcodeAr)`. Both are required. |
| App crashes on iOS after install | Run `npx pod-install` and rebuild. |
| Highlights/annotations reset on every render | The provider objects are recreated each render — this is expected. The view caches results per barcode; it does not re-call the provider on re-render. If you see flickering, check that you are not calling `viewRef.current.reset()` inside a render cycle. |
| `BarcodeArCustomHighlight` not found | Requires SDK 8.0+. Check your installed package version. |
| `BarcodeArCustomAnnotation` not found | Requires SDK 8.1+. |
| `BarcodeArResponsiveAnnotation` not found | Requires SDK 8.2+. |
| Annotation appears behind content | Children inside `<BarcodeArView>` render under the AR layer. Use `position: 'absolute'` to float UI on top of the camera but the AR annotations are always above the native view surface. |
| Context initialized multiple times | Move `DataCaptureContext.initialize(...)` to a dedicated `CaptureContext.ts` module imported once at app startup. |
