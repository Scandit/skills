# MatrixScan AR Capacitor Migration Guide

Migrate an existing `BarcodeBatch` (a.k.a. `BarcodeTracking` in older SDK versions) integration to the new `BarcodeAr` API. The concepts are identical — both track multiple barcodes simultaneously and overlay AR content — but the surface API is modernized and simplified.

---

## Step 1 — Detect that the file uses BarcodeBatch

Search the target file for any of these symbols:

```
BarcodeBatch
BarcodeBatchSettings
BarcodeBatchSession
BarcodeBatchListener
BarcodeBatchBasicOverlay
BarcodeBatchBasicOverlayStyle
BarcodeBatchAdvancedOverlay
TrackedBarcodeView
```

> **Note**: In older SDK versions the same concept was called `BarcodeTracking` (with `BarcodeTrackingSettings`, `BarcodeTrackingListener`, etc.). Apply this same migration guide regardless of which name is present — the mapping is identical.

If none of those symbols appear in the file, fall back to `references/integration.md` — the project may already be using BarcodeAr or an entirely different mode.

---

## Step 2 — Confirm the migration is appropriate

Before rewriting anything, ask the user three quick questions:

1. **Goal**: Is the goal to display AR highlights or annotations (tooltips, bubbles, custom views) on top of each tracked barcode? If the goal is a list-building UX instead, suggest SparkScan rather than BarcodeAr.

2. **Overlay type**: Are they using `BarcodeBatchAdvancedOverlay` with fully custom per-barcode HTML elements built via `TrackedBarcodeView.withHTMLElement` (like `setViewForTrackedBarcode`)? → The closest replacement is `BarcodeArInfoAnnotation` or `BarcodeArPopoverAnnotation`. **Important**: `BarcodeArCustomAnnotation` is **not available on Capacitor** — do not suggest it. If the bubbles are showing structured text fields (title, rows, footer), `BarcodeArInfoAnnotation` is the right replacement. For action buttons, use `BarcodeArPopoverAnnotation`. For compact status badges, use `BarcodeArStatusIconAnnotation`.

3. **Filtering**: Are they relying on per-barcode filtering at the mode level? Note this caveat from the integration reference:

   > **Note**: `BarcodeArFilter` is **not available on Capacitor** — the interface and `BarcodeAr.setBarcodeFilter()` are iOS/Android native only. Do not use this API in Capacitor projects. If filtering is needed, return `null` from the `highlightProvider` or `annotationProvider` for unwanted barcodes, or filter inside the `BarcodeArListener.didUpdateSession` callback.

---

## Step 3 — Update imports

Drop the BarcodeBatch symbols and add the BarcodeAr equivalents. Only remove the symbols that are actually unused after migration.

**Before:**
```javascript
import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
  ScanditCaptureCorePlugin,
  VideoResolution,
  Anchor,
  MeasureUnit,
  NumberWithUnit,
  PointWithUnit,
  Quadrilateral,
} from 'scandit-capacitor-datacapture-core';

import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchAdvancedOverlay,
  BarcodeBatchSettings,
  Symbology,
  TrackedBarcodeView,
} from 'scandit-capacitor-datacapture-barcode';
```

**After (highlights only — adjust to the annotation variant if using Advanced Overlay):**
```javascript
import {
  Camera,
  DataCaptureContext,
  FrameSourceState,
  ScanditCaptureCorePlugin,
  VideoResolution,
  Brush,
  Color,
} from 'scandit-capacitor-datacapture-core';

import {
  BarcodeAr,
  BarcodeArView,
  BarcodeArSettings,
  BarcodeArViewSettings,
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
  Symbology,
} from 'scandit-capacitor-datacapture-barcode';
```

For the Advanced Overlay → Info Annotation path, also add:
```javascript
import {
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationHeader,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArInfoAnnotationWidthPreset,
  BarcodeArAnnotationTrigger,
} from 'scandit-capacitor-datacapture-barcode';
```

**Drop entirely** (no equivalent in BarcodeAr on Capacitor):
- `DataCaptureView` — replaced by `BarcodeArView`
- `BarcodeBatchBasicOverlay` / `BarcodeBatchBasicOverlayStyle` — replaced by a `highlightProvider` object on `BarcodeArView`
- `BarcodeBatchAdvancedOverlay` — replaced by an `annotationProvider` object on `BarcodeArView`
- `TrackedBarcodeView` — no equivalent; annotation content is expressed through built-in `BarcodeArInfoAnnotation`, `BarcodeArPopoverAnnotation`, or `BarcodeArStatusIconAnnotation`
- `Anchor`, `PointWithUnit`, `NumberWithUnit`, `MeasureUnit` — the advanced overlay anchor/offset listener is gone; annotation positioning is handled automatically
- `Quadrilateral` — not needed in BarcodeAr at all

