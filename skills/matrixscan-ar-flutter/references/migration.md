# MatrixScan AR Flutter Migration Guide

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
BarcodeBatchAdvancedOverlayListener
BarcodeBatchAdvancedOverlayWidget
BarcodeBatchAdvancedOverlayWidgetState
BarcodeBatchAdvancedOverlayContainer
TrackedBarcode
```

> **Note**: In older SDK versions the same concept was called `BarcodeTracking` (with `BarcodeTrackingSettings`, `BarcodeTrackingListener`, etc.). Apply this same migration guide regardless of which name is present — the mapping is identical.

If none of those symbols appear in the file, fall back to `references/integration.md` — the project may already be using BarcodeAr or an entirely different mode.

---

## Step 2 — Confirm the migration is appropriate

Before rewriting anything, ask the user three quick questions:

1. **Goal**: Is the goal to display AR highlights or annotations (tooltips, bubbles, custom widgets) on top of each tracked barcode? If the goal is a list-building UX instead, suggest SparkScan rather than BarcodeAr.

2. **Overlay type**: Are they using `BarcodeBatchAdvancedOverlay` with fully custom per-barcode Flutter widgets (like `setWidgetForTrackedBarcode`)? → Suggest `BarcodeArCustomAnnotation`. Are the bubbles showing structured text fields (title, rows, footer)? → Suggest `BarcodeArInfoAnnotation` instead, which is less code to maintain.

3. **Filtering**: Are they relying on per-barcode rejection or filtering tracked barcodes at the mode level? Note this caveat from the integration reference:

   > **Note**: `BarcodeArFilter` is only available on iOS and Android native — it is **not available in the Flutter plugin** in the current API reference. Do not use this API in Flutter integrations. If filtering is needed, return `null` from `highlightForBarcode` or `annotationForBarcode` in the respective provider, or filter inside the `BarcodeArListener.didUpdateSession` callback.

---

## Step 3 — Update imports

Drop the BarcodeBatch symbols and add the BarcodeAr equivalents. Only remove the symbols that are actually unused after migration.

**Before:**
```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_batch.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';
```

**After (highlights only — adjust to the annotation variant if using Advanced Overlay):**
```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_ar.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';
```

The `scandit_flutter_datacapture_barcode_batch` barrel is replaced by `scandit_flutter_datacapture_barcode_ar`. The main barcode barrel (`scandit_flutter_datacapture_barcode`) and the core barrel remain unchanged.

**Drop entirely** (no equivalent in BarcodeAr):
- `DataCaptureView` — replaced by `BarcodeArView` (both are Flutter widgets, but `BarcodeArView` wraps the AR surface directly)
- `BarcodeBatchBasicOverlay` / `BarcodeBatchBasicOverlayStyle` — replaced by `BarcodeArHighlightProvider`
- `BarcodeBatchAdvancedOverlay` / `BarcodeBatchAdvancedOverlayListener` — replaced by `BarcodeArAnnotationProvider`
- `BarcodeBatchAdvancedOverlayWidget` / `BarcodeBatchAdvancedOverlayWidgetState` / `BarcodeBatchAdvancedOverlayContainer` — replaced by plain Flutter `Widget` returned from `BarcodeArCustomAnnotation`
- `TrackedBarcode` — providers receive `Barcode` directly; `TrackedBarcode` is still used in `BarcodeArSession` but you do not need to import the type unless you reference it explicitly
- `Anchor`, `PointWithUnit`, `DoubleWithUnit`, `MeasureUnit`, `Quadrilateral` — only needed if `BarcodeArCustomAnnotation` is used with a non-default anchor; otherwise drop them

---

## Step 4 — Replace the mode + view setup

### Mode construction

**Before:**
```dart
var captureSettings = BarcodeBatchSettings();
captureSettings.enableSymbologies({
  Symbology.ean8,
  Symbology.ean13Upca,
  Symbology.code128,
});
_barcodeBatch = BarcodeBatch(captureSettings)
  ..addListener(this);

