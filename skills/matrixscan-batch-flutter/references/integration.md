# MatrixScan Batch Flutter Integration Guide

MatrixScan Batch (API name: `BarcodeBatch*`) is a multi-barcode tracking mode that continuously tracks all barcodes visible in the camera feed simultaneously, reporting additions, updates, and removals on every frame. In Flutter it renders through a `DataCaptureView` with one or more overlays attached — `BarcodeBatchBasicOverlay` for per-barcode highlight frames or dots, and `BarcodeBatchAdvancedOverlay` for fully custom AR widget annotations anchored to each barcode.

> **State management note**: Examples below use `StatefulWidget` with `WidgetsBindingObserver`, matching the official `MatrixScanSimpleSample` and `MatrixScanBubblesSample`. The same APIs work with BLoC, Provider, Riverpod, or any other pattern — adapt ownership of `DataCaptureContext`, `BarcodeBatch`, the camera, and overlays to the project's existing convention.

> **TrackedObject (Flutter ≥7.3+)**: In SDK 7.3+, a `TrackedObject` base class was introduced that `TrackedBarcode` extends. No recipe is needed for this — the `TrackedBarcode` API you use day-to-day is unchanged.

## Prerequisites

- Scandit Flutter packages in `pubspec.yaml`:
  - `scandit_flutter_datacapture_barcode` (pulls in `scandit_flutter_datacapture_core` transitively)
  - `permission_handler` (for the runtime camera permission on Android)
- Flutter `>=3.22.0`, Dart SDK `>=3.0.0 <4.0.0`.
- After editing `pubspec.yaml`, run `flutter pub get` to fetch the packages.
- Minimum SDK version for BarcodeBatch on Flutter: **6.7**. The modern constructors (`BarcodeBatch(settings)`, `BarcodeBatchBasicOverlay(mode, style: ...)`, `BarcodeBatchAdvancedOverlay(mode)`, `BarcodeBatch.createRecommendedCameraSettings()`) require **Flutter ≥7.6**.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/Runner/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request at runtime with `permission_handler`.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that enabling only the symbologies actually needed improves scanning performance and accuracy.

Once the user responds, ask them which file they would like to integrate BarcodeBatch into (typically a `StatefulWidget` screen, or a BLoC / controller class). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `scandit_flutter_datacapture_barcode` and `permission_handler` to `pubspec.yaml`, then run `flutter pub get`.
2. Add `NSCameraUsageDescription` to `ios/Runner/Info.plist` with a short usage explanation.
3. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with the key from https://ssl.scandit.com.
4. Ensure `main()` calls `WidgetsFlutterBinding.ensureInitialized()` and then `await ScanditFlutterDataCaptureBarcode.initialize()` before `runApp(...)`.
5. Call `Permission.camera.request()` from `permission_handler` before the first scan (usually in `initState()` of the scanning screen).

## Step 1 — Initialize the SDK in `main()`

Plugin initialization **must** happen before any other Scandit API call.

```dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

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

final DataCaptureContext dataCaptureContext =
    DataCaptureContext.forLicenseKey(licenseKey);
```

## Step 3 — Configure BarcodeBatchSettings and construct BarcodeBatch

All symbologies are disabled by default. Only enable the ones the app actually needs.

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_batch.dart';

// Configure settings with the desired symbologies.
final captureSettings = BarcodeBatchSettings()
  ..enableSymbologies({
    Symbology.ean8,
    Symbology.ean13Upca,
    Symbology.upce,
    Symbology.code39,
    Symbology.code128,
  });

// Construct the mode (Flutter ≥7.6 context-free constructor).
final barcodeBatch = BarcodeBatch(captureSettings);

// Register the mode with the context.
dataCaptureContext.setMode(barcodeBatch);
```

### Camera setup

Set up the camera as the context's frame source. There are three steps: get the device camera, apply the camera settings BarcodeBatch recommends, and register the camera as the context frame source. The camera is started separately (after the permission is granted — see Step 8).

```dart
// 1. Get the default (rear) camera.
Camera? camera = Camera.defaultCamera;

// 2. Apply the recommended settings.
//    On Flutter this is a STATIC METHOD: BarcodeBatch.createRecommendedCameraSettings().
//    There is NO `recommendedCameraSettings` getter on Flutter.
final cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
camera?.applySettings(cameraSettings);

