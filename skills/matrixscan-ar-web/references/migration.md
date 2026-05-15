# MatrixScan AR Web Migration Guide

## Migrating from BarcodeBatch (MatrixScan Batch) to BarcodeAr (MatrixScan AR)

BarcodeBatch and BarcodeAr are different products. BarcodeBatch provides raw tracking sessions with custom HTML element overlays; BarcodeAr is a higher-level AR mode with built-in highlight and annotation types that are composited by the SDK. Migrating means replacing the entire integration.

### Key API differences

| Concept | BarcodeBatch | BarcodeAr |
|---------|-------------|-----------|
| Mode creation | `await BarcodeBatch.forContext(context, settings)` | `await BarcodeAr.forContext(context, settings)` |
| Settings class | `BarcodeBatchSettings` | `BarcodeArSettings` |
| View type | `DataCaptureView` + overlay | `BarcodeArView.create(element, context, barcodeAr)` |
| Camera setup | Manual (`Camera`, `setFrameSource`, `switchToDesiredState`) | Managed by `BarcodeArView` — no manual camera setup |
| Highlight API | `BarcodeBatchBasicOverlay` with `Brush` | `BarcodeArCircleHighlight`, `BarcodeArRectangleHighlight` |
| Custom AR views | `TrackedBarcodeView.withHTMLElement(el)` | `BarcodeArView` with `highlightProvider` / `annotationProvider` |
| Provider pattern | Listener callbacks (`viewForTrackedBarcode` returns Promise) | Provider callback pattern (`highlightForBarcode(barcode, callback)`) |
| Lifecycle start | `barcodeBatch.setEnabled(true)` + `switchToDesiredState(FrameSourceState.On)` | `barcodeArView.start()` |
| Lifecycle stop | `barcodeBatch.setEnabled(false)` + `switchToDesiredState(FrameSourceState.Off)` | `barcodeArView.stop()` |
| Cleanup | `barcodeBatch.setEnabled(false)` | `barcodeArView.stop()` → `barcodeArView.remove()` → `context.dispose()` |

### Step-by-step migration

**Before (BarcodeBatch):**

```typescript
import {
  BarcodeBatch,
  BarcodeBatchSettings,
  BarcodeBatchAdvancedOverlay,
  TrackedBarcodeView,
  barcodeCaptureLoader,
  Symbology,
} from "@scandit/web-datacapture-barcode";
import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
} from "@scandit/web-datacapture-core";

const context = await DataCaptureContext.forLicenseKey(licenseKey, {
  libraryLocation: new URL("library/engine/", document.baseURI).toString(),
  moduleLoaders: [barcodeCaptureLoader()],
});

const view = new DataCaptureView();
view.connectToElement(document.getElementById("data-capture-view")!);
await view.setContext(context);

const settings = new BarcodeBatchSettings();
settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);

const barcodeBatch = await BarcodeBatch.forContext(context, settings);

const camera = Camera.pickBestGuess();
await camera.applySettings(BarcodeBatch.recommendedCameraSettings);
await context.setFrameSource(camera);

const advancedOverlay = await BarcodeBatchAdvancedOverlay.withBarcodeBatchForView(barcodeBatch, view);
advancedOverlay.listener = {
  viewForTrackedBarcode: (_overlay, trackedBarcode) => {
    const el = document.createElement("div");
    el.textContent = trackedBarcode.barcode.data ?? "";
    return TrackedBarcodeView.withHTMLElement(el, { scale: 1 / window.devicePixelRatio });
  },
};

await context.frameSource?.switchToDesiredState(FrameSourceState.On);
await barcodeBatch.setEnabled(true);
```

**After (BarcodeAr):**

```typescript
import {
  BarcodeAr,
  BarcodeArSettings,
  BarcodeArView,
  BarcodeArCircleHighlight,
  BarcodeArCircleHighlightPreset,
  BarcodeArInfoAnnotation,
  BarcodeArInfoAnnotationBodyComponent,
  BarcodeArAnnotationTrigger,
  barcodeCaptureLoader,
  Symbology,
} from "@scandit/web-datacapture-barcode";
import { DataCaptureContext } from "@scandit/web-datacapture-core";

await DataCaptureContext.forLicenseKey(licenseKey, {
  libraryLocation: new URL("library/engine/", document.baseURI).toString(),
  moduleLoaders: [barcodeCaptureLoader()],
});

// No DataCaptureView, no Camera — BarcodeArView handles both
const settings = new BarcodeArSettings();
settings.enableSymbologies([Symbology.EAN13UPCA, Symbology.Code128]);

const barcodeAr = await BarcodeAr.forContext(DataCaptureContext.sharedInstance, settings);

const container = document.getElementById("barcode-ar-view")!;
const barcodeArView = await BarcodeArView.create(container, DataCaptureContext.sharedInstance, barcodeAr);

// Providers use callback pattern (not return value)
barcodeArView.highlightProvider = {
  async highlightForBarcode(barcode, callback) {
    const highlight = BarcodeArCircleHighlight.create(barcode, BarcodeArCircleHighlightPreset.Dot);
    callback(highlight);
  },
};

barcodeArView.annotationProvider = {
  async annotationForBarcode(barcode, callback) {
    const body = BarcodeArInfoAnnotationBodyComponent.create(); // static factory, not `new`
    body.text = barcode.data ?? "";
    const annotation = BarcodeArInfoAnnotation.create(barcode);
    annotation.body = [body];
    annotation.annotationTrigger = BarcodeArAnnotationTrigger.HighlightTapAndBarcodeScan;
    callback(annotation);
  },
};

await barcodeArView.start();
```

### What to remove

| Remove (BarcodeBatch) | Replaced by |
|-----------------------|-------------|
| `BarcodeBatch`, `BarcodeBatchSettings` imports | `BarcodeAr`, `BarcodeArSettings` |
| `BarcodeBatchBasicOverlay`, `BarcodeBatchAdvancedOverlay` imports | `BarcodeArCircleHighlight`, `BarcodeArInfoAnnotation`, etc. |
| `TrackedBarcodeView` import | (no equivalent — providers deliver SDK-managed views) |
| `DataCaptureView`, `Camera`, `FrameSourceState` imports | (not needed for BarcodeAr) |
| Manual camera setup (`Camera.pickBestGuess()`, `setFrameSource`, `switchToDesiredState`) | Managed by `BarcodeArView` |
| `BarcodeBatch.forContext()` call | `BarcodeAr.forContext()` |
| `BarcodeBatchAdvancedOverlay.withBarcodeBatchForView()` | `BarcodeArView.create()` |
| `barcodeBatch.setEnabled(true/false)` | `barcodeArView.start()` / `barcodeArView.stop()` |
| `overlay.listener` with `viewForTrackedBarcode` | `barcodeArView.highlightProvider` / `barcodeArView.annotationProvider` |

### Choosing between BarcodeBatch and BarcodeAr

If the user is unsure which to use:

- **BarcodeAr** — Use when you want built-in AR highlights and info annotations. The SDK composites the overlays for you and handles all hit-testing and lifecycle. Best for product information display, inventory lookup, warehouse picking.
- **BarcodeBatch** — Use when you need full control over the AR overlay as arbitrary HTML elements (e.g. custom rendered charts, live data feeds, complex interactive widgets). Also needed when you only want raw tracking session data without any visual overlay.
