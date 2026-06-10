# MatrixScan Count Flutter Integration Guide

MatrixScan Count (API class name: `BarcodeCount`) is a data capture mode that implements an out-of-the-box scan-and-count solution. It simultaneously tracks all barcodes in the camera feed and provides a ready-to-use UI via `BarcodeCountView`. The user presses the shutter, the SDK counts the barcodes in view, and the result is delivered in the `BarcodeCountListener.didScan` callback.

> **State management note**: Examples below use the BLoC pattern (as in the official `MatrixScanCountSimpleSample`). The same APIs work with Provider, Riverpod, GetX, or plain `StatefulWidget` — adapt ownership of `DataCaptureContext`, `BarcodeCount`, and the camera to the project's existing convention.

## Prerequisites

- Scandit Flutter packages in `pubspec.yaml`:
  - `scandit_flutter_datacapture_barcode` (pulls in `scandit_flutter_datacapture_core` transitively)
  - `permission_handler` (for the runtime camera permission on Android)
- Flutter `>=3.22.0`, Dart SDK `>=3.0.0 <4.0.0`.
- After editing `pubspec.yaml`, run `flutter pub get` to fetch the packages.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/Runner/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request at runtime with `permission_handler`.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that enabling only the symbologies actually needed improves scanning performance and accuracy.

Once the user responds, ask them which file they would like to integrate BarcodeCount into (typically a BLoC / controller class, or a page `StatefulWidget`). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `scandit_flutter_datacapture_barcode` and `permission_handler` to `pubspec.yaml`, then run `flutter pub get`.
2. Add `NSCameraUsageDescription` to `ios/Runner/Info.plist` with a short usage explanation.
3. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with the key from https://ssl.scandit.com.
4. Ensure `main()` calls `WidgetsFlutterBinding.ensureInitialized()` and then `await ScanditFlutterDataCaptureBarcode.initialize()` before `runApp(...)`.
5. Call `Permission.camera.request()` from `permission_handler` before the first scan (usually in `initState()` of the scanning page).

## Step 1 — Initialize the SDK in `main()`

Plugin initialization **must** happen before any other Scandit API call.

```dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Must be called first — sets up all Scandit plugins.
  await ScanditFlutterDataCaptureBarcode.initialize();
  runApp(const MyApp());
}
```

> **Important**: Always call `WidgetsFlutterBinding.ensureInitialized()` before the `await`. Flutter requires the binding before any platform-channel call.

## Step 2 — Create the DataCaptureContext

```dart
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

final DataCaptureContext dataCaptureContext =
    DataCaptureContext.forLicenseKey(licenseKey);
```

## Step 3 — Configure BarcodeCountSettings and Symbologies

All symbologies are disabled by default. Only enable the ones the app actually needs.

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_count.dart';

final settings = BarcodeCountSettings()
  ..enableSymbologies({
    Symbology.ean13Upca,
    Symbology.ean8,
    Symbology.upce,
    Symbology.code39,
    Symbology.code128,
  });

// Optional: declare that only unique barcodes are expected (optimizes tracking).
settings.expectsOnlyUniqueBarcodes = true;
```

### Filtering (excluding barcodes by symbology or regex)

If labels carry several barcode types and you only want to count one of them, exclude the others on `BarcodeCountSettings.filterSettings` (a `BarcodeFilterSettings`). This is the **mode-level** filter that drops barcodes before they are counted — it is **distinct** from the view-level `view.filterSettings`, which only controls how filtered barcodes are highlighted (see Step 9).

Exclude by symbology — for example enable Code 128 but never count PDF417:

```dart
final settings = BarcodeCountSettings()
  ..enableSymbology(Symbology.code128, true);

final filterSettings = settings.filterSettings;
filterSettings.excludedSymbologies = {Symbology.pdf417};
```

Exclude by regex — for example drop every barcode whose data starts with four digits:

```dart
final filterSettings = settings.filterSettings;
filterSettings.excludedCodesRegex = '^1234.*';
```

`BarcodeFilterSettings` also exposes `excludedSymbolCounts` (`Map<Symbology, Set<int>>`) to exclude specific symbol-count lengths. The getter `settings.filterSettings` returns the live instance, so mutate it in place rather than reassigning.

### Clustering (Flutter ≥8.3, beta)

Clustering groups neighbouring barcodes together — either automatically or with manual user correction. It is disabled by default; enable it by setting `clusteringMode` on `BarcodeCountSettings` before constructing the mode:

```dart
final settings = BarcodeCountSettings()
  ..clusteringMode = ClusteringMode.autoWithManualCorrection;
