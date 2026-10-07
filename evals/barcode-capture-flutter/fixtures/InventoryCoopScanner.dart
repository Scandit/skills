// SOURCE: https://github.com/lachouettecoop/InventoryCoop/blob/28fc307e288667758a63a43ed157a969543f42e6/lib/barcode_scanner.dart
// LICENSE: MIT (full notice: THIRD_PARTY_NOTICES.md)
// PLUGIN: mobile_scanner ^6.0.2
import 'dart:async';

import 'package:flutter/material.dart';
// STUBBED: inventory_coop/scanner_button_widgets.dart + scanner_error_widget.dart -> stubs/InventoryCoopScanner_stubs.dart
import 'stubs/InventoryCoopScanner_stubs.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

class BarcodeScanner extends StatefulWidget {
  const BarcodeScanner({super.key});

  @override
  State<BarcodeScanner> createState() => _BarcodeScannerState();
}

class _BarcodeScannerState extends State<BarcodeScanner> with WidgetsBindingObserver {
  final MobileScannerController controller = MobileScannerController(
    autoStart: false,
    torchEnabled: false,
    useNewCameraSelector: true,
  );

  StreamSubscription<Object?>? _subscription;
  bool scanned = false;

  void _handleBarcode(BarcodeCapture barcodes) {
    if (mounted) {
      setState(() {
        if (!scanned) {
          if (barcodes.barcodes.isNotEmpty) {
            Navigator.pop(context, barcodes.barcodes.first.displayValue);
          } else {
            Navigator.pop(context, 'Aucun Code-Bare trouvé');
          }
          scanned = true;
        }
      });
    }
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    _subscription = controller.barcodes.listen(_handleBarcode);

    unawaited(controller.start());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scanner')),
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          MobileScanner(
            controller: controller,
            errorBuilder: (context, error, child) {
              return ScannerErrorWidget(error: error);
            },
            fit: BoxFit.contain,
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: Container(
              alignment: Alignment.bottomCenter,
              height: 100,
              color: Colors.black.withValues(alpha: 0.4),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  ToggleFlashlightButton(controller: controller),
                  SwitchCameraButton(controller: controller),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Future<void> dispose() async {
    WidgetsBinding.instance.removeObserver(this);
    unawaited(_subscription?.cancel());
    _subscription = null;
    super.dispose();
    await controller.dispose();
  }
}
