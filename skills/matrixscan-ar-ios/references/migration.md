# MatrixScan Batch → MatrixScan AR Migration Guide

MatrixScan Batch and MatrixScan AR are two different products that share the idea of "track multiple barcodes simultaneously". Batch gives you a raw `DataCaptureView` + overlay and session callbacks with `addedTrackedBarcodes` / `updatedTrackedBarcodes` / `removedTrackedBarcodes` — the app draws its own shapes. MatrixScan AR gives you a pre-built `BarcodeArView` with first-class highlight and annotation providers on top of the AR view.

**A Batch → AR migration is a rewrite of the view and listener layer**, not a rename. Tell the user this up front so they know what to expect.

## Step 1: Detect the installed SDK version and the Batch API name

The MatrixScan Batch mode has been renamed across versions. Before migrating, find out which name the project uses:

1. **v6.x**: the mode class is `BarcodeTracking`, settings is `BarcodeTrackingSettings`, overlay is `BarcodeTrackingBasicOverlay`, listener is `BarcodeTrackingListener`.
2. **v7.x and later**: the mode class is `BarcodeBatch`, settings is `BarcodeBatchSettings`, overlay is `BarcodeBatchBasicOverlay`, listener is `BarcodeBatchListener`.

Search the project for the appropriate class names. Check `Package.resolved` (`"identity": "datacapture-spm"`) or `Podfile.lock` to confirm the SDK version.

`BarcodeAr` was introduced in **SDK 7.1.0**. If the project is on 7.0.x or on v6, the user must bump the SDK version first — the Batch → AR migration can only begin once `BarcodeAr` is actually available. Direct them to the SparkScan migration guide's SDK version bump steps (SPM / CocoaPods) — the process is the same.

## Step 2: API mapping

| Batch (v7+ names) | MatrixScan AR |
|---|---|
| `BarcodeBatch` | `BarcodeAr` |
| `BarcodeBatchSettings` | `BarcodeArSettings` |
| `DataCaptureView` + `BarcodeBatchBasicOverlay` | `BarcodeArView` (single pre-built view — no separate overlay) |
| `BarcodeBatchListener` | `BarcodeArListener` |
| `BarcodeBatchSession.addedTrackedBarcodes / updatedTrackedBarcodes / removedTrackedBarcodes / trackedBarcodes` | `BarcodeArSession.addedTrackedBarcodes / removedTrackedBarcodes / trackedBarcodes` — **same names, except there is no `updatedTrackedBarcodes`.** Code that iterated added/removed/tracked barcodes ports verbatim; code that relied on `updatedTrackedBarcodes` needs to be rewritten against `trackedBarcodes` (the full dictionary of currently tracked barcodes) instead. |
| `BarcodeBatchBasicOverlay` styling (`brush`, `setBrush(for:)`) | `BarcodeArHighlightProvider` — handled by the **`matrixscan-ar-highlight-ios`** skill. Do not inline highlight styling here. |
| `BarcodeBatchAdvancedOverlay` + `BarcodeBatchAdvancedOverlayDelegate` (custom `UIView` per barcode via `viewFor` / `anchorFor` / `offsetFor`) | `BarcodeArAnnotationProvider` — handled by the **`matrixscan-ar-annotation-ios`** skill. The custom `UIView` the user built (product card, status badge, etc.) usually becomes a `BarcodeArInfoAnnotation` / `BarcodeArPopoverAnnotation` / `BarcodeArStatusIconAnnotation`, or stays as a custom `UIView & BarcodeArAnnotation` if the layout is intricate. Do not inline annotation code here. |
| Overlay tap callback (`BarcodeBatchBasicOverlayDelegate.didTapBarcodeTrackingBasicOverlay` or equivalent) | `BarcodeArViewUIDelegate.barcodeAr(_:didTapHighlightFor:highlight:)` — also handled by the highlight skill. |

If the project relies on Batch APIs not in this table, **fetch the specific API page** (both the Batch page and the AR page) rather than guessing the new name.

## Step 3: Replace the mode and settings

Rename in place:
- `BarcodeBatch` (or `BarcodeTracking`) → `BarcodeAr`
- `BarcodeBatchSettings` (or `BarcodeTrackingSettings`) → `BarcodeArSettings`

Symbology configuration (`settings.set(symbology:enabled:)`) transfers unchanged — keep the exact symbology set the project already had.

## Step 4: Replace the view layer

This is the biggest change. Batch puts a `DataCaptureView` in the hierarchy and attaches a `BarcodeBatchBasicOverlay`. AR replaces both with a single `BarcodeArView` that you hand a parent view:

Before (Batch, conceptual):
```swift
let captureView = DataCaptureView(context: context, frame: view.bounds)
view.addSubview(captureView)
let overlay = BarcodeBatchBasicOverlay(barcodeBatch: mode, view: captureView)
```

After (AR):
```swift
let viewSettings = BarcodeArViewSettings()
let barcodeArView = BarcodeArView(
    parentView: view,
    barcodeAr: mode,
    settings: viewSettings,
    cameraSettings: BarcodeAr.recommendedCameraSettings
)
```

