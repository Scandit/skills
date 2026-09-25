# MatrixScan AR Capacitor Integration Guide

MatrixScan AR (API class: `BarcodeAr`) is a multi-barcode scanning mode that simultaneously tracks all barcodes in the camera view and renders visual overlays — highlights and annotations — on top of each barcode in real time. Unlike SparkScan, it requires a DOM container element: `BarcodeArView` mirrors the size and position of a `<div>` you provide, compositing the native AR layer on top of it.

> **Language note**: Examples below use JavaScript. The same API works identically with TypeScript — adapt imports and add type annotations to match the user's project.

## Prerequisites

- Scandit Capacitor packages installed:
  - `scandit-capacitor-datacapture-core`
  - `scandit-capacitor-datacapture-barcode`
- After installing, run `npx cap sync` to sync the native projects.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test
- **Minimum Capacitor SDK version: 8.2.** BarcodeAr is not available in earlier Capacitor SDK versions.
- Camera permissions configured by the app:
  - iOS: `NSCameraUsageDescription` in `Info.plist`
  - Android: handled automatically by the plugin

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it is important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which file they would like to integrate MatrixScan AR into (typically the app entry point or a page module). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Install packages: `npm install scandit-capacitor-datacapture-core scandit-capacitor-datacapture-barcode`
2. Run `npx cap sync` to apply native changes.
3. Add `NSCameraUsageDescription` to `ios/App/App/Info.plist`.
4. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key from https://ssl.scandit.com.
5. Add `<div id="barcode-ar-view">` to the scanning screen in your HTML and size it to fill the camera area.
6. Store references to `barcodeAr` and `barcodeArView` on `window` or at module scope to prevent garbage collection.

## Step 1 — Initialize Plugins and Create DataCaptureContext

Plugin initialization **must** happen before any other Scandit API call. It discovers all installed Scandit Capacitor plugins and wires up the bridge.

```javascript
import {
  DataCaptureContext,
  ScanditCaptureCorePlugin,
} from 'scandit-capacitor-datacapture-core';

// Must be called first — sets up all Scandit plugins
await ScanditCaptureCorePlugin.initializePlugins();

const context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
```

> **Important**: Always call `ScanditCaptureCorePlugin.initializePlugins()` before `DataCaptureContext.initialize()` or any other Scandit API. Skipping this step causes undefined behavior.

## Step 2 — Set Up the Camera

BarcodeAr requires an explicit camera setup. Use `BarcodeAr.createRecommendedCameraSettings()` to get optimal settings for AR tracking, then attach the camera to the context.

```javascript
import {
  Camera,
  FrameSourceState,
  VideoResolution,
} from 'scandit-capacitor-datacapture-core';

import { BarcodeAr } from 'scandit-capacitor-datacapture-barcode';

const cameraSettings = BarcodeAr.createRecommendedCameraSettings();
// Optional: override resolution
cameraSettings.preferredResolution = VideoResolution.UHD4K;

const camera = Camera.withSettings(cameraSettings);
await context.setFrameSource(camera);

// Turn the camera on when ready to scan
await camera.switchToDesiredState(FrameSourceState.On);
```

To stop the camera when leaving the scanning screen:

```javascript
await camera.switchToDesiredState(FrameSourceState.Off);
```

## Step 3 — Configure BarcodeArSettings

Choose which barcode symbologies to track. Only enable what you need.

```javascript
import {
  BarcodeArSettings,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

const settings = new BarcodeArSettings();

settings.enableSymbologies([
  Symbology.EAN13UPCA,
  Symbology.EAN8,
  Symbology.UPCE,
  Symbology.Code39,
  Symbology.Code128,
  Symbology.QR,
  Symbology.DataMatrix,
]);

// Optional: adjust per-symbology settings
const code39Settings = settings.settingsForSymbology(Symbology.Code39);
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];
```

### BarcodeArSettings Methods

| Method | Description |
|--------|-------------|
| `enableSymbologies(symbologies)` | Enable multiple symbologies at once. |
| `enableSymbology(symbology, enabled)` | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | Get per-symbology settings (e.g. `activeSymbolCounts`). |
| `setProperty(name, value)` / `getProperty(name)` | Advanced property access by name. |

