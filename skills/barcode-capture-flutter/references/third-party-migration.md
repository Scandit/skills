# Migrating from a Third-Party Scanner to BarcodeCapture (Flutter)

## Migration principles

- **Authority.** When this guide and the API reference disagree, trust the API reference — and a runtime check in the user's project — over this guide. Say which source you followed and why in the summary.
- **Behaviour changes.** Never present a visual or behaviour change (new default, different overlay look, changed feedback, changed scan timing) as a 1:1 rename. List each one in the summary as a judgment call the user must confirm.
- **Compatibility layer.** When the scanning code sits behind a shared scanner library or wrapper that other code calls, keep that library's public API frozen (same types, method names, callbacks) and replace only the third-party scanner calls underneath with Scandit ones.
- **Preserve, never invent.** Keep the app's own model, list, dedupe, clear and navigation logic. Do not add symbologies, symbol counts or filters the original did not have; do not silently drop a feature (flag it instead).

This guide covers replacing a third-party scanner — most commonly **`mobile_scanner`** (ML Kit), or **`google_mlkit_barcode_scanning`** fed by the **`camera`** plugin — with Scandit **`BarcodeCapture`** in a Flutter app. Use it when the app scans one barcode at a time and owns its camera UI. If the app is a "scan, add to a list, keep scanning" screen with no custom camera UI, `sparkscan-flutter` is usually a better fit.

For the full BarcodeCapture API and integration steps, also read `references/integration.md`. This guide focuses on the *delta* from the third-party plugin.

## Step 1: Identify the third-party scanner

Search the project for the plugin import and its types:

- `mobile_scanner`: `MobileScannerController`, the `MobileScanner` widget, `onDetect`, `controller.barcodes` (stream), `BarcodeFormat`, `DetectionSpeed`, `toggleTorch`, `switchCamera`, `errorBuilder`, `autoStart`, `start()`/`stop()`.
- `google_mlkit_barcode_scanning` + `camera`: `BarcodeScanner`, `processImage`, `InputImage`, `CameraController`, `startImageStream`.
- `flutter_barcode_scanner` / `qr_code_scanner`: single-shot scanners; same target.
- Multiple barcodes per frame genuinely needed (loop over all detections, live highlights)? Use `matrixscan-batch-flutter` instead; BarcodeCapture reports one `newlyRecognizedBarcode` per callback.

> **Name collisions.** If a third-party import must stay in the same file, disambiguate: `import 'package:mobile_scanner/mobile_scanner.dart' hide BarcodeCapture;` (mobile_scanner has its own `BarcodeCapture` result class). Scandit core exports `Rect`, `Size`, `Point`, `Brush`; give the Scandit import a prefix or `hide` them when the file also uses Flutter's `dart:ui` `Rect`/`Size`. The barcode barrel exports `ScannedBarcode` and `ScannedItem`; if an app model has the same name, import with `hide` or a prefix. Preferably remove the third-party types entirely.

## Step 2: Remove the third-party plugin

1. Delete the dependency from `pubspec.yaml` once nothing imports it (keep it if a gallery/still-image path stays, see Step 8).
2. Remove its import and all of its types from the screen.
3. Add `scandit_flutter_datacapture_barcode` (pulls in core) and `permission_handler`. Run `flutter pub get`.

## Step 3: Map the scanned formats to Scandit symbologies

Map **only** the formats the app actually scanned; fewer symbologies means better speed and accuracy.

| mobile_scanner / ML Kit `BarcodeFormat` | Scandit `Symbology` |
|---|---|
| `ean13`, `upcA` | `Symbology.ean13Upca` (UPC-A is reported as EAN-13/UPC-A) |
| `ean8` | `Symbology.ean8` |
| `upcE` | `Symbology.upce` |
| `code39` / `code93` / `code128` | `Symbology.code39` / `code93` / `code128` |
| `itf` | `Symbology.interleavedTwoOfFive` |
| `codabar` | `Symbology.codabar` |
| `qrCode` | `Symbology.qr` (**not** `qrCode`) |
| `dataMatrix` / `aztec` / `pdf417` | `Symbology.dataMatrix` / `aztec` / `pdf417` |

