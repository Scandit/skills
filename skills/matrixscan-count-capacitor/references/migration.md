# MatrixScan Count Capacitor Migration Guide

This guide covers three migration scenarios for `BarcodeCount` on Capacitor:

1. **Constructor migration** — upgrading from the pre-7.6 `BarcodeCount.forDataCaptureContext(context, settings)` factory to the ≥7.6 `new BarcodeCount(settings)` constructor.
2. **Not-in-list actions** — adopting `BarcodeCountNotInListActionSettings` (≥7.1).
3. **Status mode** — adopting `BarcodeCountStatusProvider` and related classes (≥8.3).
4. **Mapping flow** — adopting `BarcodeCountMappingFlowSettings` and `BarcodeCountView.forMapping` (≥8.3).

---

## Migration 1 — BarcodeCount Constructor (pre-7.6 → ≥7.6)

### What changed

Before SDK 7.6, the only way to create a `BarcodeCount` instance on Capacitor was via a static factory that also added the mode to the context:

```javascript
// Pre-7.6 (still works but prefer the new form)
const barcodeCount = BarcodeCount.forDataCaptureContext(context, settings);
// No need to call context.addMode — it was automatic
```

From SDK 7.6 onwards, a context-less constructor is available. The mode is **not** automatically added to the context:

```javascript
// ≥7.6
const barcodeCount = new BarcodeCount(settings);
context.addMode(barcodeCount); // explicit — required
```

### Migration steps

**Step 1** — Replace the static factory call with the constructor:

```javascript
// Before
const barcodeCount = BarcodeCount.forDataCaptureContext(context, settings);

// After
const barcodeCount = new BarcodeCount(settings);
context.addMode(barcodeCount);
```

**Step 2** — Verify `context.addMode(barcodeCount)` is present. This call is critical — without it the mode is never wired to the context and scanning will not work.

**Step 3** — Check that the import of `BarcodeCount` still comes from `scandit-capacitor-datacapture-barcode`. No import changes needed for this migration.

**Step 4** — If the codebase uses `BarcodeCountView.forContextWithMode(context, barcodeCount)` or `BarcodeCountView.forContextWithModeAndStyle(...)`, those still work. You can also switch to the object-literal constructor `new BarcodeCountView({ context, barcodeCount, style })` which is used in the official sample.

### Checklist

- [ ] `BarcodeCount.forDataCaptureContext(` is replaced with `new BarcodeCount(settings)`.
- [ ] `context.addMode(barcodeCount)` is present immediately after construction.
- [ ] The mode is not passed the context as a constructor argument.

---

## Migration 2 — Not-In-List Actions (adopt ≥7.1)

`BarcodeCountNotInListActionSettings` (available Cap ≥7.1) enables a popup action sheet when users tap a barcode that is not part of the current `BarcodeCountCaptureList`. This replaces manual handling of `didTapRecognizedBarcodeNotInList`.

### Before (manual handling)

```javascript
view.listener = {
  didTapRecognizedBarcodeNotInList: (view, trackedBarcode) => {
    // Show a custom popup or dialog
    showCustomDialog(trackedBarcode.barcode.data, (accepted) => {
      if (accepted) {
        // mark as accepted
      } else {
        // mark as rejected
      }
    });
  },
};
```

### After (built-in action settings)

```javascript
// Configure the built-in action popup
const notInListSettings = view.barcodeNotInListActionSettings;
notInListSettings.enabled = true;
notInListSettings.acceptButtonText = 'Accept';
notInListSettings.rejectButtonText = 'Reject';
notInListSettings.cancelButtonText = 'Cancel';
notInListSettings.barcodeAcceptedHint = 'Item accepted';
notInListSettings.barcodeRejectedHint = 'Item rejected';
view.barcodeNotInListActionSettings = notInListSettings;

// Receive the outcomes via listener (Cap ≥7.1)
view.listener = {
  didTapAcceptedBarcode: (view, trackedBarcode) => {
    console.log('Accepted:', trackedBarcode.barcode.data);
  },
  didTapRejectedBarcode: (view, trackedBarcode) => {
    console.log('Rejected:', trackedBarcode.barcode.data);
  },
};
```

The SDK now handles showing the action popup and fires `didTapAcceptedBarcode` / `didTapRejectedBarcode` on the view listener instead of `didTapRecognizedBarcodeNotInList`.

Custom brush support for accepted/rejected barcodes (Dot style, Cap ≥7.1):
```javascript
view.acceptedBrush = new Brush(Color.fromHex('#00CC0066'), Color.fromHex('#00CC00'), 2.0);
view.rejectedBrush = new Brush(Color.fromHex('#FF000066'), Color.fromHex('#FF0000'), 2.0);
```

### Checklist

- [ ] `BarcodeCountNotInListActionSettings` is accessed via `view.barcodeNotInListActionSettings`.
- [ ] `notInListSettings.enabled = true` is set.
- [ ] `view.barcodeNotInListActionSettings = notInListSettings` is reassigned after changes.
- [ ] `didTapAcceptedBarcode` / `didTapRejectedBarcode` replace manual popup handling.

---

## Migration 3 — Status Mode (adopt ≥8.3, Beta)

