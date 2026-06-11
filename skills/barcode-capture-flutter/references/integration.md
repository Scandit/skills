# BarcodeCapture Flutter Integration Guide

BarcodeCapture is the low-level single-barcode scanning mode. In Flutter you wire it up by hand: a `DataCaptureContext`, a `Camera` as the frame source, the `BarcodeCapture` mode, a `DataCaptureView` widget, and a `BarcodeCaptureOverlay` for the highlight. Unlike SparkScan, there is no pre-built UI — the camera preview and the highlight are the only visuals.

> **State management note**: Examples below use the BLoC pattern. The same APIs work identically with Provider, Riverpod, GetX, or plain `StatefulWidget` — adapt ownership of `DataCaptureContext`, `BarcodeCapture`, the `Camera`, and the scan stream to the project's existing convention.

## Prerequisites

- Scandit Flutter packages in `pubspec.yaml`:
  - `scandit_flutter_datacapture_barcode` (pulls in `scandit_flutter_datacapture_core` transitively)
  - `permission_handler` (for the runtime camera permission on Android)
- Flutter `>=3.22.0`, Dart SDK `>=3.0.0 <4.0.0`.
- Android `minSdk` 23 or higher (`android/app/build.gradle`).
- After editing `pubspec.yaml`, run `flutter pub get` to fetch the packages.
- A valid Scandit license key:
  - Sign in at https://ssl.scandit.com to generate one.
  - No account yet? Sign up at https://ssl.scandit.com/dashboard/sign-up?p=test.
- Camera permissions configured by the app:
  - iOS: add `NSCameraUsageDescription` to `ios/Runner/Info.plist`.
  - Android: the manifest permission is declared by the plugin; request at runtime with `permission_handler`.

## Integration flow

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which file they'd like to integrate BarcodeCapture into (typically a BLoC / controller class, or a page `StatefulWidget`). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `scandit_flutter_datacapture_barcode` and `permission_handler` to `pubspec.yaml`, then run `flutter pub get`.
2. Add `NSCameraUsageDescription` to `ios/Runner/Info.plist` with a short usage explanation.
3. Confirm `android/app/build.gradle` has `minSdk` 23 or higher.
4. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with the key from https://ssl.scandit.com.
5. Ensure `main()` calls `WidgetsFlutterBinding.ensureInitialized()` and then `await ScanditFlutterDataCaptureBarcode.initialize()` before `runApp(...)`.
6. Call `Permission.camera.request()` from `permission_handler` before the first scan (usually in `initState()` of the scanning page).

## Step 1 — Initialize the SDK in `main()`

Plugin initialization **must** happen before any other Scandit API call. It discovers all installed Scandit Flutter plugins, fetches native defaults, and wires up the method-channel bridge.

```dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Must be called first — sets up all Scandit plugins
  await ScanditFlutterDataCaptureBarcode.initialize();
  runApp(const MyApp());
}
```

> **Important**: Always call `WidgetsFlutterBinding.ensureInitialized()` before the `await` — Flutter requires the binding before any platform-channel calls.

The `DataCaptureContext` is the central hub of the SDK. Construct it once and reuse the same reference for the lifetime of the scanning surface. Hold it on a BLoC / controller that outlives any single `State`.

```dart
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

final DataCaptureContext _dataCaptureContext = DataCaptureContext.forLicenseKey(licenseKey);
```

## Step 2 — Configure BarcodeCaptureSettings

Choose which barcode symbologies to scan. By default, all symbologies are disabled — you must enable each one explicitly. Only enable what you need; each extra symbology adds processing time.

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_capture.dart';

var settings = BarcodeCaptureSettings();

settings.enableSymbologies({
  Symbology.ean13Upca,
  Symbology.ean8,
  Symbology.upce,
  Symbology.code39,
  Symbology.code128,
  Symbology.interleavedTwoOfFive,
});

// Optional: adjust active symbol counts for variable-length symbologies
var code39 = settings.settingsForSymbology(Symbology.code39);
code39.activeSymbolCounts = {7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20};

