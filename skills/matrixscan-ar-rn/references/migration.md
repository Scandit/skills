# MatrixScan AR React Native Migration Guide

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
TrackedBarcode
```

> **Note**: In older SDK versions the same concept was called `BarcodeTracking` (with `BarcodeTrackingSettings`, `BarcodeTrackingListener`, etc.). Apply this same migration guide regardless of which name is present — the mapping is identical.

If none of those symbols appear in the file, fall back to `references/integration.md` — the project may already be using BarcodeAr or an entirely different mode.

---

## Step 2 — Confirm the migration is appropriate

Before rewriting anything, ask the user three quick questions:

1. **Goal**: Is the goal to display AR highlights or annotations (tooltips, bubbles, custom views) on top of each tracked barcode? If the goal is a list-building UX instead, suggest SparkScan rather than BarcodeAr.

2. **Overlay type**: Are they using `BarcodeBatchAdvancedOverlay` with fully custom per-barcode React components (like `setViewForTrackedBarcode`)? → Suggest `BarcodeArCustomAnnotation`. Are the bubbles showing structured text fields (title, rows, footer)? → Suggest `BarcodeArInfoAnnotation` instead, which is less code to maintain.

3. **Filtering**: Are they relying on per-barcode rejection / filtering tracked barcodes at the mode level? Note this caveat:

   > **Note**: `BarcodeArFilter` is documented for React Native at SDK 8.5, but that version is **not yet published** in the `scandit-react-native-datacapture-*` packages (latest published is 8.4.0). Do not generate `BarcodeArFilter` / `setBarcodeFilter(...)` code yet. In the meantime, return `null` from the `highlightProvider` or `annotationProvider` for unwanted barcodes to hide their visuals. See the integration reference Step 9 for details.

---

## Step 3 — Update imports

Drop the BarcodeBatch symbols and add the BarcodeAr equivalents. Only remove the symbols that are actually unused after migration.

**Before:**
```typescript
import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchAdvancedOverlay,
  BarcodeBatchListener,
  BarcodeBatchSettings,
  BarcodeBatchSession,
  TrackedBarcode,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';
import {
  Anchor,
  Camera,
  DataCaptureView,
  FrameSourceState,
  MeasureUnit,
  NumberWithUnit,
  PointWithUnit,
  Quadrilateral,
} from 'scandit-react-native-datacapture-core';
```

**After (highlights only — adjust to the annotation variant if using Advanced Overlay):**
```typescript
import {
  BarcodeAr,
  BarcodeArView,
  BarcodeArSettings,
  BarcodeArViewSettings,
  BarcodeArListener,
  BarcodeArSession,
  BarcodeArHighlightProvider,
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
  Barcode,
  Symbology,
} from 'scandit-react-native-datacapture-barcode';
import {
  Camera,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';
```

For the Advanced Overlay → Custom Annotation path, also add:
```typescript
import {
  BarcodeArAnnotationProvider,
  BarcodeArCustomAnnotation,
  BarcodeArAnnotationTrigger,
} from 'scandit-react-native-datacapture-barcode';
import { Anchor } from 'scandit-react-native-datacapture-core';
```

**Drop entirely** (no equivalent in BarcodeAr):
- `DataCaptureView` — replaced by `BarcodeArView`
- `BarcodeBatchBasicOverlay` / `BarcodeBatchBasicOverlayStyle` — replaced by `BarcodeArHighlightProvider`
- `BarcodeBatchAdvancedOverlay` — replaced by `BarcodeArAnnotationProvider`
- `TrackedBarcode` — providers receive `Barcode` directly; `TrackedBarcode` is still used in `BarcodeArSession` but you do not need to import the type unless you reference it explicitly
- `Anchor`, `PointWithUnit`, `NumberWithUnit`, `MeasureUnit` — only needed if `BarcodeArCustomAnnotation` is used (which takes an `Anchor` from `scandit-react-native-datacapture-core`); otherwise drop them
- `Quadrilateral` — not needed in BarcodeAr at all

---

## Step 4 — Replace the mode + view setup

### Mode construction

**Before:**
```typescript
const settings = new BarcodeBatchSettings();
settings.enableSymbologies([...]);
const barcodeBatch = new BarcodeBatch(settings);
dataCaptureContext.setMode(barcodeBatch);
```

**After:**
```typescript
const settings = new BarcodeArSettings();
settings.enableSymbologies([...]);
const barcodeAr = new BarcodeAr(settings);
dataCaptureContext.addMode(barcodeAr);
```

Key difference: `setMode` is replaced by `addMode`. `setMode` removed all other modes first; `addMode` is additive.

### Camera settings

**Before:**
```typescript
const cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
```

**After:**
```typescript
const cameraSettings = BarcodeAr.createRecommendedCameraSettings();
```

### Ref type

**Before:**
```typescript
const viewRef = useRef<DataCaptureView>(null);
const barcodeBatchRef = useRef<BarcodeBatch>(null!);
```

**After:**
```typescript
const viewRef = useRef<BarcodeArView | null>(null);
const barcodeArRef = useRef<BarcodeAr>(null!);
```

### JSX

**Before:**
```tsx
<DataCaptureView
  style={{ flex: 1 }}
  context={dataCaptureContext}
  ref={view => {
    if (view && !viewRef.current) {
      view.addOverlay(overlay.current);
      viewRef.current = view;
    }
  }}
/>
```

**After:**
```tsx
<BarcodeArView
  style={{ flex: 1 }}
  context={dataCaptureContext}
  barcodeAr={barcodeArRef.current}
  settings={new BarcodeArViewSettings()}
  highlightProvider={highlightProvider}
  ref={(view: BarcodeArView | null) => {
    if (view) {
      view.start();   // REQUIRED — BarcodeArView does not start automatically
      viewRef.current = view;
    }
  }}
>
  {/* children render under the AR overlay */}
</BarcodeArView>
```

> **Important**: `BarcodeArView` does not start automatically on mount. You must call `view.start()` in the `ref` callback. Forgetting this means no barcodes are ever tracked.

No `addOverlay` calls are needed — highlights and annotations are wired as props directly on `<BarcodeArView>`.

---

## Step 5 — Migrate `BarcodeBatchBasicOverlay` → highlights

### Dot style → `BarcodeArCircleHighlight`

**Before:**
```typescript
const overlay = new BarcodeBatchBasicOverlay(barcodeBatch, BarcodeBatchBasicOverlayStyle.Dot);
// then: view.addOverlay(overlay)
```

**After:**
```typescript
const highlightProvider: BarcodeArHighlightProvider = {
  highlightForBarcode: async (barcode: Barcode) => {
    return new BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.Dot);
  },
};

