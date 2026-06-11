# MatrixScan AR Cordova Migration Guide

Migrate an existing `BarcodeBatch` (a.k.a. `BarcodeTracking` in older SDK versions) Cordova integration to the new `BarcodeAr` API. The concepts are identical — both track multiple barcodes simultaneously and overlay AR content — but the surface API is modernized and simplified. In Cordova all SDK symbols live on the global `Scandit.*` namespace; there are no ES module imports at runtime.

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

Also search for the older name used in pre-v7 SDK versions:

```
BarcodeTracking
BarcodeTrackingSettings
BarcodeTrackingListener
```

> **Note**: In SDK v6 and earlier the same concept was called `BarcodeTracking`. Apply this same migration guide regardless of which name is present — the mapping is identical.

If none of those symbols appear, fall back to `references/integration.md` — the project may already be using BarcodeAr or an entirely different mode.

---

## Step 2 — Confirm the migration is appropriate

Before rewriting anything, ask the user three quick questions:

1. **Goal**: Is the goal to display AR highlights or annotations (tooltips, bubbles, status icons) on top of each tracked barcode? If the goal is a list-building UX instead, suggest SparkScan rather than BarcodeAr.

2. **Overlay type**: Are they using `BarcodeBatchAdvancedOverlay` with fully custom per-barcode HTML elements (like `setViewForTrackedBarcode` / `TrackedBarcodeView.withHTMLElement`)? → In BarcodeAr the equivalent is `BarcodeArCustomAnnotation`, **but `BarcodeArCustomAnnotation` is NOT available on Cordova** (it is a React Native / Flutter / web-only class in the current API). Freeform HTML overlays must be replaced with one of the built-in annotation types: `BarcodeArInfoAnnotation`, `BarcodeArPopoverAnnotation`, `BarcodeArStatusIconAnnotation`, or `BarcodeArResponsiveAnnotation`. Flag this prominently to the user and agree on a replacement annotation type before writing code.

   Are the bubbles showing structured text fields (title, rows, footer)? → Use `BarcodeArInfoAnnotation`, which handles layout natively with no custom DOM.

3. **Filtering**: Are they relying on per-barcode rejection at the mode level? `BarcodeArFilter` is documented for Cordova at SDK 8.5, but it is **not yet in the published `scandit-cordova-datacapture-*` plugin** (latest is 8.4.0), so do not generate it today. To limit which barcodes are shown, return `null` from the `highlightProvider` or `annotationProvider` for unwanted barcodes to suppress their AR UI.

---

## Step 3 — Update plugin version and global namespace usage

### Plugin version

BarcodeAr requires plugin version **8.2 or later**. If the project is on an older version, update first:

```bash
cordova plugin remove scandit-cordova-datacapture-barcode
cordova plugin remove scandit-cordova-datacapture-core
cordova plugin add scandit-cordova-datacapture-core@^8.2.0
cordova plugin add scandit-cordova-datacapture-barcode@^8.2.0
cordova prepare
```

`cordova prepare` is required after every plugin change. Skipping it leaves the native layer on the old version.

### DataCaptureContext factory rename (v7 → v8)

If the project uses the v7 factory:

**Before:**
```javascript
const context = Scandit.DataCaptureContext.forLicenseKey('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
```

**After:**
```javascript
const context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
```

### No ES module imports needed

In plain Cordova all Scandit classes are accessed through the `Scandit.*` global. Do **not** add `import` statements from `scandit-cordova-datacapture-*` packages — those are plugin manifests, not runtime modules. Remove any such imports if present.

---

## Step 4 — Replace the mode and view setup

### Mode construction

**Before:**
```javascript
const settings = new Scandit.BarcodeBatchSettings();
settings.enableSymbologies([...]);
const barcodeBatch = new Scandit.BarcodeBatch(settings);
context.setMode(barcodeBatch);
```

**After:**
```javascript
const settings = new Scandit.BarcodeArSettings();
settings.enableSymbologies([...]);
const barcodeAr = new Scandit.BarcodeAr(settings);
// BarcodeAr is wired to context via the BarcodeArView constructor — no context.addMode() call needed on Cordova.
```

> **Important**: On Cordova, `BarcodeAr` is linked to the `DataCaptureContext` implicitly when you pass `context` to the `BarcodeArView` constructor. You do **not** call `context.addMode(barcodeAr)` or `context.setMode(barcodeAr)` separately. Remove both of those calls.

### Camera settings

**Before:**
```javascript
const cameraSettings = Scandit.BarcodeBatch.createRecommendedCameraSettings();
```