// Optional: filter duplicate scans
settings.codeDuplicateFilter = const Duration(milliseconds: 500);
```

### BarcodeCaptureSettings Properties

| Property | Type | Description |
|----------|------|-------------|
| `codeDuplicateFilter` | `Duration` | Time window to suppress duplicate scans of the same code. `Duration.zero` reports every detection; negative `Duration(seconds: -1)` reports each code only once until scanning stops. |
| `enabledSymbologies` | `Set<Symbology>` | Read-only set of currently enabled symbologies. |
| `enabledCompositeTypes` | `Set<CompositeType>` | Composite barcode types to enable. |
| `locationSelection` | `LocationSelection?` | Restrict the scan area. `null` = full frame. |
| `scanIntention` | `ScanIntention` | Scanning intent. Values: `ScanIntention.smart` (default from v7), `ScanIntention.manual`. |
| `batterySaving` | `BatterySavingMode` | Battery optimization. Values: `BatterySavingMode.auto` (default), `BatterySavingMode.on`, `BatterySavingMode.off`. |

### BarcodeCaptureSettings Methods

| Method | Description |
|--------|-------------|
| `enableSymbology(symbology, enabled)` | Enable or disable one symbology. |
| `enableSymbologies(symbologies)` | Enable a `Set<Symbology>` in one call. |
| `settingsForSymbology(symbology)` | Get per-symbology `SymbologySettings` (e.g. `activeSymbolCounts`, `enabledExtensions`). |
| `enableSymbologiesForCompositeTypes(compositeTypes)` | Enable symbologies required for composite types. |
| `setProperty(name, value)` / `getProperty(name)` | Advanced property access by name. |

## Step 3 — Camera and frame source

`Camera.defaultCamera` returns the recommended back camera. Apply `BarcodeCapture.createRecommendedCameraSettings()` for the best preset, then attach the camera as the context's frame source.

```dart
final camera = Camera.defaultCamera;
if (camera != null) {
  await camera.applySettings(BarcodeCapture.createRecommendedCameraSettings());
  await dataCaptureContext.setFrameSource(camera);
}
```

Switch the camera on / off via `camera.switchToDesiredState(...)`:

```dart
await camera.switchToDesiredState(FrameSourceState.on);  // start preview / scanning
await camera.switchToDesiredState(FrameSourceState.off); // release the camera
```

## Step 4 — Create the BarcodeCapture mode

```dart
final barcodeCapture = BarcodeCapture(settings);
dataCaptureContext.addMode(barcodeCapture);
```

`BarcodeCapture(settings)` is the v8 constructor form. The mode must be added to the context before scanning starts. Re-applying settings at runtime is done via `barcodeCapture.applySettings(newSettings)` (returns `Future<void>`).

### BarcodeCapture properties / methods

| Member | Description |
|--------|-------------|
| `isEnabled` | Pause / resume scanning without tearing down the camera. |
| `feedback` | `BarcodeCaptureFeedback` — sound / vibration on success. |
| `applySettings(settings)` | Async update of settings. |
| `addListener(listener)` / `removeListener(listener)` | Register or remove a `BarcodeCaptureListener`. |
| `BarcodeCapture.createRecommendedCameraSettings()` | Static — returns the recommended `CameraSettings` for BarcodeCapture. |

## Step 5 — DataCaptureView and BarcodeCaptureOverlay

`DataCaptureView.forContext(context)` returns the camera preview as a Flutter `Widget`. The `BarcodeCaptureOverlay` draws the highlight rectangles on top. Construct it with `BarcodeCaptureOverlay(barcodeCapture)`, then attach it to the view with `captureView.addOverlay(overlay)`.

```dart
final captureView = DataCaptureView.forContext(dataCaptureContext);

final overlay = BarcodeCaptureOverlay(barcodeCapture);
captureView.addOverlay(overlay);
```

Add the view to your widget tree as you would any other widget — typically as the body of a `Scaffold`.

```dart
return Scaffold(
  appBar: AppBar(title: const Text('Scan')),
  body: captureView,
);
```

### BarcodeCaptureOverlay Members

| Member | Type / Description |
|--------|-------------|
| `BarcodeCaptureOverlay(mode)` | Constructor — create the overlay, then add it to the view with `view.addOverlay(overlay)`. This is the v8 form. |
| `brush` | `Brush` — fill / stroke for recognized-barcode highlights. |
| `viewfinder` | `Viewfinder?` — optional viewfinder drawn on the preview. |
| `shouldShowScanAreaGuides` | `bool` — debug aid, do not enable in production. |

## Step 6 — Implement BarcodeCaptureListener

Implement `BarcodeCaptureListener` on the BLoC and forward results through a stream.

```dart
import 'dart:async';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_capture.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