// Pass to BarcodeArView:
// <BarcodeArView highlightProvider={highlightProvider} ... />
```

### Frame style → `BarcodeArRectangleHighlight`

**Before:**
```typescript
const overlay = new BarcodeBatchBasicOverlay(barcodeBatch, BarcodeBatchBasicOverlayStyle.Frame);
```

**After:**
```typescript
import { BarcodeArRectangleHighlight } from 'scandit-react-native-datacapture-barcode';

const highlightProvider: BarcodeArHighlightProvider = {
  highlightForBarcode: async (barcode: Barcode) => {
    return new BarcodeArRectangleHighlight(barcode);
  },
};
```

The provider fires once per barcode when it first enters the tracked set. Return `null` to suppress the highlight for a specific barcode.

---

## Step 6 — Migrate `BarcodeBatchAdvancedOverlay` → annotations

### Custom React component bubbles → `BarcodeArCustomAnnotation`

The Bubbles sample wires a custom `<ARView>` component per barcode using `setViewForTrackedBarcode`. In BarcodeAr, the same component is returned from an annotation provider.

**Before:**
```typescript
const overlay = new BarcodeBatchAdvancedOverlay(barcodeBatch);
overlay.listener = {
  anchorForTrackedBarcode: () => Anchor.TopCenter,
  offsetForTrackedBarcode: () =>
    new PointWithUnit(
      new NumberWithUnit(0, MeasureUnit.Fraction),
      new NumberWithUnit(-1, MeasureUnit.Fraction),
    ),
};

// In session listener:
advancedOverlay.setViewForTrackedBarcode(
  new ARView({ barcodeData, stock }),
  trackedBarcode,
).catch(console.warn);
```

**After:**
```typescript
import {
  BarcodeArAnnotationProvider,
  BarcodeArCustomAnnotation,
  BarcodeArAnnotationTrigger,
} from 'scandit-react-native-datacapture-barcode';
import { Anchor } from 'scandit-react-native-datacapture-core';

const annotationProvider: BarcodeArAnnotationProvider = {
  annotationForBarcode: async (barcode: Barcode) => {
    const barcodeData = barcode.data;
    if (!barcodeData) return null;

    return new BarcodeArCustomAnnotation({
      annotationTrigger: BarcodeArAnnotationTrigger.HighlightTapAndBarcodeScan,
      anchor: Anchor.TopCenter,
      renderAnnotation: () => (
        <ARView barcodeData={barcodeData} stock={{ shelf: 4, backRoom: 8 }} />
      ),
    });
  },
};

