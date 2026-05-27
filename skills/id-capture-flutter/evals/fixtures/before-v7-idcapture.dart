// Existing ID Capture integration written against SDK v7.
// Uses the v7 APIs that were removed/reshaped in v8:
//   - settings.scannerType = FullDocumentScanner()   (renamed/wrapped -> settings.scanner)
//   - AamvaBarcodeVerifier.create(context) + verifier.verify(...) (removed)
// The skill should migrate this to the v8 API.

import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';
import 'package:scandit_flutter_datacapture_id/scandit_flutter_datacapture_id.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

class IdScanPage extends StatefulWidget {
  const IdScanPage({super.key});

  @override
  State<IdScanPage> createState() => _IdScanPageState();
}

class _IdScanPageState extends State<IdScanPage>
    with WidgetsBindingObserver
    implements IdCaptureListener {
  final DataCaptureContext _context =
      DataCaptureContext.forLicenseKey(licenseKey);
  late IdCapture _idCapture;
  late DataCaptureView _captureView;
  AamvaBarcodeVerifier? _verifier;
  Camera? _camera = Camera.defaultCamera;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    final settings = IdCaptureSettings();
    settings.acceptedDocuments.add(DriverLicense(IdCaptureRegion.us));
    // v7 scanner assignment (removed in v8):
    settings.scannerType = FullDocumentScanner();

    _idCapture = IdCapture(settings)..addListener(this);
    _captureView = DataCaptureView.forContext(_context);
    _captureView.addOverlay(IdCaptureOverlay(_idCapture));
    _context.setMode(_idCapture);

    _camera?.applySettings(IdCapture.createRecommendedCameraSettings());
    _context.setFrameSource(_camera!);
    _camera?.switchToDesiredState(FrameSourceState.on);
    _idCapture.isEnabled = true;

    _initVerifier();
  }

  Future<void> _initVerifier() async {
    // v7 standalone verifier (removed in v8):
    _verifier = await AamvaBarcodeVerifier.create(_context);
  }

  @override
  Future<void> didCaptureId(IdCapture idCapture, CapturedId capturedId) async {
    idCapture.isEnabled = false;
    // v7 verification call (removed in v8):
    final AamvaBarcodeVerificationResult result =
        await _verifier!.verify(capturedId);
    debugPrint('AAMVA all checks passed: ${result.allChecksPassed}');
    idCapture.isEnabled = true;
  }

  @override
  Future<void> didRejectId(
      IdCapture idCapture, CapturedId? rejectedId, RejectionReason reason) async {
    debugPrint('Rejected: $reason');
  }

  @override
  Widget build(BuildContext context) => _captureView;
}
