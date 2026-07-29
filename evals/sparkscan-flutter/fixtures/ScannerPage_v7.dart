// Pre-migration v7 SparkScan Flutter integration.
// Uses v7 API surface: DataCaptureContext.forLicenseKey (still valid in v7),
// SparkScan.withSettings (deprecated in v7, removed in v8),
// and v7 SparkScanView property names.

// ignore_for_file: deprecated_member_use

import 'package:flutter/material.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_spark_scan.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

class ScannerBloc implements SparkScanListener {
  final DataCaptureContext dataCaptureContext =
      DataCaptureContext.forLicenseKey(licenseKey);
  late final SparkScan sparkScan;
  late final SparkScanViewSettings sparkScanViewSettings;

  ScannerBloc() {
    final settings = SparkScanSettings()
      ..enableSymbologies({
        Symbology.ean13Upca,
        Symbology.code128,
        Symbology.qr,
      });

    // v7: SparkScan.withSettings still works but is deprecated.
    // v8: replaced with SparkScan(settings: settings) constructor.
    sparkScan = SparkScan.withSettings(settings);
    sparkScan.addListener(this);

    sparkScanViewSettings = SparkScanViewSettings();
  }

  @override
  Future<void> didScan(
    SparkScan sparkScan,
    SparkScanSession session,
    Future<FrameData> Function() getFrameData,
  ) async {
    final barcode = session.newlyRecognizedBarcode;
    if (barcode == null) return;
    debugPrint('Scanned: ${barcode.data}');
  }

  @override
  Future<void> didUpdateSession(
    SparkScan sparkScan,
    SparkScanSession session,
    Future<FrameData> Function() getFrameData,
  ) async {}
}

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});
  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage> {
  final ScannerBloc _bloc = ScannerBloc();

  @override
  Widget build(BuildContext context) {
    final sparkScanView = SparkScanView.forContext(
      const Center(child: Text('Scanning...')),
      _bloc.dataCaptureContext,
      _bloc.sparkScan,
      _bloc.sparkScanViewSettings,
    )
      ..torchControlVisible = true
      ..barcodeFindButtonVisible = true
      ..triggerButtonCollapsedColor = const Color(0xFFFF5500)
      ..triggerButtonExpandedColor = const Color(0xFFFF5500)
      ..triggerButtonAnimationColor = const Color(0xFFFF5500)
      ..triggerButtonTintColor = const Color(0xFFFFFFFF);

    return Scaffold(
      appBar: AppBar(title: const Text('Scanner')),
      body: SafeArea(child: sparkScanView),
    );
  }
}