## Step 4 — Create BarcodeAr Mode

Construct `BarcodeAr` with the configured settings. Do not pass the context here — context wiring happens in `BarcodeArView`.

```javascript
import { BarcodeAr } from 'scandit-capacitor-datacapture-barcode';

window.barcodeAr = new BarcodeAr(settings);
```

### BarcodeAr Methods

| Method | Description |
|--------|-------------|
| `addListener(listener)` | Register a `BarcodeArListener` to receive session updates. |
| `removeListener(listener)` | Remove a previously added listener. |
| `applySettings(settings)` | Update settings at runtime (async). |
| `static createRecommendedCameraSettings()` | Get recommended `CameraSettings` for AR tracking. |

### BarcodeAr Properties

| Property | Type | Description |
|----------|------|-------------|
| `feedback` | `BarcodeArFeedback` | Sound/haptic feedback configuration. |

## Step 5 — Add a BarcodeArListener (optional)

The listener receives session updates on every processed frame. Use it to react to newly tracked or lost barcodes.

```javascript
window.barcodeAr.addListener({
  didUpdateSession: async (barcodeAr, session) => {
    const added = session.addedTrackedBarcodes;
    const removed = session.removedTrackedBarcodes;
    const all = session.trackedBarcodes;

    // added is an array of TrackedBarcode
    for (const tracked of added) {
      console.log(`New barcode: ${tracked.barcode.data}`);
    }
  },
});
```

### BarcodeArListener Interface

| Callback | Signature | Description |
|----------|-----------|-------------|
| `didUpdateSession` | `(barcodeAr, session, getFrameData?) => Promise<void>` | Called on every processed frame. |

### BarcodeArSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `addedTrackedBarcodes` | `TrackedBarcode[]` | Barcodes newly tracked in this frame. |
| `removedTrackedBarcodes` | `string[]` | Identifiers of barcodes lost in this frame. |
| `trackedBarcodes` | `{ [key: string]: TrackedBarcode }` | All currently tracked barcodes. |
| `reset()` | `Promise<void>` | Clear all tracked barcodes and state. |

## Step 6 — Create BarcodeArView and Connect to DOM

`BarcodeArView` renders the AR overlay positioned exactly over a DOM element you provide. The element must exist in the DOM before `connectToElement` is called.

```javascript
import {
  BarcodeArView,
  BarcodeArViewSettings,
} from 'scandit-capacitor-datacapture-barcode';

const viewSettings = new BarcodeArViewSettings();
// Optional: configure sound and haptics
viewSettings.soundEnabled = true;
viewSettings.hapticEnabled = true;

window.barcodeArView = new BarcodeArView({
  context,
  barcodeAr: window.barcodeAr,
  settings: viewSettings,
  cameraSettings,
});

const containerEl = document.getElementById('barcode-ar-view');
await window.barcodeArView.connectToElement(containerEl);
```

> **DOM requirement**: You must have a `<div id="barcode-ar-view">` (or equivalent) in your HTML that is sized and positioned to fill the camera area. The view mirrors this element's rect — it is not a floating native overlay.

### BarcodeArViewSettings Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `soundEnabled` | `boolean` | `true` | Play sound on barcode detection. |
| `hapticEnabled` | `boolean` | `true` | Vibrate on barcode detection. |
| `defaultCameraPosition` | `CameraPosition` | `WorldFacing` | Which camera to use by default. |

### BarcodeArView Key Properties