// 3. Attach the camera as the context's frame source.
if (camera != null) {
  dataCaptureContext.setFrameSource(camera);
}

// 4. Start it once the camera permission is granted (see Step 8).
camera?.switchToDesiredState(FrameSourceState.on);
```

> **Flutter gotcha**: use the static **method** `BarcodeBatch.createRecommendedCameraSettings()`. The `recommendedCameraSettings` *getter* exists on some other platforms (iOS, web, .NET) but **not** on Flutter — calling it will not compile.

### Camera setup members (from `scandit_flutter_datacapture_core`)

| Member | Description |
|--------|-------------|
| `Camera.defaultCamera` | Static getter — the default (rear) `Camera?`. May be `null` if no camera is available. |
| `camera.applySettings(CameraSettings)` | Apply camera settings (resolution, focus, etc.). |
| `dataCaptureContext.setFrameSource(FrameSource)` | Register the camera as the context's frame source. |
| `camera.switchToDesiredState(FrameSourceState)` | Turn the camera `on` / `off` / `standby`. |

### BarcodeBatchSettings Members

| Member | Description |
|--------|-------------|
| `BarcodeBatchSettings()` | Creates a new settings instance. All symbologies disabled by default. |
| `enableSymbologies(Set<Symbology>)` | Enable multiple symbologies at once. |
| `enableSymbology(Symbology, bool)` | Enable or disable a single symbology. |
| `settingsForSymbology(Symbology)` | Get per-symbology settings (e.g. `activeSymbolCounts`). Returns `SymbologySettings`. |
| `enabledSymbologies` | `Set<Symbology>` — the currently enabled symbologies (read-only). |
| `setProperty<T>(name, value)` / `getProperty<T>(name)` | Advanced hidden property access by name. |

### BarcodeBatch Members (Flutter-relevant)

| Member | Available | Description |
|--------|-----------|-------------|
| `BarcodeBatch(settings)` | flutter=7.6 | Context-free constructor. Call `setMode` after. |
| `addListener(listener)` / `removeListener(listener)` | flutter=7.0 | Register/remove a `BarcodeBatchListener`. |
| `applySettings(settings)` | flutter=7.0 | Update settings at runtime (async). |
| `isEnabled` | flutter=7.0 | `bool` — enable/disable without removing from context. |
| `reset()` | flutter=7.0 | Resets the object tracker. |
| `BarcodeBatch.createRecommendedCameraSettings()` | flutter=7.6 | Returns `CameraSettings` optimized for BarcodeBatch. |

## Step 4 — Receive tracked barcodes via BarcodeBatchListener

`BarcodeBatchListener.didUpdateSession` is called after every frame where the tracked barcode state changes. The session provides the full current state plus per-frame deltas.

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_batch.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

class _ScanScreenState extends State<ScanScreen>
    with WidgetsBindingObserver
    implements BarcodeBatchListener {

  @override
  Future<void> didUpdateSession(
    BarcodeBatch barcodeBatch,
    BarcodeBatchSession session,
    Future<FrameData> getFrameData(),
  ) async {
    // All currently tracked barcodes (Map<int, TrackedBarcode>)
    final allTracked = session.trackedBarcodes;

    // Newly appeared barcodes this frame
    final added = session.addedTrackedBarcodes;

    // Barcodes whose position changed this frame
    final updated = session.updatedTrackedBarcodes;

    // Identifiers of barcodes that left the frame (List<int>)
    final removedIds = session.removedTrackedBarcodes;

    for (final trackedBarcode in added) {
      debugPrint('New barcode: ${trackedBarcode.barcode.data} (${trackedBarcode.barcode.symbology})');
    }

    // IMPORTANT: do not hold a reference to session or its collections outside this callback.
    // Copy the data you need before the callback returns.
  }
}
```

Register and unregister the listener in `initState` / `dispose`:

```dart
@override
void initState() {
  super.initState();
  // ...
  barcodeBatch.addListener(this);
  barcodeBatch.isEnabled = true;
}

@override
void dispose() {
  barcodeBatch.removeListener(this);
  barcodeBatch.isEnabled = false;
  // ...
  super.dispose();
}
```

### BarcodeBatchSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `trackedBarcodes` | `Map<int, TrackedBarcode>` | All currently tracked barcodes, keyed by integer identifier. |
| `addedTrackedBarcodes` | `List<TrackedBarcode>` | Barcodes newly tracked this frame. |
| `updatedTrackedBarcodes` | `List<TrackedBarcode>` | Barcodes with updated location this frame. |
| `removedTrackedBarcodes` | `List<int>` | Integer identifiers of barcodes that were lost. |
| `frameSequenceId` | `int` | Identifier of the current frame sequence. |
| `reset()` | `Future<void>` | Resets the session (call only inside the listener). |

> **Important**: Do not hold references to the session object or its collections outside the `didUpdateSession` callback. Copy any data you need before returning.

### TrackedBarcode Properties

| Property | Type | Description |
|----------|------|-------------|
| `barcode` | `Barcode` | The barcode associated with this track. |
| `identifier` | `int` | Unique integer identifier for this track. Reused after the barcode is lost. |
| `location` | `Quadrilateral` | Location of the barcode in image-space (requires MatrixScan AR add-on). Convert to view-space with `captureView.viewQuadrilateralForFrameQuadrilateral(...)`. |

### Step 4a — Scan feedback (sound / vibration)

**`BarcodeBatch` has no built-in feedback.** Unlike `BarcodeCapture` and `SparkScan`, the BarcodeBatch mode does not expose a `feedback` property and does **not** beep or vibrate on its own. To give the user audible/haptic feedback when a barcode is first tracked, construct a `Feedback` from `scandit_flutter_datacapture_core` and call `emit()` yourself from `didUpdateSession`.

> **Import collision**: Flutter's `package:flutter/material.dart` also exports a class named `Feedback`. When you import both, the name is ambiguous. Either import the Scandit core barrel with a prefix (`as sdc`) and write `sdc.Feedback`, or hide Flutter's version with `import 'package:flutter/material.dart' hide Feedback;`.

```dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_batch.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';
// The core barrel is normally imported unprefixed (above) for Camera, DataCaptureView,
// FrameData, etc. Scandit's Feedback collides with Flutter material's Feedback, so ALSO
// import the core barrel with a prefix and use the prefixed name only for Feedback.
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart' as sdc;

class _ScanScreenState extends State<ScanScreen>
    implements BarcodeBatchListener {

  // Default sound + vibration. Use sdc.Feedback() for an empty (silent) feedback,
  // or pass null for either argument to suppress just that channel.
  final sdc.Feedback _feedback =
      sdc.Feedback(sdc.Vibration.defaultVibration, sdc.Sound.defaultSound);

  // Track which identifiers we have already given feedback for, so we beep
  // once per barcode rather than on every frame it is visible.
  final Set<int> _feedbackGiven = {};

  @override
  Future<void> didUpdateSession(
    BarcodeBatch barcodeBatch,
    BarcodeBatchSession session,
    Future<FrameData> getFrameData(),
  ) async {
    var hasNew = false;
    for (final trackedBarcode in session.addedTrackedBarcodes) {
      if (_feedbackGiven.add(trackedBarcode.identifier)) {
        hasNew = true;
      }
    }
    // Emit once per update if at least one not-previously-seen barcode appeared.
    if (hasNew) {
      _feedback.emit();
    }
  }
}
```

### Feedback / Sound / Vibration members (from `scandit_flutter_datacapture_core`)

| Member | Description |
|--------|-------------|
| `Feedback(Vibration? vibration, Sound? sound)` | Construct a feedback. **Dart order is vibration first, then sound.** Pass `null` for either to suppress that channel. |
| `Feedback()` | Empty constructor — emits no sound and no vibration. |
| `Feedback.defaultFeedback` | Static getter — a `Feedback` with `Vibration.defaultVibration` and `Sound.defaultSound`. |
| `feedback.emit()` | Plays the configured sound and vibration. Influenced by device ring mode / volume. |
| `Vibration.defaultVibration` | Static getter — the default vibration. |
| `Sound.defaultSound` | Static getter — the default scan sound. |

> **Note**: Feedback (sound/vibration) does **not** require the MatrixScan AR add-on — it is core SDK functionality. (Per-barcode brushes and AR overlays do require the add-on.)

## Step 5 — BarcodeBatchBasicOverlay: per-barcode brushes

`BarcodeBatchBasicOverlay` renders a highlight frame or dot over each tracked barcode. Implement `BarcodeBatchBasicOverlayListener` to return different brushes per tracked barcode.