**After:**
```javascript
const cameraSettings = Scandit.BarcodeAr.createRecommendedCameraSettings();
```

### View construction

**Before:**
```javascript
const view = Scandit.DataCaptureView.forContext(context);
view.connectToElement(document.getElementById('data-capture-view'));
const overlay = new Scandit.BarcodeBatchBasicOverlay(barcodeBatch, Scandit.BarcodeBatchBasicOverlayStyle.Frame);
view.addOverlay(overlay);
```

**After:**
```javascript
const viewSettings = new Scandit.BarcodeArViewSettings();
const barcodeArView = new Scandit.BarcodeArView({
  context,
  barcodeAr,
  settings: viewSettings,
  cameraSettings,
});
await barcodeArView.connectToElement(document.getElementById('barcode-ar-view'));
```

Key differences:
- `Scandit.DataCaptureView.forContext(context)` → `new Scandit.BarcodeArView({ context, barcodeAr, settings, cameraSettings })`
- `view.connectToElement(el)` is now `async` — always `await` it
- No `view.addOverlay(...)` calls — highlights and annotations are wired as properties on the view
- Rename (or re-use) the HTML container `<div>` to match the new element ID

### HTML container

**Before:**
```html
<div id="data-capture-view" class="top"></div>
```

**After:**
```html
<div id="barcode-ar-view" style="flex: 1; width: 100%;"></div>
```

The element must be in the DOM before `connectToElement` is called and must occupy the full area where the camera feed will appear.

---

## Step 5 — Migrate `BarcodeBatchBasicOverlay` → highlights

### Frame style → `BarcodeArRectangleHighlight`

**Before:**
```javascript
const overlay = new Scandit.BarcodeBatchBasicOverlay(barcodeBatch, Scandit.BarcodeBatchBasicOverlayStyle.Frame);
view.addOverlay(overlay);
```

**After:**
```javascript
barcodeArView.highlightProvider = {
  highlightForBarcode: async (barcode) => {
    return new Scandit.BarcodeArRectangleHighlight(barcode);
  },
};
```

### Dot style → `BarcodeArCircleHighlight`

**Before:**
```javascript
const overlay = new Scandit.BarcodeBatchBasicOverlay(barcodeBatch, Scandit.BarcodeBatchBasicOverlayStyle.Dot);
view.addOverlay(overlay);
```

**After:**
```javascript
barcodeArView.highlightProvider = {
  highlightForBarcode: async (barcode) => {
    return new Scandit.BarcodeArCircleHighlight(barcode, Scandit.BarcodeArCircleHighlightPreset.Dot);
  },
};
```

The provider fires once per barcode when it first enters the tracked set. Return `null` to suppress the highlight for a specific barcode.

To customize the highlight brush (colors and stroke width):
```javascript
barcodeArView.highlightProvider = {
  highlightForBarcode: async (barcode) => {
    const highlight = new Scandit.BarcodeArRectangleHighlight(barcode);
    highlight.brush = new Scandit.Brush(
      Scandit.Color.fromHex('#00FFFF66'), // fill color
      Scandit.Color.fromHex('#00FFFF'),   // stroke color
      1.0,                                // stroke width
    );
    return highlight;
  },
};
```

---

## Step 6 — Migrate `BarcodeBatchAdvancedOverlay` → annotations

> **IMPORTANT — `BarcodeArCustomAnnotation` is NOT available on Cordova.** The Bubbles sample wires fully custom HTML elements per barcode using `TrackedBarcodeView.withHTMLElement` and `setViewForTrackedBarcode`. There is no direct equivalent in BarcodeAr on Cordova. Freeform HTML overlays **must** be replaced with one of the built-in annotation types. Discuss with the user which built-in type best fits their content before writing code.

### Custom HTML bubbles → `BarcodeArInfoAnnotation`

If the existing bubble renders structured text (a title and optional detail row), replace the entire DOM creation + `setViewForTrackedBarcode` chain with a `BarcodeArInfoAnnotation`:

**Before (Bubbles sample pattern):**
```javascript
window.advancedOverlay = new Scandit.BarcodeBatchAdvancedOverlay(window.barcodeBatch);
window.advancedOverlay.listener = {
  anchorForTrackedBarcode: () => Scandit.Anchor.TopCenter,
  offsetForTrackedBarcode: () => new Scandit.PointWithUnit(
    new Scandit.NumberWithUnit(0, Scandit.MeasureUnit.Fraction),
    new Scandit.NumberWithUnit(-1, Scandit.MeasureUnit.Fraction),
  ),
};
window.view.addOverlay(window.advancedOverlay);

// In session listener or updateView:
const bubble = Scandit.TrackedBarcodeView.withHTMLElement(
  createBubbleWithContent(viewContent, trackedBarcode.barcode.data),
  { scale: 1 / window.devicePixelRatio },
);
window.advancedOverlay.setViewForTrackedBarcode(bubble, trackedBarcode).catch(console.warn);
```