**"All formats" (no `formats:` argument, `BarcodeFormat.all`, `allowsAll` config).** Do not guess a list and do not invent `activeSymbolCounts`. Search the project for what the app really consumes (product codes, QR payload parsers, backend validation) and enable exactly those. If nothing narrows it, enable the common retail and logistics set and add a summary line "symbologies were not narrowed by the original; confirm this list". A config-driven app keeps its config; convert the config values to `Symbology` at one place.

`DetectionSpeed` maps to `settings.codeDuplicateFilter` (a `Duration`): `noDuplicates` → `const Duration(seconds: -1)` (report each code once), `normal` → about `Duration(milliseconds: 500)`, `unrestricted` → `Duration.zero`. Mention the chosen value as a judgment call.

## Step 4: Replace the detection callback with `didScan`

`onDetect(BarcodeCapture)` / `controller.barcodes.listen` becomes `BarcodeCaptureListener.didScan`; read `session.newlyRecognizedBarcode?.data` instead of `capture.barcodes[i].rawValue`. Move the body of the old handler into it unchanged: dedupe set, list, `setState` (guard with `mounted`), navigation, haptics, async lookups. `didUpdateSession` is a required empty override. Do not iterate `capture.barcodes`; BarcodeCapture delivers one barcode per callback.

Result fields: `rawValue` / `displayValue` → `barcode.data` (`String?`); `rawBytes` → `barcode.rawData` (a `String`, not `List<int>`); `format` → `barcode.symbology` (`Symbology`; app models that stored `BarcodeFormat` now store `Symbology`); `boundingBox` / `corners` → `barcode.location`. Display a symbology name with `SymbologyDescription.forSymbology(symbology).readableName`.

**Scan once and return (`Navigator.pop(context, value)`):** set `barcodeCapture.isEnabled = false` before popping so a second callback cannot pop twice.
**Stop, look up, resume (`controller.stop()` ... `start()`):** disable the mode (`isEnabled = false`), do the async work, then re-enable (`isEnabled = true`); keep the camera on unless the original turned it off.

```dart
@override
Future<void> didScan(BarcodeCapture barcodeCapture, BarcodeCaptureSession session,
    Future<FrameData?> Function() getFrameData) async {
  final value = session.newlyRecognizedBarcode?.data;
  if (value == null) return;
  barcodeCapture.isEnabled = false;
  if (mounted) Navigator.pop(context, value);
}
```

Do not hold `session` outside the callback.

## Step 5: Replace the preview widget with `DataCaptureView` + overlay

`MobileScanner(controller: ..., onDetect: ...)` becomes `DataCaptureView.forContext(dataCaptureContext)` (the `DataCaptureContext`, not the `BuildContext`) used as a widget (inside the same `SizedBox`/`Stack`/`Expanded` the original used), with a `BarcodeCaptureOverlay(barcodeCapture)` added via `addOverlay`. Keep the app's surrounding UI (bottom sheets, glow, painters, buttons) as is; set `overlay.brush = Brush.transparent` only if the app drew its own highlight.

**`errorBuilder` / permission and camera-error UI.** Scandit has no `errorBuilder`. Keep the original error widget and show it in two cases: permission denied (Step 6) and `Camera.atPosition(...)` returning `null` (no camera). Do not delete the branch.

## Step 6: Camera, permission, torch, switch, lifecycle

mobile_scanner and `camera` asked for permission implicitly; Scandit does not, so **always add a `permission_handler` request** before turning the camera on. Complete working shape (compiled against 8.6.1):

