// SOURCE: https://github.com/0xteamCookie/echo/blob/1bebf45403148097ac3b54a0ff5926b8eb3a638b/lib/screens/scanner_screen.dart
// LICENSE: MIT (full notice: THIRD_PARTY_NOTICES.md)
// PLUGIN: mobile_scanner 7.2.0
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
// STUBBED: ../auth/auth_service.dart, ../main.dart (BeaconColors) (+AppState, UserRole) -> stubs/EchoScannerScreen_stubs.dart
import 'stubs/EchoScannerScreen_stubs.dart';

class ScannerScreen extends StatefulWidget {
  const ScannerScreen({super.key});

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> {
  final MobileScannerController controller = MobileScannerController(
    formats: const [BarcodeFormat.qrCode],
  );

  bool isScanning = true;

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  void _onDetect(BarcodeCapture capture) async {
    final List<Barcode> barcodes = capture.barcodes;

    for (final barcode in barcodes) {
      final token = barcode.rawValue;
      if (token != null) {
        print('Raw Scanned Data: $token');

        controller.stop();
        setState(() => isScanning = false);

        bool isValid = await AuthService.verifyAndSaveToken(token);

        if (isValid) {
          AppState().role.value = UserRole.rescuer;

          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text(
                  'Login Successful! ✅ Switched to Rescuer Dashboard',
                ),
              ),
            );
            Navigator.of(context).pop(true);
          }
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Invalid or Expired QR Code ❌')),
          );
          controller.start();
          setState(() => isScanning = true);
        }
        break;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan Login Token'),
        backgroundColor: BeaconColors.background,
        elevation: 0,
      ),
      body: MobileScanner(controller: controller, onDetect: _onDetect),
    );
  }
}
