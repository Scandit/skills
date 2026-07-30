// Pre-migration v7 BarcodeCapture Flutter integration.
// Uses v7 API surface: DataCaptureContext.forLicenseKey (still valid in v7 and v8),
// BarcodeCapture.forContext factory (deprecated in v7, removed in v8),
// and VideoResolution.auto (deprecated in v8).

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
      ..enableSymbologies({
        Symbology.ean13Upca,
        Symbology.code128,
        Symbology.qr,
      });

    // v7: BarcodeCapture.forContext still works but is deprecated.
    // v8: replaced with BarcodeCapture(settings) + dataCaptureContext.addMode.
    barcodeCapture = BarcodeCapture.forContext(dataCaptureContext, settings);
    barcodeCapture.addListener(this);

    camera = Camera.defaultCamera;
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