> **Note**: Using `brushForTrackedBarcode` and `setBrushForTrackedBarcode` requires the **MatrixScan AR add-on**.

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_batch.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

class _ScanScreenState extends State<ScanScreen>
    with WidgetsBindingObserver
    implements BarcodeBatchListener, BarcodeBatchBasicOverlayListener {

  late BarcodeBatchBasicOverlay _basicOverlay;

  @override
  void initState() {
    super.initState();
    // ...

    // Construct and add the basic overlay. Pass the optional style parameter.
    _basicOverlay = BarcodeBatchBasicOverlay(
      _barcodeBatch,
      style: BarcodeBatchBasicOverlayStyle.frame,
    )..listener = this;
    _captureView.addOverlay(_basicOverlay);
  }

  // Called from the rendering thread whenever a new barcode appears.
  // Return a Brush to override the default highlight.
  @override
  Brush? brushForTrackedBarcode(
    BarcodeBatchBasicOverlay overlay,
    TrackedBarcode trackedBarcode,
  ) {
    final data = trackedBarcode.barcode.data ?? '';

    // Vary brush by symbology
    if (trackedBarcode.barcode.symbology == Symbology.ean13Upca) {
      return Brush(
        const Color(0x6600CC44),  // fill: semi-transparent green
        const Color(0xFF00CC44),  // stroke: opaque green
        2.0,
      );
    }

    // Vary brush by data content
    if (data.startsWith('0')) {
      // Transparent brush = effectively hide this barcode
      return Brush(
        const Color(0x00000000),
        const Color(0x00000000),
        0,
      );
    }

    return Brush(
      const Color(0x660064FF),
      const Color(0xFF0064FF),
      2.0,
    );
  }

  @override
  void didTapTrackedBarcode(
    BarcodeBatchBasicOverlay overlay,
    TrackedBarcode trackedBarcode,
  ) {
    debugPrint('Tapped: ${trackedBarcode.barcode.data}');
  }
}
```

### BarcodeBatchBasicOverlay Members

| Member | Available | Description |
|--------|-----------|-------------|
| `BarcodeBatchBasicOverlay(mode, {style})` | flutter=7.6 | Constructs the overlay. `style` is optional; defaults to `frame`. |
| `listener` | flutter=7.0 | Set a `BarcodeBatchBasicOverlayListener`. |
| `brush` | flutter=7.0 | Default `Brush` for all tracked barcodes when no listener is set. |
| `setBrushForTrackedBarcode(Brush? brush, TrackedBarcode trackedBarcode)` | flutter=7.0 | Imperatively set the brush for a specific barcode. Returns `Future<void>`. |
| `clearTrackedBarcodeBrushes()` | flutter=7.0 | Clear all custom brushes. Returns `Future<void>`. |
| `shouldShowScanAreaGuides` | flutter=7.0 | Debug: show the active scan area. Default `false`. |
| `style` | flutter=7.0 | The overlay style (`frame` or `dot`). |

### BarcodeBatchBasicOverlayStyle values

| Value | Description |
|-------|-------------|
| `BarcodeBatchBasicOverlayStyle.frame` | Rectangular frame highlight with appear animation. |
| `BarcodeBatchBasicOverlayStyle.dot` | Dot highlight with appear animation. |

### BarcodeBatchBasicOverlayListener callbacks

| Callback | Description |
|----------|-------------|
| `brushForTrackedBarcode(overlay, trackedBarcode) -> Brush?` | Return a `Brush` (or `null` to use the default) for a newly tracked barcode. Return a transparent brush to hide the barcode entirely. Called from the rendering thread. Requires MatrixScan AR add-on. |
| `didTapTrackedBarcode(overlay, trackedBarcode)` | Called when the user taps a tracked barcode highlight. Called from the main thread. |

### Transparent brush pattern

To hide a barcode's highlight entirely, return a fully transparent `Brush`:

```dart
@override
Brush? brushForTrackedBarcode(
  BarcodeBatchBasicOverlay overlay,
  TrackedBarcode trackedBarcode,
) {
  // Returning null uses the default brush.
  // To completely hide the highlight, return a transparent brush instead:
  if (shouldHide(trackedBarcode)) {
    return Brush(
      const Color(0x00000000),  // transparent fill
      const Color(0x00000000),  // transparent stroke
      0,
    );
  }
  return null; // use default
}
```

## Step 6 — BarcodeBatchAdvancedOverlay: AR annotations

`BarcodeBatchAdvancedOverlay` lets you anchor a custom Flutter widget to each tracked barcode. The widget must be a subclass of `BarcodeBatchAdvancedOverlayWidget` (Flutter-only base class from `scandit_flutter_datacapture_barcode_batch`).

> **Important**: Using `BarcodeBatchAdvancedOverlay` requires the **MatrixScan AR add-on**.

### 6a — Define the BarcodeBatchAdvancedOverlayWidget subclass

Derive from `BarcodeBatchAdvancedOverlayWidget`. The state class must extend `BarcodeBatchAdvancedOverlayWidgetState<T>` and override `build()` returning a `BarcodeBatchAdvancedOverlayContainer`.

```dart
// ar_bubble.dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_batch.dart';