class ScannerBloc implements BarcodeCaptureListener {
  late final DataCaptureContext dataCaptureContext;
  late final BarcodeCapture barcodeCapture;
  late final Camera? camera;
  late final DataCaptureView captureView;
  late final BarcodeCaptureOverlay overlay;

  final StreamController<Barcode> _scans = StreamController.broadcast();
  Stream<Barcode> get scannedBarcodes => _scans.stream;

  ScannerBloc() {
    dataCaptureContext = DataCaptureContext.forLicenseKey(licenseKey);

    final settings = BarcodeCaptureSettings()
      ..enableSymbologies({Symbology.ean13Upca, Symbology.code128});

    barcodeCapture = BarcodeCapture(settings);
    barcodeCapture.addListener(this);
    dataCaptureContext.addMode(barcodeCapture);

    camera = Camera.defaultCamera;
    camera?.applySettings(BarcodeCapture.createRecommendedCameraSettings());
    if (camera != null) dataCaptureContext.setFrameSource(camera!);

    captureView = DataCaptureView.forContext(dataCaptureContext);
    overlay = BarcodeCaptureOverlay(barcodeCapture);
    captureView.addOverlay(overlay);
  }

  @override
  Future<void> didScan(
    BarcodeCapture barcodeCapture,
    BarcodeCaptureSession session,
    Future<FrameData?> Function() getFrameData,
  ) async {
    final barcode = session.newlyRecognizedBarcode;
    if (barcode == null) return;

    // Disable while we handle the scan, so duplicates don't fire.
    barcodeCapture.isEnabled = false;
    _scans.add(barcode);
    // Re-enable when ready to scan again (e.g. after navigating back).
    barcodeCapture.isEnabled = true;
  }

  @override
  Future<void> didUpdateSession(
    BarcodeCapture barcodeCapture,
    BarcodeCaptureSession session,
    Future<FrameData?> Function() getFrameData,
  ) async {
    // Called every frame; keep this fast.
  }