**After:**
```javascript
barcodeArView.annotationProvider = {
  annotationForBarcode: async (barcode) => {
    const annotation = new Scandit.BarcodeArInfoAnnotation(barcode);
    annotation.annotationTrigger = Scandit.BarcodeArAnnotationTrigger.HighlightTapAndBarcodeScan;
    annotation.width = Scandit.BarcodeArInfoAnnotationWidthPreset.Medium;
    annotation.anchor = Scandit.BarcodeArInfoAnnotationAnchor.Top;

    const header = new Scandit.BarcodeArInfoAnnotationHeader();
    header.text = 'Report stock count';
    annotation.header = header;

    const row = new Scandit.BarcodeArInfoAnnotationBodyComponent();
    row.text = 'Shelf: 4  Back Room: 8';
    annotation.body = [row];

    return annotation;
  },
};
```

`annotation.anchor = Scandit.BarcodeArInfoAnnotationAnchor.Top` replaces both `anchorForTrackedBarcode` (which returned `Anchor.TopCenter`) and `offsetForTrackedBarcode` (which pushed the overlay above the barcode with a negative fraction offset). The built-in anchor handles positioning automatically — no `PointWithUnit`, `NumberWithUnit`, or `MeasureUnit` needed.

Delete: `createBubbleWithContent`, the `viewContents` map, `isViewShowingAlternateContent`, `setView`, and `updateView` — the annotation provider replaces all of that.

### Tap-toggled alternate content → `BarcodeArInfoAnnotation` with a tap listener

The Bubbles sample shows a different bubble content when the user taps the overlay (`isViewShowingAlternateContent` toggle). In BarcodeAr, attach a listener to the annotation instead:

```javascript
barcodeArView.annotationProvider = {
  annotationForBarcode: async (barcode) => {
    const annotation = new Scandit.BarcodeArInfoAnnotation(barcode);
    annotation.width = Scandit.BarcodeArInfoAnnotationWidthPreset.Medium;
    annotation.anchor = Scandit.BarcodeArInfoAnnotationAnchor.Top;
    annotation.isEntireAnnotationTappable = true;

    const row = new Scandit.BarcodeArInfoAnnotationBodyComponent();
    row.text = 'Shelf: 4  Back Room: 8';
    annotation.body = [row];

    annotation.listener = {
      didTap: (ann) => {
        // Show alternate content (barcode data) on tap
        ann.body[0].text = ann.barcode.data;
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

### Distance-based show/hide → `BarcodeArResponsiveAnnotation`

The Bubbles sample contains a `viewLocation.width() > (screen.width * 0.1)` guard that hides the annotation when the barcode is too far away. Delete that heuristic and use `BarcodeArResponsiveAnnotation` instead:

**Before (delete this logic entirely):**
```javascript
// Old pattern — delete all of this:
Scandit.Quadrilateral.prototype.width = function () { ... };
window.view.viewQuadrilateralForFrameQuadrilateral(trackedBarcode.location)
  .then(location => updateView(trackedBarcode, location, ...));
