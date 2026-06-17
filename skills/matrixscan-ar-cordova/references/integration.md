# MatrixScan AR Cordova Integration Guide

## Integration flow

Before writing any code, align with the user:

1. **Which symbologies do they need to scan?** Retail typically uses EAN-13/UPC-A, EAN-8, UPC-E, Code 128, Code 39, ITF. Logistics often adds Data Matrix, QR, PDF417. Only enable what the user asks for — each extra symbology costs processing time.
2. **Which highlights and annotations are needed?** Circle highlights, rectangle highlights, info annotations, popovers, status icons, responsive annotations, or custom implementations. Clarify before writing provider code.
3. **Which file should BarcodeAr be wired into?** If the user hasn't told you, ask for the path of the JS/TS file that owns the scanning screen (e.g. `www/js/app.js`, `www/js/index.js`).
4. **Write the code directly into that file.** Do not dump a giant snippet and tell the user to copy/paste — open the file with the edit tools and make the changes in place. Preserve existing code (DOM wiring, event listeners, state) alongside the new BarcodeAr integration.
5. **After the code is in place, show a setup checklist** (packages, camera permissions, CSP, iOS/Android prerequisites) so the user can verify the runtime prerequisites.

MatrixScan AR (BarcodeAr) scans multiple barcodes simultaneously and renders AR highlights and annotations on top of each detected barcode in real time. The view is positioned by mirroring an HTML `<div>` element — the native AR layer sits behind the webview content but above the camera feed.

## Prerequisites

- **Cordova plugins installed**:
  - `scandit-cordova-datacapture-core`
  - `scandit-cordova-datacapture-barcode`
- Install with:
  ```bash
  cordova plugin add scandit-cordova-datacapture-core
  cordova plugin add scandit-cordova-datacapture-barcode
  ```
- **Minimum plugin version**: 8.2 for BarcodeAr on Cordova. The BarcodeAr classes do not exist in earlier versions.
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
  showHomeScreen();
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

## Step 3 — Set up the camera

BarcodeAr on Cordova manages the camera manually — there is no automatic camera lifecycle. Use the recommended camera settings from the mode:

```javascript
const cameraSettings = Scandit.BarcodeAr.createRecommendedCameraSettings();
// Optionally override resolution:
// cameraSettings.preferredResolution = Scandit.VideoResolution.UHD4K;

const camera = Scandit.Camera.withSettings(cameraSettings);
await context.setFrameSource(camera);
```

Start and stop the camera explicitly around scanning:

```javascript
// Start:
await camera.switchToDesiredState(Scandit.FrameSourceState.On);

// Stop (teardown):
await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
```

## Step 4 — Configure BarcodeArSettings

Choose which barcode symbologies to scan. Only enable what the user asked for.

```javascript
const settings = new Scandit.BarcodeArSettings();

settings.enableSymbologies([
  Scandit.Symbology.EAN13UPCA,
  Scandit.Symbology.EAN8,
  Scandit.Symbology.UPCE,
  Scandit.Symbology.Code39,
  Scandit.Symbology.Code128,
  Scandit.Symbology.DataMatrix,
  Scandit.Symbology.QR,
]);

// Optional: adjust active symbol counts for variable-length symbologies
const code39Settings = settings.settingsForSymbology(Scandit.Symbology.Code39);
code39Settings.activeSymbolCounts = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20];
```

### BarcodeArSettings methods

| Method | Description |
|--------|-------------|
| `enableSymbologies(symbologies)` | Enable multiple symbologies at once. |
| `enableSymbology(symbology, enabled)` | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | Get per-symbology `SymbologySettings`. |
| `setProperty(name, value)` / `getProperty(name)` | Advanced properties by name. |

### BarcodeArSettings properties

| Property | Type | Description |
|----------|------|-------------|
| `enabledSymbologies` | `Symbology[]` | The currently enabled symbologies (read-only). |

## Step 5 — Create the BarcodeAr mode

```javascript
const barcodeAr = new Scandit.BarcodeAr(settings);
```

On Cordova, `new Scandit.BarcodeAr(settings)` is the correct constructor — not `BarcodeAr.forContext(...)` (that form is web-only).

### BarcodeAr methods

| Method | Description |
|--------|-------------|
| `addListener(listener)` | Add a `BarcodeArListener` for session updates. |
| `removeListener(listener)` | Remove a previously added listener. |
| `applySettings(settings)` | Asynchronously apply new settings while the mode is running. Returns a `Promise`. |

### BarcodeAr properties

