import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_batch.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

/// Fully integrated MatrixScan Batch screen.
/// The screen implements BarcodeBatchListener and BarcodeBatchBasicOverlayListener.
/// Use this fixture when the eval asks to extend or modify existing BarcodeBatch integration.
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
        Symbology.code128,
      });

    _barcodeBatch = BarcodeBatch(captureSettings)
      ..addListener(this);

    _captureView = DataCaptureView.forContext(_context);

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
        'Tracked: ${trackedBarcode.barcode.data} (${trackedBarcode.barcode.symbology})',
      );
    }
  }

  @override
  Brush? brushForTrackedBarcode(
    BarcodeBatchBasicOverlay overlay,
    TrackedBarcode trackedBarcode,
  ) {
    return null; // use default brush
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