/// AR bubble anchored above each tracked barcode.
class ARBubble extends BarcodeBatchAdvancedOverlayWidget {
  final String barcodeData;

  const ARBubble(this.barcodeData, {super.key});

  @override
  ARBubbleState createState() => ARBubbleState();
}

class ARBubbleState extends BarcodeBatchAdvancedOverlayWidgetState<ARBubble> {
  @override
  BarcodeBatchAdvancedOverlayContainer build(BuildContext context) {
    return BarcodeBatchAdvancedOverlayContainer(
      width: 140,
      height: 48,
      decoration: BoxDecoration(
        color: const Color(0xFF2196F3),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Center(
        child: Text(
          widget.barcodeData,
          textDirection: TextDirection.ltr,
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.bold,
            fontSize: 13,
          ),
        ),
      ),
    );
  }
}
```

### 6b — Set up the BarcodeBatchAdvancedOverlay

Construct the overlay, implement `BarcodeBatchAdvancedOverlayListener`, add it to the view, and call `setWidgetForTrackedBarcode` from `didUpdateSession`:

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_batch.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

class _ScanScreenState extends State<ScanScreen>
    with WidgetsBindingObserver
    implements BarcodeBatchListener, BarcodeBatchAdvancedOverlayListener {

  late BarcodeBatchAdvancedOverlay _advancedOverlay;
  final Map<int, ARBubble?> _trackedWidgets = {};

  @override
  void initState() {
    super.initState();
    // ...
    _advancedOverlay = BarcodeBatchAdvancedOverlay(_barcodeBatch)
      ..listener = this;
    _captureView.addOverlay(_advancedOverlay);
  }

  // Called by the SDK on every frame update.
  @override
  Future<void> didUpdateSession(
    BarcodeBatch barcodeBatch,
    BarcodeBatchSession session,
    Future<FrameData> getFrameData(),
  ) async {
    // Remove widgets for barcodes that are no longer tracked.
    for (final removedId in session.removedTrackedBarcodes) {
      _trackedWidgets[removedId] = null;
    }

    // Set or update the widget for each currently tracked barcode.
    for (final trackedBarcode in session.trackedBarcodes.values) {
      final data = trackedBarcode.barcode.data;
      if (data == null) continue;

      if (_trackedWidgets[trackedBarcode.identifier] == null) {
        final bubble = ARBubble(data);
        _trackedWidgets[trackedBarcode.identifier] = bubble;
        // Flutter method name: setWidgetForTrackedBarcode (not setViewForTrackedBarcode)
        _advancedOverlay.setWidgetForTrackedBarcode(bubble, trackedBarcode);
      }
    }
  }

  // BarcodeBatchAdvancedOverlayListener methods

  // Return null here — widgets are set imperatively in didUpdateSession above.
  @override
  BarcodeBatchAdvancedOverlayWidget? widgetForTrackedBarcode(
    BarcodeBatchAdvancedOverlay overlay,
    TrackedBarcode trackedBarcode,
  ) {
    return null;
  }

  @override
  Anchor anchorForTrackedBarcode(
    BarcodeBatchAdvancedOverlay overlay,
    TrackedBarcode trackedBarcode,
  ) {
    // Position the widget anchored at the top-center of the barcode.
    return Anchor.topCenter;
  }

  @override
  PointWithUnit offsetForTrackedBarcode(
    BarcodeBatchAdvancedOverlay overlay,
    TrackedBarcode trackedBarcode,
  ) {
    // Shift the widget up by 100% of its own height so it sits above the barcode.
    return PointWithUnit(
      DoubleWithUnit(0, MeasureUnit.fraction),
      DoubleWithUnit(-1, MeasureUnit.fraction),
    );
  }

  @override
  void didTapViewForTrackedBarcode(
    BarcodeBatchAdvancedOverlay overlay,
    TrackedBarcode trackedBarcode,
  ) {
    debugPrint('Tapped AR bubble for: ${trackedBarcode.barcode.data}');
  }
}
```