| Property | Type | Description |
|----------|------|-------------|
| `highlightProvider` | object \| `null` | Provides highlights per barcode. `null` = default highlight for all. |
| `annotationProvider` | object \| `null` | Provides annotations per barcode. `null` = no annotations. |
| `uiListener` | object \| `null` | Receives tap events on highlights. |
| `shouldShowTorchControl` | `boolean` | Show/hide torch button (default `false`). |
| `torchControlPosition` | `Anchor` | Position of torch button (default `Anchor.TopLeft`). |
| `shouldShowZoomControl` | `boolean` | Show/hide zoom control. |
| `zoomControlPosition` | `Anchor` | Position of zoom control (default `Anchor.BottomRight`). |
| `shouldShowCameraSwitchControl` | `boolean` | Show/hide camera switch button. |
| `cameraSwitchControlPosition` | `Anchor` | Position of camera switch button (default `Anchor.TopRight`). |
| `shouldShowMacroModeControl` | `boolean` | Show/hide macro mode button (iOS only). |

### BarcodeArView Lifecycle Methods

| Method | Description |
|--------|-------------|
| `connectToElement(element)` | Attach the view to a DOM element. Must be awaited. |
| `detachFromElement()` | Detach the view from the DOM element and release resources. |
| `start()` | Start scanning. |
| `stop()` | Stop scanning. |
| `pause()` | Pause scanning. |
| `reset()` | Clear all highlights and annotations, refresh from providers. |

## Step 7 — Teardown

When leaving the scanning screen, switch the camera off and detach the view from the DOM.

```javascript
async function uninitialize() {
  if (camera) {
    await camera.switchToDesiredState(FrameSourceState.Off);
  }
  if (window.barcodeArView) {
    window.barcodeArView.detachFromElement();
    window.barcodeArView = null;
  }
}
```

## Step 8 — Highlights

Highlights are visual overlays drawn on top of each tracked barcode. Assign a `highlightProvider` object to `barcodeArView.highlightProvider`. The provider's `highlightForBarcode` method is called asynchronously for each tracked barcode and must return a highlight object or `null` (no highlight).

Two built-in highlight types are available: `BarcodeArRectangleHighlight` (rectangle) and `BarcodeArCircleHighlight` (circle, with `Dot` or `Icon` preset).

### Rectangle Highlights

```javascript
import {
  BarcodeArRectangleHighlight,
} from 'scandit-capacitor-datacapture-barcode';
import { Brush, Color } from 'scandit-capacitor-datacapture-core';

window.barcodeArView.highlightProvider = {
  highlightForBarcode: async (barcode) => {
    const highlight = new BarcodeArRectangleHighlight(barcode);
    highlight.brush = new Brush(
      Color.fromHex('#2EC1CE66'), // fill (with alpha)
      Color.fromHex('#2EC1CE'),   // stroke
      2.0,                        // stroke width
    );
    // Optionally set an icon
    // highlight.icon = someIcon;
    return highlight;
  },
};
```

### BarcodeArRectangleHighlight Properties

| Property | Type | Description |
|----------|------|-------------|
| `barcode` | `Barcode` | The barcode this highlight is for (read-only). |
| `brush` | `Brush` | Fill color, stroke color, and stroke width. Default is blue fill (45% alpha), blue stroke. |
| `icon` | `ScanditIcon \| null` | Optional icon drawn inside the highlight. Default is `null`. |

### Circle Highlights

```javascript
import {
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
} from 'scandit-capacitor-datacapture-barcode';

window.barcodeArView.highlightProvider = {
  highlightForBarcode: async (barcode) => {
    // Preset.Dot = small circle; Preset.Icon = larger circle with room for an icon
    const highlight = new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Dot);
    highlight.brush = new Brush(Color.fromHex('#00FFFF'), Color.fromHex('#00FFFF'), 1.0);
    return highlight;
  },
};
```

### BarcodeArCircleHighlight Properties

| Property | Type | Description |
|----------|------|-------------|
| `barcode` | `Barcode` | The barcode this highlight is for (read-only). |
| `brush` | `Brush` | Fill color, stroke color, and stroke width. |
| `icon` | `ScanditIcon \| null` | Optional icon drawn inside the circle. |
| `size` | `number` | Diameter in device-independent pixels. Minimum 18. |

### BarcodeArCircleHighlightPreset Values

| Value | Description |
|-------|-------------|
| `BarcodeArCircleHighlightPreset.Dot` | Small dot circle. Default blue styling. |
| `BarcodeArCircleHighlightPreset.Icon` | Larger circle sized to contain an icon. Default blue styling. |

