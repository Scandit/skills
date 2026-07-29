// Basic MatrixScan AR integration already in place (Flutter, BLoC pattern).
// Evals in this group add features on top of this baseline (custom highlights,
// info annotations, responsive annotations, custom annotation providers, etc.).

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_ar.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

class TrackedProduct {
  final String data;
  final Symbology symbology;
  TrackedProduct(this.data, this.symbology);
}

class ScannerBloc implements BarcodeArListener {
  final DataCaptureContext dataCaptureContext =
      DataCaptureContext.forLicenseKey(licenseKey);
  final Camera camera = Camera.defaultCamera!;
  late final BarcodeAr barcodeAr;
  late final BarcodeArViewSettings barcodeArViewSettings;
  late final CameraSettings cameraSettings;

  final List<TrackedProduct> trackedProducts = [];
  final StreamController<TrackedProduct> _tracksController =
      StreamController<TrackedProduct>.broadcast();

  Stream<TrackedProduct> get tracked => _tracksController.stream;

  ScannerBloc() {
    final settings = BarcodeArSettings()
      ..enableSymbologies({
        Symbology.ean13Upca,
        Symbology.code128,
        Symbology.qr,
      });

    barcodeAr = BarcodeAr(settings);
    barcodeAr.addListener(this);

    barcodeArViewSettings = BarcodeArViewSettings();
    cameraSettings = BarcodeAr.createRecommendedCameraSettings();

    dataCaptureContext.setFrameSource(camera);
  }

  void startCapturing() {
    camera.switchToDesiredState(FrameSourceState.on);
  }

  void stopCapturing() {
    camera.switchToDesiredState(FrameSourceState.off);
  }

  @override
  Future<void> didUpdateSession(
    BarcodeAr barcodeAr,
    BarcodeArSession session,
    Future<FrameData> Function() getFrameData,
  ) async {
    for (final tracked in session.addedTrackedBarcodes) {
      final barcode = tracked.barcode;
      if (barcode.data == null) continue;
      final product = TrackedProduct(barcode.data!, barcode.symbology);
      trackedProducts.add(product);
      _tracksController.add(product);
    }
  }

  Future<BarcodeArHighlight?> highlightForBarcode(Barcode barcode) async {
    return BarcodeArRectangleHighlight(barcode)
      ..brush = Brush(
        const Color(0x6600FFFF),
        const Color(0xFF00FFFF),
        1.0,
      );
  }

  void dispose() {
    barcodeAr.removeListener(this);
    _tracksController.close();
  }
}

class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});

  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage>
    with WidgetsBindingObserver
    implements BarcodeArHighlightProvider {

  final ScannerBloc _bloc = ScannerBloc();
  BarcodeArView? _barcodeArView;
  final List<TrackedProduct> _items = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _barcodeArView = BarcodeArView.forModeWithViewSettingsAndCameraSettings(
      _bloc.dataCaptureContext,
      _bloc.barcodeAr,
      _bloc.barcodeArViewSettings,
      _bloc.cameraSettings,
    )..highlightProvider = this;
    _bloc.tracked.listen((product) {
      setState(() => _items.add(product));
    });
    _requestCameraPermission();
  }

  Future<void> _requestCameraPermission() async {
    final status = await Permission.camera.request();
    if (!mounted) return;
    if (status.isGranted) _bloc.startCapturing();
  }

  @override
  Future<BarcodeArHighlight?> highlightForBarcode(Barcode barcode) {
    return _bloc.highlightForBarcode(barcode);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('MatrixScan AR')),
      body: Stack(
        children: [
          _barcodeArView!,
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: Container(
              color: Colors.black54,
              padding: const EdgeInsets.all(8),
              child: Text(
                '${_items.length} barcodes tracked',
                style: const TextStyle(color: Colors.white),
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        _requestCameraPermission();
        break;
      default:
        _bloc.stopCapturing();
        break;
    }
  }

  @override
  void dispose() {
    _bloc.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
}