  void dispose() {
    barcodeCapture.removeListener(this);
    _scans.close();
  }
}
```

### BarcodeCaptureListener Interface

| Callback | Signature | Description |
|----------|-----------|-------------|
| `didScan` | `(BarcodeCapture, BarcodeCaptureSession, Future<FrameData?> Function()) => Future<void>` | A barcode was just recognized. Read it from `session.newlyRecognizedBarcode`. |
| `didUpdateSession` | `(BarcodeCapture, BarcodeCaptureSession, Future<FrameData?> Function()) => Future<void>` | Called for every processed frame. Keep work minimal. |

> **Lazy frame data**: `getFrameData` is a `Future<FrameData?> Function()` — frame data is fetched lazily across the platform channel. Only call it if you actually need it.

> **Blocking behaviour**: Both callbacks block further frame processing until they return. For long-running work (DB lookup, network call), set `barcodeCapture.isEnabled = false`, return from the callback, and re-enable the mode when done.

### BarcodeCaptureSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `newlyRecognizedBarcode` | `Barcode?` | The barcode just scanned (single-result API since 6.26). |
| `newlyLocalizedBarcodes` | `List<LocalizedOnlyBarcode>` | Codes that were located but not decoded. |
| `frameSequenceId` | `int` | Identifier of the current frame sequence. |
| `reset()` | `Future<void>` | Clears the duplicate-filter state. Call only inside a listener callback. |

## Step 7 — Page widget and lifecycle

Drive the camera from `WidgetsBindingObserver`. Turn it on in `resumed`, off in `paused` / `inactive`. Hot-reload does not re-trigger `main()`, so the BLoC and its DataCaptureContext survive a hot reload.

```dart
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});
  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage> with WidgetsBindingObserver {
  final ScannerBloc _bloc = ScannerBloc();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _start();
    _bloc.scannedBarcodes.listen((barcode) {
      // handle scan in the UI
    });
  }

  Future<void> _start() async {
    final status = await Permission.camera.request();
    if (!status.isGranted) return;
    _bloc.barcodeCapture.isEnabled = true;
    await _bloc.camera?.switchToDesiredState(FrameSourceState.on);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _bloc.camera?.switchToDesiredState(FrameSourceState.on);
    } else {
      _bloc.camera?.switchToDesiredState(FrameSourceState.off);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Scanner')),
    body: _bloc.captureView,
  );

  @override
  void dispose() {
    _bloc.camera?.switchToDesiredState(FrameSourceState.off);
    _bloc.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
}
```

## Optional configuration

### BarcodeCaptureFeedback

By default, BarcodeCapture beeps and vibrates on success. To customize, mutate `barcodeCapture.feedback.success` (a `Feedback` instance):

```dart
barcodeCapture.feedback.success = Feedback(null, Sound.defaultSound);
```

Use `BarcodeCaptureFeedback()` (empty constructor) to suppress all feedback, or `BarcodeCaptureFeedback.defaultFeedback` for the defaults.

### Viewfinder

Attach a viewfinder to the overlay to draw a guide on the preview:

```dart
overlay.viewfinder = RectangularViewfinder.withStyleAndLineStyle(
  RectangularViewfinderStyle.square,
  RectangularViewfinderLineStyle.light,
);
```

The square `RectangularViewfinder` is one option. Two other built-in viewfinders are available:

```dart
// A camera-aimer dot + frame, good for tap-to-scan / aimed single scanning.
overlay.viewfinder = AimerViewfinder();