| Property | Type | Description |
|----------|------|-------------|
| `feedback` | `BarcodeArFeedback` | Feedback emitted on barcode events. See Step 9. |

## Step 6 — Add a BarcodeArListener (optional)

The listener fires every frame while barcodes are tracked. It is optional — highlights and annotations are driven by providers on the view, not by this listener.

```javascript
barcodeAr.addListener({
  didUpdateSession: async (barcodeAr, session, getFrameData) => {
    const added = session.addedTrackedBarcodes;
    const removed = session.removedTrackedBarcodes;
    const all = session.trackedBarcodes;
    // Process session data here
  },
});
```

### BarcodeArListener callbacks

| Callback | Signature | Description |
|----------|-----------|-------------|
| `didUpdateSession` | `(barcodeAr, session, getFrameData) => Promise<void>` | Called every frame with updated session state. |

### BarcodeArSession properties

| Property | Type | Description |
|----------|------|-------------|
| `addedTrackedBarcodes` | `TrackedBarcode[]` | Barcodes newly tracked in this frame. |
| `removedTrackedBarcodes` | `string[]` | Identifiers of barcodes that left the frame. |
| `trackedBarcodes` | `{ [id: string]: TrackedBarcode }` | All currently tracked barcodes. |
| `reset()` | `Promise<void>` | Clear all tracked barcodes and session state. |

## Step 7 — Create the BarcodeArView

`BarcodeArView` renders the camera feed and AR overlays. On Cordova it uses a **DOM-overlay model**: the native view is sized and positioned to match a plain HTML `<div>` you provide.

### Step 7a — Add the container element to your HTML

```html
<div id="barcode-ar-view" style="flex: 1; width: 100%;"></div>
```

The element should fill the space where the camera feed will appear. Surrounding controls (toolbar, buttons) sit in sibling elements outside this div.

### Step 7b — Create BarcodeArViewSettings

```javascript
const viewSettings = new Scandit.BarcodeArViewSettings();
// Defaults: soundEnabled=true, hapticEnabled=true, defaultCameraPosition=WorldFacing
// Optionally override:
// viewSettings.soundEnabled = false;
// viewSettings.hapticEnabled = false;
```

### BarcodeArViewSettings properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `soundEnabled` | `boolean` | `true` | Enable/disable sound feedback. |
| `hapticEnabled` | `boolean` | `true` | Enable/disable haptic feedback. |
| `defaultCameraPosition` | `CameraPosition` | `WorldFacing` | Which camera to open by default. |

### Step 7c — Construct the BarcodeArView and connect it to the DOM element

```javascript
const barcodeArView = new Scandit.BarcodeArView({
  context,
  barcodeAr,
  settings: viewSettings,
  cameraSettings,
});

const containerEl = document.getElementById('barcode-ar-view');
await barcodeArView.connectToElement(containerEl);
```

`connectToElement(element)` links the native AR layer to the DOM node so its size and position are mirrored. Always `await` it.

### BarcodeArView methods

| Method | Description |
|--------|-------------|
| `connectToElement(element)` | Mirror the native view to the given DOM element. Returns `Promise<void>`. |
| `detachFromElement()` | Release the DOM element. Call during teardown. Returns `Promise<void>`. |
| `start()` | Start the scanning process. Returns `Promise<void>`. |
| `stop()` | Stop the scanning process. Returns `Promise<void>`. |
| `pause()` | Pause scanning. Returns `Promise<void>`. |
| `reset()` | Clear all current highlights and annotations, then re-query providers. Returns `Promise<void>`. |

### BarcodeArView properties

| Property | Type | Description |
|----------|------|-------------|
| `highlightProvider` | `BarcodeArHighlightProvider \| null` | Supplies highlight instances per barcode. |
| `annotationProvider` | `BarcodeArAnnotationProvider \| null` | Supplies annotation instances per barcode. |
| `uiListener` | `IBarcodeArViewUiListener \| null` | Receives tap events on highlights. |
| `shouldShowTorchControl` | `boolean` | Show/hide the torch button. Default `false`. |
| `torchControlPosition` | `Anchor` | Where the torch button appears. Default `TopLeft`. |
| `shouldShowZoomControl` | `boolean` | Show/hide the zoom button. |
| `zoomControlPosition` | `Anchor` | Where the zoom button appears. Default `BottomRight`. |
| `shouldShowCameraSwitchControl` | `boolean` | Show/hide the camera-switch button. |
| `cameraSwitchControlPosition` | `Anchor` | Where the camera-switch button appears. Default `TopRight`. |
| `shouldShowMacroModeControl` | `boolean` | Show/hide the macro mode button (iOS only). |

