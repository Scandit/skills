# MatrixScan Count Flutter Migration Guide

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and change only the Scandit calls underneath.
- **Dual-version code.** When code must run on both the old and the target version, branch on a symbol this guide lists as removed in the target version — never on a version string, and never on the presence of the new API. A deprecated symbol that is still present proves nothing about the installed version. Example: `BarcodeCapture.forContext` is removed on Flutter and React Native 7→8, but still exists on Web and deprecated-but-present on Capacitor and Cordova.

This guide covers three migration scenarios:

1. **Constructor migration** — `BarcodeCount.forDataCaptureContext(context, settings)` (pre-7.6) → `BarcodeCount(settings)` (≥7.6)
2. **Adopting Status Mode** — first available on Flutter 7.0 (beta)
3. **Adopting Mapping Flow and Not-in-List Actions** — first available on Flutter 8.3 (beta)

---

## Scenario 1 — Constructor Migration (pre-7.6 → ≥7.6)

### Background

Before SDK 7.6 on Flutter, the only way to create a `BarcodeCount` was with the factory that requires a `DataCaptureContext`:

```dart
// Pre-7.6 pattern:
final barcodeCount = await BarcodeCount.forDataCaptureContext(
  dataCaptureContext, settings);
// The mode was automatically added to the context.
barcodeCount.addListener(this);
```

From SDK 7.6 onwards a context-free constructor is available. The mode is **not** automatically added to the context — you must call `setMode` explicitly.

### Migration Steps

**Step 1 — Replace the constructor call**

Before:
```dart
final barcodeCount = await BarcodeCount.forDataCaptureContext(
  dataCaptureContext, barcodeCountSettings);
```

After:
```dart
final barcodeCount = BarcodeCount(barcodeCountSettings);
dataCaptureContext.setMode(barcodeCount);
```

Key differences:
- No `await` — the new constructor is synchronous.
- No `dataCaptureContext` argument — the context is not passed to the constructor.
- `dataCaptureContext.setMode(barcodeCount)` must be called explicitly — the mode is no longer auto-registered.

**Step 2 — Add `createRecommendedCameraSettings()` (if not already present)**

The static method `BarcodeCount.createRecommendedCameraSettings()` became available on Flutter ≥7.6 (previously it was not available via the Flutter plugin). Apply it after setting up the camera:

```dart
_camera?.applySettings(BarcodeCount.createRecommendedCameraSettings());
```

**Step 3 — Verify dispose path**

The disposal pattern is unchanged. `dataCaptureContext.removeAllModes()` is still the correct way to detach the mode:

```dart
void dispose() {
  _camera?.switchToDesiredState(FrameSourceState.off);
  barcodeCount.removeListener(this);
  dataCaptureContext.removeAllModes();
}
```

**Step 4 — Update `pubspec.yaml`**

Ensure the SDK constraint allows ≥7.6. The plugin package name is unchanged: `scandit_flutter_datacapture_barcode`. Bump the version constraint accordingly.

### Full before / after

**Before (Flutter 6.17–7.5):**
```dart
class CountBloc implements BarcodeCountListener {
  late DataCaptureContext dataCaptureContext;
  late BarcodeCount barcodeCount;

  Future<void> _init() async {
    dataCaptureContext = DataCaptureContext.forLicenseKey(licenseKey);
    _camera = Camera.defaultCamera;
    if (_camera != null) dataCaptureContext.setFrameSource(_camera!);

    final settings = BarcodeCountSettings()
      ..enableSymbologies({Symbology.ean13Upca, Symbology.code128});

    // Async factory — must be awaited; auto-adds to context.
    barcodeCount = await BarcodeCount.forDataCaptureContext(
        dataCaptureContext, settings);
    barcodeCount.addListener(this);
  }
}
```