### Advanced Overlay Members

| Member | Available | Description |
|--------|-----------|-------------|
| `BarcodeBatchAdvancedOverlay(mode)` | flutter=7.6 | Constructs the overlay. |
| `listener` | flutter=7.0 | Set a `BarcodeBatchAdvancedOverlayListener`. |
| `setWidgetForTrackedBarcode(widget, trackedBarcode)` | flutter=7.0 | Set the Flutter widget for a tracked barcode. Pass `null` to remove. Returns `Future<void>`. Flutter-specific name (other platforms use `setViewForTrackedBarcode`). |
| `setAnchorForTrackedBarcode(anchor, trackedBarcode)` | flutter=7.0 | Override the anchor imperatively. Returns `Future<void>`. |
| `setOffsetForTrackedBarcode(offset, trackedBarcode)` | flutter=7.0 | Override the offset imperatively. Returns `Future<void>`. |
| `clearTrackedBarcodeWidgets()` | flutter=7.0 | Remove all AR widgets. Returns `Future<void>`. Flutter-specific name (other platforms use `clearTrackedBarcodeViews`). |
| `shouldShowScanAreaGuides` | flutter=7.0 | Debug: show the active scan area. Default `false`. |
| `view` | flutter=7.0 | The `DataCaptureView` this overlay is attached to. Flutter-only getter. |

### BarcodeBatchAdvancedOverlayListener callbacks

| Callback | Description |
|----------|-------------|
| `widgetForTrackedBarcode(overlay, trackedBarcode) -> BarcodeBatchAdvancedOverlayWidget?` | Return a widget instance (or `null`) for a newly tracked barcode. Ignored if `setWidgetForTrackedBarcode` was already called. Flutter-specific name. |
| `anchorForTrackedBarcode(overlay, trackedBarcode) -> Anchor` | Return an `Anchor` for the widget. Called after `widgetForTrackedBarcode`. |
| `offsetForTrackedBarcode(overlay, trackedBarcode) -> PointWithUnit` | Return a `PointWithUnit` offset. Called after `anchorForTrackedBarcode`. Flutter includes this method directly on the listener. |
| `didTapViewForTrackedBarcode(overlay, trackedBarcode)` | Called when the user taps the AR widget. |

### BarcodeBatchAdvancedOverlayWidget class hierarchy

| Class | Description |
|-------|-------------|
| `BarcodeBatchAdvancedOverlayWidget` | Flutter-only abstract base (extends `StatefulWidget`). Subclass to define your AR widget. Available flutter=7.0. |
| `BarcodeBatchAdvancedOverlayWidgetState<T>` | Abstract state class. Override `build()` to return a `BarcodeBatchAdvancedOverlayContainer`. Available flutter=7.0. |
| `BarcodeBatchAdvancedOverlayContainer` | Extends Flutter's `Container`. Must be the return type of `build()`. Available flutter=7.0. |

### Tap handling (Bubbles pattern)

In the Bubbles sample, taps on an AR bubble toggle its displayed content. Because AR widgets are rendered on the native layer and not by the Flutter engine, modifying widget state alone is not enough — you must also call `setWidgetForTrackedBarcode` again to push the updated widget to the native layer:

```dart
@override
void didTapViewForTrackedBarcode(
  BarcodeBatchAdvancedOverlay overlay,
  TrackedBarcode trackedBarcode,
) {
  final bubble = _trackedWidgets[trackedBarcode.identifier];
  if (bubble != null) {
    // Notify the widget to update its internal state.
    bubble.onTap();
    // Re-push the widget to the native layer to show the updated state.
    _advancedOverlay.setWidgetForTrackedBarcode(bubble, trackedBarcode);
  }
}
```

## Step 7 — Render DataCaptureView

Set up `DataCaptureView` and use it as the main widget body. The view must fill the available space.

