import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_label/scandit_flutter_datacapture_label.dart';

const licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ScanditFlutterDataCaptureBarcode.initialize();
  await ScanditFlutterDataCaptureLabel.initialize();
  DataCaptureContext.initialize(licenseKey);
  runApp(const MaterialApp(home: ScanScreen()));
}

class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});
  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen>
    implements LabelCaptureValidationFlowExtendedListener {
  late final DataCaptureContext _context;
  late final Camera? _camera;
  late final LabelCapture _labelCapture;
  late final DataCaptureView _view;
  late final LabelCaptureValidationFlowOverlay _overlay;

  @override
  void initState() {
    super.initState();
    _context = DataCaptureContext.sharedInstance;
    _camera = Camera.defaultCamera;
    _camera?.applySettings(LabelCapture.createRecommendedCameraSettings());
    _context.setFrameSource(_camera);

    final barcode = CustomBarcodeBuilder()
        .setSymbologies({Symbology.ean13Upca, Symbology.code128})
        .isOptional(false)
        .build('Barcode');
    final expiry = ExpiryDateTextBuilder().isOptional(false).build('Expiry Date');
    final definition = LabelDefinitionBuilder()
        .addCustomBarcode(barcode)
        .addExpiryDateText(expiry)
        .build('Perishable Product');

    _labelCapture = LabelCapture.forContext(_context, LabelCaptureSettings([definition]));
    _view = DataCaptureView.forContext(_context);
    _overlay = LabelCaptureValidationFlowOverlay.withLabelCaptureForView(_labelCapture, _view);
    _overlay.listener = this;

    _camera?.switchToDesiredState(FrameSourceState.on);
    _labelCapture.isEnabled = true;
  }

  @override
  void didCaptureLabelWithFields(List<LabelField> fields) {
    final body = fields
        .map((f) => '${f.name}: ${f.barcode?.data ?? f.text ?? 'N/A'}')
        .join('\n');
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('LABEL CAPTURED'),
        content: Text(body),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('OK')),
        ],
      ),
    );
  }

  @override
  void didSubmitManualInputForField(LabelField field, String? oldValue, String newValue) {
    // User manually corrected a field value.
  }

  @override
  void dispose() {
    _overlay.listener = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(body: _view);
}