// Pass to BarcodeArView:
// <BarcodeArView annotationProvider={annotationProvider} ... />
```

The `anchor` property on `BarcodeArCustomAnnotation` replaces both `anchorForTrackedBarcode` and `offsetForTrackedBarcode` from the advanced overlay listener. Built-in annotation types (`BarcodeArInfoAnnotation`, `BarcodeArPopoverAnnotation`) auto-position — no offset is needed.

> **Note**: `BarcodeArCustomAnnotation` requires SDK 8.1+. For structured text bubbles (title + rows + footer) consider `BarcodeArInfoAnnotation` instead — it handles layout natively and does not require `BarcodeBatchAdvancedOverlayView` subclassing.

### Structured info bubbles → `BarcodeArInfoAnnotation`

If the existing `ARView` just shows text fields (e.g. barcode data, stock count), replace the whole custom component with a `BarcodeArInfoAnnotation`:

```typescript
import {
  BarcodeArAnnotationProvider,
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationHeader,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArInfoAnnotationWidthPreset,
  BarcodeArInfoAnnotationAnchor,
} from 'scandit-react-native-datacapture-barcode';

const annotationProvider: BarcodeArAnnotationProvider = {
  annotationForBarcode: async (barcode: Barcode) => {
    const header = new BarcodeArInfoAnnotationHeader();
    header.text = 'Report Stock Count';

    const shelfRow = new BarcodeArInfoAnnotationBodyComponent();
    shelfRow.text = 'Shelf: 4  Back Room: 8';

    const annotation = new BarcodeArInfoAnnotation(barcode);
    annotation.header = header;
    annotation.body = [shelfRow];
    annotation.width = BarcodeArInfoAnnotationWidthPreset.Medium;
    annotation.anchor = BarcodeArInfoAnnotationAnchor.Top;
    return annotation;
  },
};
```

### Distance-based show/hide → `BarcodeArResponsiveAnnotation`

The Bubbles sample contains a manual `getQuadrilateralWidth` heuristic that hides the annotation when the barcode is too small on screen:

```typescript
// Old pattern — delete this entirely:
const getQuadrilateralWidth = (quadrilateral: Quadrilateral): number => { ... };
const shouldBeShown = getQuadrilateralWidth(viewLocation) > Dimensions.get('window').width * 0.1;
viewRef.current?.viewQuadrilateralForFrameQuadrilateral(trackedBarcode.location).then(location => {
  updateView(trackedBarcode, location);
});
```

Replace it with `BarcodeArResponsiveAnnotation` (SDK 8.2+), which switches between two `BarcodeArInfoAnnotation` variants based on the barcode's relative size on screen:

```typescript
import { BarcodeArResponsiveAnnotation } from 'scandit-react-native-datacapture-barcode';