```dart
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

class _ScanScreenState extends State<ScanScreen> with WidgetsBindingObserver {
  late DataCaptureView _captureView;

  @override
  void initState() {
    super.initState();
    // Create the capture view for this context.
    _captureView = DataCaptureView.forContext(dataCaptureContext);
    // Add overlays here (see Steps 5 and 6).
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _captureView,
    );
  }
}
```

## Step 8 — Lifecycle: enable/disable, dispose, camera permissions

### Camera permission

Request the camera permission before the first scan. The sample uses a helper that also starts the camera after the permission is granted:

```dart
import 'package:permission_handler/permission_handler.dart';

void _checkPermission() {
  Permission.camera.request().then((status) {
    if (!mounted) return;
    if (status.isGranted && _camera != null) {
      _camera!.switchToDesiredState(FrameSourceState.on);
    }
  });
}
```

### App lifecycle (foreground / background)

Implement `WidgetsBindingObserver` to pause the camera and disable the mode when the app goes to the background:

```dart
class _ScanScreenState extends State<ScanScreen> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _checkPermission();
    // ...
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        _checkPermission(); // re-check permission and resume camera
        break;
      default:
        _camera?.switchToDesiredState(FrameSourceState.off);
        break;
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _cleanup();
    super.dispose();
  }
}
```

### Cleanup

```dart
void _cleanup() {
  WidgetsBinding.instance.removeObserver(this);
  _barcodeBatch.removeListener(this);
  _barcodeBatch.isEnabled = false;
  _camera?.switchToDesiredState(FrameSourceState.off);
  // Remove the mode from the context so it stops processing frames.
  dataCaptureContext.removeAllModes();
}
```

> Use `dataCaptureContext.removeAllModes()` (or `dataCaptureContext.removeCurrentMode()` when using the singleton / `sharedInstance` pattern) for cleanup. This stops all frame processing.

### Enable/disable without removing the mode

```dart
// Pause scanning (e.g. while showing a dialog)
_barcodeBatch.isEnabled = false;
_camera?.switchToDesiredState(FrameSourceState.off);

// Resume scanning
_barcodeBatch.isEnabled = true;
_camera?.switchToDesiredState(FrameSourceState.on);
```

## Step 9 — Complete Example

### main.dart

```dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ScanditFlutterDataCaptureBarcode.initialize();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'MatrixScan Batch',
      home: const ScanScreen(),
    );
  }
}
```

### scan_screen.dart (basic overlay, per-barcode brushes)

```dart
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_batch.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';
import 'main.dart' show licenseKey;

class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen>
    with WidgetsBindingObserver
    implements BarcodeBatchListener, BarcodeBatchBasicOverlayListener {

  final DataCaptureContext _context =
      DataCaptureContext.forLicenseKey(licenseKey);
  Camera? _camera = Camera.defaultCamera;
  late BarcodeBatch _barcodeBatch;
  late DataCaptureView _captureView;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    final cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
    _camera?.applySettings(cameraSettings);

    _checkPermission();

    final captureSettings = BarcodeBatchSettings()
      ..enableSymbologies({
        Symbology.ean8,
        Symbology.ean13Upca,
        Symbology.upce,
        Symbology.code39,
        Symbology.code128,
      });

    _barcodeBatch = BarcodeBatch(captureSettings)
      ..addListener(this);

    _captureView = DataCaptureView.forContext(_context);

    // Add basic overlay with per-barcode brush listener.
    _captureView.addOverlay(
      BarcodeBatchBasicOverlay(_barcodeBatch, style: BarcodeBatchBasicOverlayStyle.frame)
        ..listener = this,
    );

    if (_camera != null) {
      _context.setFrameSource(_camera!);
    }
    _barcodeBatch.isEnabled = true;
    _context.setMode(_barcodeBatch);
  }

  void _checkPermission() {
    Permission.camera.request().then((status) {
      if (!mounted) return;
      if (status.isGranted && _camera != null) {
        _camera!.switchToDesiredState(FrameSourceState.on);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(body: _captureView);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        _checkPermission();
        break;
      default:
        _camera?.switchToDesiredState(FrameSourceState.off);
        break;
    }
  }

  @override
  Future<void> didUpdateSession(
    BarcodeBatch barcodeBatch,
    BarcodeBatchSession session,
    Future<FrameData> getFrameData(),
  ) async {
    for (final trackedBarcode in session.addedTrackedBarcodes) {
      debugPrint(
        'New: ${trackedBarcode.barcode.data} (${trackedBarcode.barcode.symbology})',
      );
    }
  }

  // Per-barcode brush — called from the rendering thread.
  @override
  Brush? brushForTrackedBarcode(
    BarcodeBatchBasicOverlay overlay,
    TrackedBarcode trackedBarcode,
  ) {
    if (trackedBarcode.barcode.symbology == Symbology.ean13Upca) {
      return Brush(const Color(0x6600CC44), const Color(0xFF00CC44), 2.0);
    }
    return Brush(const Color(0x660064FF), const Color(0xFF0064FF), 2.0);
  }

  @override
  void didTapTrackedBarcode(
    BarcodeBatchBasicOverlay overlay,
    TrackedBarcode trackedBarcode,
  ) {
    debugPrint('Tapped: ${trackedBarcode.barcode.data}');
  }

  void _cleanup() {
    WidgetsBinding.instance.removeObserver(this);
    _barcodeBatch.removeListener(this);
    _barcodeBatch.isEnabled = false;
    _camera?.switchToDesiredState(FrameSourceState.off);
    _context.removeAllModes();
  }

  @override
  void dispose() {
    _cleanup();
    super.dispose();
  }
}
```