## Step 8 — Highlights

Highlights are native overlays drawn on top of each detected barcode. Two built-in shapes are available: circle and rectangle. The `highlightProvider` on `BarcodeArView` is called once per barcode and returns the highlight to display.

### Setting a highlight provider

```javascript
barcodeArView.highlightProvider = {
  highlightForBarcode: async (barcode) => {
    const highlight = new Scandit.BarcodeArRectangleHighlight(barcode);
    // Customize the brush (fill color, stroke color, stroke width):
    highlight.brush = new Scandit.Brush(
      Scandit.Color.fromHex('#00FFFF66'),  // fill
      Scandit.Color.fromHex('#00FFFF'),    // stroke
      1.0,                                 // stroke width
    );
    return highlight;
  },
};
```

Return `null` from `highlightForBarcode` to suppress the highlight for a specific barcode.

### BarcodeArCircleHighlight

A circular highlight. Two presets are available:

| Preset | Description |
|--------|-------------|
| `Scandit.BarcodeArCircleHighlightPreset.Dot` | Smaller blue circle. |
| `Scandit.BarcodeArCircleHighlightPreset.Icon` | Larger blue circle, suited for icons. |

```javascript
const highlight = new Scandit.BarcodeArCircleHighlight(
  barcode,
  Scandit.BarcodeArCircleHighlightPreset.Icon,
);
highlight.brush = new Scandit.Brush(
  Scandit.Color.fromHex('#0D853D'),
  Scandit.Color.fromHex('#0D853D'),
  1.0,
);
// Optional icon (e.g. checkmark):
highlight.icon = new Scandit.ScanditIconBuilder()
  .withIcon(Scandit.ScanditIconType.Checkmark)
  .withIconColor(Scandit.Color.fromHex('#FFFFFF'))
  .build();
highlight.size = 48; // device-independent pixels, minimum 18
```

### BarcodeArCircleHighlight properties

| Property | Type | Description |
|----------|------|-------------|
| `barcode` | `Barcode` | The barcode this highlight is for (read-only). |
| `brush` | `Brush` | Fill/stroke colors and width. |
| `icon` | `ScanditIcon \| null` | Icon shown inside the circle. |
| `size` | `number` | Circle diameter in dp. Minimum 18. |

### BarcodeArRectangleHighlight

A rectangular highlight aligned to the barcode bounding box.

```javascript
const highlight = new Scandit.BarcodeArRectangleHighlight(barcode);
highlight.brush = new Scandit.Brush(
  Scandit.Color.fromHex('#0000FF66'),
  Scandit.Color.fromHex('#0000FF'),
  1.0,
);
highlight.icon = null; // optional icon
```

### BarcodeArRectangleHighlight properties

| Property | Type | Description |
|----------|------|-------------|
| `barcode` | `Barcode` | The barcode this highlight is for (read-only). |
| `brush` | `Brush` | Fill/stroke colors and width. |
| `icon` | `ScanditIcon \| null` | Optional icon drawn inside the rectangle. |

### Reacting to highlight taps

To respond when the user taps a barcode highlight, set `uiListener` on the view:

```javascript
barcodeArView.uiListener = {
  didTapHighlightForBarcode: (barcodeAr, barcode, highlight) => {
    console.log('Tapped barcode:', barcode.data);
    // You can mutate highlight properties here to update its appearance:
    highlight.brush = new Scandit.Brush(
      Scandit.Color.fromHex('#FF000066'),
      Scandit.Color.fromHex('#FF0000'),
      2.0,
    );
  },
};
```

### ScanditIcon construction

Icons used in highlights and annotations are built with `ScanditIconBuilder`:

```javascript
const icon = new Scandit.ScanditIconBuilder()
  .withIcon(Scandit.ScanditIconType.Checkmark)        // icon type
  .withIconColor(Scandit.Color.fromHex('#FFFFFF'))     // icon color
  .withBackgroundShape(Scandit.ScanditIconShape.Circle) // optional background
  .withBackgroundColor(Scandit.Color.fromHex('#0D853D')) // background color
  .build();
```

Available `ScanditIconType` values include `Checkmark`, `ExclamationMark`, `XMark`, and others — check the Core API reference for the full list.

## Step 9 — Annotations

Annotations appear outside the barcode area and display additional information or interactive controls. They are driven by `annotationProvider` on `BarcodeArView`. The provider is called once per barcode and returns an annotation or `null`.

### Annotation triggers

