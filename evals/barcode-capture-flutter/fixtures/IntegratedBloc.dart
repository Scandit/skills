// Basic BarcodeCapture integration already in place (Flutter, v8 API, BLoC pattern).
// Evals in this group add features on top of this baseline (custom feedback,
// viewfinder, location selection, lifecycle disposal, scan intention, etc.).

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode.dart';
import 'package:scandit_flutter_datacapture_barcode/scandit_flutter_datacapture_barcode_capture.dart';
import 'package:scandit_flutter_datacapture_core/scandit_flutter_datacapture_core.dart';

const String licenseKey = '-- ENTER YOUR SCANDIT LICENSE KEY HERE --';

class ScannedProduct {
  final String data;
  final Symbology symbology;
  ScannedProduct(this.data, this.symbology);
}

class HomeBloc implements BarcodeCaptureListener {
  final DataCaptureContext dataCaptureContext =
      DataCaptureContext.forLicenseKey(licenseKey);
  late final BarcodeCapture barcodeCapture;
  late final Camera? camera;
  late final DataCaptureView captureView;
  late final BarcodeCaptureOverlay overlay;

  final List<ScannedProduct> scannedProducts = [];
  final StreamController<ScannedProduct> _scansController =
      StreamController<ScannedProduct>.broadcast();

  Stream<ScannedProduct> get scanned => _scansController.stream;

  HomeBloc() {
    final settings = BarcodeCaptureSettings()
      ..enableSymbologies({
        Symbology.ean13Upca,
        Symbology.code128,
        Symbology.qr,
      });

    barcodeCapture = BarcodeCapture(settings);
    barcodeCapture.addListener(this);
    dataCaptureContext.addMode(barcodeCapture);

    camera = Camera.defaultCamera;
    camera?.applySettings(BarcodeCapture.createRecommendedCameraSettings());
    if (camera != null) dataCaptureContext.setFrameSource(camera!);

    captureView = DataCaptureView.forContext(dataCaptureContext);
    overlay = BarcodeCaptureOverlay(barcodeCapture);
    captureView.addOverlay(overlay);
  }

  @override
  Future<void> didScan(
    BarcodeCapture barcodeCapture,
    BarcodeCaptureSession session,
    Future<FrameData?> Function() getFrameData,
  ) async {
    final barcode = session.newlyRecognizedBarcode;
    if (barcode == null) return;
    final product = ScannedProduct(barcode.data ?? '', barcode.symbology);
    scannedProducts.add(product);
    _scansController.add(product);
  }

  @override
  Future<void> didUpdateSession(
    BarcodeCapture barcodeCapture,
    BarcodeCaptureSession session,
    Future<FrameData?> Function() getFrameData,
  ) async {}
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with WidgetsBindingObserver {
  final HomeBloc _bloc = HomeBloc();
  final List<ScannedProduct> _items = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _start();
    _bloc.scanned.listen((product) {
      setState(() => _items.add(product));
    });
  }

  Future<void> _start() async {
    await Permission.camera.request();
    _bloc.barcodeCapture.isEnabled = true;
    await _bloc.camera?.switchToDesiredState(FrameSourceState.on);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scanner')),
      body: _bloc.captureView,
    );
  }

  @override
  void dispose() {
    _bloc.camera?.switchToDesiredState(FrameSourceState.off);
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
}