> **Capacitor-specific**: `BarcodeArCustomAnnotation` is **not available on Capacitor**. Do not add it to imports. The Capacitor API does not expose custom HTML annotations through this class — use `BarcodeArInfoAnnotation` (text fields), `BarcodeArPopoverAnnotation` (action buttons), `BarcodeArStatusIconAnnotation` (compact badges), or `BarcodeArResponsiveAnnotation` (distance-adaptive) instead.

---

## Step 4 — Replace the mode + view setup

### Mode construction

**Before:**
```javascript
const settings = new BarcodeBatchSettings();
settings.enableSymbologies([...]);
const barcodeBatch = new BarcodeBatch(settings);
context.setMode(barcodeBatch);
```

**After:**
```javascript
const settings = new BarcodeArSettings();
settings.enableSymbologies([...]);
window.barcodeAr = new BarcodeAr(settings);
context.addMode(window.barcodeAr);
```

Key difference: `setMode` is replaced by `addMode`. `setMode` removed all other modes first; `addMode` is additive. Also note that `new BarcodeAr(settings)` takes **only** settings — the context is wired via `BarcodeArView`, not passed to the mode constructor.

### Camera settings

**Before:**
```javascript
// Simple sample pattern (no createRecommendedCameraSettings):
const camera = Camera.default;
camera.preferredResolution = VideoResolution.FullHD;
context.setFrameSource(camera);

// Bubbles sample pattern:
const cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
cameraSettings.preferredResolution = VideoResolution.UHD4K;
window.camera = Camera.withSettings(cameraSettings);
context.setFrameSource(window.camera);
```

**After:**
```javascript
const cameraSettings = BarcodeAr.createRecommendedCameraSettings();
cameraSettings.preferredResolution = VideoResolution.UHD4K;
const camera = Camera.withSettings(cameraSettings);
await context.setFrameSource(camera);
```

Always use `BarcodeAr.createRecommendedCameraSettings()` — it returns settings optimized for AR tracking performance.

### View construction

**Before:**
```javascript
const view = DataCaptureView.forContext(context);
view.connectToElement(document.getElementById('data-capture-view'));
// Then: view.addOverlay(basicOverlay);
```

**After:**
```javascript
const viewSettings = new BarcodeArViewSettings();
window.barcodeArView = new BarcodeArView({
  context,
  barcodeAr: window.barcodeAr,
  settings: viewSettings,
  cameraSettings,
});
await window.barcodeArView.connectToElement(document.getElementById('barcode-ar-view'));
```

Key differences:
- `BarcodeArView` is constructed with an options object `{ context, barcodeAr, settings, cameraSettings }` — not via a static factory.
- `connectToElement` must be **awaited**.
- No `addOverlay` calls are needed — highlights and annotations are wired as properties directly on the `BarcodeArView` instance.
- The DOM element id may need updating if the HTML used `data-capture-view` — rename it to `barcode-ar-view` or whatever id the existing HTML uses, and verify the `<div>` has non-zero dimensions at the time `connectToElement` is called.

Store `barcodeAr` and `barcodeArView` on `window` (or at module scope) to prevent garbage collection.

---

## Step 5 — Migrate `BarcodeBatchBasicOverlay` → highlights

### Frame style → `BarcodeArRectangleHighlight`

**Before:**
```javascript
const basicOverlay = new BarcodeBatchBasicOverlay(barcodeBatch, BarcodeBatchBasicOverlayStyle.Frame);
view.addOverlay(basicOverlay);
```

**After:**
```javascript
import { BarcodeArRectangleHighlight } from 'scandit-capacitor-datacapture-barcode';
import { Brush, Color } from 'scandit-capacitor-datacapture-core';

window.barcodeArView.highlightProvider = {
  highlightForBarcode: async (barcode) => {
    const highlight = new BarcodeArRectangleHighlight(barcode);
    highlight.brush = new Brush(
      Color.fromHex('#2EC1CE66'), // fill (with alpha)
      Color.fromHex('#2EC1CE'),   // stroke
      2.0,
    );
    return highlight;
  },
};
```

### Dot style → `BarcodeArCircleHighlight`

**Before:**
```javascript
const basicOverlay = new BarcodeBatchBasicOverlay(barcodeBatch, BarcodeBatchBasicOverlayStyle.Dot);
view.addOverlay(basicOverlay);
```