| Trigger | Description |
|---------|-------------|
| `Scandit.BarcodeArAnnotationTrigger.HighlightTap` | Shown only when the user taps the highlight. |
| `Scandit.BarcodeArAnnotationTrigger.HighlightTapAndBarcodeScan` | Shown immediately on scan, toggleable by tap. (Default for most annotation types.) |

### BarcodeArInfoAnnotation

A tooltip that shows structured text (header, body components, footer) anchored to a barcode.

```javascript
barcodeArView.annotationProvider = {
  annotationForBarcode: async (barcode) => {
    const annotation = new Scandit.BarcodeArInfoAnnotation(barcode);
    annotation.annotationTrigger = Scandit.BarcodeArAnnotationTrigger.HighlightTapAndBarcodeScan;
    annotation.width = Scandit.BarcodeArInfoAnnotationWidthPreset.Medium;
    annotation.anchor = Scandit.BarcodeArInfoAnnotationAnchor.Bottom;
    annotation.backgroundColor = Scandit.Color.fromHex('#FFFFFF');

    // Header (optional)
    const header = new Scandit.BarcodeArInfoAnnotationHeader();
    header.text = 'Product Info';
    header.backgroundColor = Scandit.Color.fromHex('#00FFFF');
    annotation.header = header;

    // Body (one or more rows)
    const row1 = new Scandit.BarcodeArInfoAnnotationBodyComponent();
    row1.text = barcode.data;

    const row2 = new Scandit.BarcodeArInfoAnnotationBodyComponent();
    row2.text = 'In stock';
    row2.leftIcon = new Scandit.ScanditIconBuilder()
      .withIcon(Scandit.ScanditIconType.Checkmark)
      .withIconColor(Scandit.Color.fromHex('#0D853D'))
      .build();

    annotation.body = [row1, row2];

    // Footer (optional)
    const footer = new Scandit.BarcodeArInfoAnnotationFooter();
    footer.text = 'Tap for details';
    footer.backgroundColor = Scandit.Color.fromHex('#121619');
    annotation.footer = footer;

    // Handle taps on the whole annotation (set isEntireAnnotationTappable to true)
    annotation.isEntireAnnotationTappable = true;
    annotation.listener = {
      didTap: (ann) => {
        console.log('Annotation tapped for barcode:', ann.barcode.data);
      },
      didTapHeader: () => {},
      didTapFooter: () => {},
      didTapLeftIcon: () => {},
      didTapRightIcon: () => {},
    };

    return annotation;
  },
};
```

### BarcodeArInfoAnnotation properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `barcode` | `Barcode` | — | The barcode this annotation is for (read-only). |
| `annotationTrigger` | `BarcodeArAnnotationTrigger` | `HighlightTapAndBarcodeScan` | When to show the annotation. |
| `width` | `BarcodeArInfoAnnotationWidthPreset` | `Small` | Annotation width preset. |
| `anchor` | `BarcodeArInfoAnnotationAnchor` | `Bottom` | Anchor edge relative to the barcode. |
| `hasTip` | `boolean` | `true` | Whether the annotation has a tip arrow. |
| `isEntireAnnotationTappable` | `boolean` | `false` | If `true`, the whole annotation fires `didTap`. |
| `backgroundColor` | `Color` | `#CCFFFFFF` | Annotation background color. |
| `body` | `BarcodeArInfoAnnotationBodyComponent[]` | `[]` | Array of row components. |
| `header` | `BarcodeArInfoAnnotationHeader \| null` | `null` | Optional header. |
| `footer` | `BarcodeArInfoAnnotationFooter \| null` | `null` | Optional footer. |
| `listener` | `IBarcodeArInfoAnnotationListener \| null` | `null` | Callback object for tap events. |

### BarcodeArInfoAnnotationWidthPreset values

| Value | Description |
|-------|-------------|
| `Scandit.BarcodeArInfoAnnotationWidthPreset.Small` | Best for text/icon only, no header or footer. |
| `Scandit.BarcodeArInfoAnnotationWidthPreset.Medium` | Medium width. |
| `Scandit.BarcodeArInfoAnnotationWidthPreset.Large` | Wide annotation. |

### BarcodeArInfoAnnotationAnchor values

`Top`, `Bottom`, `Left`, `Right` — determines which edge of the annotation attaches to the barcode.

### BarcodeArInfoAnnotationBodyComponent

Each body component is a horizontal row with optional left/right icons and a text label.

