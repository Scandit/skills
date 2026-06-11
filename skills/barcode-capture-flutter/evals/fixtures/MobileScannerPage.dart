// Existing barcode scanning built on the mobile_scanner plugin (Flutter ML Kit wrapper).
// Scans EAN-13, Code 128 and QR, de-duplicates by raw value, and shows a running
// summary of everything scanned in the current session.

import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

class ScannedItem {
  final String value;
  final BarcodeFormat format;
  ScannedItem(this.value, this.format);
}

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});

  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage> {
  final MobileScannerController _controller = MobileScannerController(
    formats: const [
      BarcodeFormat.ean13,
      BarcodeFormat.code128,
      BarcodeFormat.qrCode,
    ],
    detectionSpeed: DetectionSpeed.normal,
  );

  // Running summary of unique scans in this session.
  final List<ScannedItem> _scannedItems = [];
  final Set<String> _seenValues = {};

  void _onDetect(BarcodeCapture capture) {
    for (final barcode in capture.barcodes) {
      final value = barcode.rawValue;
      if (value == null) continue;

      // De-duplicate: ignore a code we've already recorded this session.
      if (_seenValues.contains(value)) continue;
      _seenValues.add(value);

      setState(() {
        _scannedItems.add(ScannedItem(value, barcode.format));
      });
    }
  }

  void _clear() {
    setState(() {
      _scannedItems.clear();
      _seenValues.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scanner'),
        actions: [
          IconButton(onPressed: _clear, icon: const Icon(Icons.delete)),
        ],
      ),
      body: Column(
        children: [
          SizedBox(
            height: 300,
            child: MobileScanner(
              controller: _controller,
              onDetect: _onDetect,
            ),
          ),
          Expanded(
            child: ListView.builder(
              itemCount: _scannedItems.length,
              itemBuilder: (context, index) {
                final item = _scannedItems[index];
                return ListTile(
                  title: Text(item.value),
                  subtitle: Text(item.format.name),
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(8),
            child: Text('Total scanned: ${_scannedItems.length}'),
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
