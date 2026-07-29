import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

/// Existing multi-barcode scanning screen built on the `mobile_scanner`
/// plugin (Google ML Kit under the hood). The app tracks several barcodes
/// in the live camera feed and keeps a deduplicated list of their values.
///
/// Use this fixture for third-party-migration evals (mobile_scanner -> BarcodeBatch).
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});

  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  final MobileScannerController _controller = MobileScannerController(
    detectionSpeed: DetectionSpeed.normal,
    formats: const [
      BarcodeFormat.ean13,
      BarcodeFormat.code128,
      BarcodeFormat.qrCode,
    ],
  );

  // Deduplicated set of scanned values, plus a display list.
  final Set<String> _seen = {};
  final List<String> scanResults = [];

  void _onDetect(BarcodeCapture capture) {
    for (final barcode in capture.barcodes) {
      final value = barcode.rawValue;
      if (value == null) continue;
      if (_seen.add(value)) {
        setState(() => scanResults.add(value));
        debugPrint('Detected ${barcode.format.name}: $value');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan')),
      body: Stack(
        children: [
          MobileScanner(
            controller: _controller,
            onDetect: _onDetect,
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: Text('${scanResults.length} scanned'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}