```

`ClusteringMode` values:

| Value | Behavior |
|-------|----------|
| `ClusteringMode.disabled` | No clustering (default). |
| `ClusteringMode.manual` | The user selects which barcodes to cluster via the on-screen UI. |
| `ClusteringMode.auto` | Clusters are formed automatically and cannot be tuned. |
| `ClusteringMode.autoWithManualCorrection` | Clusters are formed automatically but can be created or dissolved manually. |

When clustering is enabled, the grouped barcodes are reported on `session.recognizedClusters` (`List<Cluster>`) in the `didScan` callback, and cluster taps are delivered through `didTapCluster` on `IBarcodeCountViewExtendedListener` (see Step 7). The clustering gesture hint text is set via `view.textForClusteringGestureHint`.

### BarcodeCountSettings Properties and Methods

| API | Type | Description |
|-----|------|-------------|
| `enableSymbologies(symbologies)` | method | Enable multiple symbologies (takes a `Set<Symbology>`). |
| `enableSymbology(symbology, enabled)` | method | Enable or disable a single symbology. |
| `settingsForSymbology(symbology)` | method | Get per-symbology settings (e.g. `activeSymbolCounts`). Flutter: `SymbologySettings`. |
| `expectsOnlyUniqueBarcodes` | `bool` | Set to `true` if duplicates within a batch are not expected. Default `false`. |
| `filterSettings` | `BarcodeFilterSettings` (read-only getter) | Mode-level filter: `excludedSymbologies` (`Set<Symbology>`), `excludedCodesRegex` (`String`), `excludedSymbolCounts` (`Map<Symbology, Set<int>>`). Distinct from `view.filterSettings`. |
| `disableModeWhenCaptureListCompleted` | `bool` | Auto-disable the mode when the capture list is fully scanned. Flutter ≥8.3. Default `false`. |
| `mappingEnabled` | `bool` | Enable the barcode mapping flow (beta). Flutter ≥8.3. Default `false`. |
| `clusteringMode` | `ClusteringMode` | Smart grouping of neighbouring barcodes. Flutter ≥8.3. |
| `scanPreviewEnabled` | `bool` (read-only) | Whether scan preview is enabled (set at construction). Flutter ≥8.3. |
| `setProperty<T>(name, value)` | method | Advanced hidden property setter. |
| `getProperty<T>(name)` | method | Advanced hidden property getter. |

### Scan Preview (beta)

To enable the scan preview so barcodes appear highlighted before the shutter is pressed:

```dart
final settings = BarcodeCountSettings(scanPreviewEnabled: true);
```

Only basic scanning and scanning against a list are supported when scan preview is enabled.

## Step 4 — Construct BarcodeCount

Use the `BarcodeCount(settings)` constructor available on Flutter ≥7.6. After construction, register the mode with the context explicitly.

```dart
final barcodeCount = BarcodeCount(settings);
dataCaptureContext.setMode(barcodeCount);
```

Apply recommended camera settings:

```dart
final cameraSettings = BarcodeCount.createRecommendedCameraSettings();
camera.applySettings(cameraSettings);
```

### BarcodeCount Methods and Properties

| API | Available | Description |
|-----|-----------|-------------|
| `BarcodeCount(settings)` | Flutter ≥7.6 | Context-free constructor. |
| `addListener(listener)` / `removeListener(listener)` | Flutter ≥6.17 | Register/remove a `BarcodeCountListener`. |
| `applySettings(settings)` | Flutter ≥6.17 | Asynchronously apply updated settings at runtime. Returns `Future<void>`. |
| `BarcodeCount.createRecommendedCameraSettings()` | Flutter ≥7.6 | Returns `CameraSettings` tuned for BarcodeCount. |
| `reset()` | Flutter ≥6.17 | Resets the session, clearing history. Returns `Future<void>`. |
| `startScanningPhase()` | Flutter ≥6.17 | Programmatically trigger a scan (same as pressing the shutter). Returns `Future<void>`. |
| `endScanningPhase()` | Flutter ≥6.17 | Disables the mode and switches off the frame source. Returns `Future<void>`. |
| `setBarcodeCountCaptureList(list)` | Flutter ≥6.17 | Enable scanning against a target list. Returns `Future<void>`. |
| `setAdditionalBarcodes(barcodes)` | Flutter ≥6.17 | Inject barcodes from a previous session. Returns `Future<void>`. |
| `clearAdditionalBarcodes()` | Flutter ≥6.17 | Clear injected additional barcodes. Returns `Future<void>`. |
| `isEnabled` | `bool` | Enable/disable the mode. |
| `feedback` | `BarcodeCountFeedback` | Sound/vibration feedback on scan events. |
| `context` | `DataCaptureContext?` | The context this mode is attached to (read-only). |

## Step 5 — BarcodeCountListener

Implement `BarcodeCountListener` on the BLoC to receive scan results. The primary callback is `didScan`, called once the scanning phase completes (i.e., the user pressed the shutter or `startScanningPhase()` was called).

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_count.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

class CountBloc implements BarcodeCountListener {
  @override
  Future<void> didScan(
    BarcodeCount barcodeCount,
    BarcodeCountSession session,
    Future<FrameData> Function() getFrameData,
  ) async {
    final recognized = session.recognizedBarcodes;
    for (final barcode in recognized) {
      debugPrint('Scanned: ${barcode.data} (${barcode.symbology})');
    }
  }
}
```

### BarcodeCountListener Dart Callbacks

| Callback | Signature | Description |
|----------|-----------|-------------|
| `didScan` | `(BarcodeCount, BarcodeCountSession, Future<FrameData> Function()) => Future<void>` | Called once the scanning phase is over (shutter pressed). |

### IBarcodeCountExtendedListener (Flutter ≥8.3)

Implement `IBarcodeCountExtendedListener` (instead of `BarcodeCountListener`) to also receive per-frame session updates:

```dart
class CountBloc implements IBarcodeCountExtendedListener {
  @override
  Future<void> didScan(BarcodeCount barcodeCount, BarcodeCountSession session,
      Future<FrameData> Function() getFrameData) async { ... }

  @override
  void didUpdateSession(BarcodeCount barcodeCount, BarcodeCountSession session,
      Future<FrameData> Function() getFrameData) { ... }
}
```

`didUpdateSession` is **Flutter-only** (part of `IBarcodeCountExtendedListener`) and is called on every processed frame. Use it to react to barcode tracking changes in real-time between shutter presses.

### BarcodeCountSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `recognizedBarcodes` | `List<Barcode>` | All currently recognized barcodes (available from Flutter 7.0). |
| `additionalBarcodes` | `List<Barcode>` | Barcodes injected via `setAdditionalBarcodes`. |
| `recognizedClusters` | `List<Cluster>` | Grouped barcodes when `clusteringMode` is enabled. Flutter ≥8.3. |
| `frameSequenceId` | `int` | Identifier of the current frame sequence. |
| `reset()` | `Future<void>` | Reset the session inside the listener callback. |
| `getSpatialMap()` | `Future<BarcodeSpatialGrid?>` | Compute the spatial map (requires `mappingEnabled = true`). Flutter ≥8.3. |
| `getSpatialMapWithHints(rows, cols)` | `Future<BarcodeSpatialGrid?>` | Compute spatial map with grid size hints. Flutter ≥8.3. |

## Step 6 — Create BarcodeCountView

`BarcodeCountView` is a Flutter `StatefulWidget`. It must be **presented full screen**. The canonical pattern from the sample creates it inline in `build()` with the cascade operator to set the listeners:

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_count.dart';

// Inside build():
BarcodeCountView.forContextWithModeAndStyle(
  _bloc.dataCaptureContext,
  _bloc.barcodeCount,
  BarcodeCountViewStyle.icon,
)
  ..uiListener = _bloc
  ..listener = _bloc
```

### BarcodeCountView Constructors

| Constructor | Description |
|-------------|-------------|
| `BarcodeCountView.forContextWithMode(dataCaptureContext, barcodeCount)` | Default style (dot). |
| `BarcodeCountView.forContextWithModeAndStyle(dataCaptureContext, barcodeCount, style)` | Explicit style (icon or dot). |
| `BarcodeCountView.forMapping(dataCaptureContext, barcodeCount, style, mappingFlowSettings)` | For the grid mapping flow (Flutter ≥8.3). |

### BarcodeCountViewStyle

| Value | Description |
|-------|-------------|
| `BarcodeCountViewStyle.icon` | Draws highlights as icons with entry animation. |
| `BarcodeCountViewStyle.dot` | Draws highlights as dots with entry animation. |

Default style is `dot`. Use `icon` for the most common MatrixScan Count UI.

### Widget tree integration

The view must fill the screen. The sample wraps it in a `LayoutBuilder` + `AspectRatio` to handle portrait/landscape, but a simple `Expanded` or `SizedBox.expand` is sufficient for full-screen:

```dart
@override
Widget build(BuildContext context) {
  return Scaffold(
    backgroundColor: Colors.black,
    body: SafeArea(
      bottom: false,
      child: BarcodeCountView.forContextWithModeAndStyle(
        _bloc.dataCaptureContext,
        _bloc.barcodeCount,
        BarcodeCountViewStyle.icon,
      )
        ..uiListener = _bloc
        ..listener = _bloc,
    ),
  );
}
```

## Step 7 — BarcodeCountViewListener

Implement `BarcodeCountViewListener` on the BLoC to receive tap events on barcode highlights. This listener also receives `didCompleteCaptureList` when a target list is fully scanned.

```dart
class CountBloc implements BarcodeCountListener, BarcodeCountViewListener {
  @override
  Brush? brushForRecognizedBarcode(BarcodeCountView view, TrackedBarcode trackedBarcode) {
    // Return null to use the default brush (or when using icon style).
    return null;
  }

