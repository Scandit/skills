# SparkScan Flutter Integration Guide

SparkScan is a pre-built scanning UI for high-volume single-scanning workflows. In Flutter it is a `StatefulWidget` that wraps your normal widget tree. The scanning controls (floating trigger button, toolbar, mini preview, toasts) render as a native platform view on top of the child widget, so users scan barcodes without leaving the current screen.

> **State management note**: Examples below use the BLoC pattern (as in the official `ListBuildingSample`). The same APIs work identically with Provider, Riverpod, GetX, or plain `StatefulWidget` — adapt ownership of `DataCaptureContext`, `SparkScan`, and the scan stream to the project's existing convention.

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

Ask the user which barcode symbologies they need to scan. When asking, mention that it's important to only enable the symbologies they actually need, as enabling fewer improves scanning performance and accuracy.

Once the user responds, ask them which file they'd like to integrate SparkScan into (typically a BLoC / controller class, or a page `StatefulWidget`). Then write the integration code directly into that file. Do not just show the code in chat; apply it to the file.

After providing the code, show this setup checklist:

**Setup checklist:**
1. Add `scandit_flutter_datacapture_barcode` and `permission_handler` to `pubspec.yaml`, then run `flutter pub get`.
2. Add `NSCameraUsageDescription` to `ios/Runner/Info.plist` with a short usage explanation.
3. Replace `-- ENTER YOUR SCANDIT LICENSE KEY HERE --` with the key from https://ssl.scandit.com.
4. Ensure `main()` calls `WidgetsFlutterBinding.ensureInitialized()` and then `await ScanditFlutterDataCaptureBarcode.initialize()` before `runApp(...)`.
5. Call `Permission.camera.request()` from `permission_handler` before the first scan (usually in `initState()` of the scanning page).

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

## Step 2 — Create the DataCaptureContext

```dart
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

final DataCaptureContext _dataCaptureContext = DataCaptureContext.forLicenseKey(licenseKey);
```

- `DataCaptureContext.forLicenseKey(licenseKey)` returns a singleton instance — call it once and reuse the same reference.
- The static `DataCaptureContext.initialize(licenseKey)` is also available and has identical semantics.
- For a given process only **one** `DataCaptureContext` exists; repeated calls return the same instance.

## Step 3 — Configure SparkScanSettings

Choose which barcode symbologies to scan. Only enable what you need — each extra symbology adds processing time.

```dart
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_spark_scan.dart';

var sparkScanSettings = SparkScanSettings();

sparkScanSettings.enableSymbologies({
  Symbology.ean13Upca,
  Symbology.ean8,
  Symbology.upce,
  Symbology.code39,
  Symbology.code128,
  Symbology.interleavedTwoOfFive,
});

// Optional: adjust active symbol counts for variable-length symbologies
var code39 = sparkScanSettings.settingsForSymbology(Symbology.code39);
code39.activeSymbolCounts = {7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20};
```

### SparkScanSettings Properties

| Property | Type | Description |
|----------|------|-------------|
| `codeDuplicateFilter` | `Duration` | Time window to suppress duplicate scans of the same code. |
| `scanIntention` | `ScanIntention` | Scanning intent mode. Values: `ScanIntention.smart`, `ScanIntention.manual`. |
| `batterySaving` | `BatterySavingMode` | Battery optimization level. Values: `BatterySavingMode.auto`, `BatterySavingMode.on`, `BatterySavingMode.off`. |
| `locationSelection` | `LocationSelection?` | Restrict the scan area. `null` = full frame. |
| `enabledCompositeTypes` | `Set<CompositeType>` | Composite barcode types. |
| `itemDefinitions` | `List<ScanItemDefinition>?` | For item-based (USI) scanning. |

### SparkScanSettings Methods

| Method | Description |
|--------|-------------|
| `enableSymbologies(symbologies)` | Enable multiple symbologies (takes a `Set<Symbology>`). |
| `enableSymbology(symbology, enabled)` | Enable or disable one. |
| `settingsForSymbology(symbology)` | Get per-symbology settings (e.g., `activeSymbolCounts`). |
| `enableSymbologiesForCompositeTypes(compositeTypes)` | Enable symbologies required for composite types. |
| `setProperty(name, value)` / `getProperty(name)` | Advanced property access by name. |