const shouldBeShown = viewLocation.width() > (screen.width * 0.1);
```

**After:**
```javascript
barcodeArView.annotationProvider = {
  annotationForBarcode: async (barcode) => {
    // Close-up: full detail
    const closeUp = new Scandit.BarcodeArInfoAnnotation(barcode);
    closeUp.width = Scandit.BarcodeArInfoAnnotationWidthPreset.Medium;
    const closeUpHeader = new Scandit.BarcodeArInfoAnnotationHeader();
    closeUpHeader.text = 'Report stock count';
    closeUp.header = closeUpHeader;
    const closeUpRow = new Scandit.BarcodeArInfoAnnotationBodyComponent();
    closeUpRow.text = 'Shelf: 4  Back Room: 8';
    closeUp.body = [closeUpRow];
    closeUp.anchor = Scandit.BarcodeArInfoAnnotationAnchor.Top;

    // Far away: minimal placeholder
    const farAway = new Scandit.BarcodeArInfoAnnotation(barcode);
    farAway.width = Scandit.BarcodeArInfoAnnotationWidthPreset.Small;
    const farAwayRow = new Scandit.BarcodeArInfoAnnotationBodyComponent();
    farAwayRow.text = barcode.data;
    farAway.body = [farAwayRow];
    farAway.anchor = Scandit.BarcodeArInfoAnnotationAnchor.Top;

    const responsive = new Scandit.BarcodeArResponsiveAnnotation(barcode, closeUp, farAway);
    responsive.threshold = 0.1; // ~10% of screen width, matches the old heuristic
    return responsive;
  },
};
```

No `Scandit.Quadrilateral.prototype.width`, `viewQuadrilateralForFrameQuadrilateral`, `screen.width`, or `shouldBeShown` needed.

---

## Step 7 — Migrate the listener

In BarcodeBatch the session listener drove both app state and overlay content (calling `setViewForTrackedBarcode` for every frame). In BarcodeAr these responsibilities are split:

- **Visual content** (highlights, annotations) → handled by the providers (Steps 5 and 6). Do not call overlay methods in the listener.
- **App state** (e.g. building a results map, reacting to removed barcodes) → handled in `BarcodeArListener.didUpdateSession`.

**Before (Simple sample pattern):**
```javascript
barcodeBatch.addListener({
  didUpdateSession: (barcodeBatch, session) => {
    Object.values(session.trackedBarcodes).forEach(trackedBarcode => {
      window.results[trackedBarcode.barcode.data] = trackedBarcode;
    });
  }
});
```

**After:**
```javascript
barcodeAr.addListener({
  didUpdateSession: async (barcodeAr, session, getFrameData) => {
    // Use addedTrackedBarcodes — only newly tracked barcodes, not all of them every frame.
    session.addedTrackedBarcodes.forEach(trackedBarcode => {
      window.results[trackedBarcode.barcode.data] = trackedBarcode;
    });
  }
});
```

Key changes:
- `Object.values(session.trackedBarcodes)` → `session.addedTrackedBarcodes` (array, not object)
- The listener is registered on `barcodeAr.addListener(...)` (same pattern, different instance)
- Make the callback `async` (or return a Promise) — the BarcodeAr listener expects a Promise

**Before (Bubbles sample — removed barcodes):**
```javascript
session.removedTrackedBarcodes.forEach(identifier => {
  isViewShowingAlternateContent[identifier] = null;
  viewContents[identifier] = null;
});
```

In BarcodeAr, if the provider already handles content per barcode, you may not need the removed-barcode bookkeeping at all — delete it if the `viewContents`/`isViewShowingAlternateContent` maps are gone. If you still track per-barcode state, keep the `session.removedTrackedBarcodes` loop — that property exists on `BarcodeArSession` unchanged.

---

## Step 8 — Migrate lifecycle

### Enabling / disabling scanning

**Before:**
```javascript
// Start
barcodeBatch.isEnabled = true;
camera.switchToDesiredState(Scandit.FrameSourceState.On);

// Stop / freeze
barcodeBatch.isEnabled = false;
camera.switchToDesiredState(Scandit.FrameSourceState.Off);
```

**After:**
```javascript
// Start
await camera.switchToDesiredState(Scandit.FrameSourceState.On);
// BarcodeArView starts automatically once the camera is running

// Stop / freeze
await barcodeArView.stop();
await camera.switchToDesiredState(Scandit.FrameSourceState.Off);

// Resume
await camera.switchToDesiredState(Scandit.FrameSourceState.On);
await barcodeArView.start();
```

`BarcodeAr` has no `isEnabled` property. Use `barcodeArView.start()` / `barcodeArView.stop()` / `barcodeArView.pause()` for scanning control. Camera state is still toggled via `camera.switchToDesiredState(Scandit.FrameSourceState.On/Off)` — that pattern is unchanged.

> **`stop()` is reversible — `detachFromElement()` is not.** If the user is *leaving* the scan screen (back button, navigation away), do not stop here — go to Step 9 and call `detachFromElement` instead. Calling `stop()` without ever detaching leaks the native view.

The Bubbles sample's `freeze()` / `unfreeze()` functions become:

```javascript
const freeze = async () => {
  await barcodeArView.stop();
  await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
};

const unfreeze = async () => {
  await camera.switchToDesiredState(Scandit.FrameSourceState.On);
  await barcodeArView.start();
};
```

### App backgrounding / resuming

```javascript
document.addEventListener('pause', async () => {
  if (camera) await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
}, false);

