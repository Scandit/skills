# MatrixScan Count React Native Migration Guide

This guide covers two migration scenarios:

1. **Constructor migration** — Moving from the old `BarcodeCount.forDataCaptureContext(context, settings)` factory (pre-7.6) to the new `new BarcodeCount(settings)` constructor + `context.addMode(barcodeCount)` pattern (7.6+).
2. **Adopting newer APIs** — Adding Status Provider (8.3+), Mapping Flow (requires `mappingEnabled`), and Not-in-List Action Settings (7.1+) to an existing integration.

---

## Part 1 — Constructor Migration (pre-7.6 → 7.6+)

### Step 1 — Detect the old factory pattern

Search the target file for:

```
BarcodeCount.forDataCaptureContext(
```

If this is present, the file uses the pre-7.6 factory. Proceed with the steps below.

If you find `new BarcodeCount(settings)` already, the file is on the new constructor. Skip to Part 2 if the user wants to adopt newer APIs.

---

### Step 2 — Replace the factory with the constructor

**Before (pre-7.6 factory):**
```typescript
// Context is passed in, mode is auto-added to context
const barcodeCount = BarcodeCount.forDataCaptureContext(dataCaptureContext, settings);
```

**After (7.6+ constructor):**
```typescript
// Context is NOT passed in — add mode explicitly
const barcodeCount = new BarcodeCount(settings);
dataCaptureContext.addMode(barcodeCount);
```

Key differences:
- The old factory accepted the context as its first argument and automatically added the mode to the context. The new constructor takes only settings.
- With the new constructor you must call `dataCaptureContext.addMode(barcodeCount)` explicitly before any capture starts.
- If the old code relied on the factory's auto-add behavior, the explicit `addMode` call is the replacement.

---

### Step 3 — Update camera setup if needed

**Before (pre-7.6 — `BarcodeCount.createRecommendedCameraSettings()` not yet available):**
```typescript
const camera = Camera.default;
if (!camera) throw new Error('No default camera');
dataCaptureContext.setFrameSource(camera);
```

**After (7.6+ — recommended camera settings available):**
```typescript
const camera = Camera.withSettings(BarcodeCount.createRecommendedCameraSettings());
if (!camera) throw new Error('Camera unavailable');
dataCaptureContext.setFrameSource(camera);
```

`BarcodeCount.createRecommendedCameraSettings()` returns camera settings optimized for counting workloads — use this whenever your plugin is 7.6+.

---

### Step 4 — Update the listener callback (if using session.recognizedBarcodes)

**Before (pre-7.0 — session used a dictionary-style API):**
```typescript
barcodeCount.addListener({
  didScan: async (_: BarcodeCount, session: BarcodeCountSession) => {
    // Old pattern: iterate Object.values if the session exposed a map
    // (exact shape varied by version)
  },
});
```

**After (7.0+ — `session.recognizedBarcodes` is a `Barcode[]` array):**
```typescript
barcodeCount.addListener({
  didScan: async (_: BarcodeCount, session: BarcodeCountSession) => {
    const allBarcodes = session.recognizedBarcodes;  // Barcode[]
    allBarcodes.forEach(barcode => {
      console.log(barcode.data, barcode.symbology);
    });
  },
});
```

---

### Step 5 — Verify

Run through this checklist:

- [ ] `BarcodeCount.forDataCaptureContext(` is no longer present anywhere in the file.
- [ ] `new BarcodeCount(settings)` is present.
- [ ] `dataCaptureContext.addMode(barcodeCount)` is present (called after constructing the mode).
- [ ] If the project is 7.6+, `BarcodeCount.createRecommendedCameraSettings()` is used for camera setup.
- [ ] `session.recognizedBarcodes` is used as an array (not a dictionary/object).
- [ ] No `dataCaptureContext.setMode(` calls remain (use `addMode`).

---

## Part 2 — Adopt Status Provider (RN 8.3+)

`BarcodeCountStatusProvider` allows you to attach per-barcode status icons (expired, low stock, quality check, etc.) to the counting view after a scan.

### Step 1 — Add imports

```typescript
import {
  BarcodeCountStatusProvider,
  BarcodeCountStatusProviderCallback,
  BarcodeCountStatusItem,
  BarcodeCountStatusResultSuccess,
  BarcodeCountStatus,
} from 'scandit-react-native-datacapture-barcode';
import { TrackedBarcode } from 'scandit-react-native-datacapture-barcode';
```

### Step 2 — Implement the provider