const annotationProvider: BarcodeArAnnotationProvider = {
  annotationForBarcode: async (barcode: Barcode) => {
    // Close-up: full detail
    const closeUp = new BarcodeArInfoAnnotation(barcode);
    closeUp.body = [/* full content rows */];
    closeUp.width = BarcodeArInfoAnnotationWidthPreset.Large;

    // Far away: minimal placeholder
    const farAway = new BarcodeArInfoAnnotation(barcode);
    farAway.body = [{ text: 'Get closer' }];
    farAway.width = BarcodeArInfoAnnotationWidthPreset.Small;

    const responsive = new BarcodeArResponsiveAnnotation(barcode, closeUp, farAway);
    responsive.threshold = 0.1; // ~10% of screen width, matches old heuristic
    return responsive;
  },
};
```

No `Quadrilateral`, `Dimensions`, `viewQuadrilateralForFrameQuadrilateral`, or `getQuadrilateralWidth` needed.

---

## Step 7 — Migrate the listener

In BarcodeBatch the session listener iterated `session.trackedBarcodes` on every frame to both update app state and drive overlay content. In BarcodeAr these responsibilities are split:

- **Visual content** (highlights, annotations) → handled by the providers (Steps 5 and 6). Do not call `setViewForTrackedBarcode` or create overlay objects in the listener.
- **App state** (e.g. populating a results map) → handled in `BarcodeArListener.didUpdateSession` using `session.addedTrackedBarcodes`.

**Before (Simple sample pattern):**
```typescript
barcodeBatch.addListener({
  didUpdateSession: async (_: BarcodeBatch, session: BarcodeBatchSession) => {
    Object.values(session.trackedBarcodes).forEach(trackedBarcode => {
      const { data, symbology } = trackedBarcode.barcode;
      if (data) {
        setResults(prevResults => ({ ...prevResults, [data]: { data, symbology } }));
      }
    });
  },
});
```

**After:**
```typescript
barcodeAr.addListener({
  didUpdateSession: async (_: BarcodeAr, session: BarcodeArSession) => {
    // Use addedTrackedBarcodes — only newly tracked barcodes, not all of them every frame.
    session.addedTrackedBarcodes.forEach(trackedBarcode => {
      const { data, symbology } = trackedBarcode.barcode;
      if (data) {
        setResults(prevResults => ({ ...prevResults, [data]: { data, symbology } }));
      }
    });
  },
});
```

Key changes:
- `Object.values(session.trackedBarcodes)` → `session.addedTrackedBarcodes` (array, not object)
- `BarcodeBatch` / `BarcodeBatchSession` type annotations → `BarcodeAr` / `BarcodeArSession`
- The listener is registered on `barcodeAr.addListener(...)` (same pattern, different instance)

If the old code also handled `session.removedTrackedBarcodes`, keep that logic — the property exists on `BarcodeArSession` with the same name.

---

## Step 8 — Migrate lifecycle

### Enabling / disabling scanning

**Before:**
```typescript
const startCapture = () => {
  barcodeBatchRef.current.isEnabled = true;
  startCamera();
};
const stopCapture = () => {
  barcodeBatchRef.current.isEnabled = false;
  stopCamera();
};
```

**After:**
```typescript
const startCapture = () => {
  viewRef.current?.start();
  startCamera();
};
const stopCapture = () => {
  viewRef.current?.stop();
  stopCamera();
};
```

`BarcodeAr` has no `isEnabled` property. Use `view.start()` / `view.stop()` / `view.pause()` on the `BarcodeArView` ref instead.

### Camera lifecycle — no change needed

The camera setup using `Camera.withSettings(...)`, `dataCaptureContext.setFrameSource(camera)`, and `camera.switchToDesiredState(FrameSourceState.On/Off)` is unchanged. Keep the `AppState` subscription and the `navigation.isFocused()` guard exactly as they are.

### Initial start

In BarcodeBatch the view was passive — the mode drove scanning. In BarcodeAr the view must be explicitly started. Call `view.start()` in the `ref` callback when the `BarcodeArView` first mounts:

```tsx
ref={(view: BarcodeArView | null) => {
  if (view) {
    view.start();
    viewRef.current = view;
  }
}}
```

---

## Step 9 — Cleanup

**Before:**
```typescript
useEffect(() => {
  return () => {
    dataCaptureContext.removeMode(barcodeBatchRef.current);
  };
}, []);
```

**After:**
```typescript
useEffect(() => {
  return () => {
    dataCaptureContext.removeMode(barcodeArRef.current);
  };
}, []);
```

The `removeMode` call pattern is identical — only the ref changes. Remove all `overlay.current` refs entirely; there are no overlay objects to clean up in BarcodeAr.

---

## Step 10 — Verify

Run through this checklist before considering the migration complete:

- [ ] No `BarcodeBatch`, `BarcodeBatchSettings`, `BarcodeBatchSession`, `BarcodeBatchListener`, `BarcodeBatchBasicOverlay`, `BarcodeBatchBasicOverlayStyle`, `BarcodeBatchAdvancedOverlay`, or `TrackedBarcode` symbols remain in the file (a text search for `BarcodeBatch` or `BarcodeTracking` should return zero matches).
- [ ] Imports from `scandit-react-native-datacapture-barcode` contain only `BarcodeAr*` symbols, `Barcode`, and `Symbology` (plus any annotation/highlight types used).
- [ ] `<DataCaptureView>` is replaced by `<BarcodeArView>` — no `DataCaptureView` in the JSX tree.
- [ ] `view.addOverlay(...)` calls are gone.
- [ ] At least one of `highlightProvider` or `annotationProvider` is passed to `<BarcodeArView>`.
- [ ] `view.start()` is called inside the `BarcodeArView` `ref` callback.
- [ ] `dataCaptureContext.setMode(...)` is replaced by `dataCaptureContext.addMode(...)`.
- [ ] No unused `Anchor`, `PointWithUnit`, `NumberWithUnit`, `MeasureUnit`, or `Quadrilateral` imports remain (they are only needed if `BarcodeArCustomAnnotation` with a non-default anchor is used).
- [ ] No `Dimensions.get('window')` or `viewQuadrilateralForFrameQuadrilateral` calls remain (replaced by `BarcodeArResponsiveAnnotation` if distance-based show/hide was needed).