  @override
  Brush? brushForRecognizedBarcodeNotInList(BarcodeCountView view, TrackedBarcode trackedBarcode) {
    return null;
  }

  @override
  void didTapRecognizedBarcode(BarcodeCountView view, TrackedBarcode trackedBarcode) {
    debugPrint('Tapped: ${trackedBarcode.barcode.data}');
  }

  @override
  void didTapRecognizedBarcodeNotInList(BarcodeCountView view, TrackedBarcode trackedBarcode) {
    // Only called when a capture list is set.
  }

  @override
  void didTapFilteredBarcode(BarcodeCountView view, TrackedBarcode filteredBarcode) {}

  @override
  void didCompleteCaptureList(BarcodeCountView view) {
    // All target barcodes have been scanned.
  }
}
```

### BarcodeCountViewListener Dart Callbacks

| Callback | Description |
|----------|-------------|
| `brushForRecognizedBarcode(view, trackedBarcode) -> Brush?` | Per-barcode brush for recognized barcodes. Returns `null` to use default. Dot style only. |
| `brushForRecognizedBarcodeNotInList(view, trackedBarcode) -> Brush?` | Per-barcode brush for not-in-list barcodes. Dot style only. Only called when a capture list is set. |
| `didTapRecognizedBarcode(view, trackedBarcode)` | Called when a recognized barcode is tapped. |
| `didTapRecognizedBarcodeNotInList(view, trackedBarcode)` | Called when a not-in-list barcode is tapped. Only when a capture list is set. |
| `didTapFilteredBarcode(view, filteredBarcode)` | Called when a filtered barcode is tapped. |
| `didCompleteCaptureList(view)` | Called when all items in the capture list have been scanned. Only when a capture list is set. |

### IBarcodeCountViewExtendedListener (Flutter ≥8.3)

Implement `IBarcodeCountViewExtendedListener` (instead of `BarcodeCountViewListener`) to also receive cluster-tap events:

```dart
class CountBloc implements IBarcodeCountViewExtendedListener {
  // ... all BarcodeCountViewListener methods plus:
  @override
  void didTapCluster(BarcodeCountView view, Cluster cluster) { ... }
}
```

`didTapCluster` is **Flutter-only** (part of `IBarcodeCountViewExtendedListener`).

## Step 8 — BarcodeCountViewUiListener

Implement `BarcodeCountViewUiListener` to receive button-tap events from the view's UI.

```dart
class CountBloc implements BarcodeCountViewUiListener {
  @override
  void didTapListButton(BarcodeCountView view) {
    // Navigate to the scanned items list.
  }

  @override
  void didTapExitButton(BarcodeCountView view) {
    // Navigate out of the scanning screen.
  }

  @override
  void didTapSingleScanButton(BarcodeCountView view) {
    // Trigger a single-item scan.
  }
}
```

### BarcodeCountViewUiListener Dart Callbacks

| Callback | Description |
|----------|-------------|
| `didTapListButton(view)` | List button tapped. Freezes the mode by default (unless `shouldShowListButton` is modified). |
| `didTapExitButton(view)` | Exit button tapped. |
| `didTapSingleScanButton(view)` | Single scan button tapped (only visible when `shouldShowSingleScanButton` is `true`). |

## Step 9 — BarcodeCountView Customization

`BarcodeCountView` exposes an extensive set of properties to tailor the UI. All are set directly on the view instance (typically via cascade in `build()` or after construction in `initState()`).

### Visibility Booleans

| Property | Default | Description |
|----------|---------|-------------|
| `shouldShowUserGuidanceView` | `true` | Show the user guidance / loading view. |
| `shouldShowListProgressBar` | `true` | Show the capture-list progress bar (Flutter ≥6.25). |
| `shouldShowListButton` | `true` | Show the list button (lower-left). |
| `shouldShowExitButton` | `true` | Show the exit button (lower-right). |
| `shouldShowShutterButton` | `true` | Show the centered shutter button. |
| `shouldShowHints` | `true` | Show scanning hint messages. |
| `shouldShowClearHighlightsButton` | `false` | Show the "clear highlights" button above the shutter. |
| `shouldShowSingleScanButton` | `false` | Show the single-scan button (lower-left). |
| `shouldShowStatusModeButton` | `false` | Show the status-mode toggle button (Flutter ≥7.0, beta). |
| `shouldShowFloatingShutterButton` | `false` | Show the draggable floating shutter button. |
| `shouldShowToolbar` | `true` | Show the collapsable toolbar at the top. |
| `shouldShowScanAreaGuides` | `false` | Visualize the scan area (debug only). |
| `shouldShowTorchControl` | `false` | Show the torch toggle button (Flutter ≥6.28). |
| `shouldShowStatusIconsOnScan` | `false` | Show status icons immediately on scan without activating status mode (Flutter ≥8.3, beta). |
| `shouldDisableModeOnExitButtonTapped` | `true` | Auto-disable mode when exit button is tapped (Flutter ≥8.3). |

```dart
BarcodeCountView.forContextWithModeAndStyle(ctx, mode, BarcodeCountViewStyle.icon)
  ..shouldShowToolbar = false
  ..shouldShowExitButton = false
  ..shouldShowClearHighlightsButton = true
  ..shouldShowFloatingShutterButton = true
```

### Brushes (Dot style only)

Brushes control the highlight color for barcodes in the dot style. They have no effect in icon style.

**Static defaults** (read the defaults for reference):
```dart
final defaultRecognized = BarcodeCountView.defaultRecognizedBrush;
final defaultNotInList  = BarcodeCountView.defaultNotInListBrush;
final defaultAccepted   = BarcodeCountView.defaultAcceptedBrush;   // Flutter ≥8.3
final defaultRejected   = BarcodeCountView.defaultRejectedBrush;   // Flutter ≥8.3
```

**Instance brush properties** (override the default for all barcodes of a category):
```dart
view
  ..recognizedBrush = Brush(
      const Color(0x6600FF00), const Color(0xFF00FF00), 1.0)
  ..notInListBrush = Brush(
      const Color(0x66FF0000), const Color(0xFFFF0000), 1.0)
  ..acceptedBrush = Brush(                              // Flutter ≥8.3
      const Color(0x660000FF), const Color(0xFF0000FF), 1.0)
  ..rejectedBrush = Brush(                              // Flutter ≥8.3
      const Color(0x66FF8800), const Color(0xFFFF8800), 1.0);