**After:**
```javascript
import {
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
} from 'scandit-capacitor-datacapture-barcode';

window.barcodeArView.highlightProvider = {
  highlightForBarcode: async (barcode) => {
    return new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Dot);
  },
};
```

The provider is called once per barcode when it first enters the tracked set. Return `null` to suppress the highlight for a specific barcode.

---

## Step 6 — Migrate `BarcodeBatchAdvancedOverlay` → annotations

### Capacitor caveat — no `BarcodeArCustomAnnotation`

> **Important**: `BarcodeArCustomAnnotation` is **not available on Capacitor**. The old `BarcodeBatchAdvancedOverlay` pattern used `TrackedBarcodeView.withHTMLElement(domElement, ...)` + `setViewForTrackedBarcode(...)` to inject arbitrary HTML into the AR layer. There is no 1:1 replacement for this on Capacitor. Custom HTML overlays built with `createBubbleWithContent` and `TrackedBarcodeView` **do not have a direct equivalent** — the user must redesign their AR content using the built-in annotation types: `BarcodeArInfoAnnotation`, `BarcodeArPopoverAnnotation`, `BarcodeArStatusIconAnnotation`, or `BarcodeArResponsiveAnnotation`.

Flag this prominently to the user before proceeding. Confirm which annotation type best matches their original content:
- Text fields (title, stock count rows) → `BarcodeArInfoAnnotation`
- Action buttons (accept/reject) → `BarcodeArPopoverAnnotation`
- Compact status badges → `BarcodeArStatusIconAnnotation`
- Distance-adaptive content → `BarcodeArResponsiveAnnotation`

### HTML bubble with text fields → `BarcodeArInfoAnnotation`

The Bubbles sample builds a custom DOM element with a title and a text row per barcode and injects it via `setViewForTrackedBarcode`. Replace the entire `createBubbleWithContent` / `setView` / `updateView` chain with an annotation provider:

**Before:**
```javascript
window.advancedOverlay = new BarcodeBatchAdvancedOverlay(window.barcodeBatch);
window.advancedOverlay.listener = {
  anchorForTrackedBarcode: () => Anchor.TopCenter,
  offsetForTrackedBarcode: () =>
    new PointWithUnit(
      new NumberWithUnit(0, MeasureUnit.Fraction),
      new NumberWithUnit(-1, MeasureUnit.Fraction)
    ),
};

// In didUpdateSession:
const bubble = TrackedBarcodeView.withHTMLElement(
  createBubbleWithContent({ title: 'Report stock count', text: 'Shelf: 4 Back Room: 8' }),
  { scale: 1 / window.devicePixelRatio },
);
window.advancedOverlay.setViewForTrackedBarcode(bubble, trackedBarcode).catch(console.warn);
```

**After:**
```javascript
import {
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationHeader,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArInfoAnnotationWidthPreset,
  BarcodeArAnnotationTrigger,
} from 'scandit-capacitor-datacapture-barcode';

window.barcodeArView.annotationProvider = {
  annotationForBarcode: async (barcode) => {
    if (!barcode.data) return null;

    const header = new BarcodeArInfoAnnotationHeader();
    header.text = 'Report stock count';

    const shelfRow = new BarcodeArInfoAnnotationBodyComponent();
    shelfRow.text = 'Shelf: 4  Back Room: 8';

    const annotation = new BarcodeArInfoAnnotation(barcode);
    annotation.header = header;
    annotation.body = [shelfRow];
    annotation.width = BarcodeArInfoAnnotationWidthPreset.Medium;
    return annotation;
  },
};
```

The `annotationProvider` replaces both the overlay listener (`anchorForTrackedBarcode`, `offsetForTrackedBarcode`) and the `setViewForTrackedBarcode` call. No `Anchor`, `PointWithUnit`, `NumberWithUnit`, `MeasureUnit`, `TrackedBarcodeView`, or `createBubbleWithContent` are needed.

### Distance-based show/hide → `BarcodeArResponsiveAnnotation`

The Bubbles sample contains a manual size heuristic that hides the annotation when the barcode is too small on screen:

```javascript
// Old pattern — delete this entirely:
Quadrilateral.prototype.width = function () { ... };
const shouldBeShown = viewLocation.width() > (screen.width * 0.1);
window.view.viewQuadrilateralForFrameQuadrilateral(trackedBarcode.location)
  .then(location => updateView(trackedBarcode, location, ...));
```

Replace it with `BarcodeArResponsiveAnnotation`, which switches between two `BarcodeArInfoAnnotation` variants based on the barcode's relative size on screen:

```javascript
import {
  BarcodeArResponsiveAnnotation,
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArInfoAnnotationWidthPreset,
} from 'scandit-capacitor-datacapture-barcode';

window.barcodeArView.annotationProvider = {
  annotationForBarcode: async (barcode) => {
    if (!barcode.data) return null;

    // Close-up: full detail annotation
    const closeUp = new BarcodeArInfoAnnotation(barcode);
    const headerClose = new BarcodeArInfoAnnotationHeader();
    headerClose.text = 'Report stock count';
    const bodyClose = new BarcodeArInfoAnnotationBodyComponent();
    bodyClose.text = 'Shelf: 4  Back Room: 8';
    closeUp.header = headerClose;
    closeUp.body = [bodyClose];
    closeUp.width = BarcodeArInfoAnnotationWidthPreset.Large;

    // Far away: minimal placeholder
    const farAway = new BarcodeArInfoAnnotation(barcode);
    const bodyFar = new BarcodeArInfoAnnotationBodyComponent();
    bodyFar.text = barcode.data;
    farAway.body = [bodyFar];
    farAway.width = BarcodeArInfoAnnotationWidthPreset.Small;

    const responsive = new BarcodeArResponsiveAnnotation(barcode, closeUp, farAway);
    responsive.threshold = 0.1; // ~10% of screen width, matches old heuristic
    return responsive;
  },
};
```

No `Quadrilateral`, `screen.width`, `viewQuadrilateralForFrameQuadrilateral`, or `updateView` needed.

### Tap-to-toggle alternate content

The Bubbles sample toggles between two bubble states when the user taps (via `didTapViewForTrackedBarcode`). In BarcodeAr, handle this in a `uiListener` on `BarcodeArView`:

```javascript
window.barcodeArView.uiListener = {
  didTapHighlightForBarcode: async (barcodeAr, barcode, highlight) => {
    // Re-query the annotationProvider with updated state for this barcode
    // or update highlight appearance directly on the highlight object
    console.log('Tapped:', barcode.data);
  },
};
```

For toggling annotation content on tap, manage a state map keyed by barcode data and call `window.barcodeArView.reset()` to force the annotationProvider to be re-invoked for all tracked barcodes.

---

## Step 7 — Migrate the listener

In BarcodeBatch the session listener iterated `session.trackedBarcodes` on every frame to both update app state and drive overlay content. In BarcodeAr these responsibilities are split:

- **Visual content** (highlights, annotations) → handled by the providers (Steps 5 and 6). Do not call `setViewForTrackedBarcode` or create overlay objects in the listener.
- **App state** (e.g. populating a results map) → handled in `BarcodeArListener.didUpdateSession` using `session.addedTrackedBarcodes`.

**Before (Simple sample pattern):**
```javascript
barcodeBatch.addListener({
  didUpdateSession: async (barcodeBatch, session) => {
    Object.values(session.trackedBarcodes).forEach(trackedBarcode => {
      results[trackedBarcode.barcode.data] = trackedBarcode;
    });
  }
});
```

**After:**
```javascript
window.barcodeAr.addListener({
  didUpdateSession: async (barcodeAr, session) => {
    // Use addedTrackedBarcodes — only newly tracked barcodes, not all of them every frame.
    for (const trackedBarcode of session.addedTrackedBarcodes) {
      if (trackedBarcode.barcode.data) {
        results[trackedBarcode.barcode.data] = trackedBarcode;
      }
    }
  }
});
```

Key changes:
- `Object.values(session.trackedBarcodes)` → `session.addedTrackedBarcodes` (already an array)
- The listener is registered on `window.barcodeAr.addListener(...)` (same pattern, different instance)

**Before (Bubbles sample — also drove overlay content from listener):**
```javascript
window.barcodeBatch.addListener({
  didUpdateSession: async (mode, session) => {
    session.removedTrackedBarcodes.forEach(identifier => {
      isViewShowingAlternateContent[identifier] = null;
      viewContents[identifier] = null;
    });
    Object.values(session.trackedBarcodes).forEach(trackedBarcode =>
      window.view.viewQuadrilateralForFrameQuadrilateral(trackedBarcode.location)
        .then(location => updateView(trackedBarcode, location, ...)));
  }
});
```

**After:**
```javascript
window.barcodeAr.addListener({
  didUpdateSession: async (barcodeAr, session) => {
    // Visual content is now handled by annotationProvider — do not call
    // viewQuadrilateralForFrameQuadrilateral or setViewForTrackedBarcode here.
    // Only manage app state:
    for (const identifier of session.removedTrackedBarcodes) {
      delete myStateMap[identifier];
    }
  }
});
```