_captureView = DataCaptureView.forContext(_context);
_captureView.addOverlay(
  BarcodeBatchBasicOverlay(_barcodeBatch, style: BarcodeBatchBasicOverlayStyle.frame)
);
_context.setMode(_barcodeBatch);
```

**After:**
```dart
var settings = BarcodeArSettings();
settings.enableSymbologies({
  Symbology.ean8,
  Symbology.ean13Upca,
  Symbology.code128,
});
_barcodeAr = BarcodeAr(settings)
  ..addListener(this);
```

Key differences:
- `BarcodeBatchSettings` → `BarcodeArSettings`
- `BarcodeBatch(captureSettings)` → `BarcodeAr(settings)`
- `_context.setMode(...)` is **removed** — `BarcodeArView` wires the mode to the context internally when constructed
- `DataCaptureView.forContext(...)` is removed — replaced by `BarcodeArView` created in `initState()`
- `_captureView.addOverlay(...)` is removed — highlights and annotations are wired as properties on `BarcodeArView`

### Camera settings

**Before:**
```dart
var cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
```

**After:**
```dart
final cameraSettings = BarcodeAr.createRecommendedCameraSettings();
```

### Field declarations

**Before:**
```dart
late BarcodeBatch _barcodeBatch;
late DataCaptureView _captureView;
```

**After:**
```dart
late BarcodeAr _barcodeAr;
BarcodeArView? _barcodeArView;
```

### BarcodeArView construction

Create the view **once in `initState()`** and store it as a field. Never create it inside `build()`.

```dart
@override
void initState() {
  super.initState();
  WidgetsBinding.instance.addObserver(this);

  final cameraSettings = BarcodeAr.createRecommendedCameraSettings();
  _camera?.applySettings(cameraSettings);

  var settings = BarcodeArSettings()
    ..enableSymbologies({
      Symbology.ean8,
      Symbology.ean13Upca,
      Symbology.code128,
    });

  _barcodeAr = BarcodeAr(settings)
    ..addListener(this);

  final viewSettings = BarcodeArViewSettings();

  _barcodeArView = BarcodeArView.forModeWithViewSettingsAndCameraSettings(
    _context,
    _barcodeAr,
    viewSettings,
    cameraSettings,
  )..highlightProvider = this;  // or ..annotationProvider = this

  _checkPermission();
}
```

Embed the stored field in `build()`:

```dart
@override
Widget build(BuildContext context) {
  return Scaffold(
    body: _barcodeArView!,
  );
}
```

> **Important**: `BarcodeArView` starts scanning automatically when added to the widget tree. You do not need to call `view.start()` explicitly on construction — unlike the React Native counterpart where `view.start()` is required in the `ref` callback. Use `_barcodeArView?.start()` / `_barcodeArView?.stop()` to manually control scanning after the view is mounted.

No `addOverlay` calls are needed — highlights and annotations are wired as properties on `BarcodeArView`.

---

## Step 5 — Migrate `BarcodeBatchBasicOverlay` → highlights

The `State` class implements `BarcodeArHighlightProvider` and overrides `highlightForBarcode`.

### Frame style → `BarcodeArRectangleHighlight`

**Before:**
```dart
_captureView.addOverlay(
  BarcodeBatchBasicOverlay(_barcodeBatch, style: BarcodeBatchBasicOverlayStyle.frame)
);
```

**After:**

Add `BarcodeArHighlightProvider` to the class `implements` clause:
```dart
class _MatrixScanScreenState extends State<MatrixScanScreen>
    with WidgetsBindingObserver
    implements BarcodeArListener, BarcodeArHighlightProvider {
```

Implement the provider method:
```dart
@override
Future<BarcodeArHighlight?> highlightForBarcode(Barcode barcode) async {
  return BarcodeArRectangleHighlight(barcode);
}
```

Wire it to the view in `initState()`:
```dart
_barcodeArView = BarcodeArView.forModeWithViewSettingsAndCameraSettings(
  _context, _barcodeAr, viewSettings, cameraSettings,
)..highlightProvider = this;
```

### Dot style → `BarcodeArCircleHighlight`

**Before:**
```dart
_captureView.addOverlay(
  BarcodeBatchBasicOverlay(_barcodeBatch, style: BarcodeBatchBasicOverlayStyle.dot)
);
```

**After:**
```dart
@override
Future<BarcodeArHighlight?> highlightForBarcode(Barcode barcode) async {
  return BarcodeArCircleHighlight(barcode, BarcodeArCircleHighlightPreset.dot);
}
```

The provider fires once per barcode when it first enters the tracked set. Return `null` to suppress the highlight for a specific barcode.

---

## Step 6 — Migrate `BarcodeBatchAdvancedOverlay` → annotations

The Bubbles sample wires a custom `ProductBubble` widget per barcode using `setWidgetForTrackedBarcode`. In BarcodeAr, the same widget is returned from an annotation provider.

### Custom Flutter widget bubbles → `BarcodeArCustomAnnotation`

**Before:**
```dart
// Field declarations
late BarcodeBatchAdvancedOverlay _advancedOverlay;
Map<int, ProductBubble?> _trackedBarcodes = {};

// In initState():
var _basicOverlay = BarcodeBatchBasicOverlay(_barcodeBatch, style: BarcodeBatchBasicOverlayStyle.dot);
_captureView.addOverlay(_basicOverlay);
_advancedOverlay = BarcodeBatchAdvancedOverlay(_barcodeBatch)..listener = this;
_captureView.addOverlay(_advancedOverlay);

// Listener callbacks:
@override
Anchor anchorForTrackedBarcode(BarcodeBatchAdvancedOverlay overlay, TrackedBarcode trackedBarcode) {
  return Anchor.topCenter;
}

@override
PointWithUnit offsetForTrackedBarcode(BarcodeBatchAdvancedOverlay overlay, TrackedBarcode trackedBarcode) {
  return PointWithUnit(DoubleWithUnit(0, MeasureUnit.fraction), DoubleWithUnit(-1, MeasureUnit.fraction));
}

@override
BarcodeBatchAdvancedOverlayWidget? widgetForTrackedBarcode(
    BarcodeBatchAdvancedOverlay overlay, TrackedBarcode trackedBarcode) {
  return null;
}

@override
void didTapViewForTrackedBarcode(BarcodeBatchAdvancedOverlay overlay, TrackedBarcode trackedBarcode) {
  var productBubble = _trackedBarcodes[trackedBarcode.identifier];
  if (productBubble != null) {
    productBubble.onTap();
  }
  _advancedOverlay.setWidgetForTrackedBarcode(productBubble, trackedBarcode);
}
```

**After:**

Add `BarcodeArAnnotationProvider` to the `implements` clause:
```dart
class _MatrixScanScreenState extends State<MatrixScanScreen>
    with WidgetsBindingObserver
    implements BarcodeArListener, BarcodeArHighlightProvider, BarcodeArAnnotationProvider {
```

Implement the annotation provider:
```dart
@override
Future<BarcodeArAnnotation?> annotationForBarcode(Barcode barcode) async {
  final data = barcode.data;
  if (data == null) return null;

  return BarcodeArCustomAnnotation(
    barcode: barcode,
    annotationTrigger: BarcodeArAnnotationTrigger.highlightTapAndBarcodeScan,
    child: ProductBubble(data),  // your existing bubble widget, now plain StatefulWidget
  );
}
```

Wire it to the view in `initState()`:
```dart
_barcodeArView = BarcodeArView.forModeWithViewSettingsAndCameraSettings(
  _context, _barcodeAr, viewSettings, cameraSettings,
)
  ..highlightProvider = this
  ..annotationProvider = this;
```

The `anchor` and `offsetForTrackedBarcode` callbacks are replaced by the `annotationTrigger` property on `BarcodeArCustomAnnotation`. Built-in annotation types (`BarcodeArInfoAnnotation`, `BarcodeArPopoverAnnotation`) auto-position — no explicit anchor or offset is needed.

> **Note**: `BarcodeArCustomAnnotation` requires SDK 8.1+. The `child` widget is serialized as a static image at render time — animated widgets will not animate inside the AR overlay.

### Remove the ProductBubble inheritance

`ProductBubble` extended `BarcodeBatchAdvancedOverlayWidget` with a `BarcodeBatchAdvancedOverlayWidgetState`. In BarcodeAr it becomes a plain Flutter `StatefulWidget`:

**Before:**
```dart
class ProductBubble extends BarcodeBatchAdvancedOverlayWidget { ... }
class ProductBubbleState extends BarcodeBatchAdvancedOverlayWidgetState<ProductBubble> {
  @override
  BarcodeBatchAdvancedOverlayContainer build(BuildContext context) {
    return BarcodeBatchAdvancedOverlayContainer(width: 160, height: 60, ...);
  }
}
```

**After:**
```dart
class ProductBubble extends StatefulWidget {
  // onTap() can be removed — BarcodeArCustomAnnotation handles tap via its trigger
  const ProductBubble(this.barcodeData, {super.key});
  final String barcodeData;
  @override
  State<ProductBubble> createState() => ProductBubbleState();
}

class ProductBubbleState extends State<ProductBubble> {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 160,
      height: 60,
      decoration: BoxDecoration(
        color: const Color(0xFFFFFFEE),
        borderRadius: BorderRadius.circular(30),
      ),
      child: Center(child: Text(widget.barcodeData)),
    );
  }
}
```

`BarcodeBatchAdvancedOverlayContainer` is replaced by a plain `Container` (or any `Widget`).

### Structured info bubbles → `BarcodeArInfoAnnotation`

If the existing `ProductBubble` only shows text fields (e.g. stock count and barcode data), replace the whole custom widget with a `BarcodeArInfoAnnotation`:

```dart
@override
Future<BarcodeArAnnotation?> annotationForBarcode(Barcode barcode) async {
  final header = BarcodeArInfoAnnotationHeader()
    ..text = 'Report stock count';

  final stockRow = BarcodeArInfoAnnotationBodyComponent()
    ..text = 'Shelf: 4  Back room: 8';

  final annotation = BarcodeArInfoAnnotation(barcode)
    ..width = BarcodeArInfoAnnotationWidthPreset.medium
    ..anchor = BarcodeArInfoAnnotationAnchor.top
    ..header = header
    ..body = [stockRow];

  return annotation;
}
```

### Distance-based show/hide → `BarcodeArResponsiveAnnotation`

The Bubbles sample contains a manual `viewQuadrilateralForFrameQuadrilateral` call combined with a width threshold to hide annotations when the barcode is too small on screen:

```dart
// Old pattern — delete this entirely:
for (final trackedBarcode in session.trackedBarcodes.values) {
  _captureView
      .viewQuadrilateralForFrameQuadrilateral(trackedBarcode.location)
      .then((location) => _updateView(trackedBarcode, location));
}