```

Setting any brush property to `null` hides all barcodes in that category.

**Per-barcode brush methods** (override for an individual barcode, called from `BarcodeCountViewListener`):
```dart
// Inside didTapRecognizedBarcode or a custom flow — Flutter ≥8.3:
await view.setBrushForRecognizedBarcode(trackedBarcode, myBrush);
await view.setBrushForRecognizedBarcodeNotInList(trackedBarcode, myBrush);
await view.setBrushForAcceptedBarcode(trackedBarcode, myBrush);    // Flutter ≥8.3
await view.setBrushForRejectedBarcode(trackedBarcode, myBrush);    // Flutter ≥8.3
```

### Customizable Text

| Property | Description |
|----------|-------------|
| `exitButtonText` | Text of the exit button label. |
| `clearHighlightsButtonText` | Text of the "clear highlights" button. |

### Hint Text Setters

All `textFor*Hint` properties are available on Flutter (exact version varies per property):

| Property | Description |
|----------|-------------|
| `textForTapShutterToScanHint` | Hint prompting the user to tap the shutter. |
| `textForScanningHint` | Hint shown while scanning is in progress. |
| `textForMoveCloserAndRescanHint` | Hint shown when the camera is too far. |
| `textForMoveFurtherAndRescanHint` | Hint shown when the camera is too close. |
| `textForBarcodesNotInListDetectedHint` | Hint shown when a not-in-list barcode is detected (Flutter ≥8.3). |
| `textForScreenCleanedUpHint` | Hint shown when the screen is cleaned (Flutter ≥8.3). |
| `textForTapToUncountHint` | Hint shown when the user deselects an item (Flutter ≥7.0). |
| `textForClusteringGestureHint` | Hint shown for cluster gestures (Flutter ≥8.3). |

```dart
view
  ..textForTapShutterToScanHint = 'Tap to scan'
  ..textForScanningHint = 'Scanning…'
  ..textForMoveCloserAndRescanHint = 'Move closer and scan again'
  ..textForMoveFurtherAndRescanHint = 'Move further and scan again'
  ..textForTapToUncountHint = 'Tap to remove';
```

### Accessibility (label and hint pairs)

The following accessibility string properties are available on Flutter. Properties marked "(iOS only)" have effect only on iOS; "(Android only)" only on Android.

| Property | Platform | Description |
|----------|----------|-------------|
| `listButtonAccessibilityLabel` | iOS only | Accessibility label for the list button. |
| `listButtonAccessibilityHint` | iOS only | Accessibility hint for the list button. |
| `listButtonContentDescription` | Android only | Content description for the list button. |
| `exitButtonAccessibilityLabel` | iOS only | Accessibility label for the exit button. |
| `exitButtonAccessibilityHint` | iOS only | Accessibility hint for the exit button. |
| `exitButtonContentDescription` | Android only | Content description for the exit button. |
| `shutterButtonAccessibilityLabel` | iOS only | Accessibility label for the shutter button. |
| `shutterButtonAccessibilityHint` | iOS only | Accessibility hint for the shutter button. |
| `shutterButtonContentDescription` | Android only | Content description for the shutter button. |
| `floatingShutterButtonAccessibilityLabel` | iOS only | Accessibility label for the floating shutter button. |
| `floatingShutterButtonAccessibilityHint` | iOS only | Accessibility hint for the floating shutter button. |
| `floatingShutterButtonContentDescription` | Android only | Content description for the floating shutter button. |
| `singleScanButtonAccessibilityLabel` | iOS only | Accessibility label for the single scan button. |
| `singleScanButtonAccessibilityHint` | iOS only | Accessibility hint for the single scan button. |
| `singleScanButtonContentDescription` | Android only | Content description for the single scan button. |
| `clearHighlightsButtonAccessibilityLabel` | iOS only | Accessibility label for the clear highlights button. |
| `clearHighlightsButtonAccessibilityHint` | iOS only | Accessibility hint for the clear highlights button. |
| `clearHighlightsButtonContentDescription` | Android only | Content description for the clear highlights button. |
| `statusModeButtonAccessibilityLabel` | iOS only | Accessibility label for the status mode button (Flutter ≥8.3). |
| `statusModeButtonAccessibilityHint` | iOS only | Accessibility hint for the status mode button (Flutter ≥8.3). |
| `statusModeButtonContentDescription` | Android only | Content description for the status mode button (Flutter ≥8.3). |

### Hardware Trigger (enterprise devices)

For enterprise scanners (e.g. Zebra XCover) with a physical scan button:

```dart
// Android: enable the hardware trigger (pass null to use the default key):
await view.enableHardwareTrigger(null);

// iOS: enable hardware trigger via the volume button:
view.hardwareTriggerEnabled = true;   // Flutter ≥8.3

// Check support at runtime (Android only):
if (BarcodeCountView.hardwareTriggerSupported) {  // Flutter ≥8.3
  await view.enableHardwareTrigger(null);
}
```

`enableHardwareTrigger(keyCode)` — Flutter ≥8.3. On Android, pass `null` to use the default key (dedicated HW key on XCover, or volume-down on others; requires API ≥28). On iOS, `hardwareTriggerEnabled = true` reacts to the volume button.

### Tap-to-Uncount

```dart
view.tapToUncountEnabled = true;  // Flutter ≥7.0, default false
view.textForTapToUncountHint = 'Tap to remove';
```

Allows users to deselect a scanned barcode by tapping on its highlight.

### Torch Control

```dart
view
  ..shouldShowTorchControl = true    // Flutter ≥6.28, default false
  ..torchControlPosition = Anchor.topLeft;  // topLeft, topRight, bottomLeft, bottomRight
```

### Not-in-List Action Settings (Flutter ≥8.3, beta)

When scanning against a capture list, optionally show an accept/reject popup for barcodes not in the list:

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_count.dart';

final notInListSettings = BarcodeCountNotInListActionSettings()
  ..enabled = true
  ..acceptButtonText = 'Accept'
  ..rejectButtonText = 'Reject'
  ..cancelButtonText = 'Cancel'
  ..barcodeAcceptedHint = 'Barcode accepted'
  ..barcodeRejectedHint = 'Barcode rejected';

view.barcodeNotInListActionSettings = notInListSettings;
```

### Filter Highlight Settings (view-level)

This is the **view-level** highlight appearance for filtered barcodes — not the mode-level exclusion filter. To exclude barcodes from counting by symbology or regex, set `BarcodeCountSettings.filterSettings` instead (see Step 3, "Filtering").

```dart
// view.filterSettings accepts a BarcodeFilterHighlightSettings instance.
// See the BarcodeFilterHighlightSettings API for details.
view.filterSettings = myFilterHighlightSettings;
```

### View-level Methods

| Method | Description |
|--------|-------------|
| `view.clearHighlights()` | Clear all highlight overlays (returns `Future<void>`). |
| `view.setToolbarSettings(settings)` | Configure toolbar text and accessibility strings (returns `Future<void>`). |
| `view.setStatusProvider(provider)` | Attach a `BarcodeCountStatusProvider` for status mode (returns `Future<void>`). Flutter ≥7.0. |

### Listeners

| Property | Type | Description |
|----------|------|-------------|
| `view.listener` | `BarcodeCountViewListener?` | Brush and tap callbacks per tracked barcode. |
| `view.uiListener` | `BarcodeCountViewUiListener?` | Button tap callbacks (list, exit, single-scan). |

## Step 10 — Scanning Against a Target List (End-to-End Recipe)

> **Critical**: Do **not** compare scanned data against a plain `List<String>` or `Set<String>`. `BarcodeCountCaptureList` is the only correct way to obtain `session.correctBarcodes`, `session.wrongBarcodes`, and `session.missingBarcodes`. Without it, the SDK has no knowledge of expected quantities, and those session properties will be empty.

`BarcodeCountCaptureList` enables scanning against a fixed set of expected barcodes (quantity-aware). The view automatically shows a progress bar and highlights barcodes not in the list differently from matched ones.