```javascript
const row = new Scandit.BarcodeArInfoAnnotationBodyComponent();
row.text = 'Row text';
row.textSize = 14;          // scale-independent pixels
row.textColor = Scandit.Color.fromHex('#121619');
row.leftIcon = someIcon;    // ScanditIcon or null
row.rightIcon = null;
row.isLeftIconTappable = true;
row.isRightIconTappable = true;
```

### BarcodeArInfoAnnotationHeader / BarcodeArInfoAnnotationFooter

```javascript
const header = new Scandit.BarcodeArInfoAnnotationHeader();
header.text = 'Title';
header.icon = someIcon;
header.textSize = 16;
header.textColor = Scandit.Color.fromHex('#000000');
header.backgroundColor = Scandit.Color.fromHex('#00FFFF');

const footer = new Scandit.BarcodeArInfoAnnotationFooter();
footer.text = 'Footer note';
footer.textColor = Scandit.Color.fromHex('#FFFFFF');
footer.backgroundColor = Scandit.Color.fromHex('#000000');
```

### IBarcodeArInfoAnnotationListener callbacks

All callbacks are optional. Only implement what you need.

| Callback | When called |
|----------|-------------|
| `didTap(annotation)` | Entire annotation tapped (requires `isEntireAnnotationTappable = true`). |
| `didTapHeader(annotation)` | Header tapped (requires `isEntireAnnotationTappable = false`). |
| `didTapFooter(annotation)` | Footer tapped (requires `isEntireAnnotationTappable = false`). |
| `didTapLeftIcon(annotation, component, componentIndex)` | Left icon in a body row tapped. |
| `didTapRightIcon(annotation, component, componentIndex)` | Right icon in a body row tapped. |

### BarcodeArPopoverAnnotation

A set of icon+text buttons that appear when the user taps a highlight. Good for accept/reject or action workflows.

```javascript
barcodeArView.annotationProvider = {
  annotationForBarcode: async (barcode) => {
    const acceptIcon = new Scandit.ScanditIconBuilder()
      .withIcon(Scandit.ScanditIconType.Checkmark)
      .withIconColor(Scandit.Color.fromHex('#FFFFFF'))
      .withBackgroundShape(Scandit.ScanditIconShape.Circle)
      .withBackgroundColor(Scandit.Color.fromHex('#0D853D'))
      .build();

    const rejectIcon = new Scandit.ScanditIconBuilder()
      .withIcon(Scandit.ScanditIconType.XMark)
      .withIconColor(Scandit.Color.fromHex('#FFFFFF'))
      .withBackgroundShape(Scandit.ScanditIconShape.Circle)
      .withBackgroundColor(Scandit.Color.fromHex('#D92121'))
      .build();

    const acceptButton = new Scandit.BarcodeArPopoverAnnotationButton(acceptIcon, 'Accept');
    const rejectButton = new Scandit.BarcodeArPopoverAnnotationButton(rejectIcon, 'Reject');

    const popover = new Scandit.BarcodeArPopoverAnnotation(barcode, [acceptButton, rejectButton]);
    popover.annotationTrigger = Scandit.BarcodeArAnnotationTrigger.HighlightTap;

    popover.listener = {
      didTapButton: (popover, button, buttonIndex) => {
        if (buttonIndex === 0) {
          console.log('Accepted:', popover.barcode.data);
        } else {
          console.log('Rejected:', popover.barcode.data);
        }
      },
    };

    return popover;
  },
};
```

### BarcodeArPopoverAnnotation properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `barcode` | `Barcode` | — | The barcode this popover is for (read-only). |
| `annotationTrigger` | `BarcodeArAnnotationTrigger` | `HighlightTap` | When to show the popover. |
| `isEntirePopoverTappable` | `boolean` | `false` | If `true`, tapping anywhere fires `didTap`. |
| `buttons` | `BarcodeArPopoverAnnotationButton[]` | — | The buttons (read-only, set in constructor). |
| `listener` | `IBarcodeArPopoverAnnotationListener \| null` | `null` | Tap callback object. |

### BarcodeArPopoverAnnotationButton constructor

```javascript
new Scandit.BarcodeArPopoverAnnotationButton(icon, text)
```

| Arg | Type | Description |
|-----|------|-------------|
| `icon` | `ScanditIcon` | Button icon. |
| `text` | `string` | Button label. |

### IBarcodeArPopoverAnnotationListener callbacks

| Callback | When called |
|----------|-------------|
| `didTapButton(popover, button, buttonIndex)` | A button was tapped (requires `isEntirePopoverTappable = false`). |
| `didTap(popover)` | Entire popover tapped (requires `isEntirePopoverTappable = true`). |

### BarcodeArStatusIconAnnotation