## Step 4 — Create SparkScan Mode and Add a Listener

The cleanest pattern is for a BLoC (or equivalent controller) to implement `SparkScanListener` directly. Results are forwarded to the UI through a stream.

```dart
import 'dart:async';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_spark_scan.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

class ScannerBloc implements SparkScanListener {
  late final DataCaptureContext dataCaptureContext;
  late final SparkScan sparkScan;
  late final SparkScanViewSettings sparkScanViewSettings;
  final StreamController<Barcode> _scans = StreamController.broadcast();

  Stream<Barcode> get scannedBarcodes => _scans.stream;

  ScannerBloc() {
    dataCaptureContext = DataCaptureContext.forLicenseKey(licenseKey);

    final settings = SparkScanSettings()
      ..enableSymbologies({Symbology.ean13Upca, Symbology.code128});

    sparkScan = SparkScan(settings: settings);
    sparkScan.addListener(this);

    sparkScanViewSettings = SparkScanViewSettings();
  }

  @override
  Future<void> didScan(
    SparkScan sparkScan,
    SparkScanSession session,
    Future<FrameData> Function() getFrameData,
  ) async {
    final barcode = session.newlyRecognizedBarcode;
    if (barcode == null) return;
    _scans.add(barcode);
  }

  @override
  Future<void> didUpdateSession(
    SparkScan sparkScan,
    SparkScanSession session,
    Future<FrameData> Function() getFrameData,
  ) async {
    // Usually unused for SparkScan.
  }

  void dispose() {
    sparkScan.removeListener(this);
    _scans.close();
  }
}
```

### SparkScanListener Interface