### Highlight Tap Listener

To receive tap events on highlights, set `barcodeArView.uiListener`:

```javascript
window.barcodeArView.uiListener = {
  didTapHighlightForBarcode: async (barcodeAr, barcode, highlight) => {
    console.log(`Tapped barcode: ${barcode.data}`);
    // Mutate the highlight directly to update its appearance
    highlight.brush = new Brush(Color.fromHex('#FF000066'), Color.fromHex('#FF0000'), 2.0);
  },
};
```

## Step 9 — Annotations

Annotations display additional information near a tracked barcode. Assign an `annotationProvider` object to `barcodeArView.annotationProvider`. Return `null` from `annotationForBarcode` to show no annotation for a given barcode.

Three built-in annotation types are available: `BarcodeArInfoAnnotation`, `BarcodeArPopoverAnnotation`, and `BarcodeArStatusIconAnnotation`. A fourth type, `BarcodeArResponsiveAnnotation`, wraps two `BarcodeArInfoAnnotation` instances and switches between them based on barcode distance.

### Info Annotations

Info annotations display text content in a card-style tooltip with an optional header, body rows, and footer.

```javascript
import {
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationHeader,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArInfoAnnotationFooter,
  BarcodeArInfoAnnotationWidthPreset,
} from 'scandit-capacitor-datacapture-barcode';
import { Color } from 'scandit-capacitor-datacapture-core';

window.barcodeArView.annotationProvider = {
  annotationForBarcode: async (barcode) => {
    const annotation = new BarcodeArInfoAnnotation(barcode);
    annotation.width = BarcodeArInfoAnnotationWidthPreset.Large;
    annotation.backgroundColor = Color.fromHex('#FFFFFF');

    // Header
    const header = new BarcodeArInfoAnnotationHeader();
    header.text = 'Product Info';
    header.backgroundColor = Color.fromHex('#2EC1CE');
    annotation.header = header;

    // Body rows
    const row1 = new BarcodeArInfoAnnotationBodyComponent();
    row1.text = barcode.data;

    const row2 = new BarcodeArInfoAnnotationBodyComponent();
    row2.text = 'Tap for details';

    annotation.body = [row1, row2];

    // Footer
    const footer = new BarcodeArInfoAnnotationFooter();
    footer.text = 'Powered by Scandit';
    footer.backgroundColor = Color.fromHex('#121619');
    annotation.footer = footer;

    return annotation;
  },
};
```

### BarcodeArInfoAnnotation Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `barcode` | `Barcode` | — | The barcode this annotation is for (read-only). |
| `body` | `BarcodeArInfoAnnotationBodyComponent[]` | `[]` | Array of body row components. |
| `header` | `BarcodeArInfoAnnotationHeader \| null` | `null` | Optional header. |
| `footer` | `BarcodeArInfoAnnotationFooter \| null` | `null` | Optional footer. |
| `width` | `BarcodeArInfoAnnotationWidthPreset` | `Small` | Width preset: `Small`, `Medium`, or `Large`. |
| `backgroundColor` | `Color` | `#CCFFFFFF` | Background color of the annotation card. |
| `annotationTrigger` | `BarcodeArAnnotationTrigger` | `HighlightTapAndBarcodeScan` | When the annotation is shown. |
| `anchor` | `BarcodeArInfoAnnotationAnchor` | `Bottom` | Where the annotation attaches relative to the barcode. |
| `isEntireAnnotationTappable` | `boolean` | `false` | If `true`, the whole annotation fires `didTap`. If `false`, individual elements (header, footer, icons) are independently tappable. |
| `hasTip` | `boolean` | `true` | Whether to draw a pointer tip toward the barcode. |
| `listener` | object \| `null` | `null` | Receives tap callbacks (see below). |

### BarcodeArInfoAnnotation Listener Callbacks

