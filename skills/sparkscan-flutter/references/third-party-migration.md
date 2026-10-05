# Migrating from a Third-Party Scanner to SparkScan (Flutter)

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm. Replacing a full-screen camera preview with SparkScan's trigger button and mini preview is always one of them.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and replace only the third-party scanner calls underneath with Scandit ones.
- **Preserve, never invent.** Keep the app's own model, list, dedupe, clear and navigation logic. Do not add symbologies or filters the original did not have; do not silently drop a feature (flag it instead).

This guide covers replacing a third-party scanner — most commonly **`mobile_scanner`** (ML Kit), or **`google_mlkit_barcode_scanning`** with the **`camera`** plugin — with Scandit **SparkScan** (`SparkScanView`) in a Flutter app.

For the full SparkScan API and integration steps, also read `references/integration.md`. This guide focuses on the *delta* from the third-party plugin.

## Step 1: Decide whether SparkScan fits

- **SparkScan fits** a screen that scans one code at a time and either continues ("scan, add to a list, keep scanning") or returns once, and whose camera UI is just the preview plus a few buttons.
- **Use `barcode-capture-flutter` instead** (read its `references/third-party-migration.md`) when the screen has a custom camera UI that must stay: own painter or scan-box overlay, region-of-interest logic, a bespoke preview layout, or camera ownership in a shared controller class. Say so in one line and continue with that skill.
- Several barcodes per frame genuinely needed (loop over all detections, live highlights)? Use `matrixscan-batch-flutter`. SparkScan reports one `newlyRecognizedBarcode` per callback.

Identify the plugin by its imports and types: `MobileScannerController`, the `MobileScanner` widget, `onDetect`, `controller.barcodes`, `BarcodeFormat`, `DetectionSpeed`, `toggleTorch`, `switchCamera`, `errorBuilder`, `start()`/`stop()`; or `BarcodeScanner`, `processImage`, `InputImage`, `CameraController`, `startImageStream`.

> **Name collisions.** `mobile_scanner` exports its own `BarcodeCapture`; if a third-party import must stay, use `hide BarcodeCapture`. Scandit core exports `Rect`, `Size`, `Point`, `Brush`: prefix or `hide` them when the file also uses `dart:ui` types. The barcode barrel exports `ScannedBarcode` and `ScannedItem`; if an app model has the same name and is imported from another file, use `hide` or an import prefix. Preferably remove the third-party types entirely.

## Step 2: Remove the third-party plugin

1. Delete the dependency from `pubspec.yaml` once nothing imports it (keep it if a gallery/still-image path stays, see Step 7).
2. Remove its import and types (`MobileScannerController`, `MobileScanner`, `onDetect`, `BarcodeFormat`).
3. Add `scandit_flutter_datacapture_barcode` (pulls in core) and `permission_handler`; run `flutter pub get`.

## Step 3: Map formats to symbologies

Map **only** the formats the app scanned.

| `BarcodeFormat` | Scandit `Symbology` |
|---|---|
| `ean13`, `upcA` | `Symbology.ean13Upca` |
| `ean8` / `upcE` | `Symbology.ean8` / `Symbology.upce` |
| `code39` / `code93` / `code128` | `Symbology.code39` / `code93` / `code128` |
| `itf` / `codabar` | `Symbology.interleavedTwoOfFive` / `Symbology.codabar` |
| `qrCode` | `Symbology.qr` (**not** `qrCode`) |
| `dataMatrix` / `aztec` / `pdf417` | `Symbology.dataMatrix` / `aztec` / `pdf417` |

**"All formats" (no `formats:` argument).** Do not guess a list or invent symbol counts. Search the project for what the app consumes (parsers, backend checks) and enable exactly those; if nothing narrows it, enable the common retail and logistics set and flag "symbologies were not narrowed by the original; confirm this list". Symbologies go on `SparkScanSettings.enableSymbologies({...})`.

`DetectionSpeed` maps to `settings.codeDuplicateFilter` (`Duration`): `noDuplicates` → `const Duration(seconds: -1)`, `normal` → about 500 ms, `unrestricted` → `Duration.zero`. List the chosen value as a judgment call.

## Step 4: Replace the callback with `SparkScanListener.didScan`

`onDetect` / `controller.barcodes.listen` becomes `SparkScanListener.didScan`; read `session.newlyRecognizedBarcode?.data` instead of `capture.barcodes[i].rawValue`. Move the old handler body in unchanged: dedupe `Set`, list, model, `setState` (guard with `mounted`), async lookups, navigation. `didUpdateSession` is a required empty override. Do not iterate a barcode list.

Result fields: `rawValue` / `displayValue` → `barcode.data` (`String?`); `rawBytes` → `barcode.rawData` (a `String`, not `List<int>`); `format` → `barcode.symbology` (`Symbology`; app models that stored `BarcodeFormat` now store `Symbology`); `boundingBox` / `corners` → `barcode.location`. Display a symbology name with `SymbologyDescription.forSymbology(symbology).readableName`.

- **Scan and continue** (running list, dedupe, clear): nothing else; SparkScan keeps scanning.
- **Scan once and return (`Navigator.pop(context, value)`):** pause the view first, then pop, so a second callback cannot pop twice (`await _view?.pauseScanning()`).
- **Stop, look up, resume:** `pauseScanning()`, do the async work, then `startScanning()`.

