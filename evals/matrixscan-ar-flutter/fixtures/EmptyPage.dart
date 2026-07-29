// Empty starter page for the MatrixScan AR Flutter integration eval.
// The skill should fill in the BLoC (BarcodeArListener), page widget
// with providers (BarcodeArHighlightProvider), and main() plugin initialization.

import 'package:flutter/material.dart';

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});

  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('MatrixScan AR')),
      body: const Center(
        child: Text('BarcodeAr will go here'),
      ),
    );
  }
}