| Callback | When called |
|----------|-------------|
| `didTap(annotation)` | `isEntireAnnotationTappable` is `true` and annotation is tapped. |
| `didTapHeader(annotation)` | Header tapped (`isEntireAnnotationTappable` is `false`). |
| `didTapFooter(annotation)` | Footer tapped (`isEntireAnnotationTappable` is `false`). |
| `didTapLeftIcon(annotation, component, index)` | Left icon in a body component tapped. |
| `didTapRightIcon(annotation, component, index)` | Right icon in a body component tapped. |

### BarcodeArInfoAnnotationBodyComponent Properties

| Property | Type | Description |
|----------|------|-------------|
| `text` | `string` | Row text. |
| `leftIcon` | `ScanditIcon \| null` | Icon on the left side. `null` = no icon. |
| `rightIcon` | `ScanditIcon \| null` | Icon on the right side. `null` = no icon. |
| `isLeftIconTappable` | `boolean` | Whether left icon fires a tap callback. Default `true`. |
| `isRightIconTappable` | `boolean` | Whether right icon fires a tap callback. Default `true`. |
| `textColor` | `Color` | Text color. Default `#121619`. |
| `textAlign` | `TextAlignment` | Text alignment. Default center. |

### BarcodeArInfoAnnotationWidthPreset Values

| Value | Use case |
|-------|----------|
| `Small` | Text or icon only, no header/footer. |
| `Medium` | Moderate content. |
| `Large` | Rich content with header, multiple body rows, footer. |

### BarcodeArAnnotationTrigger Values

| Value | Description |
|-------|-------------|
| `HighlightTap` | Annotation shown only when user taps the highlight. |
| `HighlightTapAndBarcodeScan` | Shown immediately on scan; toggles with tap. |

### Popover Annotations

Popover annotations display a row of action buttons that appear when the user taps a highlight.

```javascript
import {
  BarcodeArPopoverAnnotation,
  BarcodeArPopoverAnnotationButton,
  BarcodeArAnnotationTrigger,
  ScanditIconBuilder,
  ScanditIconType,
  ScanditIconShape,
} from 'scandit-capacitor-datacapture-barcode';
import { Color } from 'scandit-capacitor-datacapture-core';

window.barcodeArView.annotationProvider = {
  annotationForBarcode: async (barcode) => {
    const acceptIcon = new ScanditIconBuilder()
      .withIcon(ScanditIconType.Checkmark)
      .withIconColor(Color.fromHex('#FFFFFF'))
      .withBackgroundShape(ScanditIconShape.Circle)
      .withBackgroundColor(Color.fromHex('#0D853D'))
      .build();

    const rejectIcon = new ScanditIconBuilder()
      .withIcon(ScanditIconType.XMark)
      .withIconColor(Color.fromHex('#FFFFFF'))
      .withBackgroundShape(ScanditIconShape.Circle)
      .withBackgroundColor(Color.fromHex('#D92121'))
      .build();

    const acceptButton = new BarcodeArPopoverAnnotationButton(acceptIcon, 'Accept');
    const rejectButton = new BarcodeArPopoverAnnotationButton(rejectIcon, 'Reject');

    const annotation = new BarcodeArPopoverAnnotation(barcode, [acceptButton, rejectButton]);
    annotation.annotationTrigger = BarcodeArAnnotationTrigger.HighlightTap;

    annotation.listener = {
      didTapButton: async (annotation, button, buttonIndex) => {
        if (buttonIndex === 0) {
          console.log('Accepted:', annotation.barcode.data);
        } else {
          console.log('Rejected:', annotation.barcode.data);
        }
      },
    };

    return annotation;
  },
};
```

### BarcodeArPopoverAnnotation Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `barcode` | `Barcode` | — | The barcode this annotation is for (read-only). |
| `buttons` | `BarcodeArPopoverAnnotationButton[]` | — | Buttons passed in constructor (read-only). |
| `annotationTrigger` | `BarcodeArAnnotationTrigger` | `HighlightTap` | When the popover is shown. |
| `isEntirePopoverTappable` | `boolean` | `false` | If `true`, tap anywhere on popover fires `didTap`. |
| `listener` | object \| `null` | `null` | Receives button/popover tap callbacks. |

### Status Icon Annotations