A compact annotation that shows an icon (collapsed state) and optionally expands to show a short text on tap. Useful for status indicators such as expiry warnings.

```javascript
barcodeArView.annotationProvider = {
  annotationForBarcode: async (barcode) => {
    const annotation = new Scandit.BarcodeArStatusIconAnnotation(barcode);
    annotation.text = 'Close to expiry'; // max 20 characters
    annotation.icon = new Scandit.ScanditIconBuilder()
      .withBackgroundShape(Scandit.ScanditIconShape.Circle)
      .withBackgroundColor(Scandit.Color.fromHex('#FBC02C'))
      .withIcon(Scandit.ScanditIconType.ExclamationMark)
      .withIconColor(Scandit.Color.fromHex('#000000'))
      .build();
    annotation.backgroundColor = Scandit.Color.fromHex('#FFFFFF');
    return annotation;
  },
};
```

### BarcodeArStatusIconAnnotation properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `barcode` | `Barcode` | — | The barcode (read-only). |
| `annotationTrigger` | `BarcodeArAnnotationTrigger` | `HighlightTapAndBarcodeScan` | When to show. |
| `icon` | `ScanditIcon` | Yellow exclamation | The status icon. |
| `text` | `string \| null` | `null` | Expanded text. Max 20 chars. `null` = no expand. |
| `textColor` | `Color` | `#121619` | Text color in expanded state. |
| `backgroundColor` | `Color` | `#FFFFFF` | Background color. |
| `hasTip` | `boolean` | `true` | Whether the annotation has a tip arrow. |

### BarcodeArResponsiveAnnotation

Switches between two `BarcodeArInfoAnnotation` variants based on barcode size relative to screen. Use it to show a compact annotation from far away and a detailed one close-up.

```javascript
barcodeArView.annotationProvider = {
  annotationForBarcode: async (barcode) => {
    // Close-up annotation (shown when barcode area > threshold % of screen)
    const closeUp = new Scandit.BarcodeArInfoAnnotation(barcode);
    closeUp.width = Scandit.BarcodeArInfoAnnotationWidthPreset.Large;
    const closeUpRow = new Scandit.BarcodeArInfoAnnotationBodyComponent();
    closeUpRow.text = `${barcode.data} — full details here`;
    closeUp.body = [closeUpRow];

    // Far-away annotation (shown when barcode is small)
    const farAway = new Scandit.BarcodeArInfoAnnotation(barcode);
    farAway.width = Scandit.BarcodeArInfoAnnotationWidthPreset.Small;
    const farAwayRow = new Scandit.BarcodeArInfoAnnotationBodyComponent();
    farAwayRow.text = barcode.data;
    farAway.body = [farAwayRow];

    const responsive = new Scandit.BarcodeArResponsiveAnnotation(barcode, closeUp, farAway);
    responsive.threshold = 0.05; // 5% of screen area = switch to close-up
    return responsive;
  },
};
```

### BarcodeArResponsiveAnnotation properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `barcode` | `Barcode` | — | The barcode (read-only). |
| `annotationTrigger` | `BarcodeArAnnotationTrigger` | `HighlightTapAndBarcodeScan` | When to show. |
| `threshold` | `number` | `0.05` | Fraction of screen area (0–1) at which close-up annotation is used. |
| `closeUpAnnotation` | `BarcodeArInfoAnnotation \| null` | — | Shown when barcode area exceeds threshold. |
| `farAwayAnnotation` | `BarcodeArInfoAnnotation \| null` | — | Shown when barcode area is below threshold. |

Pass `null` for either annotation variant to display nothing in that state.

> **Filtering visible barcodes:** `BarcodeArFilter` is documented for Cordova at SDK 8.5, but
> it is **not yet in the published `scandit-cordova-datacapture-*` plugin** (latest is 8.4.0),
> so do not generate it today. To limit which barcodes are shown, return `null` from the
> `highlightProvider` / `annotationProvider` for the barcodes you want to suppress.

## Step 10 — Feedback

`BarcodeArFeedback` controls sound and vibration emitted on barcode events. It lives on the `BarcodeAr` mode, not on the view.

```javascript
// Default feedback (sound + vibration):
barcodeAr.feedback = Scandit.BarcodeArFeedback.defaultFeedback;

// Customize — scanned event:
const customFeedback = new Scandit.BarcodeArFeedback();
customFeedback.scanned = new Scandit.Feedback(
  new Scandit.Vibration(Scandit.VibrationType.Default),
  new Scandit.Sound(null),  // null = no sound
);
barcodeAr.feedback = customFeedback;

// Disable all feedback:
barcodeAr.feedback = new Scandit.BarcodeArFeedback();
```