```typescript
const statusProvider: BarcodeCountStatusProvider = {
  onStatusRequested: (
    barcodes: TrackedBarcode[],
    callback: BarcodeCountStatusProviderCallback,
  ) => {
    // Build status items from your backend or local data
    const statusItems = barcodes.map(tb => {
      const status = lookupStatus(tb.barcode.data);  // your logic
      return BarcodeCountStatusItem.create(tb, status);
    });

    // Deliver result via callback — NOT awaited
    callback.onStatusReady(
      BarcodeCountStatusResultSuccess.create(
        statusItems,
        'Status mode on',
        'Status mode off',
      ),
    );
  },
};
```

> **Critical**: `onStatusRequested` is callback-based — do NOT `await callback.onStatusReady(...)`. Call it directly.

### Step 3 — Wire the provider to the view

```typescript
ref={view => {
  if (view) {
    view.setStatusProvider(statusProvider);

    // Option A: show a button that lets the user toggle status mode
    view.shouldShowStatusModeButton = true;

    // Option B: auto-show status icons after every scan (recommended)
    view.shouldShowStatusIconsOnScan = true;

    view.listener = viewListenerRef.current;
    view.uiListener = viewUiListenerRef.current;
  }
}}
```

---

## Part 3 — Adopt Mapping Flow (BarcodeCountSettings.mappingEnabled)

Barcode mapping overlays a spatial grid showing which barcodes were scanned where. Enable it in settings and call `session.getSpatialMap()` after scanning.

```typescript
// Enable mapping in settings:
const settings = new BarcodeCountSettings();
settings.mappingEnabled = true;
// ... enable symbologies ...

const barcodeCount = new BarcodeCount(settings);
barcodeCount.addListener({
  didScan: async (_: BarcodeCount, session: BarcodeCountSession) => {
    const spatialMap = await session.getSpatialMap();
    if (spatialMap) {
      // spatialMap.barcodes contains barcodes organized in a grid
      console.log('Spatial grid:', spatialMap);
    }
  },
});
```

> **Note**: The Barcode Count mapping API is still in beta and may change in future versions.

---

## Part 4 — Adopt Not-in-List Action Settings (RN 7.1+)

When scanning against a list, tapping a "not in list" barcode can show an action popup.

```typescript
// In the BarcodeCountView ref callback:
ref={view => {
  if (view) {
    const notInListSettings = view.barcodeNotInListActionSettings;
    notInListSettings.enabled = true;
    notInListSettings.acceptButtonText = 'Accept';
    notInListSettings.rejectButtonText = 'Reject';
    notInListSettings.cancelButtonText = 'Cancel';
    notInListSettings.barcodeAcceptedHint = 'Item added';
    notInListSettings.barcodeRejectedHint = 'Item rejected';
    // (iOS accessibility):
    notInListSettings.acceptButtonAccessibilityLabel = 'Accept this item';
    notInListSettings.rejectButtonAccessibilityLabel = 'Reject this item';

    view.listener = viewListenerRef.current;
    view.uiListener = viewUiListenerRef.current;
  }
}}
```

Also handle the tap callbacks in the view listener:

```typescript
const viewListener: BarcodeCountViewListener = {
  // ...
  didTapAcceptedBarcode: (view, trackedBarcode) => {
    console.log('Accepted:', trackedBarcode.barcode.data);
  },
  didTapRejectedBarcode: (view, trackedBarcode) => {
    console.log('Rejected:', trackedBarcode.barcode.data);
  },
};
```

And use the accepted/rejected brushes (Dot style) to visually distinguish these states:

```typescript
ref={view => {
  if (view) {
    view.acceptedBrush = new Brush(Color.fromHex('#2196F3'), Color.fromHex('#2196F3'), 1);
    view.rejectedBrush = new Brush(Color.fromHex('#FF9800'), Color.fromHex('#FF9800'), 1);
    // ...
  }
}}
```

---

## Final Verification Checklist

After completing any of the above migrations:

- [ ] No `BarcodeCount.forDataCaptureContext(` remains (if migrating constructor).
- [ ] `new BarcodeCount(settings)` is present and `dataCaptureContext.addMode(barcodeCount)` is called.
- [ ] `BarcodeCount.createRecommendedCameraSettings()` is used if the plugin is 7.6+.
- [ ] `session.recognizedBarcodes` is accessed as an array.
- [ ] If Status Provider is used: `view.setStatusProvider(...)` is called in the `ref` callback, and `onStatusRequested` calls `callback.onStatusReady(result)` directly (not awaited).
- [ ] If Not-in-List Actions are used: `view.barcodeNotInListActionSettings.enabled = true` is set and accepted/rejected brush and listener callbacks are wired.
- [ ] No unused imports remain.
- [ ] Pod install has been run after upgrading the Scandit package version.