Status icon annotations display a compact icon that expands on tap to reveal a text label.

```javascript
import {
  BarcodeArStatusIconAnnotation,
  ScanditIconBuilder,
  ScanditIconType,
  ScanditIconShape,
} from 'scandit-capacitor-datacapture-barcode';
import { Color } from 'scandit-capacitor-datacapture-core';

window.barcodeArView.annotationProvider = {
  annotationForBarcode: async (barcode) => {
    const annotation = new BarcodeArStatusIconAnnotation(barcode);
    annotation.text = 'Needs review';  // max 20 characters
    annotation.icon = new ScanditIconBuilder()
      .withBackgroundShape(ScanditIconShape.Circle)
      .withBackgroundColor(Color.fromHex('#FBC02C'))
      .withIcon(ScanditIconType.ExclamationMark)
      .withIconColor(Color.fromHex('#000000'))
      .build();
    annotation.backgroundColor = Color.fromHex('#FFFFFF');
    return annotation;
  },
};
```

### BarcodeArStatusIconAnnotation Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `barcode` | `Barcode` | — | The barcode this annotation is for (read-only). |
| `icon` | `ScanditIcon` | Yellow exclamation | Icon displayed in collapsed state. |
| `text` | `string \| null` | `null` | Text shown in expanded state. Max 20 characters. `null` = does not expand. |
| `annotationTrigger` | `BarcodeArAnnotationTrigger` | `HighlightTapAndBarcodeScan` | When the annotation is shown. |
| `backgroundColor` | `Color` | `#FFFFFF` | Background color. |
| `textColor` | `Color` | `#121619` | Text color in expanded state. |
| `hasTip` | `boolean` | `true` | Whether to draw a pointer tip. |

### Responsive Annotations

`BarcodeArResponsiveAnnotation` wraps two `BarcodeArInfoAnnotation` instances and automatically switches between them based on the barcode's size on screen. Use it when you want richer content when the user is close-up, and a simpler view when the barcode is small.

```javascript
import {
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArInfoAnnotationWidthPreset,
  BarcodeArResponsiveAnnotation,
} from 'scandit-capacitor-datacapture-barcode';

window.barcodeArView.annotationProvider = {
  annotationForBarcode: async (barcode) => {
    // Close-up: rich info annotation
    const closeup = new BarcodeArInfoAnnotation(barcode);
    closeup.width = BarcodeArInfoAnnotationWidthPreset.Large;
    const detailRow = new BarcodeArInfoAnnotationBodyComponent();
    detailRow.text = `Data: ${barcode.data}`;
    closeup.body = [detailRow];

    // Far away: minimal annotation
    const faraway = new BarcodeArInfoAnnotation(barcode);
    faraway.width = BarcodeArInfoAnnotationWidthPreset.Medium;
    const shortRow = new BarcodeArInfoAnnotationBodyComponent();
    shortRow.text = barcode.data;
    faraway.body = [shortRow];

    const responsive = new BarcodeArResponsiveAnnotation(barcode, closeup, faraway);
    responsive.threshold = 0.05; // 5% of screen area = close-up boundary
    return responsive;
  },
};
```

### BarcodeArResponsiveAnnotation Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `threshold` | `number` | `0.05` | Fraction of screen area above which the close-up annotation is shown. Value between 0.0 and 1.0. |
| `annotationTrigger` | `BarcodeArAnnotationTrigger` | `HighlightTapAndBarcodeScan` | When annotations are shown. |

## Step 10 — Feedback

By default, `BarcodeArView` emits sound and haptics when barcodes are detected. Configure this through `BarcodeArViewSettings` (applied at view creation) or through the `feedback` property on the `BarcodeAr` mode.

```javascript
import { BarcodeArFeedback } from 'scandit-capacitor-datacapture-barcode';
import { Feedback } from 'scandit-capacitor-datacapture-core';

// Use the default feedback (sound + haptic)
window.barcodeAr.feedback = BarcodeArFeedback.defaultFeedback;

// Or create a custom feedback
const customFeedback = new BarcodeArFeedback();
customFeedback.scanned = Feedback.defaultFeedback;
window.barcodeAr.feedback = customFeedback;
```