If the old code handled `session.removedTrackedBarcodes`, keep that logic — the property exists on `BarcodeArSession` with the same name.

---

## Step 8 — Migrate lifecycle

### Enabling / disabling scanning

**Before:**
```javascript
// Enable
barcodeBatch.isEnabled = true;
// Disable
barcodeBatch.isEnabled = false;
```

**After:**
```javascript
// Start
await window.barcodeArView.start();
// Stop / pause
await window.barcodeArView.stop();
```

`BarcodeAr` has no `isEnabled` property. Use `barcodeArView.start()` / `barcodeArView.stop()` / `barcodeArView.pause()` on the view instance instead.

### Camera lifecycle

The camera setup using `BarcodeAr.createRecommendedCameraSettings()`, `Camera.withSettings(...)`, `context.setFrameSource(camera)`, and `camera.switchToDesiredState(FrameSourceState.On/Off)` is unchanged in concept. Keep any existing camera on/off toggle logic — only replace `barcodeBatch.isEnabled` with `barcodeArView.start()`/`stop()`.

### Freeze / unfreeze pattern

**Before (Bubbles sample):**
```javascript
const freeze = async () => {
  window.barcodeBatch.isEnabled = false;
  await window.camera.switchToDesiredState(FrameSourceState.Off);
};
const unfreeze = async () => {
  window.barcodeBatch.isEnabled = true;
  await window.camera.switchToDesiredState(FrameSourceState.On);
};
```

**After:**
```javascript
const freeze = async () => {
  await window.barcodeArView.stop();
  await window.camera.switchToDesiredState(FrameSourceState.Off);
};
const unfreeze = async () => {
  await window.camera.switchToDesiredState(FrameSourceState.On);
  await window.barcodeArView.start();
};
```

---

## Step 9 — Cleanup / teardown

**Before:**
```javascript
async function uninitialize() {
  await camera.switchToDesiredState(FrameSourceState.Off);
  // No explicit view teardown in old samples
}
```

**After:**
```javascript
async function uninitialize() {
  if (window.camera) {
    await window.camera.switchToDesiredState(FrameSourceState.Off);
    window.camera = null;
  }
  if (window.barcodeArView) {
    window.barcodeArView.detachFromElement();
    window.barcodeArView = null;
  }
}
```

Key changes:
- Call `barcodeArView.detachFromElement()` (not `dispose()` — that is a SparkScan API) to release native resources and disconnect the view from the DOM element.
- Remove all `overlay` references (basic and advanced) — there are no overlay objects to clean up in BarcodeAr.
- Set `window.barcodeArView` to `null` to allow garbage collection.

---

## Step 10 — Verify

Run through this checklist before considering the migration complete:

- [ ] No `BarcodeBatch`, `BarcodeBatchSettings`, `BarcodeBatchBasicOverlay`, `BarcodeBatchBasicOverlayStyle`, or `BarcodeBatchAdvancedOverlay` symbols remain in the file (a text search for `BarcodeBatch` or `BarcodeTracking` should return zero matches).
- [ ] No `TrackedBarcodeView` import or usage remains — this class has no equivalent in BarcodeAr on Capacitor.
- [ ] Imports from `scandit-capacitor-datacapture-barcode` contain only `BarcodeAr*` symbols and `Symbology` (plus any annotation/highlight types used).
- [ ] `DataCaptureView.forContext(...)` and `DataCaptureView` are gone — replaced by `new BarcodeArView({...})`.
- [ ] `view.addOverlay(...)` calls are gone.
- [ ] `barcodeArView.highlightProvider` or `barcodeArView.annotationProvider` (or both) is set on the view.
- [ ] `connectToElement(...)` is awaited.
- [ ] `context.setMode(...)` is replaced by `context.addMode(...)`.
- [ ] `barcodeBatch.isEnabled = true/false` is replaced by `barcodeArView.start()` / `barcodeArView.stop()`.
- [ ] Teardown calls `barcodeArView.detachFromElement()` (not `dispose()`).
- [ ] No `Anchor`, `PointWithUnit`, `NumberWithUnit`, `MeasureUnit`, or `Quadrilateral` imports remain.
- [ ] No `viewQuadrilateralForFrameQuadrilateral`, `createBubbleWithContent`, `setViewForTrackedBarcode`, or `screen.width` calls remain.
- [ ] `BarcodeArCustomAnnotation` is **not** in the file — it is not available on Capacitor.
- [ ] `BarcodeArFilter` / `setBarcodeFilter` is **not** in the file — it is not available on Capacitor.
- [ ] `window.barcodeAr` and `window.barcodeArView` are stored at module/window scope to prevent garbage collection.
