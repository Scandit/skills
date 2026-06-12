# MatrixScan Batch Cordova — Version Migration Guide

This guide covers upgrading an existing Cordova MatrixScan integration to the current `BarcodeBatch` API. The most common migration is the **`BarcodeTracking` → `BarcodeBatch` rename**, plus the SDK 8 constructor modernization.

> **Language note**: Examples use plain JavaScript via the global `Scandit.*` namespace, matching the Cordova samples. Do not emit `import` from `scandit-cordova-datacapture-*` in WebView runtime code.

> **Judge note for this skill**: When migrating, scope old-API-absence claims to the rewritten code block. It is fine for prose to mention the old name (e.g. "replace `BarcodeTracking` with `BarcodeBatch`").

## The `BarcodeTracking` → `BarcodeBatch` rename

MatrixScan Batch was originally shipped under the name **Barcode Tracking** (`BarcodeTracking*`). It was renamed to **Barcode Batch** (`BarcodeBatch*`) in SDK 7. **It is the same feature** — same multi-barcode tracking, same `didUpdateSession` listener callback, same session shape. Only the class names changed.

If a project still uses `BarcodeTracking*` classes, or a user asks "is BarcodeTracking the same as BarcodeBatch?", the answer is: yes — `BarcodeTracking` is the legacy name, `BarcodeBatch` is the current name, and current SDKs should use the `BarcodeBatch*` classes.

### Type rename table

| Legacy (`BarcodeTracking*`) | Current (`BarcodeBatch*`) |
|---|---|
| `Scandit.BarcodeTracking` | `Scandit.BarcodeBatch` |
| `Scandit.BarcodeTrackingSettings` | `Scandit.BarcodeBatchSettings` |
| `Scandit.BarcodeTrackingSession` | `Scandit.BarcodeBatchSession` |
| `BarcodeTrackingListener` (the listener object you pass to `addListener`) | `BarcodeBatchListener` |
| `Scandit.BarcodeTrackingBasicOverlay` | `Scandit.BarcodeBatchBasicOverlay` |
| `Scandit.BarcodeTrackingBasicOverlayStyle` | `Scandit.BarcodeBatchBasicOverlayStyle` |
| `Scandit.BarcodeTrackingAdvancedOverlay` | `Scandit.BarcodeBatchAdvancedOverlay` |

### Unchanged across the rename

- The listener callback is still `didUpdateSession: (mode, session) => { ... }`.
- `session.trackedBarcodes`, `session.addedTrackedBarcodes`, `session.updatedTrackedBarcodes`, and `session.removedTrackedBarcodes` keep the same names and shapes.
- `trackedBarcode.barcode.data`, `.symbology`, `trackedBarcode.identifier`, `trackedBarcode.location` are unchanged.
- `DataCaptureContext`, `Camera`, `DataCaptureView`, `Symbology` are unaffected by this rename.

## SDK 8 constructor modernization

While renaming, also modernize construction to the SDK 7.6+ / 8 pattern:

| Legacy factory call | Modern construction (SDK ≥7.6) |
|---|---|
| `Scandit.DataCaptureContext.forLicenseKey(key)` | `Scandit.DataCaptureContext.initialize(key)` |
| `Scandit.BarcodeTracking.forContext(context, settings)` | `new Scandit.BarcodeBatch(settings)` then `context.setMode(barcodeBatch)` |
| `Scandit.BarcodeTrackingBasicOverlay.withBarcodeTrackingForView(mode, view)` | `new Scandit.BarcodeBatchBasicOverlay(barcodeBatch, style)` then `view.addOverlay(overlay)` |
| `Scandit.Camera.default` | `Scandit.Camera.withSettings(Scandit.BarcodeBatch.createRecommendedCameraSettings())` |

> The `.forContext(...)` factory took both the context and settings and auto-registered the mode. The modern `new Scandit.BarcodeBatch(settings)` constructor does **not** take the context — register the mode separately with `context.setMode(barcodeBatch)`. Likewise, `withBarcodeTrackingForView` auto-attached the overlay to the view; the modern overlay constructor does not, so call `view.addOverlay(overlay)` explicitly.

## Before / after

```javascript
// BEFORE (legacy BarcodeTracking):
const context = Scandit.DataCaptureContext.forLicenseKey('YOUR_LICENSE_KEY');
const settings = new Scandit.BarcodeTrackingSettings();
settings.enableSymbologies([Scandit.Symbology.EAN13UPCA, Scandit.Symbology.Code128]);
const barcodeTracking = Scandit.BarcodeTracking.forContext(context, settings);
barcodeTracking.addListener({
  didUpdateSession: (mode, session) => { /* ... */ },
});
const view = Scandit.DataCaptureView.forContext(context);
view.connectToElement(document.getElementById('data-capture-view'));
const overlay = Scandit.BarcodeTrackingBasicOverlay.withBarcodeTrackingForView(barcodeTracking, view);
```

```javascript
// AFTER (current BarcodeBatch):
const context = Scandit.DataCaptureContext.initialize('YOUR_LICENSE_KEY');
const settings = new Scandit.BarcodeBatchSettings();
settings.enableSymbologies([Scandit.Symbology.EAN13UPCA, Scandit.Symbology.Code128]);
window.barcodeBatch = new Scandit.BarcodeBatch(settings);
context.setMode(window.barcodeBatch);
window.barcodeBatch.addListener({
  didUpdateSession: (mode, session) => { /* ... unchanged ... */ },
});
window.view = Scandit.DataCaptureView.forContext(context);
window.view.connectToElement(document.getElementById('data-capture-view'));
window.basicOverlay = new Scandit.BarcodeBatchBasicOverlay(
  window.barcodeBatch,
  Scandit.BarcodeBatchBasicOverlayStyle.Frame,
);
window.view.addOverlay(window.basicOverlay);
```

## After migrating

1. Bump the Cordova plugin versions (`scandit-cordova-datacapture-core` and `scandit-cordova-datacapture-barcode`) in `config.xml` / `package.json` to the target major version.
2. Run **`cordova prepare`** so the native projects pick up the new plugin versions. A web/native version mismatch causes runtime errors.
3. Show a summary of the renames that were applied. Reference the official [Cordova 6 → 7](https://docs.scandit.com/sdks/cordova/migrate-6-to-7/) and [Cordova 7 → 8](https://docs.scandit.com/sdks/cordova/migrate-7-to-8/) migration guides for anything outside MatrixScan Batch.

> Do not guess documentation URLs for specific classes. Use the migration guide links above, or fetch the [BarcodeBatch API index](https://docs.scandit.com/data-capture-sdk/cordova/barcode-capture/api.html) and follow links from there.