### BarcodeArFeedback Properties

| Property | Type | Description |
|----------|------|-------------|
| `scanned` | `Feedback` | Feedback triggered when a barcode is first scanned/tracked. |
| `tapped` | `Feedback` | Feedback triggered when a barcode highlight or annotation is tapped. |

## Step 11 — HTML Setup

Unlike SparkScan, MatrixScan AR **requires** a DOM container element. The `<div id="barcode-ar-view">` must be present on the scanning screen and be sized to fill the camera area. The native AR overlay will mirror its position and size.

### Minimal HTML

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>MatrixScan AR</title>
  <meta name="viewport" content="viewport-fit=cover, width=device-width, initial-scale=1.0,
    minimum-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <style>
    html, body {
      margin: 0;
      padding: 0;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      font-family: Arial, Helvetica, sans-serif;
    }
    #scanning {
      display: flex;
      flex-direction: column;
      width: 100vw;
      height: 100vh;
    }
    #barcode-ar-view {
      flex: 1;
      position: relative;
      width: 100%;
    }
  </style>
</head>
<body>
  <div id="scanning">
    <div id="barcode-ar-view"></div>
  </div>
  <script type="module" src="js/app.js"></script>
</body>
</html>
```

### Key CSS considerations

- The `#barcode-ar-view` element must have non-zero dimensions at the time `connectToElement` is called. If it is hidden (`display: none`) at initialization time, show it first and then call `connectToElement`.
- Use `env(safe-area-inset-*)` for any UI chrome (toolbars, buttons) surrounding the camera view to handle device notches and home indicators correctly.
- The AR view tracks DOM rect changes automatically — resizing the container element will update the native overlay.

## Step 12 — Complete Example

A full working app with circle highlights and info annotations.

### index.html (scanning screen excerpt)

```html
<div id="scanning" class="hidden scanning-screen">
  <div class="toolbar">
    <p class="toolbar-title">MatrixScan AR</p>
  </div>
  <div id="barcode-ar-view" style="flex:1; position:relative; width:100%;"></div>
  <div class="bottom-toolbar">
    <button id="return-button">Return</button>
  </div>
</div>
```

### app.js

```javascript
import {
  Camera,
  DataCaptureContext,
  FrameSourceState,
  ScanditCaptureCorePlugin,
  VideoResolution,
  Color,
  Brush,
  ScanditIconBuilder,
  ScanditIconType,
} from 'scandit-capacitor-datacapture-core';

import {
  BarcodeAr,
  BarcodeArView,
  BarcodeArSettings,
  BarcodeArViewSettings,
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArInfoAnnotationWidthPreset,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';

let context;
let camera;

async function initializeSDK() {
  if (!context) {
    context = DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
  }

  // Set up camera with recommended settings for AR
  const cameraSettings = BarcodeAr.createRecommendedCameraSettings();
  cameraSettings.preferredResolution = VideoResolution.UHD4K;
  camera = Camera.withSettings(cameraSettings);
  await context.setFrameSource(camera);

  // Configure symbologies
  const settings = new BarcodeArSettings();
  settings.enableSymbologies([
    Symbology.EAN13UPCA,
    Symbology.EAN8,
    Symbology.Code128,
    Symbology.QR,
  ]);

  // Create the BarcodeAr mode (no context argument here)
  window.barcodeAr = new BarcodeAr(settings);

  // Create view settings
  const viewSettings = new BarcodeArViewSettings();

  // Create the view
  window.barcodeArView = new BarcodeArView({
    context,
    barcodeAr: window.barcodeAr,
    settings: viewSettings,
    cameraSettings,
  });

  // Connect to DOM element
  const containerEl = document.getElementById('barcode-ar-view');
  await window.barcodeArView.connectToElement(containerEl);

  // Set highlight provider: circle dots
  window.barcodeArView.highlightProvider = {
    highlightForBarcode: async (barcode) => {
      const highlight = new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Dot);
      highlight.brush = new Brush(Color.fromHex('#2EC1CE'), Color.fromHex('#2EC1CE'), 1.0);
      return highlight;
    },
  };

  // Set annotation provider: info annotation with barcode data
  window.barcodeArView.annotationProvider = {
    annotationForBarcode: async (barcode) => {
      const annotation = new BarcodeArInfoAnnotation(barcode);
      annotation.width = BarcodeArInfoAnnotationWidthPreset.Medium;

      const row = new BarcodeArInfoAnnotationBodyComponent();
      row.text = barcode.data || '(unknown)';
      annotation.body = [row];

      return annotation;
    },
  };

  // Turn camera on
  await camera.switchToDesiredState(FrameSourceState.On);
}

async function uninitializeSDK() {
  if (camera) {
    await camera.switchToDesiredState(FrameSourceState.Off);
    camera = null;
  }
  if (window.barcodeArView) {
    window.barcodeArView.detachFromElement();
    window.barcodeArView = null;
  }
}

window.addEventListener('load', async () => {
  // initializePlugins must be called before any Scandit API
  await ScanditCaptureCorePlugin.initializePlugins();

  document.getElementById('return-button').addEventListener('click', uninitializeSDK);

  await initializeSDK();
});
```