### BarcodeArFeedback properties

| Property | Type | Description |
|----------|------|-------------|
| `scanned` | `Feedback` | Feedback emitted when a barcode is scanned. |
| `tapped` | `Feedback` | Feedback emitted when an element is tapped. |
| `static defaultFeedback` | `BarcodeArFeedback` | Default feedback with sound and vibration. |

## Step 11 — Lifecycle management

### Starting scanning

After calling `connectToElement`, start the camera and optionally call `barcodeArView.start()`:

```javascript
await barcodeArView.connectToElement(containerEl);
await camera.switchToDesiredState(Scandit.FrameSourceState.On);
// BarcodeArView starts automatically once the camera is running
```

### Stopping / tearing down

Always tear down in this order when leaving the scanning screen:

```javascript
const teardown = async () => {
  // 1. Stop the camera
  if (camera) {
    await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
    camera = null;
  }
  // 2. Detach from DOM
  if (barcodeArView) {
    await barcodeArView.detachFromElement();
    barcodeArView = null;
  }
  // 3. Nullify mode references
  barcodeAr = null;
  context = null;
};
```

### Pausing / resuming (e.g. app backgrounding)

```javascript
// Pause when app goes to background:
document.addEventListener('pause', async () => {
  await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
}, false);

// Resume when app comes back to foreground:
document.addEventListener('resume', async () => {
  await camera.switchToDesiredState(Scandit.FrameSourceState.On);
}, false);
```

## Step 12 — HTML setup

### Container element

The `barcode-ar-view` container must be in the DOM before `connectToElement` is called. It should occupy the full area where the camera feed is shown:

```html
<div class="scanning-screen">
  <div class="toolbar">
    <span>MatrixScan AR</span>
  </div>
  <div id="barcode-ar-view" style="flex: 1;"></div>
  <div class="bottom-bar">
    <button onclick="done()">Done</button>
  </div>
</div>
```

### Content-Security-Policy

Cordova requires a CSP meta tag. Use the standard Cordova CSP:

```html
<meta http-equiv="Content-Security-Policy"
  content="default-src 'self' 'unsafe-inline' data: gap: https://ssl.gstatic.com 'unsafe-eval';
           style-src 'self' 'unsafe-inline';
           media-src *;
           img-src 'self' data: content:;" />
```

### Viewport and safe area

```html
<meta name="viewport" content="width=device-width, user-scalable=no, viewport-fit=cover" />
```

In CSS, handle safe areas:

```css
.toolbar {
  padding-top: calc(env(safe-area-inset-top, 0px) + 16px);
}
.bottom-bar {
  padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 16px);
}
#barcode-ar-view {
  flex: 1;
}
.scanning-screen {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
}
```

## Step 13 — Complete example

Full working app based on the official MatrixScanARSimpleSample.

### `www/index.html` (scanning screen excerpt)

```html
<!doctype html>
<html>
  <head>
    <meta http-equiv="Content-Security-Policy"
      content="default-src 'self' 'unsafe-inline' data: gap: https://ssl.gstatic.com 'unsafe-eval';
               style-src 'self' 'unsafe-inline'; media-src *; img-src 'self' data: content:;" />
    <meta name="viewport" content="width=device-width, user-scalable=no, viewport-fit=cover" />
    <title>MatrixScan AR</title>
    <style>
      body { margin: 0; width: 100vw; height: 100vh; overflow: hidden; }
      .scanning-screen { display: flex; flex-direction: column; width: 100%; height: 100%; }
      .toolbar {
        background: #000;
        color: #fff;
        padding: calc(env(safe-area-inset-top, 0px) + 12px) 16px 12px;
        text-align: center;
      }
      #barcode-ar-view { flex: 1; }
      .bottom-bar {
        background: #000;
        display: flex;
        justify-content: center;
        padding: 12px 16px calc(env(safe-area-inset-bottom, 0px) + 12px);
      }
      .hidden { display: none !important; }
    </style>
  </head>
  <body>
    <div id="home">
      <button onclick="startScanning()">Start MatrixScan AR</button>
    </div>
    <div id="scanning" class="scanning-screen hidden">
      <div class="toolbar">MatrixScan AR</div>
      <div id="barcode-ar-view"></div>
      <div class="bottom-bar">
        <button onclick="done()">Done</button>
      </div>
    </div>
    <script src="cordova.js"></script>
    <script src="index.js"></script>
  </body>
</html>
```

### `www/index.js`