**After (Flutter ≥7.6):**
```dart
class CountBloc implements BarcodeCountListener {
  late final DataCaptureContext dataCaptureContext;
  late final BarcodeCount barcodeCount;

  CountBloc() {
    dataCaptureContext = DataCaptureContext.forLicenseKey(licenseKey);
    _camera = Camera.defaultCamera;
    _camera?.applySettings(BarcodeCount.createRecommendedCameraSettings());
    if (_camera != null) dataCaptureContext.setFrameSource(_camera!);

    final settings = BarcodeCountSettings()
      ..enableSymbologies({Symbology.ean13Upca, Symbology.code128});

    // Synchronous constructor; must setMode explicitly.
    barcodeCount = BarcodeCount(settings);
    dataCaptureContext.setMode(barcodeCount);
    barcodeCount.addListener(this);
  }
}
```

**Checklist:**
- [ ] No `await BarcodeCount.forDataCaptureContext(...)` remains in the codebase.
- [ ] `dataCaptureContext.setMode(barcodeCount)` is called after construction.
- [ ] `BarcodeCount.createRecommendedCameraSettings()` is applied to the camera.
- [ ] `pubspec.yaml` SDK constraint allows ≥7.6.

---

## Scenario 2 — Adopting Status Mode (Flutter ≥7.0)

Status mode shows status icons on each scanned barcode (e.g. "verified", "needs recount"). It is activated either by the user pressing the status mode button, or automatically via `shouldShowStatusIconsOnScan` (Flutter ≥8.3).

> **Note**: Status mode is still in beta and may change in future SDK versions.

### Minimum version

Flutter ≥7.0 (this is the **earliest** Flutter version that has `BarcodeCountStatusProvider` and `setStatusProvider`).

### Step 1 — Implement BarcodeCountStatusProvider

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_count.dart';

class MyStatusProvider implements BarcodeCountStatusProvider {
  @override
  void onStatusRequested(
    List<TrackedBarcode> barcodes,
    BarcodeCountStatusProviderCallback providerCallback,
  ) {
    // Build a status list — one BarcodeCountStatusItem per barcode.
    // Consult your inventory system here.
    final statusItems = barcodes.map((b) {
      // Example: accept all barcodes.
      return BarcodeCountStatusItem(b, BarcodeCountStatus.accept);
    }).toList();
    providerCallback.onStatusReady(statusItems);
  }
}
```

`BarcodeCountStatusProviderCallback.onStatusReady(items)` must be called to deliver the result. The `BarcodeCountStatus` enum values available on Flutter are: `none`, `notAvailable`, `expired`, `fragile`, `qualityCheck`, `lowStock`, `wrong`, `expiringSoon` — see the `integration.md` status section for descriptions of each value.

### Step 2 — Attach the provider to the view

```dart
await view.setStatusProvider(MyStatusProvider());
```

Call this after the view is created. It is safe to call from `initState()` or from the BLoC's setup method.

### Step 3 — Enable the status mode button or auto-show icons

Option A — manual toggle (user presses the button):
```dart
view.shouldShowStatusModeButton = true;  // Flutter ≥7.0
```

Option B — auto-show icons immediately on scan (Flutter ≥8.3, recommended):
```dart
view.shouldShowStatusIconsOnScan = true;
// When this is true, shouldShowStatusModeButton has no effect.
```

### Step 4 — Handle tap events (optional)

If using the dot style, implement `BarcodeCountViewListener` tap callbacks for accepted/rejected barcodes:

```dart
@override
void didTapAcceptedBarcode(BarcodeCountView view, TrackedBarcode trackedBarcode) {
  // Handle tap on an accepted barcode.
}

@override
void didTapRejectedBarcode(BarcodeCountView view, TrackedBarcode trackedBarcode) {
  // Handle tap on a rejected barcode.
}
```

---

## Scenario 3 — Adopting Mapping Flow (Flutter ≥8.3)

The mapping flow presents a grid view that maps scanned barcodes to spatial positions. It is in beta.

> **Note**: The grid mapping flow only supports grids of 4 rows × 2 columns.

### Minimum version

Flutter ≥8.3.

### Step 1 — Enable mapping in settings

```dart
final settings = BarcodeCountSettings()
  ..mappingEnabled = true
  ..enableSymbologies({Symbology.ean13Upca, Symbology.code128});
