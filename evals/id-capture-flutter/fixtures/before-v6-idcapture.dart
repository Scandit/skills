// Existing ID Capture integration written against SDK v6.
// Uses the v6 APIs that were removed at v7:
//   - settings.supportedDocuments = IdDocumentType.<...> bitmask   (removed -> acceptedDocuments)
//   - settings.supportedSides = SupportedSides.frontAndBack         (removed -> scanner)
// The skill should migrate this to the list-based v7+ model and the v8 scanner form.

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
  Camera? _camera = Camera.defaultCamera;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    final settings = IdCaptureSettings();
    // v6 document selection via bitmask (removed in v7):
    settings.supportedDocuments =
        IdDocumentType.idCardViz | IdDocumentType.passportMrz;
    // v6 side selection (removed in v7):
    settings.supportedSides = SupportedSides.frontAndBack;

    _idCapture = IdCapture(settings)..addListener(this);
    _captureView = DataCaptureView.forContext(_context);
    _captureView.addOverlay(IdCaptureOverlay(_idCapture));
    _context.setMode(_idCapture);

    _camera?.applySettings(IdCapture.createRecommendedCameraSettings());
    _context.setFrameSource(_camera!);
    _camera?.switchToDesiredState(FrameSourceState.on);
    _idCapture.isEnabled = true;
  }

  @override
  Future<void> didCaptureId(IdCapture idCapture, CapturedId capturedId) async {
    idCapture.isEnabled = false;
    // v6 document type access (removed in v7):
    debugPrint('Type: ${capturedId.documentType}');
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