_updateView(TrackedBarcode trackedBarcode, Quadrilateral viewLocation) {
  var shouldBeShown = viewLocation.width() > MediaQuery.of(context).size.width * 0.1;
  if (!shouldBeShown) {
    _advancedOverlay.setWidgetForTrackedBarcode(null, trackedBarcode);
    return;
  }
  _advancedOverlay.setWidgetForTrackedBarcode(bubble, trackedBarcode);
}
```

Replace it with `BarcodeArResponsiveAnnotation` (SDK 8.2+), which switches between two `BarcodeArInfoAnnotation` variants based on the barcode's relative size on screen:

```dart
@override
Future<BarcodeArAnnotation?> annotationForBarcode(Barcode barcode) async {
  // Close-up: full detail
  final closeUp = BarcodeArInfoAnnotation(barcode)
    ..width = BarcodeArInfoAnnotationWidthPreset.large
    ..body = [
      BarcodeArInfoAnnotationBodyComponent()..text = 'Shelf: 4  Back room: 8',
    ];

  // Far away: minimal placeholder
  final farAway = BarcodeArInfoAnnotation(barcode)
    ..width = BarcodeArInfoAnnotationWidthPreset.small
    ..body = [
      BarcodeArInfoAnnotationBodyComponent()..text = 'Get closer',
    ];

  return BarcodeArResponsiveAnnotation(barcode, closeUp, farAway)
    ..threshold = 0.1; // ~10% of screen width, matches old heuristic
}
```

No `Quadrilateral`, `MediaQuery`, `viewQuadrilateralForFrameQuadrilateral`, or `_updateView` helper needed.

---

## Step 7 — Migrate the listener

In BarcodeBatch the session listener updated both app state and drove overlay content (calling `setWidgetForTrackedBarcode` in response to every frame). In BarcodeAr these responsibilities are split:

- **Visual content** (highlights, annotations) → handled by the providers (Steps 5 and 6). Do not call `setWidgetForTrackedBarcode` or create overlay objects in the listener.
- **App state** (e.g. accumulating scan results) → handled in `BarcodeArListener.didUpdateSession` using `session.addedTrackedBarcodes`.

**Before (Simple sample pattern):**
```dart
@override
Future<void> didUpdateSession(
    BarcodeBatch barcodeBatch, BarcodeBatchSession session, Future<void> getFrameData()) async {
  for (final trackedBarcode in session.addedTrackedBarcodes) {
    scanResults.add(ScanResult(trackedBarcode.barcode.symbology, trackedBarcode.barcode.data ?? ''));
  }
}
```

**After:**
```dart
@override
Future<void> didUpdateSession(
    BarcodeAr barcodeAr, BarcodeArSession session, Future<FrameData> Function() getFrameData) async {
  // Use addedTrackedBarcodes — only newly tracked barcodes, not all of them every frame.
  for (final trackedBarcode in session.addedTrackedBarcodes) {
    scanResults.add(ScanResult(trackedBarcode.barcode.symbology, trackedBarcode.barcode.data ?? ''));
  }
}
```

Key changes:
- `BarcodeBatch` / `BarcodeBatchSession` type annotations → `BarcodeAr` / `BarcodeArSession`
- `Future<void> getFrameData()` → `Future<FrameData> Function() getFrameData` (the callback signature changed)
- Session updates that iterated `session.trackedBarcodes.values` to drive `setWidgetForTrackedBarcode` are removed entirely — the annotation provider handles that now

**Before (Bubbles sample pattern — delete the loop that called `_updateView`):**
```dart
@override
Future<void> didUpdateSession(
    BarcodeBatch barcodeBatch, BarcodeBatchSession session, Future<FrameData> getFrameData()) async {
  for (final removedBarcodeId in session.removedTrackedBarcodes) {
    _trackedBarcodes[removedBarcodeId] = null;
  }
  for (final trackedBarcode in session.trackedBarcodes.values) {
    _captureView
        .viewQuadrilateralForFrameQuadrilateral(trackedBarcode.location)
        .then((location) => _updateView(trackedBarcode, location));
  }
}
```

**After:**
```dart
@override
Future<void> didUpdateSession(
    BarcodeAr barcodeAr, BarcodeArSession session, Future<FrameData> Function() getFrameData) async {
  // Visual updates are handled by annotationForBarcode — nothing to do here.
  // Keep only app-state updates (e.g. count of unique barcodes, audit log).
}
```

If the old code handled `session.removedTrackedBarcodes`, the property exists on `BarcodeArSession` with the same name — keep that logic if needed.

---

## Step 8 — Migrate lifecycle

### Enabling / disabling scanning

**Before:**
```dart
void _showScanResults(BuildContext context) {
  _barcodeBatch.isEnabled = false;
  Navigator.pushNamed(context, '/scanResults', arguments: scanResults)
      .then((value) => _resetScanResults());
}