```

### Step 2 — Create BarcodeCountMappingFlowSettings

```dart
final mappingSettings = BarcodeCountMappingFlowSettings()
  ..scanBarcodesGuidanceText = 'Tap shutter to scan batch'
  ..nextButtonText = 'Next'
  ..finishButtonText = 'Done'
  ..redoScanButtonText = 'Redo';
```

### Step 3 — Use the mapping view constructor

```dart
BarcodeCountView.forMapping(
  _bloc.dataCaptureContext,
  _bloc.barcodeCount,
  BarcodeCountViewStyle.icon,
  mappingSettings,
)
  ..uiListener = _bloc
  ..listener = _bloc
```

### Step 4 — Retrieve the spatial map from the session

```dart
@override
Future<void> didScan(BarcodeCount barcodeCount, BarcodeCountSession session,
    Future<FrameData> Function() getFrameData) async {
  final spatialMap = await session.getSpatialMap();
  if (spatialMap != null) {
    // Process the grid layout.
  }
}
```

Or with row/column hints:
```dart
final spatialMap = await session.getSpatialMapWithHints(4, 2);
```

---

## Scenario 4 — Adopting Not-in-List Action Settings (Flutter ≥8.3)

When scanning against a capture list, `BarcodeCountNotInListActionSettings` shows an accept/reject popup for barcodes not in the list.

### Minimum version

Flutter ≥8.3.

### Step 1 — Configure the settings

```dart
final notInListSettings = BarcodeCountNotInListActionSettings()
  ..enabled = true
  ..acceptButtonText = 'Accept'
  ..rejectButtonText = 'Reject'
  ..cancelButtonText = 'Cancel'
  ..barcodeAcceptedHint = 'Barcode accepted'
  ..barcodeRejectedHint = 'Barcode rejected';

view.barcodeNotInListActionSettings = notInListSettings;
```

### Step 2 — Handle accept/reject taps

Implement `didTapAcceptedBarcode` and `didTapRejectedBarcode` in the `BarcodeCountViewListener`:

```dart
@override
void didTapAcceptedBarcode(BarcodeCountView view, TrackedBarcode trackedBarcode) {
  // Barcode was accepted by the user.
}

@override
void didTapRejectedBarcode(BarcodeCountView view, TrackedBarcode trackedBarcode) {
  // Barcode was rejected by the user.
}
```

---

## Version Availability Quick Reference

| Feature | Flutter minimum version |
|---------|------------------------|
| `BarcodeCount` mode | 6.17 |
| `BarcodeCountView` | 6.17 |
| `BarcodeCountCaptureList` | 6.17 |
| `BarcodeCount(settings)` context-free constructor | **7.6** |
| `BarcodeCount.createRecommendedCameraSettings()` | **7.6** |
| `BarcodeCountStatusProvider` / status mode | **7.0** (earliest!) |
| `tapToUncountEnabled` | 7.0 |
| Mapping flow (`BarcodeCountMappingFlowSettings`) | **8.3** |
| `BarcodeCountNotInListActionSettings` | **8.3** |
| `shouldDisableModeOnExitButtonTapped` | **8.3** |
| `IBarcodeCountExtendedListener.didUpdateSession` | **8.3** (Flutter-only) |
| `IBarcodeCountCaptureListExtendedListener.didCompleteCaptureList` | **8.3** (Flutter-only) |
| `IBarcodeCountViewExtendedListener.didTapCluster` | **8.3** (Flutter-only) |
| `hardwareTriggerEnabled` (iOS volume button) | **8.3** |
| `BarcodeCountView.hardwareTriggerSupported` | **8.3** |
| `shouldShowStatusIconsOnScan` | **8.3** |
| `textForBarcodesNotInListDetectedHint` | **8.3** |
| `textForClusteringGestureHint` | **8.3** |
