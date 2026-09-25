# MatrixScan Count Cordova Migration Guide

Migrate an existing `BarcodeCount` Cordova integration to the current best-practice API. The primary migration paths are:

1. **Pre-7.6 constructor → ≥7.6 constructor** (most common)
2. **Adopting Not-in-list action settings** (≥7.1)
3. **Adopting Status mode** (≥8.3)
4. **Adopting Mapping flow** (≥8.3)

In Cordova all SDK symbols live on the global `Scandit.*` namespace.

---

## Migration 1 — Constructor pattern: pre-7.6 → ≥7.6

### What changed

Prior to plugin 7.6, `BarcodeCount` was constructed with `BarcodeCount.forDataCaptureContext(context, settings)`, which automatically added the mode to the context. Starting in 7.6, the recommended pattern is `new BarcodeCount(settings)` followed by an explicit `context.addMode(barcodeCount)`.

### Before (pre-7.6)

```javascript
const settings = new Scandit.BarcodeCountSettings();
settings.enableSymbologies([Scandit.Symbology.EAN13UPCA, Scandit.Symbology.Code128]);

// Old factory — takes context as first argument, auto-adds mode to context
const barcodeCount = Scandit.BarcodeCount.forDataCaptureContext(context, settings);
barcodeCount.isEnabled = true;
```

### After (≥7.6)

```javascript
const settings = new Scandit.BarcodeCountSettings();
settings.enableSymbologies([Scandit.Symbology.EAN13UPCA, Scandit.Symbology.Code128]);

// New constructor — does NOT auto-add mode to context
const barcodeCount = new Scandit.BarcodeCount(settings);
context.addMode(barcodeCount);  // must be called explicitly
barcodeCount.isEnabled = true;
```

### Teardown change

Because `addMode` is now explicit, `removeMode` must be called on teardown:

```javascript
// Before (pre-7.6): no removeMode needed
barcodeCount.isEnabled = false;

// After (≥7.6):
barcodeCount.isEnabled = false;
context.removeMode(barcodeCount);
```

### `createRecommendedCameraSettings` (≥7.6)

The static method `BarcodeCount.createRecommendedCameraSettings()` was introduced in Cordova 7.6. If upgrading from <7.6 where this method was absent, replace any manual camera-settings construction with:

```javascript
const cameraSettings = Scandit.BarcodeCount.createRecommendedCameraSettings();
```

### Verification checklist

- [ ] `BarcodeCount.forDataCaptureContext(` is NOT present.
- [ ] `new Scandit.BarcodeCount(settings)` is present.
- [ ] `context.addMode(barcodeCount)` is called after construction.
- [ ] `context.removeMode(barcodeCount)` is called during teardown.
- [ ] `Scandit.BarcodeCount.createRecommendedCameraSettings()` is used (if ≥7.6).

---

## Migration 2 — Adopting Not-in-list action settings (≥7.1)

When a `BarcodeCountCaptureList` is active, barcodes not in the list used to have no built-in action UI. From Cordova 7.1, you can show an accept/reject popup for unrecognized barcodes.

### Before (pre-7.1)

```javascript
// No per-barcode accept/reject UI for not-in-list barcodes.
// Developers had to implement custom logic in didTapRecognizedBarcodeNotInList.
view.listener = {
  didTapRecognizedBarcodeNotInList: (view, trackedBarcode) => {
    // Custom dialog or UI
    showCustomAcceptRejectDialog(trackedBarcode.barcode.data);
  },
};
```

### After (≥7.1)

```javascript
const notInListSettings = view.barcodeNotInListActionSettings;
notInListSettings.enabled = true;
notInListSettings.acceptButtonText = 'Accept';
notInListSettings.rejectButtonText = 'Reject';
notInListSettings.cancelButtonText = 'Cancel';
notInListSettings.barcodeAcceptedHint = 'Barcode accepted';
notInListSettings.barcodeRejectedHint = 'Barcode rejected';
view.barcodeNotInListActionSettings = notInListSettings;

// Handle results via listener — the SDK now fires accepted/rejected callbacks:
view.listener = {
  ...view.listener,
  didTapAcceptedBarcode: (view, trackedBarcode) => {
    console.log('Accepted:', trackedBarcode.barcode.data);
  },
  didTapRejectedBarcode: (view, trackedBarcode) => {
    console.log('Rejected:', trackedBarcode.barcode.data);
  },
};
```

Remove any custom accept/reject dialog logic that was previously driven by `didTapRecognizedBarcodeNotInList`.

### Verification checklist