Status mode allows showing contextual status icons (expired, low stock, wrong item, etc.) on top of scanned barcodes. It is available from Capacitor 8.3 and is marked **beta** — the API may change in future versions.

### Before (no status support)

The view showed no per-barcode status information. Custom overlays required BarcodeCountViewListener brush callbacks or navigation to a separate results screen.

### After (status provider)

```javascript
import {
  BarcodeCountStatus,
  BarcodeCountStatusItem,
  BarcodeCountStatusResultSuccess,
  BarcodeCountStatusResultError,
  BarcodeCountStatusResultAbort,
} from 'scandit-capacitor-datacapture-barcode';

// Recommended: auto-show status icons on scan (no button needed)
view.shouldShowStatusIconsOnScan = true;

// Alternative: show a status-mode toggle button
// view.shouldShowStatusModeButton = true;

// Set the provider
view.setStatusProvider({
  onStatusRequested: async (barcodes, callback) => {
    try {
      const statusItems = await Promise.all(
        barcodes.map(async (trackedBarcode) => {
          const status = await fetchStatusFromBackend(trackedBarcode.barcode.data);
          return BarcodeCountStatusItem.create(trackedBarcode, status);
        }),
      );
      const result = BarcodeCountStatusResultSuccess.create(
        statusItems,
        'Stock status loaded',
        'Status mode off',
      );
      await callback.onStatusReady(result);
    } catch (err) {
      // Provide a partial result with an error message
      const result = BarcodeCountStatusResultAbort.create('Failed to load status');
      await callback.onStatusReady(result);
    }
  },
});

async function fetchStatusFromBackend(barcodeData) {
  // Replace with real backend call
  return BarcodeCountStatus.None;
}
```

### Key points

- `shouldShowStatusIconsOnScan = true` is the **recommended approach** — shows status icons immediately after scanning, without requiring the user to activate status mode manually. When set, `shouldShowStatusModeButton` has no effect.
- `shouldShowStatusModeButton = true` shows a toggle button; the user must tap it to enter status mode. Requires a provider to be set, otherwise the tap has no effect.
- `BarcodeCountStatusItem.create(trackedBarcode, status)` pairs a `TrackedBarcode` with a `BarcodeCountStatus` value.
- The `onStatusRequested` callback **must** call `callback.onStatusReady(result)` — not doing so leaves the view in a loading state.
- `BarcodeCountStatusResultAbort` aborts status mode immediately and shows the error message to the user.

### Checklist

- [ ] `view.setStatusProvider({...})` is called with an object implementing `onStatusRequested`.
- [ ] `onStatusRequested` calls `callback.onStatusReady(result)` in all code paths.
- [ ] `shouldShowStatusIconsOnScan = true` or `shouldShowStatusModeButton = true` is set.
- [ ] Status is not used on SDK <8.3 — guard with a version check if targeting both.

---

## Migration 4 — Mapping Flow (adopt ≥8.3, Beta)

The mapping flow provides a grid-based spatial map of scanned barcodes. It requires a dedicated `BarcodeCountView` factory and is available from Capacitor 8.3.

### Before (no mapping)

```javascript
const view = new BarcodeCountView({
  context,
  barcodeCount,
  style: BarcodeCountViewStyle.Icon,
});
```

### After (mapping view)

```javascript
import { BarcodeCountMappingFlowSettings } from 'scandit-capacitor-datacapture-barcode';

// Enable mapping in settings
settings.mappingEnabled = true;
const barcodeCount = new BarcodeCount(settings);
context.addMode(barcodeCount);

// Configure mapping flow UI text
const mappingSettings = new BarcodeCountMappingFlowSettings();
mappingSettings.scanBarcodesGuidanceText = 'Tap shutter to scan all codes';
mappingSettings.nextButtonText = 'Next';
mappingSettings.finishButtonText = 'Finish';
mappingSettings.redoScanButtonText = 'Redo map';
mappingSettings.stepBackGuidanceText = 'Step back to fit all codes';

// Use the forMapping factory
const view = BarcodeCountView.forMapping(
  context,
  barcodeCount,
  BarcodeCountViewStyle.Icon,
  mappingSettings,
);

view.connectToElement(document.getElementById('data-capture-view'));
```

> **Note**: The grid mapping flow only supports grids of 4 rows by 2 columns. The mapping API is beta and may change in future versions.

### Key points

- `settings.mappingEnabled = true` must be set before creating `BarcodeCount`.
- Use `BarcodeCountView.forMapping(context, barcodeCount, style, mappingFlowSettings)` instead of the standard constructors.
- `BarcodeCountMappingFlowSettings` is available from Cap 8.3.
- `BarcodeCountSession.getSpatialMap()` / `getSpatialMapWithHints(rows, columns)` retrieves the spatial map from the listener (Cap ≥6.21 for the basic version).

### Checklist

- [ ] `settings.mappingEnabled = true` is set before `new BarcodeCount(settings)`.
- [ ] `BarcodeCountView.forMapping(...)` is used (not `forContextWithMode` or `new BarcodeCountView({...})`).
- [ ] `BarcodeCountMappingFlowSettings` is instantiated and configured.
- [ ] Mapping is not used on SDK <8.3 — guard with a version check if targeting both.
