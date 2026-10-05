// Stubs for HackErSEx3/barcode_scanner_app models/services/widgets/screens (no scanning code).
// NOTE: BarcodeFormatConfig references the ML Kit BarcodeFormat enum because the screen
// passes its values straight to the scanner; this stub therefore needs the same plugin.
import 'package:flutter/material.dart';
import 'package:google_mlkit_barcode_scanning/google_mlkit_barcode_scanning.dart';

class BarcodeFormatConfig {
  const BarcodeFormatConfig({
    this.allowedFormats = const [BarcodeFormat.all],
    this.presetLabel = 'All',
  });
  final List<BarcodeFormat> allowedFormats;
  final String presetLabel;
  bool accepts(BarcodeFormat format) =>
      allowedFormats.contains(BarcodeFormat.all) ||
      allowedFormats.contains(format);
}

class ScannedBarcode {
  ScannedBarcode({
    required this.value,
    required this.format,
    required this.scannedAt,
    this.rawBytes,
  });
  final String value;
  final String format;
  final DateTime scannedAt;
  final String? rawBytes;
}

class BarcodeCacheService {
  BarcodeCacheService._();
  static final BarcodeCacheService instance = BarcodeCacheService._();
  Future<String?> save(ScannedBarcode barcode) async => null;
}

class ScannerOverlay extends StatelessWidget {
  const ScannerOverlay({
    super.key,
    required this.scanBox,
    required this.barcodes,
    required this.allowedFormats,
  });
  final Rect scanBox;
  final List<Barcode> barcodes;
  final Set<String> allowedFormats;
  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});
  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});
  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