- [ ] `view.barcodeNotInListActionSettings` is read, modified, and assigned back.
- [ ] `notInListSettings.enabled = true` is present.
- [ ] `didTapAcceptedBarcode` and `didTapRejectedBarcode` callbacks are implemented if reactions are needed.

---

## Migration 3 — Adopting Status mode (≥8.3)

Status mode allows each barcode to display a status indicator (e.g. in-stock / out-of-stock). It is beta in 8.3.

### Before (pre-8.3)

No status mode available. Custom per-barcode state was communicated via brushes or custom overlays.

### After (≥8.3)

```javascript
// 1. Show the status mode toggle button:
view.shouldShowStatusModeButton = true;

// 2. Register a status provider:
view.setStatusProvider({
  statusForBarcodes: async (barcodes) => {
    // barcodes: TrackedBarcode[]
    // Return an array of BarcodeCountStatusItem for each barcode you want to annotate.
    // Return an empty array for no annotations.
    // BarcodeCountStatusItem.create(barcode, status) — two parameters only (verified from RST and TS source).
    return barcodes.map(tb => {
      const isInStock = checkStockStatus(tb.barcode.data);
      return Scandit.BarcodeCountStatusItem.create(
        tb,
        isInStock ? Scandit.BarcodeCountStatus.Success : Scandit.BarcodeCountStatus.Error
      );
    });
  },
});
```

Alternatively, set `shouldShowStatusIconsOnScan = true` to show status icons automatically on scan without requiring the user to tap the status mode button:

```javascript
view.shouldShowStatusIconsOnScan = true;
// When true, shouldShowStatusModeButton has no effect.
```

> **Note**: Status mode is beta. The `BarcodeCountStatusItem` and `BarcodeCountStatus` API may change in future releases. Mark all status-related code with a comment noting the beta status.

### Verification checklist

- [ ] `view.shouldShowStatusModeButton = true` is present (or `view.shouldShowStatusIconsOnScan = true`).
- [ ] `view.setStatusProvider(provider)` is called.
- [ ] `statusForBarcodes` callback is `async` or returns a `Promise`.

---

## Migration 4 — Adopting Mapping flow (≥8.3)

The Mapping flow provides a grid-based UI for spatially mapping scanned barcodes. It requires constructing the view with `BarcodeCountView.forMapping`.

### Before (pre-8.3)

```javascript
const view = Scandit.BarcodeCountView.forContextWithModeAndStyle(
  context,
  barcodeCount,
  Scandit.BarcodeCountViewStyle.Icon
);
```

### After (≥8.3)

```javascript
// Create mapping flow settings — no-arg constructor (verified: RST and TS source).
// Optional: customize button/guidance text before passing to forMapping.
const mappingFlowSettings = new Scandit.BarcodeCountMappingFlowSettings();
// mappingFlowSettings.scanBarcodesGuidanceText = 'Tap shutter to scan all codes in batches';
// mappingFlowSettings.nextButtonText = 'Next';
// mappingFlowSettings.stepBackGuidanceText = 'Step back to fit all codes into camera view';
// mappingFlowSettings.redoScanButtonText = 'Redo map';
// mappingFlowSettings.restartButtonText = 'Restart';   // ≥Cordova 8.3
// mappingFlowSettings.finishButtonText = 'Finish';

const view = Scandit.BarcodeCountView.forMapping(
  context,
  barcodeCount,
  Scandit.BarcodeCountViewStyle.Icon,
  mappingFlowSettings
);
```

Also enable mapping in `BarcodeCountSettings`:

```javascript
settings.mappingEnabled = true;
```

> **Note**: The grid mapping flow only supports grids of 4 rows by 2 columns. Mapping API is beta.

### Verification checklist

- [ ] `settings.mappingEnabled = true` is present.
- [ ] `BarcodeCountView.forMapping(...)` is used instead of `forContextWithModeAndStyle`.
- [ ] `BarcodeCountMappingFlowSettings` is constructed and passed.

---

## Common DataCaptureContext factory rename

If the project uses the older factory:

**Before:**
```javascript
const context = Scandit.DataCaptureContext.forLicenseKey('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
```

**After (v8):**
```javascript
const context = Scandit.DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
```

---

## connectToElement signature note

`BarcodeCountView.connectToElement(element)` returns `void` on Cordova (verified against plugin source). It is synchronous — do **not** `await` it. This differs from BarcodeAr's `connectToElement` which returns `Promise<void>`.

```javascript
// Correct:
view.connectToElement(containerEl);

// Incorrect — do not await:
// await view.connectToElement(containerEl);
```

Similarly, `detachFromElement()` returns `void` — no await needed.