document.addEventListener('resume', async () => {
  if (camera) await camera.switchToDesiredState(Scandit.FrameSourceState.On);
}, false);
```

This pattern is unchanged from the BarcodeBatch integration.

---

## Step 9 — Cleanup / teardown

### Find the teardown site

`BarcodeBatch` had no formal teardown — the legacy code typically just toggled `isEnabled` and switched the camera off. `BarcodeArView` **must** be detached from its DOM element when the scan screen is left, otherwise the native AR layer leaks.

Locate the teardown site in the legacy code. It is one of:
- An explicit `teardown()` / `cleanup()` / `dispose()` function.
- The function that runs when the user navigates away from the scan screen (e.g. a `stopScanning()` / `closeScanner()` / `onBack()` handler that is called by the back button or screen change — **not** the freeze/unfreeze handlers, which are temporary pauses).
- A `pagebeforehide` / `cordova.exec` event handler if the project uses one.

If no such function exists in the legacy code, **add one** — `BarcodeAr` makes teardown mandatory where `BarcodeBatch` made it optional. A scan screen that the user can leave needs a teardown.

### Migrate the teardown

**Before:**
```javascript
// BarcodeBatch — no formal teardown, camera was just switched off
camera.switchToDesiredState(Scandit.FrameSourceState.Off);
barcodeBatch.isEnabled = false;
```

**After:**
```javascript
const teardown = async () => {
  // 1. Stop the camera
  if (camera) {
    await camera.switchToDesiredState(Scandit.FrameSourceState.Off);
    camera = null;
  }
  // 2. Detach the view from the DOM element — releases native resources
  if (barcodeArView) {
    await barcodeArView.detachFromElement();
    barcodeArView = null;
  }
  // 3. Nullify mode and context references
  barcodeAr = null;
  context = null;
};
```

`barcodeArView.detachFromElement()` is **required** — it releases the native AR layer. Forgetting this call leaks native resources. There are no overlay objects to clean up — the `BarcodeBatchBasicOverlay` and `BarcodeBatchAdvancedOverlay` refs are gone entirely.

> **Do not confuse freeze with teardown.** A `freeze` / `pause` function (Step 8) calls `barcodeArView.stop()` and `camera.switchToDesiredState(Off)` — it does *not* call `detachFromElement`. The view is still attached and can be resumed. Teardown is one-way: after `detachFromElement`, the view cannot be restarted; a new `BarcodeArView` must be created.

---

## Step 10 — Verify

Run through this checklist before considering the migration complete:

- [ ] No `BarcodeBatch`, `BarcodeBatchSettings`, `BarcodeBatchSession`, `BarcodeBatchBasicOverlay`, `BarcodeBatchBasicOverlayStyle`, `BarcodeBatchAdvancedOverlay`, or `TrackedBarcodeView` symbols remain (a text search for `BarcodeBatch` or `BarcodeTracking` should return zero matches).
- [ ] `Scandit.DataCaptureView.forContext(...)` is gone — replaced by `new Scandit.BarcodeArView({ ... })`.
- [ ] `view.addOverlay(...)` calls are gone.
- [ ] `context.setMode(...)` is removed. (BarcodeAr is linked to the context via the `BarcodeArView` constructor, not via `addMode`/`setMode`.)
- [ ] At least one of `barcodeArView.highlightProvider` or `barcodeArView.annotationProvider` is set.
- [ ] `await barcodeArView.connectToElement(el)` is called after constructing the view. The DOM element must exist at that point.
- [ ] `await barcodeArView.detachFromElement()` is called during teardown.
- [ ] `barcodeBatch.isEnabled = true/false` is replaced by camera state toggling and `barcodeArView.start()`/`barcodeArView.stop()`.
- [ ] `Scandit.BarcodeBatch.createRecommendedCameraSettings()` is replaced by `Scandit.BarcodeAr.createRecommendedCameraSettings()`.
- [ ] No `Scandit.Quadrilateral.prototype.width`, `viewQuadrilateralForFrameQuadrilateral`, `PointWithUnit`, `NumberWithUnit`, `MeasureUnit`, or `TrackedBarcodeView.withHTMLElement` calls remain.
- [ ] No `setViewForTrackedBarcode`, `setAnchorForTrackedBarcode`, or `setOffsetForTrackedBarcode` calls remain.
- [ ] **`BarcodeArCustomAnnotation` is NOT used** — it is not available on Cordova. Any freeform HTML overlay content must use a built-in annotation type (`BarcodeArInfoAnnotation`, `BarcodeArPopoverAnnotation`, `BarcodeArStatusIconAnnotation`, or `BarcodeArResponsiveAnnotation`).
- [ ] `cordova prepare` has been run after updating plugin versions.
- [ ] Provider callbacks are `async` functions (or return `Promise.resolve(...)`).