`BarcodeArView` adds itself into `parentView` — **remove the manual `addSubview`**. Remove the overlay instantiation entirely; it has no direct equivalent.

## Step 5: Replace the lifecycle

Batch uses a `Camera` on the context plus `context.setFrameSource` and `camera.switch(toDesiredState:)` to start and stop. AR wraps all of that in the view:

- Remove `Camera`, `context.setFrameSource`, and manual `camera.switch(toDesiredState:)` calls tied to `viewWillAppear`/`viewWillDisappear`.
- Call `barcodeArView.start()` in `viewWillAppear`.
- Call `barcodeArView.stop()` in `viewWillDisappear`.

If the app uses the camera outside of MatrixScan (e.g. a separate capture view on another screen), leave that code alone — only remove camera wiring that existed to drive the Batch pipeline.

## Step 6: Replace the listener

`BarcodeBatchListener.barcodeBatch(_:didUpdate:frameData:)` (or the v6 `BarcodeTrackingListener` equivalent) is replaced by `BarcodeArListener.barcodeAr(_:didUpdate:frameData:)`.

`BarcodeArSession` keeps `addedTrackedBarcodes`, `removedTrackedBarcodes`, and `trackedBarcodes` under the same names as `BarcodeBatchSession`, so accumulation / deduplication logic built on those three ports verbatim into the new callback. The one difference: **there is no `updatedTrackedBarcodes`** — if the Batch listener relied on it (e.g. reacting to location changes on an already-tracked barcode), rewrite that branch against the full `trackedBarcodes` dictionary or move the visual side of that logic into the highlight provider where per-frame updates are handled automatically.

Preserve the app's downstream business logic (data models, analytics calls, UI updates) — only the listener method signature and the `updatedTrackedBarcodes` branch need to change.

Both callbacks fire on a **background queue** — existing `DispatchQueue.main.async` wrapping around UI updates can stay.

## Step 7: Highlights and annotations

Old Batch code fell into three styling patterns. Each maps to a different sibling skill:

1. **Basic overlay with default styling only** (`BarcodeBatchBasicOverlay(barcodeBatch:view:)` or `style: .dot` / `.frame`, no delegate, no custom brushes): the default `BarcodeArView` visuals work out of the gate and no further action is needed.
2. **Basic overlay with custom brushes** (`overlay.brush = ...` or `BarcodeBatchBasicOverlayDelegate` returning a `Brush` per barcode): rebuild with `BarcodeArHighlightProvider`. Leave a TODO in the file and route the user to **`matrixscan-ar-highlight-ios`**.
3. **Advanced overlay** (`BarcodeBatchAdvancedOverlay` + a delegate returning a custom `UIView` + `Anchor` + `PointWithUnit` offset per barcode): rebuild with `BarcodeArAnnotationProvider`. Leave a TODO and route the user to **`matrixscan-ar-annotation-ios`**.

When migrating case 2 or 3:
- **Remove** the overlay instantiation, the overlay delegate conformance, and all delegate methods (those protocols do not exist in MatrixScan AR). Keeping them as dead code would not compile.
- **Preserve** the user-owned types (custom `UIView` subclasses, data models, business logic that prepares per-barcode content). The annotation/highlight skills will reuse them as the concrete output of the new provider.
- **Preserve** any per-barcode filtering logic (e.g. "hide the overlay when the barcode occupies less than N% of the view"). Do not assume it maps cleanly to the AR provider: the AR provider is invoked once per newly detected barcode, while Batch filters like `canShowOverlay` were re-evaluated every frame from the listener. Keep the filtering helper methods intact and leave a TODO to re-wire them via the annotation skill, which handles the concrete mechanism (e.g. `BarcodeArResponsiveAnnotation` for distance-driven visibility, or returning `nil` from the provider for conditions decidable at detection time).
- If the listener's body existed **only** to manage the overlay's view dictionary (add / remove / toggle visibility), the listener itself becomes unnecessary in the migrated code — the AR view manages per-barcode visual lifecycle automatically via the providers. Remove the `BarcodeArListener` conformance and the `addListener` call unless the app genuinely needs raw session data for non-UI reasons (analytics, counts, custom business logic).

Do not inline highlight or annotation provider code in this migration. The scope boundary is strict: this skill migrates the *pipeline*, the sibling skills rebuild the *visuals*.

## Step 8: Feedback

Batch relied on app-level code for scan feedback. AR has built-in feedback via `BarcodeArViewSettings.soundEnabled` / `hapticEnabled` (both default `true`) and customizable via `BarcodeAr.feedback` (a `BarcodeArFeedback` with `scanned` and `tapped` `Feedback` events). If the Batch code had custom sound/vibration logic tied to scan events, move that configuration onto `BarcodeArFeedback` rather than keeping the old manual calls.

## After migration

1. Build the project and fix any remaining compile errors using the [MatrixScan AR API reference](https://docs.scandit.com/data-capture-sdk/ios/barcode-capture/api.html).
2. Show the user a summary of only the changes actually made: which files were edited, which classes were renamed, what was removed (overlay, manual camera, old listener), and any TODOs left for the highlight/annotation skills.
3. Do not list APIs that were already correct or unchanged.