### 10.1 — Modeling the Target List

Target barcodes typically come from a JSON API or a local repository as a list of pick-list entries. Model each entry as a simple data class:

```dart
/// A single line from a pick-list / purchase order.
class PicklistItem {
  final String data;       // barcode content (e.g. "3614274083034")
  final Symbology symbology; // must match an enabled symbology in BarcodeCountSettings
  final int quantity;      // expected scan count — must be >= 1

  const PicklistItem({
    required this.data,
    required this.symbology,
    required this.quantity,
  });

  /// Parse from JSON returned by a warehouse/ERP API.
  factory PicklistItem.fromJson(Map<String, dynamic> json) {
    return PicklistItem(
      data: json['barcode'] as String,
      // JSON uses 'code128'; Dart enum is lowerCamelCase: Symbology.code128
      symbology: _symbologyFromString(json['symbology'] as String),
      quantity: (json['quantity'] as num).toInt(),
    );
  }
}

// Example helper — extend as needed for your symbology set.
Symbology _symbologyFromString(String s) {
  switch (s) {
    case 'ean13Upca': return Symbology.ean13Upca;
    case 'code128':   return Symbology.code128;
    case 'code39':    return Symbology.code39;
    case 'upce':      return Symbology.upce;
    case 'ean8':      return Symbology.ean8;
    default: throw ArgumentError('Unknown symbology: $s');
  }
}
```

Convert `PicklistItem` objects into `TargetBarcode` instances and bundle them into a `BarcodeCountCaptureList`:

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_count.dart';

/// Converts a list of PicklistItems to a BarcodeCountCaptureList wired to [listener].
BarcodeCountCaptureList buildCaptureList(
  List<PicklistItem> items,
  BarcodeCountCaptureListListener listener,
) {
  // TargetBarcode.create(data, quantity) — quantity must be >= 1.
  final targetBarcodes = items
      .map((item) => TargetBarcode.create(item.data, item.quantity))
      .toList();

  // BarcodeCountCaptureList.create(listener, targetBarcodes)
  return BarcodeCountCaptureList.create(listener, targetBarcodes);
}
```

> **Note**: `TargetBarcode` matches barcodes by data string only — it is symbology-agnostic. Make sure every symbology present in the list is enabled in `BarcodeCountSettings` via `enableSymbology` or `enableSymbologies`. If a symbology is not enabled it will never be scanned, so those items will always appear in `missingBarcodes`.

### 10.2 — Wiring the List to the Mode

Call `setBarcodeCountCaptureList` on `BarcodeCount` **after** constructing the mode and before the first scan. This is an async call; await it so the list is set before any frames are processed.

```dart
// In CountBloc constructor or an async initializer:

BarcodeCountCaptureList? _captureList;

Future<void> loadPicklist(List<PicklistItem> items) async {
  _captureList = buildCaptureList(items, this); // 'this' implements the listener
  // IMPORTANT: without this call, scans are never validated against the list
  // and correctBarcodes / wrongBarcodes / missingBarcodes will be empty.
  await barcodeCount.setBarcodeCountCaptureList(_captureList!);
}
```

> **Callout**: `setBarcodeCountCaptureList` must be called before any scan. Calling it after the first `didScan` is possible (to swap lists mid-session) but the results screen will reflect only the new list from that point onward.

### 10.3 — Brushes for Matched / Not-In-List / Accepted (Dot Style Only)

> **Important**: Brush properties have effect **only in the dot style** (`BarcodeCountViewStyle.dot`). In icon style (`BarcodeCountViewStyle.icon`) the SDK draws its own icons and ignores all brush settings. If you use icon style, skip this section.

Set instance brush properties on the `BarcodeCountView` to make the three scan states visually distinct:

```dart
// Inside build() using the cascade operator, or after construction in initState().
// Use BarcodeCountViewStyle.dot for brush properties to take effect.
BarcodeCountView.forContextWithModeAndStyle(
  _bloc.dataCaptureContext,
  _bloc.barcodeCount,
  BarcodeCountViewStyle.dot,   // brushes have no effect in icon style
)
  ..uiListener = _bloc
  ..listener = _bloc
  // Green fill + stroke — barcode matched the target list (correctBarcodes).
  ..recognizedBrush = Brush(
      const Color(0x6600CC44), const Color(0xFF00CC44), 1.0)
  // Red fill + stroke — barcode scanned but NOT in the list (wrongBarcodes).
  ..notInListBrush = Brush(
      const Color(0x66FF2D2D), const Color(0xFFFF2D2D), 1.0)
  // White fill + stroke — recognized but not yet matched (default appearance).
  ..recognizedBrush = Brush(
      const Color(0x66FFFFFF), const Color(0xFFFFFFFF), 1.0)
  // Show the built-in progress bar for list completion.
  ..shouldShowListProgressBar = true;
```

Per-barcode brushes (from `BarcodeCountViewListener`) follow the same dot-style restriction:

```dart
@override
Brush? brushForRecognizedBarcode(BarcodeCountView view, TrackedBarcode trackedBarcode) {
  // Dot style only. Return null to fall back to view.recognizedBrush.
  return null;
}

@override
Brush? brushForRecognizedBarcodeNotInList(BarcodeCountView view, TrackedBarcode trackedBarcode) {
  // Dot style only. Return null to fall back to view.notInListBrush.
  return null;
}
```

### 10.4 — Implementing BarcodeCountCaptureListListener

Implement `BarcodeCountCaptureListListener` to receive list-level session updates. This fires **alongside** (not instead of) `BarcodeCountListener.didScan` — both listeners can coexist on the same BLoC.

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_count.dart';

class CountBloc
    implements
        BarcodeCountListener,
        BarcodeCountViewListener,
        BarcodeCountViewUiListener,
        BarcodeCountCaptureListListener {

  // --- BarcodeCountCaptureListListener ---

  /// Called after each frame is processed and the list state is updated.
  /// :available: flutter=6.17
  @override
  void didUpdateSession(
    BarcodeCountCaptureList barcodeCountCaptureList,
    BarcodeCountCaptureListSession session,
  ) {
    // session.correctBarcodes  — List<TrackedBarcode> matched to the target list
    // session.wrongBarcodes    — List<TrackedBarcode> scanned but NOT in the list
    // session.missingBarcodes  — List<TargetBarcode> not yet scanned
    final matched  = session.correctBarcodes.length;
    final wrong    = session.wrongBarcodes.length;
    final missing  = session.missingBarcodes.length;
    final total    = matched + missing; // total expected unique target lines
    debugPrint('$matched/$total matched, $wrong extras');

    // Emit a BLoC event so the UI can react (see §10.5 for the full event/state pair).
    _progressController.add(
      ScanProgressState(
        matched: matched,
        total: total,
        extras: wrong,
        missingBarcodes: List.unmodifiable(session.missingBarcodes),
      ),
    );
  }
}
```

To also receive a callback when **all** list items are scanned, implement `BarcodeCountCaptureListExtendedListener` (Flutter ≥8.3) instead of the base listener:

```dart
/// Flutter ≥8.3 — extends BarcodeCountCaptureListListener.
class CountBloc extends ... implements BarcodeCountCaptureListExtendedListener {

  @override
  void didUpdateSession(
    BarcodeCountCaptureList barcodeCountCaptureList,
    BarcodeCountCaptureListSession session,
  ) {
    // same as above
  }

  /// Called once every item in the target list has been correctly scanned.
  /// :available: flutter=8.3
  @override
  void didCompleteCaptureList(
    BarcodeCountCaptureList barcodeCountCaptureList,
    BarcodeCountCaptureListSession session,
  ) {
    // Navigate to results automatically, or show a completion banner.
    _progressController.add(ScanProgressState.completed());
  }
}
```

### BarcodeCountCaptureListSession Properties

| Property | Type | Available | Description |
|----------|------|-----------|-------------|
| `correctBarcodes` | `List<TrackedBarcode>` | flutter=6.17 | Tracked barcodes matched to the target list. |
| `wrongBarcodes` | `List<TrackedBarcode>` | flutter=6.17 | Scanned barcodes that are **not** in the list. |
| `missingBarcodes` | `List<TargetBarcode>` | flutter=6.17 | Target barcodes not yet scanned. |
| `additionalBarcodes` | `List<Barcode>` | flutter=6.17 | Barcodes injected via `setAdditionalBarcodes`. |
| `acceptedBarcodes` | `List<TrackedBarcode>` | flutter=8.3 | Barcodes marked as accepted (not-in-list action). |
| `rejectedBarcodes` | `List<TrackedBarcode>` | flutter=8.3 | Barcodes marked as rejected (not-in-list action). |

### 10.5 — Progress UI with BLoC Events

Define a `ScanProgressState` event/state to carry progress data to the scanning UI:

```dart
// --- BLoC event/state ---

class ScanProgressState {
  final int matched;      // count of correctly scanned target lines
  final int total;        // total unique target lines in the list
  final int extras;       // count of wrongBarcodes (not in list)
  final List<TargetBarcode> missingBarcodes;
  final bool completed;

  const ScanProgressState({
    required this.matched,
    required this.total,
    required this.extras,
    required this.missingBarcodes,
    this.completed = false,
  });

  const ScanProgressState.completed()
      : matched = 0, total = 0, extras = 0,
        missingBarcodes = const [], completed = true;

  String get progressSummary =>
      '$matched of $total items scanned'
      '${extras > 0 ? ', $extras unexpected' : ''}';
}
```

In the BLoC, expose a stream so widgets can rebuild on each update:

```dart
class CountBloc implements BarcodeCountCaptureListListener, ... {
  final _progressController =
      StreamController<ScanProgressState>.broadcast();

  Stream<ScanProgressState> get progress => _progressController.stream;

  // ...

  @override
  void didUpdateSession(
    BarcodeCountCaptureList list,
    BarcodeCountCaptureListSession session,
  ) {
    final matched = session.correctBarcodes.length;
    final missing = session.missingBarcodes.length;
    _progressController.add(ScanProgressState(
      matched: matched,
      total: matched + missing,
      extras: session.wrongBarcodes.length,
      missingBarcodes: List.unmodifiable(session.missingBarcodes),
    ));
  }

  void dispose() {
    _progressController.close();
    // ...
  }
}
```

In the scanning screen, subscribe to the progress stream and overlay a banner above `BarcodeCountView`:

```dart
// count_screen.dart — add a progress overlay above the camera view.
@override
Widget build(BuildContext context) {
  return Scaffold(
    backgroundColor: Colors.black,
    body: SafeArea(
      bottom: false,
      child: Stack(
        children: [
          // Full-screen camera + scanning view.
          BarcodeCountView.forContextWithModeAndStyle(
            _bloc.dataCaptureContext,
            _bloc.barcodeCount,
            BarcodeCountViewStyle.dot, // use dot for brush colours
          )
            ..uiListener = _bloc
            ..listener = _bloc
            ..recognizedBrush = Brush(const Color(0x6600CC44), const Color(0xFF00CC44), 1.0)
            ..notInListBrush  = Brush(const Color(0x66FF2D2D), const Color(0xFFFF2D2D), 1.0)
            ..shouldShowListProgressBar = true,

          // Progress banner driven by the BLoC stream.
          Positioned(
            top: 8, left: 16, right: 16,
            child: StreamBuilder<ScanProgressState>(
              stream: _bloc.progress,
              builder: (context, snapshot) {
                if (!snapshot.hasData) return const SizedBox.shrink();
                final state = snapshot.data!;
                return Material(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(8),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    child: Text(
                      state.progressSummary,
                      style: const TextStyle(color: Colors.white, fontSize: 14),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    ),
  );
}
```

> `shouldShowListProgressBar = true` (default) activates the SDK's built-in progress bar inside `BarcodeCountView` — no extra code needed for that widget. The `StreamBuilder` overlay above adds a text summary on top for extra clarity.

### 10.6 — Results Screen

After scanning, navigate to a results screen that shows three sections: matched items, missing items (targets never scanned), and unexpected items (not in list).

```dart
// --- BLoC-driven results derivation ---

class ScanResultArgs {
  final List<TargetBarcode> targetList;        // the original pick-list items
  final List<TrackedBarcode> correctBarcodes;  // session.correctBarcodes
  final List<TrackedBarcode> wrongBarcodes;    // session.wrongBarcodes
  final List<TargetBarcode> missingBarcodes;   // session.missingBarcodes

  const ScanResultArgs({
    required this.targetList,
    required this.correctBarcodes,
    required this.wrongBarcodes,
    required this.missingBarcodes,
  });
}
```

Expose an accessor on the BLoC that packages the last known session state for navigation:

```dart
// In CountBloc — store the last session snapshot.
BarcodeCountCaptureListSession? _lastListSession;

@override
void didUpdateSession(
  BarcodeCountCaptureList list,
  BarcodeCountCaptureListSession session,
) {
  _lastListSession = session;
  // ... emit progress state as before
}

ScanResultArgs get resultArgs {
  final s = _lastListSession;
  return ScanResultArgs(
    targetList: _currentPicklist.map((i) => TargetBarcode.create(i.data, i.quantity)).toList(),
    correctBarcodes: s?.correctBarcodes ?? [],
    wrongBarcodes:   s?.wrongBarcodes   ?? [],
    missingBarcodes: s?.missingBarcodes ?? [],
  );
}
```

The results `StatefulWidget`:

```dart
class ResultsPage extends StatelessWidget {
  final ScanResultArgs args;
  const ResultsPage({super.key, required this.args});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan Results')),
      body: ListView(
        children: [
          // --- Section 1: Matched (targets scanned correctly) ---
          _sectionHeader(
            context,
            'Matched (${args.correctBarcodes.length})',
            color: Colors.green,
          ),
          for (final tb in args.correctBarcodes)
            ListTile(
              leading: const Icon(Icons.check_circle, color: Colors.green),
              title: Text(tb.barcode.data ?? ''),
              subtitle: Text(tb.barcode.symbology.toString()),
            ),

          // --- Section 2: Missing (targets not yet scanned) ---
          _sectionHeader(
            context,
            'Missing (${args.missingBarcodes.length})',
            color: Colors.orange,
          ),
          for (final target in args.missingBarcodes)
            ListTile(
              leading: const Icon(Icons.radio_button_unchecked, color: Colors.orange),
              title: Text(target.data),
              subtitle: Text('Expected qty: ${target.quantity}'),
            ),

          // --- Section 3: Unexpected (scanned but not in list) ---
          _sectionHeader(
            context,
            'Unexpected (${args.wrongBarcodes.length})',
            color: Colors.red,
          ),
          for (final tb in args.wrongBarcodes)
            ListTile(
              leading: const Icon(Icons.warning_amber, color: Colors.red),
              title: Text(tb.barcode.data ?? ''),
              subtitle: Text(tb.barcode.symbology.toString()),
            ),
        ],
      ),
    );
  }

  Widget _sectionHeader(BuildContext context, String title, {required Color color}) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
      child: Text(
        title,
        style: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.bold,
          color: color,
        ),
      ),
    );
  }
}
```

