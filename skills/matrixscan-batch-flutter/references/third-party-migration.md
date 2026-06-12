# Migrating from a Third-Party Scanner to MatrixScan Batch (Flutter)

This guide covers replacing a third-party multi-barcode scanner — most commonly the **`mobile_scanner`** plugin (Google ML Kit) — with Scandit **MatrixScan Batch (`BarcodeBatch`)** in a Flutter app. Use it when the project already scans (and ideally tracks) several barcodes at once and wants Scandit's tracking, AR overlays, and accuracy.

For the full BarcodeBatch API and integration steps, also read `references/integration.md`. This guide focuses on the *delta* from the third-party plugin.

## Step 1: Identify the third-party scanner

Search the project for the plugin import and its types:

- `mobile_scanner`: `import 'package:mobile_scanner/mobile_scanner.dart';`, `MobileScannerController`, the `MobileScanner` widget, `onDetect`, `BarcodeCapture` (mobile_scanner's *own* result class), `Barcode`, `BarcodeFormat`.
- `google_mlkit_barcode_scanning`: `BarcodeScanner`, `processImage`, `Barcode`, `BarcodeFormat`.
- `flutter_barcode_scanner` / `qr_code_scanner`: single-shot scanners — migrating these to *Batch* only makes sense if the app actually needs multi-barcode tracking; otherwise consider single-scan SparkScan/BarcodeCapture instead.

> **Name collision warning**: `mobile_scanner` exports a class literally named `BarcodeCapture` (its detection-result type), and Scandit's barcode SDK also defines `BarcodeCapture` (the single-scan mode). If any third-party symbol lingers in the same file as Scandit imports, disambiguate with an import prefix or `hide`, or — preferably — remove the third-party types entirely.

## Step 2: Remove the third-party plugin

1. Delete the third-party dependency from `pubspec.yaml` (e.g. `mobile_scanner:`) once the migration is complete.
2. Remove its import and all of its types from the screen (`MobileScannerController`, `MobileScanner`, `onDetect`, `BarcodeCapture`, `Barcode`, `BarcodeFormat`).
3. Add the Scandit dependency: `scandit_flutter_datacapture_barcode` (pulls in `scandit_flutter_datacapture_core` transitively) and `permission_handler`. Run `flutter pub get`.

## Step 3: Map the scanned formats to Scandit symbologies

mobile_scanner / ML Kit use a `BarcodeFormat` enum. Scandit uses `Symbology` (lowerCamelCase in Dart). Map only the formats the app actually scanned — enabling fewer symbologies improves performance and accuracy.

| mobile_scanner `BarcodeFormat` | Scandit `Symbology` |
|---|---|
| `ean13` | `Symbology.ean13Upca` |
| `ean8` | `Symbology.ean8` |
| `upcA` | `Symbology.ean13Upca` (UPC-A is reported under EAN-13/UPC-A) |
| `upcE` | `Symbology.upce` |
| `code39` | `Symbology.code39` |
| `code93` | `Symbology.code93` |
| `code128` | `Symbology.code128` |
| `itf` | `Symbology.interleavedTwoOfFive` |
| `codabar` | `Symbology.codabar` |
| `qrCode` | `Symbology.qr` (note: **`qr`**, not `qrCode`) |
| `dataMatrix` | `Symbology.dataMatrix` |
| `aztec` | `Symbology.aztec` |
| `pdf417` | `Symbology.pdf417` |

> **Gotcha**: the Scandit QR symbology is `Symbology.qr` — there is no `Symbology.qrCode`. UPC-A barcodes are delivered under `Symbology.ean13Upca`.

```dart
final captureSettings = BarcodeBatchSettings()
  ..enableSymbologies({
    Symbology.ean13Upca, // was BarcodeFormat.ean13
    Symbology.code128,   // was BarcodeFormat.code128
    Symbology.qr,        // was BarcodeFormat.qrCode
  });
```

## Step 4: Replace the detection callback with `didUpdateSession`

mobile_scanner pushes results through an `onDetect(BarcodeCapture capture)` callback, reading `capture.barcodes[i].rawValue`. With BarcodeBatch you implement `BarcodeBatchListener.didUpdateSession` and read `trackedBarcode.barcode.data`. Preserve the app's deduplication logic — BarcodeBatch reports the *added* set per frame, so dedup is naturally cheap, but keep the project's `Set`/`List` semantics intact.

**Before (mobile_scanner):**
```dart
void _onDetect(BarcodeCapture capture) {
  for (final barcode in capture.barcodes) {
    final value = barcode.rawValue;
    if (value == null) continue;
    if (_seen.add(value)) {
      setState(() => scanResults.add(value));
    }
  }
}
```

**After (BarcodeBatch):**
```dart
@override
Future<void> didUpdateSession(
  BarcodeBatch barcodeBatch,
  BarcodeBatchSession session,
  Future<FrameData> getFrameData(),
) async {
  for (final trackedBarcode in session.addedTrackedBarcodes) {
    final value = trackedBarcode.barcode.data;
    if (value == null) continue;
    if (_seen.add(value)) {
      setState(() => scanResults.add(value));
    }
  }
}
```

> Do not hold a reference to `session` or its collections outside the callback — copy what you need.

## Step 5: Replace the preview widget with `DataCaptureView` + overlay

mobile_scanner renders the camera with its `MobileScanner` widget. With Scandit, build a `DataCaptureView` from the context, attach a `BarcodeBatchBasicOverlay` (frame or dot highlights), and use the view as the screen body. See `references/integration.md` Steps 5–7.

```dart
_captureView = DataCaptureView.forContext(_context);
_captureView.addOverlay(
  BarcodeBatchBasicOverlay(_barcodeBatch, style: BarcodeBatchBasicOverlayStyle.frame),
);
```

## Step 6: Camera & lifecycle

mobile_scanner's `MobileScannerController` owned the camera, `start()`, `stop()`, and `dispose()`. With Scandit you own the camera explicitly:

- `Camera.defaultCamera`, then `camera.applySettings(BarcodeBatch.createRecommendedCameraSettings())` (static **method** on Flutter), and `dataCaptureContext.setFrameSource(camera)`.
- Start with `camera.switchToDesiredState(FrameSourceState.on)` after the permission is granted (request via `permission_handler`).
- On `dispose()`: `removeListener`, `isEnabled = false`, switch the camera off, and `dataCaptureContext.removeAllModes()`.

See `references/integration.md` Step 8 for the full lifecycle pattern.

## Step 7: Setup checklist & summary

After rewriting the file, show the user:

**Setup checklist:**
1. Remove `mobile_scanner` from `pubspec.yaml`; add `scandit_flutter_datacapture_barcode` and `permission_handler`, then run `flutter pub get`.
2. Add `NSCameraUsageDescription` to `ios/Runner/Info.plist` (iOS). On Android the plugin declares the manifest permission; request it at runtime with `permission_handler`.
3. Replace `'-- ENTER YOUR SCANDIT LICENSE KEY HERE --'` with a key from https://ssl.scandit.com.
4. Ensure `main()` calls `WidgetsFlutterBinding.ensureInitialized()` then `await ScanditFlutterDataCaptureBarcode.initialize()` before `runApp(...)`.

**Summary**: list what was removed (the `mobile_scanner` controller, widget, and `onDetect`) and what was added (the BarcodeBatch mode, listener, DataCaptureView + overlay, camera ownership), plus the format→symbology mapping you applied. Do not list code that was already correct.

## API reference

- BarcodeBatch API: https://docs.scandit.com/data-capture-sdk/flutter/barcode-capture/api.html
- MatrixScan Get Started: https://docs.scandit.com/sdks/flutter/matrixscan/get-started/