```dart
class _ScannerPageState extends State<ScannerPage>
    with WidgetsBindingObserver
    implements BarcodeCaptureListener, FrameSourceListener {
  late final DataCaptureContext _context;
  late final BarcodeCapture _barcodeCapture;
  late final DataCaptureView _captureView;
  Camera? _camera;
  CameraPosition _position = CameraPosition.worldFacing;
  bool _torchOn = false;
  bool _permissionDenied = false;
  bool _cameraUnavailable = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _context = DataCaptureContext.forLicenseKey('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
    final settings = BarcodeCaptureSettings()
      ..enableSymbologies({Symbology.ean13Upca, Symbology.code128, Symbology.qr});
    _barcodeCapture = BarcodeCapture(settings)..addListener(this);
    _context.addMode(_barcodeCapture);
    _captureView = DataCaptureView.forContext(_context);
    _captureView.addOverlay(BarcodeCaptureOverlay(_barcodeCapture));
    _initCamera();
  }

  Future<void> _initCamera() async {
    final status = await Permission.camera.request();
    if (!mounted) return;
    if (!status.isGranted) {
      setState(() => _permissionDenied = true);
      return;
    }
    await _useCamera(Camera.atPosition(_position));
  }

  // Returns false when no camera exists at that position; a failed switch keeps the current one.
  Future<bool> _useCamera(Camera? next) async {
    if (next == null) {
      if (_camera == null && mounted) setState(() => _cameraUnavailable = true);
      return false;
    }
    final previous = _camera;
    previous?.removeListener(this);
    await previous?.switchToDesiredState(FrameSourceState.off);
    _camera = next; // dispose() turns off whatever is current, even mid-setup
    await next.applySettings(BarcodeCapture.createRecommendedCameraSettings());
    if (!mounted) return false;
    next.addListener(this);
    await _context.setFrameSource(next);
    if (!mounted) return false;
    _barcodeCapture.isEnabled = true;
    await next.switchToDesiredState(FrameSourceState.on);
    if (!mounted) await next.switchToDesiredState(FrameSourceState.off);
    return true;
  }

  void _toggleTorch() {
    _torchOn = !_torchOn;
    _camera?.desiredTorchState = _torchOn ? TorchState.on : TorchState.off;
  }

  Future<void> _switchCamera() async {
    final target = _position == CameraPosition.worldFacing
        ? CameraPosition.userFacing
        : CameraPosition.worldFacing;
    if (await _useCamera(Camera.atPosition(target))) _position = target;
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (_permissionDenied) return;
    _camera?.switchToDesiredState(
        state == AppLifecycleState.resumed ? FrameSourceState.on : FrameSourceState.off);
  }

  @override
  void didChangeState(FrameSource frameSource, FrameSourceState newState) {}

  @override
  Widget build(BuildContext context) => Scaffold(
        body: _permissionDenied || _cameraUnavailable // or the original errorBuilder widget
            ? Center(child: Text(_permissionDenied ? 'Camera permission denied' : 'No camera available'))
            : _captureView,
      );

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _barcodeCapture.removeListener(this);
    _barcodeCapture.isEnabled = false;
    _camera?.removeListener(this);
    _camera?.switchToDesiredState(FrameSourceState.off);
    _context.removeMode(_barcodeCapture);
    super.dispose();
  }
  // didScan / didUpdateSession: Step 4.
}
```

Rules this encodes:

- **Wire torch and camera-switch controls.** If the original had torch/switch buttons (`toggleTorch`, `switchCamera`, a `ToggleFlashlightButton(controller: ...)` helper), connect them to `_toggleTorch` / `_switchCamera`; never pass the old controller or `_camera ?? Object()` placeholders. If a helper widget needs the controller, change its constructor to take callbacks.
- **Camera positions are `CameraPosition.worldFacing` / `CameraPosition.userFacing`** (not `back`/`front`). `Camera.defaultCamera` is world-facing. `desiredTorchState` takes `TorchState.on`/`off` and needs the camera attached to the context.
- **Autostart.** `autoStart: false` + `start()` becomes "call `switchToDesiredState(on)` when the original called `start()`". Applying camera settings is `await camera.applySettings(BarcodeCapture.createRecommendedCameraSettings())`.
- **Lifecycle.** mobile_scanner paused itself; add the `WidgetsBindingObserver` shown above (respect the original's `_isNavigating`/`isScanning` flags before resuming).
- **Full teardown, in this order:** `removeListener`, `isEnabled = false`, camera off, `removeMode`. Stopping only the camera leaves the mode attached.
- Bind `Camera.defaultCamera` to a local before a null check; `camera!` on a field is flagged by the analyzer.

## Step 7: Preserve scan-area logic

- **Fixed "scan box" via `boundingBox` overlap tests** (ML Kit) → `settings.locationSelection = RectangularLocationSelection.withSize(SizeWithUnit(DoubleWithUnit(0.75, MeasureUnit.fraction), DoubleWithUnit(0.28, MeasureUnit.fraction)))`. The semantics differ (the code must be inside the region, not 70% overlapping); flag it as a judgment call.
- **Hit-testing a barcode yourself** → `session.newlyRecognizedBarcode.location` (a `Quadrilateral` with `topLeft`/`topRight`/`bottomLeft`/`bottomRight` `Point`s in **camera-frame** coordinates). Convert it with `await captureView.viewQuadrilateralForFrameQuadrilateral(location)` before comparing with a scan box or painter laid out in the view.
- **Per-frame quality gates and throttles** (blur checks, 300 ms throttles) have no BarcodeCapture equivalent: Scandit processes frames itself. Say they were removed and why; do not drop them silently.

## Step 8: ML Kit + `camera` pipelines

For `CameraController` + `startImageStream` + `InputImage.fromBytes` + `BarcodeScanner.processImage`: delete the whole frame-conversion path (plane bytes, rotation, metadata). `Camera` + `BarcodeCapture` replaces camera init, the stream and the decoder; the screen's consumer widget then renders `DataCaptureView` instead of `CameraPreview(cameraController)`, so expose the view (or keep the widget) and update that contract. Keep the controller's public status/notifier API frozen and publish results from `didScan`.

**Gallery / still-image decode** (`InputImage.fromFilePath`, `image_picker`) has **no BarcodeCapture path**; BarcodeCapture only reads camera frames. Keep that function on `google_mlkit_barcode_scanning` (leave the dependency), or flag it as unsupported in the summary. Never replace it with an error status silently.

## Step 9: Verify and fix

Run `dart analyze` on the migrated file (or `flutter analyze`) and fix every error and warning (unused imports, `camera!` on a promotable field, ambiguous imports, `undefined_*`) before finishing. Check no `mobile_scanner`, `controller`, `onDetect` or `rawValue` reference or new `TODO` is left.

## Step 10: Setup checklist & summary

**Setup checklist:**
1. Remove `mobile_scanner` from `pubspec.yaml` (unless a gallery path stays); add `scandit_flutter_datacapture_barcode` and `permission_handler`, then run `flutter pub get`.
2. Add `NSCameraUsageDescription` to `ios/Runner/Info.plist`. On Android the plugin declares the manifest permission; the screen requests it at runtime.
3. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with your key (see **Licence key** in `SKILL.md`).
4. Ensure `main()` calls `WidgetsFlutterBinding.ensureInitialized()` then `await ScanditFlutterDataCaptureBarcode.initialize()` before `runApp(...)`.

**Summary**: list what was removed and added, the format→symbology mapping, and every judgment call (duplicate filter, region semantics, dropped quality gates, kept gallery path, symbologies not narrowed). Do not list code that was already correct.

## API reference

- BarcodeCapture API: https://docs.scandit.com/data-capture-sdk/flutter/barcode-capture/api.html
- Get Started: https://docs.scandit.com/sdks/flutter/barcode-capture/get-started/
