// Pre-migration v6 BarcodeCapture Flutter integration.
// Uses v6 API surface: DataCaptureContext.forLicenseKey, BarcodeCapture.forContext
// factory, manual ScanIntention setting, and no recommendedCameraSettings.
// The skill should migrate this to v7 or v8.

// ignore_for_file: deprecated_member_use

import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

class ScannerBloc implements BarcodeCaptureListener {
  final DataCaptureContext dataCaptureContext =
      DataCaptureContext.forLicenseKey(licenseKey);
  late final BarcodeCapture barcodeCapture;
  late final Camera? camera;
  late final DataCaptureView captureView;

  ScannerBloc() {
    final settings = BarcodeCaptureSettings()
      ..enableSymbologies({Symbology.ean13Upca, Symbology.code128})
      // v6: ScanIntention.manual was the implicit default — projects often
      // set it explicitly. v7 default is ScanIntention.smart.
      ..scanIntention = ScanIntention.manual
      // v6: composite types were enabled by default; v7 requires explicit opt-in.
      ..enabledCompositeTypes = {CompositeType.a, CompositeType.b};

    settings.enableSymbologiesForCompositeTypes({CompositeType.a, CompositeType.b});

    // v6 / early v7: BarcodeCapture.forContext factory — removed in v8.
    barcodeCapture = BarcodeCapture.forContext(dataCaptureContext, settings);
    barcodeCapture.addListener(this);

    camera = Camera.defaultCamera;
    // v6: VideoResolution.auto preset — deprecated in v8.
    final cameraSettings = CameraSettings()
      ..preferredResolution = VideoResolution.auto;
    camera?.applySettings(cameraSettings);
    if (camera != null) dataCaptureContext.setFrameSource(camera!);

    captureView = DataCaptureView.forContext(dataCaptureContext);
    BarcodeCaptureOverlay.withBarcodeCaptureForView(barcodeCapture, captureView);
  }

  @override
  Future<void> didScan(
    BarcodeCapture barcodeCapture,
    BarcodeCaptureSession session,
    Future<FrameData?> Function() getFrameData,
  ) async {
    final barcode = session.newlyRecognizedBarcode;
    if (barcode == null) return;
    debugPrint('Scanned: ${barcode.data}');
  }

  @override
  Future<void> didUpdateSession(
    BarcodeCapture barcodeCapture,
    BarcodeCaptureSession session,
    Future<FrameData?> Function() getFrameData,
  ) async {}
}

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});
  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage> {
  final ScannerBloc _bloc = ScannerBloc();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scanner')),
      body: _bloc.captureView,
    );
  }
}