Navigate to it from the BLoC's `didTapListButton` or `didTapExitButton`:

```dart
@override
void didTapListButton(BarcodeCountView view) {
  barcodeCount.removeListener(this);
  Navigator.of(_context).push(
    MaterialPageRoute(builder: (_) => ResultsPage(args: resultArgs)),
  );
}
```

### 10.7 — Exit / Re-entry Behavior

The capture list persists across `prepareScanning` calls and survives background/foreground transitions. To **swap** the list for a new order mid-session:

```dart
Future<void> switchToNewOrder(List<PicklistItem> newItems) async {
  final newList = buildCaptureList(newItems, this);
  // Swap the list — in-flight barcodes from the previous list are discarded.
  await barcodeCount.setBarcodeCountCaptureList(newList);
  // Clear visual highlights from the previous session.
  // view.clearHighlights() must be called on the BarcodeCountView instance.
  await _barcodeCountView?.clearHighlights();
  // Reset the mode's internal barcode history.
  await barcodeCount.clearAdditionalBarcodes();
  await barcodeCount.reset();
}
```

> If `clearHighlights()` is not called, old green/red dot overlays from the previous list remain on screen until the next frame is processed.

### 10.8 — Common Pitfalls

- **Do NOT compare scanned data against a `List<String>` or `Set<String>`.** `BarcodeCountCaptureList` is the only way to get `session.correctBarcodes`, `session.wrongBarcodes`, and `session.missingBarcodes`. A plain Dart collection cannot drive the SDK's validated matching or list-progress UI.
- **`TargetBarcode.create(data, quantity)` — quantity must be ≥ 1.** A quantity of `0` causes undefined behavior; validate before constructing.
- **List items are symbology-agnostic at the API level**, but the barcode must be enabled in `BarcodeCountSettings`. If a symbology is not enabled, those barcodes will never be scanned and will always appear in `missingBarcodes`.
- **`BarcodeCountCaptureListListener.didUpdateSession` fires alongside `BarcodeCountListener.didScan`**, not instead of it. Both listeners can coexist on the same BLoC — `didScan` fires once per shutter press, `didUpdateSession` fires on every frame update.
- **Symbology values in Dart are lowerCamelCase**: `Symbology.code128`, `Symbology.ean13Upca`, `Symbology.code39` — never `Symbology.Code128` or `Symbology.EAN13_UPCA`.
- **Brushes are dot-style only**: `recognizedBrush`, `notInListBrush`, `brushForRecognizedBarcode`, and `brushForRecognizedBarcodeNotInList` have no visual effect in `BarcodeCountViewStyle.icon`.

## Step 11 — Status Provider (Flutter ≥7.0, beta)

`BarcodeCountStatusProvider` allows assigning a status icon to each scanned barcode (e.g. "in stock", "needs recount"). Activated via the status mode button (or `shouldShowStatusIconsOnScan`).

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_count.dart';

class MyStatusProvider implements BarcodeCountStatusProvider {
  @override
  void onStatusRequested(
    List<TrackedBarcode> barcodes,
    BarcodeCountStatusProviderCallback providerCallback,
  ) {
    // Build a list of BarcodeCountStatusItem for each barcode and call the callback.
    // Choose a BarcodeCountStatus value for each barcode (see enum table below).
    providerCallback.onStatusReady(statusItems);
  }
}

// Attach to the view:
await view.setStatusProvider(MyStatusProvider());
view.shouldShowStatusModeButton = true;
```

### BarcodeCountStatus Enum Values (Flutter ≥7.0)

All values are available on Flutter from SDK 7.0 unless noted otherwise. Use Dart lowerCamelCase form when constructing a `BarcodeCountStatusItem`.

| Value | Description |
|-------|-------------|
| `BarcodeCountStatus.none` | No status — barcode has not been assigned any status icon. |
| `BarcodeCountStatus.notAvailable` | Error retrieving the status — the backend could not provide a result. |
| `BarcodeCountStatus.expired` | The item is expired. |
| `BarcodeCountStatus.fragile` | The item must be handled with care (fragile). |
| `BarcodeCountStatus.qualityCheck` | The item requires a quality check before acceptance. |
| `BarcodeCountStatus.lowStock` | Stock level for this item is low. |
| `BarcodeCountStatus.wrong` | The item is incorrect (e.g. wrong SKU or wrong location). |
| `BarcodeCountStatus.expiringSoon` | The item will expire soon (Flutter ≥7.0, Android/iOS ≥7.0). |

> **Note**: `BarcodeCountStatus` is a true enum. There are no `accept` / `reject` values in the Flutter SDK enum. If you need to distinguish accepted vs. rejected barcodes visually, use `BarcodeCountStatus.none` for accepted items (no icon shown) and a meaningful value such as `BarcodeCountStatus.wrong` or `BarcodeCountStatus.notAvailable` for rejected items, combined with the `acceptedBrush` / `rejectedBrush` view properties.

## Step 12 — Feedback

`BarcodeCountFeedback` controls sound and vibration on scan events.

```dart
// Use the default feedback (sound + vibration for success and failure):
barcodeCount.feedback = BarcodeCountFeedback.defaultFeedback;

// Disable all feedback:
barcodeCount.feedback = BarcodeCountFeedback();

// Custom: keep success vibration, disable success sound:
final feedback = BarcodeCountFeedback()
  ..success = Feedback(vibration: Vibration.defaultVibration, sound: null)
  ..failure = Feedback(vibration: null, sound: null);
barcodeCount.feedback = feedback;
```

### BarcodeCountFeedback Properties

| Property | Type | Description |
|----------|------|-------------|
| `success` | `Feedback` | Feedback for a successful scan event. |
| `failure` | `Feedback` | Feedback for a failure event. |
| `BarcodeCountFeedback.defaultFeedback` | static | Default config: both sound and vibration for success and failure. |

## Step 13 — Camera lifecycle

Camera state is managed via `Camera.switchToDesiredState`. Pause when the app goes to background; resume on foreground.

```dart
class _CountScreenState extends State<CountScreen> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _bloc.didResume(); // request camera permission + enable mode
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        _bloc.didResume();
        break;
      default:
        _bloc.didPause();
        break;
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _bloc.dispose();
    super.dispose();
  }
}
```

In the BLoC:
```dart
void didResume() {
  barcodeCount.addListener(this);
  barcodeCount.isEnabled = true;
  Permission.camera.request().then((status) {
    if (status.isGranted) resumeFrameSource();
  });
}

