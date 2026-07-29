import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_tracking.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

/// Legacy MatrixScan screen written against the Scandit SDK v6 MatrixScan API
/// (BarcodeTracking*). Use this fixture for version-migration evals
/// (v6 BarcodeTracking -> v7 BarcodeBatch rename, and v7 -> v8 constructor change).
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen>
    with WidgetsBindingObserver
    implements BarcodeTrackingListener {

  final DataCaptureContext _context =
      DataCaptureContext.forLicenseKey(licenseKey);
  Camera? _camera = Camera.defaultCamera;
  late BarcodeTracking _barcodeTracking;
  late DataCaptureView _captureView;

  final List<String> scanResults = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    // v6 hand-rolled camera settings.
    final cameraSettings = CameraSettings()
      ..preferredResolution = VideoResolution.uhd4k;
    _camera?.applySettings(cameraSettings);

    _checkPermission();

    final captureSettings = BarcodeTrackingSettings()
      ..enableSymbologies({
        Symbology.ean13Upca,
        Symbology.code128,
      });

    // v6 factory constructor — mode is added to the context automatically.
    _barcodeTracking =
        BarcodeTracking.forContext(_context, captureSettings)
          ..addListener(this);

    _captureView = DataCaptureView.forContext(_context);

    _captureView.addOverlay(
      BarcodeTrackingBasicOverlay(
        _barcodeTracking,
        style: BarcodeTrackingBasicOverlayStyle.frame,
      ),
    );

    if (_camera != null) {
      _context.setFrameSource(_camera!);
    }
    _barcodeTracking.isEnabled = true;
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
    BarcodeTracking barcodeTracking,
    BarcodeTrackingSession session,
    Future<FrameData> getFrameData(),
  ) async {
    for (final trackedBarcode in session.addedTrackedBarcodes) {
      final data = trackedBarcode.barcode.data;
      if (data != null && !scanResults.contains(data)) {
        scanResults.add(data);
      }
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _barcodeTracking.removeListener(this);
    _barcodeTracking.isEnabled = false;
    _camera?.switchToDesiredState(FrameSourceState.off);
    _context.removeAllModes();
    super.dispose();
  }
}