// A horizontal laser line.
overlay.viewfinder = LaserlineViewfinder();
```

Both come from `scandit_flutter_datacapture_core`. `AimerViewfinder` exposes `frameColor` and `dotColor`; `LaserlineViewfinder` exposes `width`, `enabledColor`, and `disabledColor`.

### Overlay brush (highlight appearance)

`BarcodeCaptureOverlay.brush` controls the fill / stroke drawn over a recognized barcode. The `Brush` constructor takes `(fillColor, strokeColor, strokeWidth)` using Flutter `Color`s:

```dart
overlay.brush = Brush(Colors.green.withValues(alpha: 0.2), Colors.green, 2);
```

To hide the highlight entirely, assign the fully-transparent brush:

```dart
overlay.brush = Brush.transparent;
```

> The overlay must be held as a field (not a throwaway local) to mutate `brush` or `viewfinder` after construction. Promote it from the constructor: `overlay = BarcodeCaptureOverlay(barcodeCapture);` followed by `captureView.addOverlay(overlay);`.

### Rejecting unwanted codes

BarcodeCapture has a single overlay `brush`; there is no per-barcode brush callback (that is a MatrixScan feature). To "reject" codes that don't match your business rules, inspect `barcode.data` inside `didScan`, and for a non-matching code set the overlay brush transparent and return early without recording the scan:

```dart
@override
Future<void> didScan(
  BarcodeCapture barcodeCapture,
  BarcodeCaptureSession session,
  Future<FrameData?> Function() getFrameData,
) async {
  final barcode = session.newlyRecognizedBarcode;
  if (barcode == null) return;

  // Reject codes that don't start with the expected prefix.
  if (barcode.data == null || !barcode.data!.startsWith('PROD-')) {
    overlay.brush = Brush.transparent;
    return;
  }

  overlay.brush = Brush(Colors.green.withValues(alpha: 0.2), Colors.green, 2);
  // ...accept and process the barcode...
}
```

### Per-symbology settings

`settings.settingsForSymbology(symbology)` returns a `SymbologySettings` object whose mutations apply when you construct (or `applySettings`) the mode.

**Extensions** — symbology-specific features (e.g. Code 39 Full ASCII). Use the named `enabled:` parameter:

```dart
var code39 = settings.settingsForSymbology(Symbology.code39);
code39.setExtensionEnabled('full_ascii', enabled: true);
```

**Checksums** — set the optional checksum algorithm(s). `checksums` is a `Set<Checksum>`:

```dart
var code39 = settings.settingsForSymbology(Symbology.code39);
code39.checksums = {Checksum.mod43};
```

Available values: `Checksum.mod10`, `Checksum.mod11`, `Checksum.mod16`, `Checksum.mod43`, `Checksum.mod47`. Only a subset is valid per symbology.

**Active symbol counts** — the allowed length range for variable-length 1D symbologies. `activeSymbolCounts` is a `Set<int>`:

```dart
var code39 = settings.settingsForSymbology(Symbology.code39);
code39.activeSymbolCounts = {7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20};
```

**Color-inverted codes** — by default only dark-on-light codes are read. To also read bright-on-dark (inverted) codes for a symbology:

```dart
var code128 = settings.settingsForSymbology(Symbology.code128);
code128.isColorInvertedEnabled = true;
```

### LocationSelection

Restrict scanning to a sub-area of the preview by setting `BarcodeCaptureSettings.locationSelection`:

```dart
settings.locationSelection = RectangularLocationSelection.withSize(
  SizeWithUnit(
    DoubleWithUnit(0.9, MeasureUnit.fraction),
    DoubleWithUnit(0.3, MeasureUnit.fraction),
  ),
);
```

### ScanIntention

Default is `ScanIntention.smart` from v7+, which uses the Smart Scan algorithm. Set to `ScanIntention.manual` for the legacy behaviour:

```dart
settings.scanIntention = ScanIntention.manual;
```

### CodeDuplicateFilter

Suppress duplicate scans of the same code within a time window. Negative `Duration(seconds: -1)` reports each code only once until scanning is stopped; `Duration.zero` reports every detection.

```dart
settings.codeDuplicateFilter = const Duration(milliseconds: 500);
```

### Composite codes

Composite codes (linear + 2D companion) require both the symbologies and the composite types to be enabled:

```dart
settings.enableSymbologiesForCompositeTypes({CompositeType.a, CompositeType.b});
settings.enabledCompositeTypes = {CompositeType.a, CompositeType.b};
```

## Key Rules

1. **Initialize plugins first** — `await ScanditFlutterDataCaptureBarcode.initialize()` must run in `main()` after `WidgetsFlutterBinding.ensureInitialized()` and before `runApp(...)`.
2. **One context per scanning surface** — `DataCaptureContext.forLicenseKey(licenseKey)` and `DataCaptureContext.initialize(licenseKey)` both return the singleton; either is fine.
3. **Mode lifecycle** — construct `BarcodeCapture(settings)`, add it to the context with `dataCaptureContext.addMode(barcodeCapture)`. Use `barcodeCapture.isEnabled = false` to pause.
4. **Listener lives on the owner** — implement `BarcodeCaptureListener` on the BLoC; the page only listens to the resulting stream.
5. **Disable inside `didScan`** — set `barcodeCapture.isEnabled = false` before doing any non-trivial work in the callback to avoid duplicate / racing scans.
6. **Lazy frame data** — `getFrameData` is `Future<FrameData?> Function()`; only invoke it if needed.
7. **Camera lifecycle** — drive `camera.switchToDesiredState(FrameSourceState.on/off)` from `WidgetsBindingObserver.didChangeAppLifecycleState` and from `dispose()`.
8. **Overlay wiring is explicit** — construct `BarcodeCaptureOverlay(barcodeCapture)` and attach it with `captureView.addOverlay(overlay)`. There is no implicit overlay.
9. **Camera permission** — iOS needs `NSCameraUsageDescription`; Android needs the runtime permission via `permission_handler`.
10. **Symbologies** — enable only what's needed; each extra symbology adds processing time. Variable-length 1D symbologies (Code39, Code128, ITF) may need `activeSymbolCounts` adjusted.
11. **Settings order** — configure `BarcodeCaptureSettings` before constructing `BarcodeCapture(settings)`. To change settings at runtime, use `barcodeCapture.applySettings(newSettings)`.
12. **Dispose cleanly** — call `barcodeCapture.removeListener(this)`, close any `StreamController`s, and turn the camera off from the parent state's `dispose()`.
