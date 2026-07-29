// Empty starter page for the MatrixScan Count Flutter integration eval.
// The skill should fill in the BLoC (BarcodeCountListener, BarcodeCountViewListener,
// BarcodeCountViewUiListener), the page widget, and main() plugin initialization.

import 'package:flutter/material.dart';

class CountPage extends StatefulWidget {
  const CountPage({super.key});

  @override
  State<CountPage> createState() => _CountPageState();
}

class _CountPageState extends State<CountPage> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('MatrixScan Count')),
      body: const Center(
        child: Text('BarcodeCount will go here'),
      ),
    );
  }
}
