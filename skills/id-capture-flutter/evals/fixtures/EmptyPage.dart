// Empty starter page for the ID Capture Flutter integration eval.
// The skill should fill in plugin initialization in main(), the
// DataCaptureContext + IdCaptureSettings + IdCapture wiring, the
// IdCaptureListener callbacks, and the DataCaptureView + camera lifecycle.

import 'package:flutter/material.dart';

class IdScanPage extends StatefulWidget {
  const IdScanPage({super.key});

  @override
  State<IdScanPage> createState() => _IdScanPageState();
}

class _IdScanPageState extends State<IdScanPage> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan ID')),
      body: const Center(
        child: Text('ID Capture will go here'),
      ),
    );
  }
}