All callbacks are required overrides (no-op for the ones you don't need).

| Callback | Signature | Description |
|----------|-----------|-------------|
| `didScan` | `(SparkScan, SparkScanSession, Future<FrameData> Function()) => Future<void>` | Called when a barcode is scanned. |
| `didUpdateSession` | `(SparkScan, SparkScanSession, Future<FrameData> Function()) => Future<void>` | Called on every frame processed. |

### SparkScanSession Properties

| Property | Type | Description |
|----------|------|-------------|
| `newlyRecognizedBarcode` | `Barcode?` | The barcode just scanned. |
| `frameSequenceId` | `int` | Frame identifier. |
| `newlyRecognizedItems` / `allRecognizedItems` | `List<ScannedItem>` | For USI / item-based scanning. |
| `reset()` | `Future<void>` | Clear session state. |

### SparkScan Methods

| Method | Description |
|--------|-------------|
| `addListener(listener)` / `removeListener(listener)` | Register/remove a listener. |
| `applySettings(settings)` | Update settings at runtime (returns `Future<void>`). |
| `isEnabled` | Enable/disable scanning without tearing down the view. |

## Step 5 — Create SparkScanView

`SparkScanView` is a `StatefulWidget` that hosts a native platform view for the scanning UI and renders your own widget tree underneath. The view is bound to the `DataCaptureContext` and `SparkScan` mode via the `forContext` factory.

```dart
@override
Widget build(BuildContext context) {
  final sparkScanView = SparkScanView.forContext(
    _buildBody(),                      // your normal widget tree (list, empty state, etc.)
    bloc.dataCaptureContext,
    bloc.sparkScan,
    bloc.sparkScanViewSettings,
  )..feedbackDelegate = bloc;          // optional — see Step 7

  return Scaffold(
    appBar: AppBar(title: const Text('Scanner')),
    body: SafeArea(child: sparkScanView),
  );
}
```

> The `SparkScanViewSettings` argument is optional — pass `null` or a default `SparkScanViewSettings()` for defaults.

## Step 6 — SparkScanView Lifecycle

| Method | Description |
|--------|-------------|
| `startScanning()` | Begin barcode capture (returns `Future<void>`). |
| `pauseScanning()` | Pause (resume with `startScanning()`). |
| `stopScanning()` | Stop and release the camera. |
| `showToast(text)` | Display a temporary toast on the overlay. |

The view handles its own platform-view create/destroy lifecycle. You don't need to call a `dispose()` on the view widget — disposing the `State` tears down the native view automatically. Do dispose your **BLoC** (which owns the listener subscription and stream) from the parent state's `dispose()`.

## Step 7 — SparkScanView Properties

### Visibility Controls (`bool`)

| Property | Description |
|----------|-------------|
| `previewSizeControlVisible` | Preview size toggle (mini vs. full). |
| `scanningBehaviorButtonVisible` | Single-scan / continuous-scan toggle. |
| `barcodeCountButtonVisible` | Barcode Count mode button. |
| `barcodeFindButtonVisible` | Barcode Find mode button. |
| `targetModeButtonVisible` | Target mode button. |
| `labelCaptureButtonVisible` | Label Capture mode button. |
| `cameraSwitchButtonVisible` | Front/back camera switch. |
| `torchControlVisible` | Torch (flashlight) toggle. |
| `zoomSwitchControlVisible` | Zoom level control. |
| `previewCloseControlVisible` | Close button on camera preview. |
| `triggerButtonVisible` | Floating trigger button. |

### Color Properties (`Color?`)

All colors use Flutter's `Color` type (e.g. `Color(0xFFFF5500)` or `Colors.red`).

| Property | Description |
|----------|-------------|
| `toolbarBackgroundColor` | Toolbar background. |
| `toolbarIconActiveTintColor` / `toolbarIconInactiveTintColor` | Toolbar icon tints. |
| `triggerButtonAnimationColor` | Animation ring color. |
| `triggerButtonExpandedColor` / `triggerButtonCollapsedColor` | Trigger button state colors. |
| `triggerButtonTintColor` | Trigger button icon tint. |

### Other Properties

| Property | Type | Description |
|----------|------|-------------|
| `triggerButtonImage` | `Image?` (get) / `setTriggerButtonImage(Uint8List)` | Custom image for the trigger button. |
| `SparkScanView.defaultBrush` | `Brush` (static) | Default highlight brush. |
| `SparkScanView.hardwareTriggerSupported` | `bool` (static) | Whether hardware trigger is available on this device. |

## Step 8 — Custom Feedback

By default SparkScan provides visual and haptic feedback on each scan. To customize feedback per-barcode (e.g., reject invalid codes), implement `SparkScanFeedbackDelegate` on the BLoC and assign it to `sparkScanView.feedbackDelegate`.

```dart
class ScannerBloc implements SparkScanListener, SparkScanFeedbackDelegate {
  // ... existing code ...

  bool _isValidBarcode(Barcode barcode) =>
      barcode.data != null && barcode.data != '123456789';

  @override
  SparkScanBarcodeFeedback? feedbackForBarcode(Barcode barcode) {
    if (_isValidBarcode(barcode)) {
      return SparkScanBarcodeSuccessFeedback();
    }
    return SparkScanBarcodeErrorFeedback.fromMessage(
      'Wrong barcode',
      const Duration(seconds: 60),
    );
  }
}
```

### SparkScanFeedbackDelegate Interface

| Callback | Signature | Description |
|----------|-----------|-------------|
| `feedbackForBarcode` | `(Barcode) => SparkScanBarcodeFeedback?` | Return success/error feedback per scanned barcode. `null` = default. |

### SparkScanBarcodeSuccessFeedback

| Constructor / Factory | Description |
|-----------------------|-------------|
| `SparkScanBarcodeSuccessFeedback()` | Default success visuals. |
| `SparkScanBarcodeSuccessFeedback(visualFeedbackColor: ..., brush: ..., feedback: ...)` | Customize color / brush / feedback. |

### SparkScanBarcodeErrorFeedback

| Constructor / Factory | Description |
|-----------------------|-------------|
| `SparkScanBarcodeErrorFeedback(message, resumeCapturingDelay, ...)` | Full constructor (`Duration`, `Color?`, `Brush?`, `Feedback?`). |
| `SparkScanBarcodeErrorFeedback.fromMessage(message, resumeCapturingDelay)` | Convenience factory with defaults. |

## Step 9 — SparkScanViewUiListener

Listen for user interactions with the SparkScan overlay buttons:

```dart
class _HomePageState extends State<HomePage> implements SparkScanViewUiListener {
  @override
  void initState() {
    super.initState();
    // Assign once the view exists; commonly after first build.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      sparkScanView.setListener(this);
    });
  }

  @override
  void didTapBarcodeCountButton(SparkScanView view) {
    Navigator.of(context).pushNamed('/count');
  }

  @override
  void didTapBarcodeFindButton(SparkScanView view) { /* ... */ }

  @override
  void didTapLabelCaptureButton(SparkScanView view) { /* ... */ }

  @override
  void didChangeViewState(SparkScanViewState newState) { /* expanded/collapsed */ }
}
```

All methods must be implemented (return without doing anything for the ones you don't need). Use `SparkScanViewUiExtendedListener` instead if you also need `didChangeScanningMode`.

## Step 10 — Widget Tree and Permissions

Flutter renders your child widget *inside* the `SparkScanView`. Lay out your UI the same way you would any screen; the native trigger button floats over the bottom of the view.

### Minimal page scaffold

```dart
class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with WidgetsBindingObserver {
  final bloc = ScannerBloc();
  final List<Barcode> _items = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _requestCameraPermission();
    bloc.scannedBarcodes.listen((barcode) {
      setState(() => _items.add(barcode));
    });
  }

  Future<void> _requestCameraPermission() async {
    final status = await Permission.camera.request();
    if (!status.isGranted) debugPrint('Camera permission denied');
  }

  @override
  Widget build(BuildContext context) {
    final view = SparkScanView.forContext(
      _buildList(),
      bloc.dataCaptureContext,
      bloc.sparkScan,
      bloc.sparkScanViewSettings,
    )..feedbackDelegate = bloc;

    return Scaffold(
      appBar: AppBar(title: const Text('ListBuilding')),
      body: SafeArea(child: view),
    );
  }

  Widget _buildList() => ListView.builder(
    itemCount: _items.length,
    itemBuilder: (_, i) => ListTile(title: Text(_items[i].data ?? '')),
  );

  @override
  void dispose() {
    bloc.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
}
```

### Key widget-tree considerations

- Wrap `SparkScanView` in a `SafeArea` so the trigger button clears the home indicator / status bar on notched devices.
- The child widget gets `Positioned.fill` under the native overlay — build it as if the screen were empty except for a bottom floating action; do not add your own bottom action bar in the same horizontal band as the trigger button.
- `WidgetsBindingObserver` is useful to re-request camera permission when the app resumes from background.

## Step 11 — Complete Example

A full working integration: plugin init, context, scan pipeline, list UI, and feedback delegate — based on the official ListBuildingSample.

### main.dart

```dart
import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';

import 'home/view/home_page.dart';

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
    title: 'ListBuildingSample',
    home: const HomePage(),
  );
}
```

### home/bloc/home_bloc.dart

```dart
import 'dart:async';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_spark_scan.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

class HomeBloc implements SparkScanListener, SparkScanFeedbackDelegate {
  final DataCaptureContext dataCaptureContext =
      DataCaptureContext.forLicenseKey(licenseKey);
  late final SparkScan sparkScan;
  late final SparkScanViewSettings sparkScanViewSettings;
  final StreamController<Barcode> _scans = StreamController.broadcast();
  Stream<Barcode> get scannedBarcodes => _scans.stream;
  int _scannedCount = 0;

  HomeBloc() {
    final settings = SparkScanSettings()
      ..enableSymbologies({
        Symbology.ean13Upca,
        Symbology.ean8,
        Symbology.upce,
        Symbology.code39,
        Symbology.code128,
        Symbology.interleavedTwoOfFive,
      });
    settings.settingsForSymbology(Symbology.code39).activeSymbolCounts = {
      7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    };
    sparkScan = SparkScan(settings: settings);
    sparkScan.addListener(this);
    sparkScanViewSettings = SparkScanViewSettings();
  }

  bool _isValid(Barcode b) => b.data != null && b.data != '123456789';

  @override
  Future<void> didScan(
    SparkScan sparkScan,
    SparkScanSession session,
    Future<FrameData> Function() getFrameData,
  ) async {
    final barcode = session.newlyRecognizedBarcode;
    if (barcode == null) return;
    if (_isValid(barcode)) {
      _scannedCount += 1;
      _scans.add(barcode);
    }
  }

  @override
  Future<void> didUpdateSession(
    SparkScan sparkScan,
    SparkScanSession session,
    Future<FrameData> Function() getFrameData,
  ) async {}

  @override
  SparkScanBarcodeFeedback? feedbackForBarcode(Barcode barcode) {
    if (_isValid(barcode)) return SparkScanBarcodeSuccessFeedback();
    return SparkScanBarcodeErrorFeedback.fromMessage(
      'Wrong barcode',
      const Duration(seconds: 60),
    );
  }

  void clear() => _scannedCount = 0;

  void dispose() {
    sparkScan.removeListener(this);
    _scans.close();
  }
}
```

### home/view/home_page.dart

```dart
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_spark_scan.dart';

import '../bloc/home_bloc.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with WidgetsBindingObserver {
  final HomeBloc _bloc = HomeBloc();
  final List<String> _items = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _requestCameraPermission();
    _bloc.scannedBarcodes.listen((barcode) {
      setState(() => _items.add(barcode.data ?? ''));
    });
  }

  Future<void> _requestCameraPermission() async {
    await Permission.camera.request();
  }

  @override
  Widget build(BuildContext context) {
    final view = SparkScanView.forContext(
      _buildBody(),
      _bloc.dataCaptureContext,
      _bloc.sparkScan,
      _bloc.sparkScanViewSettings,
    )..feedbackDelegate = _bloc;

    return Scaffold(
      appBar: AppBar(title: const Text('ListBuilding')),
      body: SafeArea(child: view),
    );
  }

  Widget _buildBody() => Column(
    children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: Text('${_items.length} items',
          style: const TextStyle(fontWeight: FontWeight.bold)),
      ),
      Expanded(
        child: ListView.separated(
          itemCount: _items.length,
          separatorBuilder: (_, __) => const Divider(height: 1),
          itemBuilder: (_, i) => ListTile(title: Text(_items[i])),
        ),
      ),
      Padding(
        padding: const EdgeInsets.all(12),
        child: TextButton(
          onPressed: () {
            _bloc.clear();
            setState(() => _items.clear());
          },
          child: const Text('CLEAR LIST'),
        ),
      ),
    ],
  );

  @override
  void dispose() {
    _bloc.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
}
```

## Key Rules

1. **Initialize plugins first** — `await ScanditFlutterDataCaptureBarcode.initialize()` must be called in `main()` after `WidgetsFlutterBinding.ensureInitialized()` and before `runApp(...)`. Flutter-specific, no equivalent in JS-based frameworks.
2. **Context creation** — `DataCaptureContext.forLicenseKey(licenseKey)` and `DataCaptureContext.initialize(licenseKey)` both return the same singleton; either is fine.
3. **`SparkScanView` wraps a child** — the native scanning controls overlay your own widget tree; build the child as usual.
4. **Listener / delegate lives on the owner (BLoC)** — implement `SparkScanListener` and `SparkScanFeedbackDelegate` on the BLoC; assign `feedbackDelegate` on the view, not on the SparkScan mode.
5. **Dispose cleanly** — call `sparkScan.removeListener(...)` and close any `StreamController`s from the parent state's `dispose()`. The platform view tears itself down with the `State`.
6. **Camera permission** — iOS needs `NSCameraUsageDescription` in `Info.plist`. Android runtime permission is requested with `permission_handler`.
7. **Symbologies** — only enable the ones the app actually needs — each extra symbology adds processing time.
8. **Settings order** — configure `SparkScanSettings` before constructing `SparkScan(settings: settings)`. Use `sparkScan.applySettings(settings)` to change them at runtime.
9. **SDK version** — `DataCaptureContext.initialize` is available from v7+; `SparkScan({settings})` constructor is the v8 form (v6 used `SparkScan.forSettings` — see `references/migration.md`).
10. **Lifecycle observer** — add `WidgetsBindingObserver` and re-request camera permission from `didChangeAppLifecycleState` when the app resumes; users commonly revoke camera access from system settings.