## Step 5: Replace the preview with `SparkScanView`

`SparkScanView` **wraps** the screen's existing body widget; the camera preview widget (`MobileScanner`, `CameraPreview`) is deleted and the rest of the page (list, summary, buttons) becomes the `child`. Create the view in `build`, keep a reference for `pauseScanning`/`startScanning`, and wrap it in `SafeArea`:

```dart
class _ScannerPageState extends State<ScannerPage> implements SparkScanListener {
  late final DataCaptureContext _context;
  late final SparkScan _sparkScan;
  SparkScanView? _view;
  bool _permissionDenied = false;
  final List<ScannedItem> _scannedItems = [];
  final Set<String> _seenValues = {};

  @override
  void initState() {
    super.initState();
    _context = DataCaptureContext.forLicenseKey('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
    final settings = SparkScanSettings()
      ..enableSymbologies({Symbology.ean13Upca, Symbology.code128, Symbology.qr})
      ..codeDuplicateFilter = const Duration(milliseconds: 500);
    _sparkScan = SparkScan(settings: settings)..addListener(this);
    _requestPermission();
  }

  Future<void> _requestPermission() async {
    final status = await Permission.camera.request();
    if (!status.isGranted && mounted) setState(() => _permissionDenied = true);
  }

  @override
  Widget build(BuildContext context) {
    final view = SparkScanView.forContext(_buildBody(), _context, _sparkScan, SparkScanViewSettings())
      ..torchControlVisible = true
      ..cameraSwitchButtonVisible = true;
    _view = view;
    final body = _permissionDenied ? const Center(child: Text('Camera permission denied')) : view;
    return Scaffold(appBar: AppBar(title: const Text('Scanner')), body: SafeArea(child: body));
  }

  @override
  void dispose() {
    _sparkScan.removeListener(this);
    _sparkScan.isEnabled = false;
    super.dispose();
  }
  // didScan / didUpdateSession / _buildBody: the original body, unchanged.
}
```

Imports: `scandit_flutter_datacapture_barcode.dart`, `scandit_flutter_datacapture_spark_scan.dart` (SparkScan classes), `scandit_flutter_datacapture_core.dart`, and `permission_handler`.

## Step 6: Permission, torch, camera switch, errors, lifecycle

- **Permission.** mobile_scanner asked implicitly; Scandit does not. Always add `await Permission.camera.request()` before the first scan; when denied, render the original error/placeholder widget instead of the view.
- **Torch and camera switch** are SparkScanView controls (`torchControlVisible`, `cameraSwitchButtonVisible`); SparkScan owns the camera, so there is no `Camera` object to drive. Delete the app's own torch/switch buttons and say so in the summary; if they must stay, the screen needs `barcode-capture-flutter` instead (Step 1).
- **`errorBuilder`** has no equivalent: keep its widget for the permission-denied branch and say it replaces the old camera-error callback.
- **Lifecycle.** The view manages the camera on pause/resume; remove the old `WidgetsBindingObserver` start/stop code unless it guards app state. Respect any `_isNavigating` flag by calling `pauseScanning()`/`startScanning()` around navigation.
- **Teardown** in `dispose`: `removeListener`, then `isEnabled = false`; dispose your BLoC/stream owner as usual.

## Step 7: ML Kit + `camera` pipelines

`CameraController` + `startImageStream` + `InputImage` + `processImage`: delete the whole frame-conversion and decode path; SparkScan owns camera and decoding. Keep the owner class's public status/notifier API and publish results from `didScan`; the consumer widget must now render `SparkScanView` instead of `CameraPreview`. `boundingBox` region checks (scan box) have no SparkScan equivalent; use `barcode-capture-flutter` (location selection) if the region logic must stay.

**Gallery / still-image decode** (`InputImage.fromFilePath`, `image_picker`) has **no SparkScan path**; keep it on `google_mlkit_barcode_scanning` (leave the dependency) or flag it as unsupported. Never replace it with an error status silently.

## Step 8: Verify and fix

Run `dart analyze` on the migrated file (or `flutter analyze`) and fix every error and warning before finishing. Check no `mobile_scanner`, `controller`, `onDetect` or `rawValue` reference or new `TODO` is left.

## Step 9: Setup checklist & summary

**Setup checklist:**
1. Remove `mobile_scanner` from `pubspec.yaml` (unless a gallery path stays); add `scandit_flutter_datacapture_barcode` and `permission_handler`, then run `flutter pub get`.
2. Add `NSCameraUsageDescription` to `ios/Runner/Info.plist`; on Android the runtime request is in the screen.
3. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key (see **Licence key** in `SKILL.md`).
4. Ensure `main()` calls `WidgetsFlutterBinding.ensureInitialized()` then `await ScanditFlutterDataCaptureBarcode.initialize()` before `runApp(...)`.

**Summary**: list what was removed (`mobile_scanner` controller, widget, `onDetect`) and added (SparkScan mode, listener, `SparkScanView`), the format→symbology mapping, and every judgment call (new scanning UI, duplicate filter, removed torch/switch buttons, dropped error UI, kept gallery path, symbologies not narrowed). Do not list code that was already correct.

## API reference

- SparkScan API: https://docs.scandit.com/data-capture-sdk/flutter/barcode-capture/api.html
- Get Started: https://docs.scandit.com/sdks/flutter/sparkscan/get-started/