## Key Rules

1. **Initialize plugins first** — `await ScanditCaptureCorePlugin.initializePlugins()` must be called before any other Scandit API. Capacitor-specific, no equivalent in other frameworks.
2. **Minimum SDK 8.2** — BarcodeAr is not available on Capacitor before SDK version 8.2. Do not suggest downgrading.
3. **Context creation** — `DataCaptureContext.initialize(licenseKey)` is the current API. `forLicenseKey()` still exists but is deprecated.
4. **BarcodeAr constructor** — `new BarcodeAr(settings)` takes only settings. The context is wired through `BarcodeArView`, not the mode constructor.
5. **DOM container required** — `BarcodeArView` must be connected to a DOM element with `await barcodeArView.connectToElement(element)` before use. The element must have non-zero dimensions.
6. **Camera is explicit** — Use `BarcodeAr.createRecommendedCameraSettings()`, `Camera.withSettings(...)`, and `context.setFrameSource(camera)` to configure and attach the camera. Switch it on with `camera.switchToDesiredState(FrameSourceState.On)`.
7. **Teardown** — Call `camera.switchToDesiredState(FrameSourceState.Off)` and `barcodeArView.detachFromElement()` when done. Do not call `dispose()` (that is SparkScan; BarcodeArView uses `detachFromElement`).
8. **Provider methods are async** — `highlightForBarcode` and `annotationForBarcode` must return a `Promise`. Returning `null` suppresses the highlight or annotation for that barcode.
9. **Imports** — Core types from `scandit-capacitor-datacapture-core`; barcode types from `scandit-capacitor-datacapture-barcode`. `ScanditIconBuilder`, `Color`, `Brush` come from core.
10. **Cap sync** — Run `npx cap sync` after installing or updating Scandit packages.
11. **Prevent garbage collection** — Store `barcodeAr` and `barcodeArView` on `window` or at module scope.
12. **Camera permissions** — iOS requires `NSCameraUsageDescription` in `Info.plist`. Android handles it automatically.
13. **BarcodeArFilter is not yet available on the published Capacitor package** — `BarcodeArFilter` is documented for Capacitor at SDK 8.5, but it is not yet present in the published `scandit-capacitor-datacapture-*` package (latest published is 8.4.0). Do not generate `BarcodeArFilter` / `BarcodeAr.setBarcodeFilter()` code today. To limit which barcodes are shown, return `null` from the `highlightProvider` / `annotationProvider` for the barcodes you want to hide.
14. **BarcodeArCustomHighlight is not available on Capacitor** — Fully custom highlight views (`BarcodeArCustomHighlight`) exist only on React Native and Flutter. On Capacitor, customize the built-in `BarcodeArRectangleHighlight` / `BarcodeArCircleHighlight` via their `brush` and `icon` properties instead. Do not suggest `BarcodeArCustomHighlight` in a Capacitor project.