void _resetScanResults() {
  scanResults.clear();
  _barcodeBatch.isEnabled = true;
}

void _freeze(bool isFrozen) {
  _barcodeBatch.isEnabled = !isFrozen;
  _camera?.switchToDesiredState(isFrozen ? FrameSourceState.off : FrameSourceState.on);
}
```

**After:**
```dart
void _showScanResults(BuildContext context) {
  _barcodeArView?.stop();
  Navigator.pushNamed(context, '/scanResults', arguments: scanResults)
      .then((value) => _resetScanResults());
}

void _resetScanResults() {
  scanResults.clear();
  _barcodeArView?.start();
}

void _freeze(bool isFrozen) {
  if (isFrozen) {
    _barcodeArView?.stop();
    _camera?.switchToDesiredState(FrameSourceState.off);
  } else {
    _barcodeArView?.start();
    _camera?.switchToDesiredState(FrameSourceState.on);
  }
}
```

`BarcodeAr` has no `isEnabled` property. Use `_barcodeArView?.start()` / `_barcodeArView?.stop()` / `_barcodeArView?.pause()` instead.

### Camera lifecycle — no change needed

The camera setup using `Camera.defaultCamera`, `_camera?.applySettings(cameraSettings)`, `_context.setFrameSource(_camera!)`, and `_camera!.switchToDesiredState(FrameSourceState.on/off)` is unchanged. Keep the `WidgetsBindingObserver` subscription and the `didChangeAppLifecycleState` guard exactly as they are.

### setMode removal

`_context.setMode(_barcodeBatch)` is removed entirely. `BarcodeArView` registers the mode with the context when it is constructed via the factory.

---

## Step 9 — Cleanup

**Before:**
```dart
void _cleanup() {
  WidgetsBinding.instance.removeObserver(this);
  _barcodeBatch.removeListener(this);
  _barcodeBatch.isEnabled = false;
  _camera?.switchToDesiredState(FrameSourceState.off);
  _context.removeAllModes();  // or DataCaptureContext.sharedInstance.removeCurrentMode()
}
```

**After:**
```dart
void _cleanup() {
  WidgetsBinding.instance.removeObserver(this);
  _barcodeAr.removeListener(this);
  _camera?.switchToDesiredState(FrameSourceState.off);
  // _barcodeArView tears itself down with the State — no removeMode call needed.
}
```

Or equivalently, if cleanup is in `dispose()`:
```dart
@override
void dispose() {
  _barcodeAr.removeListener(this);
  WidgetsBinding.instance.removeObserver(this);
  super.dispose();
}
```

Remove all `_advancedOverlay` and `_captureView` refs entirely; there are no overlay objects to clean up in BarcodeAr.

---

## Step 10 — Verify

Run through this checklist before considering the migration complete:

- [ ] No `BarcodeBatch`, `BarcodeBatchSettings`, `BarcodeBatchSession`, `BarcodeBatchListener`, `BarcodeBatchBasicOverlay`, `BarcodeBatchBasicOverlayStyle`, `BarcodeBatchAdvancedOverlay`, `BarcodeBatchAdvancedOverlayListener`, `BarcodeBatchAdvancedOverlayWidget`, `BarcodeBatchAdvancedOverlayWidgetState`, `BarcodeBatchAdvancedOverlayContainer`, or `TrackedBarcode` symbols remain in the files (a text search for `BarcodeBatch` or `BarcodeTracking` should return zero matches).
- [ ] The import `scandit_flutter_datacapture_barcode_batch` is gone; replaced by `scandit_flutter_datacapture_barcode_ar`.
- [ ] `DataCaptureView` is replaced by `BarcodeArView` — no `DataCaptureView.forContext(...)` in the file.
- [ ] `_captureView.addOverlay(...)` calls are gone.
- [ ] At least one of `highlightProvider` or `annotationProvider` is set on the `BarcodeArView` instance.
- [ ] `BarcodeArView` is created in `initState()` and stored as a field, not inside `build()`.
- [ ] `_context.setMode(...)` is removed — `BarcodeArView` wires the mode internally.
- [ ] `_barcodeBatch.isEnabled` assignments are replaced by `_barcodeArView?.start()` / `_barcodeArView?.stop()`.
- [ ] The `didUpdateSession` signature uses `BarcodeAr`, `BarcodeArSession`, and `Future<FrameData> Function()` (not `Future<void>`).
- [ ] No `viewQuadrilateralForFrameQuadrilateral` calls remain (replaced by `BarcodeArResponsiveAnnotation` if distance-based show/hide was needed).
- [ ] No `setWidgetForTrackedBarcode` calls remain (replaced by the annotation provider).
- [ ] `ProductBubble` (or equivalent bubble widget) no longer extends `BarcodeBatchAdvancedOverlayWidget` — it is a plain `StatefulWidget`.
- [ ] `Symbology` values use **lowerCamelCase** throughout: `Symbology.ean13Upca`, `Symbology.code128`, etc.
- [ ] Run `flutter analyze` — zero errors and zero warnings related to BarcodeBatch symbols.
