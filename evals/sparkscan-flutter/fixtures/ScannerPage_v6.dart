// Pre-migration v6 SparkScan Flutter integration.
// Uses v6 API surface: DataCaptureContext.forLicenseKey, a brush on the view,
// and v6 SparkScanView property names. The skill should migrate this to v7 or v8.

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
      ..enableSymbologies({Symbology.ean13Upca, Symbology.code128});

    // v6: SparkScan.forSettings / SparkScan.withSettings factory — replaced in v8.
    sparkScan = SparkScan.withSettings(settings);
    sparkScan.addListener(this);

    // v6: defaultHandMode on the view settings — removed in v7.
    sparkScanViewSettings = SparkScanViewSettings()
      ..defaultHandMode = SparkScanHandMode.right;
  }

  @override
  Future<void> didScan(
    SparkScan sparkScan,
    SparkScanSession session,
    Future<FrameData> Function() getFrameData,
  ) async {
    final barcode = session.newlyRecognizedBarcodes.isNotEmpty
        ? session.newlyRecognizedBarcodes.first
        : null;
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
      // v6 properties — all of these need migration to v7.
      ..torchButtonVisible = true
      ..fastFindButtonVisible = true
      ..handModeButtonVisible = false
      ..soundModeButtonVisible = false
      ..hapticModeButtonVisible = false
      ..shouldShowScanAreaGuides = false
      ..captureButtonBackgroundColor = const Color(0xFFFF5500)
      ..captureButtonActiveBackgroundColor = const Color(0xFFAA3300)
      ..captureButtonTintColor = const Color(0xFFFFFFFF)
      ..startCapturingText = 'START'
      ..stopCapturingText = 'STOP'
      ..resumeCapturingText = 'RESUME'
      ..scanningCapturingText = 'SCANNING'
      ..brush = Brush(
          const Color(0xFF00FF00), const Color(0xFF00FF00), 1);

    return Scaffold(
      appBar: AppBar(title: const Text('Scanner')),
      body: SafeArea(child: sparkScanView),
    );
  }
}