## Key Rules

1. **Initialize plugins first** — `await ScanditFlutterDataCaptureBarcode.initialize()` must be in `main()` after `WidgetsFlutterBinding.ensureInitialized()` and before `runApp(...)`.
2. **Import barrels** — BarcodeBatch classes live in `scandit_flutter_datacapture_barcode_batch`. Always import this alongside `scandit_flutter_datacapture_barcode`.
3. **Constructor version** — Use `BarcodeBatch(settings)` on Flutter ≥7.6, then call `dataCaptureContext.setMode(barcodeBatch)` explicitly.
4. **Flutter overlay method names** — On Flutter: `setWidgetForTrackedBarcode` (not `setViewForTrackedBarcode`) and `clearTrackedBarcodeWidgets` (not `clearTrackedBarcodeViews`).
5. **AR add-on required** — `brushForTrackedBarcode`, `setBrushForTrackedBarcode`, and all `BarcodeBatchAdvancedOverlay` APIs require the MatrixScan AR add-on license.
6. **Widget subclass** — AR widgets must extend `BarcodeBatchAdvancedOverlayWidget`. The state must extend `BarcodeBatchAdvancedOverlayWidgetState<T>` and return `BarcodeBatchAdvancedOverlayContainer` from `build()`.
7. **Tap handling pattern** — After modifying a widget's state in `didTapViewForTrackedBarcode`, call `setWidgetForTrackedBarcode` again to push the update to the native layer.
8. **Session data** — The session object is only safe to access inside `didUpdateSession`. Copy collections before using them outside.
9. **Symbologies** — use lowerCamelCase: `Symbology.ean13Upca`, `Symbology.code128`, etc.
10. **Cleanup** — Call `removeListener`, set `isEnabled = false`, switch camera off, and call `dataCaptureContext.removeAllModes()` in `dispose()`.
11. **Camera permission** — iOS: `NSCameraUsageDescription` in `ios/Runner/Info.plist`. Android: runtime request via `permission_handler`. Re-request on `AppLifecycleState.resumed`.

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Nothing scans when the screen mounts | Camera not started. Call `_camera?.switchToDesiredState(FrameSourceState.on)` after permission is granted. |
| `setWidgetForTrackedBarcode` not found | Verify the import is `scandit_flutter_datacapture_barcode_batch`, not a different barrel. |
| AR widgets not updating after tap | Must call `setWidgetForTrackedBarcode` again after changing widget state — native layer does not observe Flutter state. |
| Brushes not showing | `brushForTrackedBarcode` requires the MatrixScan AR add-on. Verify the license. |
| `BarcodeBatch(settings)` not found | Requires flutter=7.6. On older SDKs, use a context-accepting constructor. |
| `BarcodeBatch.createRecommendedCameraSettings()` not found | Requires flutter=7.6. |
| Session data accessed outside callback | Copy `addedTrackedBarcodes`, `trackedBarcodes`, etc. before the callback returns. |
| Mode not cleaning up after navigation | Call `dataCaptureContext.removeAllModes()` in `dispose()`. |