void didPause() {
  pauseFrameSource();
  barcodeCount.removeListener(this);
}

void pauseFrameSource() => camera?.switchToDesiredState(FrameSourceState.off);
void resumeFrameSource() => camera?.switchToDesiredState(FrameSourceState.on);
```

## Step 14 — Toolbar Settings

`BarcodeCountToolbarSettings` configures the text of the collapsable toolbar buttons.

```dart
final toolbarSettings = BarcodeCountToolbarSettings()
  ..audioOnButtonText = 'Sound On'
  ..audioOffButtonText = 'Sound Off'
  ..vibrationOnButtonText = 'Vibration On'
  ..vibrationOffButtonText = 'Vibration Off';
await view.setToolbarSettings(toolbarSettings);
```

Key properties: `audioOnButtonText`, `audioOffButtonText`, `vibrationOnButtonText`, `vibrationOffButtonText`, `strapModeOnButtonText`, `strapModeOffButtonText`, `colorSchemeOnButtonText`, `colorSchemeOffButtonText`. Each has iOS (`*AccessibilityLabel`, `*AccessibilityHint`) and Android (`*ContentDescription`) accessibility variants.

## Step 15 — Complete Example

### main.dart

```dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ScanditFlutterDataCaptureBarcode.initialize();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'MatrixScan Count',
    home: CountScreen(),
  );
}
```

### count_bloc.dart

```dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_count.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

class CountBloc
    implements BarcodeCountListener, BarcodeCountViewListener, BarcodeCountViewUiListener {
  late final DataCaptureContext dataCaptureContext;
  late final BarcodeCount barcodeCount;
  Camera? _camera;

  final List<Barcode> scannedBarcodes = [];
  final _controller = StreamController<List<Barcode>>.broadcast();
  Stream<List<Barcode>> get scanned => _controller.stream;

  CountBloc() {
    dataCaptureContext = DataCaptureContext.forLicenseKey(licenseKey);
    _camera = Camera.defaultCamera;
    _camera?.applySettings(BarcodeCount.createRecommendedCameraSettings());
    if (_camera != null) dataCaptureContext.setFrameSource(_camera!);

    final settings = BarcodeCountSettings()
      ..enableSymbologies({
        Symbology.ean13Upca,
        Symbology.ean8,
        Symbology.code128,
      });

    barcodeCount = BarcodeCount(settings);
    dataCaptureContext.setMode(barcodeCount);
  }

  void didResume() {
    barcodeCount.addListener(this);
    barcodeCount.isEnabled = true;
    Permission.camera.request().then((status) {
      if (status.isGranted) _camera?.switchToDesiredState(FrameSourceState.on);
    });
  }

  void didPause() {
    _camera?.switchToDesiredState(FrameSourceState.off);
    barcodeCount.removeListener(this);
  }

  @override
  Future<void> didScan(BarcodeCount barcodeCount, BarcodeCountSession session,
      Future<FrameData> Function() getFrameData) async {
    scannedBarcodes.addAll(session.recognizedBarcodes);
    _controller.add(List.unmodifiable(scannedBarcodes));
  }

  @override
  Brush? brushForRecognizedBarcode(BarcodeCountView view, TrackedBarcode trackedBarcode) => null;

  @override
  Brush? brushForRecognizedBarcodeNotInList(BarcodeCountView view, TrackedBarcode trackedBarcode) => null;

  @override
  void didTapRecognizedBarcode(BarcodeCountView view, TrackedBarcode trackedBarcode) {}

  @override
  void didTapRecognizedBarcodeNotInList(BarcodeCountView view, TrackedBarcode trackedBarcode) {}

  @override
  void didTapFilteredBarcode(BarcodeCountView view, TrackedBarcode filteredBarcode) {}

  @override
  void didCompleteCaptureList(BarcodeCountView view) {}

  @override
  void didTapListButton(BarcodeCountView view) {}

  @override
  void didTapExitButton(BarcodeCountView view) {}

  @override
  void didTapSingleScanButton(BarcodeCountView view) {}

  Future<void> resetSession() async {
    scannedBarcodes.clear();
    await barcodeCount.clearAdditionalBarcodes();
    await barcodeCount.reset();
  }

  void dispose() {
    _camera?.switchToDesiredState(FrameSourceState.off);
    barcodeCount.removeListener(this);
    dataCaptureContext.removeAllModes();
    _controller.close();
  }
}
```

### count_screen.dart

```dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_count.dart';
import 'count_bloc.dart';

class CountScreen extends StatefulWidget {
  @override
  State<CountScreen> createState() => _CountScreenState();
}

class _CountScreenState extends State<CountScreen> with WidgetsBindingObserver {
  late final CountBloc _bloc;

  @override
  void initState() {
    super.initState();
    _bloc = CountBloc();
    WidgetsBinding.instance.addObserver(this);
    _bloc.didResume();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        bottom: false,
        child: BarcodeCountView.forContextWithModeAndStyle(
          _bloc.dataCaptureContext,
          _bloc.barcodeCount,
          BarcodeCountViewStyle.icon,
        )
          ..uiListener = _bloc
          ..listener = _bloc,
      ),
    );
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        _bloc.didResume();
        break;
      default:
        _bloc.didPause();
        break;
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _bloc.dispose();
    super.dispose();
  }
}
```

## Key Rules

1. **Initialize plugins first** — `await ScanditFlutterDataCaptureBarcode.initialize()` must be in `main()` after `WidgetsFlutterBinding.ensureInitialized()` and before `runApp(...)`.
2. **Import** — BarcodeCount classes live in `scandit_flutter_datacapture_barcode_count`. Always import this alongside `scandit_flutter_datacapture_barcode`.
3. **Constructor version** — Use `BarcodeCount(settings)` on Flutter ≥7.6, then call `dataCaptureContext.setMode(barcodeCount)` explicitly. On older SDKs, use `BarcodeCount.forDataCaptureContext(context, settings)` and await the Future.
4. **Present full screen** — `BarcodeCountView` must be full screen per SDK documentation. The sample uses `AspectRatio(9/16)` in portrait / `AspectRatio(16/9)` in landscape.
5. **BLoC owns listeners** — The BLoC implements `BarcodeCountListener`, `BarcodeCountViewListener`, and `BarcodeCountViewUiListener`. Wire them via `..listener = _bloc ..uiListener = _bloc` on the view.
6. **Brush properties are dot-style only** — `recognizedBrush`, `notInListBrush`, `acceptedBrush`, `rejectedBrush`, `setBrushFor*` methods, and `brushFor*` listener callbacks have no effect in icon style.
7. **Symbologies** — use lowerCamelCase: `Symbology.ean13Upca`, `Symbology.code128`, etc.
8. **Session access** — Access `BarcodeCountSession` only inside `didScan`. Do not keep a reference to the session beyond the callback.
9. **Camera permission** — iOS needs `NSCameraUsageDescription` in `Info.plist`. Android runtime permission via `permission_handler`. Re-request on `AppLifecycleState.resumed`.
10. **Beta APIs** — Status mode, mapping flow, not-in-list action settings, and clustering are marked beta and may change in future SDK versions.