```javascript
// @ts-check

let context = null;
let camera = null;
let barcodeAr = null;
let barcodeArView = null;

function showScreen(id) {
  document.getElementById('home').classList.toggle('hidden', id !== 'home');
  document.getElementById('scanning').classList.toggle('hidden', id !== 'scanning');
}

async function startScanning() {
  showScreen('scanning');
  await initializeSDK();
  await camera.switchToDesiredState(Scandit.FrameSourceState.On);
}

async function done() {
  await teardown();
  showScreen('home');
}

async function initializeSDK() {
  if (context) return;

  context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');

  const cameraSettings = Scandit.BarcodeAr.createRecommendedCameraSettings();
  camera = Scandit.Camera.withSettings(cameraSettings);
  await context.setFrameSource(camera);

  const settings = new Scandit.BarcodeArSettings();
  settings.enableSymbologies([
    Scandit.Symbology.EAN13UPCA,
    Scandit.Symbology.EAN8,
    Scandit.Symbology.Code128,
    Scandit.Symbology.DataMatrix,
  ]);

  barcodeAr = new Scandit.BarcodeAr(settings);

  const viewSettings = new Scandit.BarcodeArViewSettings();
  barcodeArView = new Scandit.BarcodeArView({
    context,
    barcodeAr,
    settings: viewSettings,
    cameraSettings,
  });

  // Wire highlight provider
  barcodeArView.highlightProvider = {
    highlightForBarcode: async (barcode) => {
      const highlight = new Scandit.BarcodeArRectangleHighlight(barcode);
      highlight.brush = new Scandit.Brush(
        Scandit.Color.fromHex('#00FFFF66'),
        Scandit.Color.fromHex('#00FFFF'),
        1.0,
      );
      return highlight;
    },
  };

  // Wire annotation provider
  barcodeArView.annotationProvider = {
    annotationForBarcode: async (barcode) => {
      const annotation = new Scandit.BarcodeArInfoAnnotation(barcode);
      annotation.width = Scandit.BarcodeArInfoAnnotationWidthPreset.Medium;

      const row = new Scandit.BarcodeArInfoAnnotationBodyComponent();
      row.text = barcode.data || '—';
      annotation.body = [row];

      return annotation;
    },
  };

  const containerEl = document.getElementById('barcode-ar-view');
  await barcodeArView.connectToElement(containerEl);
}

async function teardown() {
  if (camera) {
    await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
    camera = null;
  }
  if (barcodeArView) {
    await barcodeArView.detachFromElement();
    barcodeArView = null;
  }
  barcodeAr = null;
  context = null;
}

document.addEventListener('deviceready', () => {
  showScreen('home');
}, false);

document.addEventListener('pause', async () => {
  if (camera) await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
}, false);

document.addEventListener('resume', async () => {
  if (camera) await camera.switchToDesiredState(Scandit.FrameSourceState.On);
}, false);
```

## Key rules

1. **Always wait for `deviceready`** before calling any `Scandit.*` API. Never call at module load time.
2. **Use the `Scandit.*` global at runtime** in plain Cordova projects. `scandit-cordova-datacapture-*` are plugin manifests, not runtime modules.
3. **BarcodeAr requires plugin 8.2 or later.** There is no v6/v7 Cordova BarcodeAr history.
4. **`new Scandit.BarcodeAr(settings)`** — Cordova constructor. Do not use `BarcodeAr.forContext(...)`.
5. **`DataCaptureContext.initialize(key)`** — the v8 entry point. Not `.forLicenseKey()` or `.sharedInstance`.
6. **Camera is managed manually.** Call `Scandit.BarcodeAr.createRecommendedCameraSettings()`, set it as the frame source, and switch state explicitly.
7. **`await barcodeArView.connectToElement(el)`** must be called after constructing the view. The DOM container must exist at that time.
8. **`await barcodeArView.detachFromElement()`** must be called during teardown to release native resources.
9. **Provider methods must return a `Promise`** — make them `async` or return `Promise.resolve(...)`. Return `null` to suppress a highlight or annotation for a specific barcode.
10. **Mutating a highlight in `didTapHighlightForBarcode`** updates its appearance in real time — no need to call `reset()` for simple visual state changes.
11. **`barcodeArView.reset()`** clears all visible highlights and annotations and re-queries the providers. Use it when the underlying data changes significantly (e.g. a full product-list refresh).
12. **Run `cordova prepare`** after installing or updating plugins.
13. **Safe-area CSS** (`env(safe-area-inset-*)`) is required on modern iOS notch/Dynamic Island devices.
